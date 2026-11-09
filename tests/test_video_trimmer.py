import hashlib
import os
from pathlib import Path
import time
import pytest
from PySide6.QtCore import QCoreApplication, QEvent, Qt, QPoint
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from zeste.catalog import family, VIDEOS, VIDEO_OUTPUTS, operations
from zeste.engine import Engine, ConversionError
from zeste.video_trimmer import VideoTrimmer, ClipTimeline, TimeField, clock_text


@pytest.fixture(scope="module")
def video(tmp_path_factory):
    path = tmp_path_factory.mktemp("video-clips") / "Vidéo été & vacances.mp4"
    Engine().ff(["-f", "lavfi", "-i", "color=red:s=160x120:r=20:d=1.5", "-f", "lavfi", "-i", "color=blue:s=160x120:r=20:d=2.5",
        "-f", "lavfi", "-i", "sine=frequency=550:duration=4", "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]",
        "-map", "[v]", "-map", "2:a", "-c:v", "libx264", "-g", "60", "-pix_fmt", "yuv420p", "-c:a", "aac", path])
    return path


@pytest.mark.parametrize("ext", VIDEO_OUTPUTS)
def test_trim_each_export_format_preserves_duration_and_audio(video, ext, tmp_path):
    before = hashlib.sha256(video.read_bytes()).hexdigest()
    output = Path(Engine(output_dir=tmp_path).execute([video], "trim", {"start":1.7,"duration":.8,"output_format":ext})[0])
    info = Engine().media_info(output)
    assert output.suffix == "." + ext
    assert .65 <= info["duration"] <= 1.1
    assert info["video_streams"] == 1 and info["audio_streams"] == 1
    # Decode real pixels: the requested point is blue, between two keyframes.
    from PIL import Image
    frame = tmp_path / "first.png"
    Engine().ff(["-i",output,"-frames:v","1",frame])
    r,g,b = Image.open(frame).convert("RGB").getpixel((50,50))
    assert b > r+100 and b > g+100
    assert hashlib.sha256(video.read_bytes()).hexdigest() == before


@pytest.mark.parametrize("ext,codec,muxer", [
    ("mov","libx264",None),("mkv","libx264",None),("webm","libvpx-vp9",None),
    ("avi","mpeg4",None),("wmv","wmv2",None),("m4v","libx264",None),
    ("mpeg","mpeg2video",None),("ts","libx264","mpegts"),("mts","libx264","mpegts"),
    ("m2ts","libx264","mpegts"),("vob","mpeg2video",None),("flv","flv",None),
    ("3gp","mpeg4",None),("ogv","libtheora",None),("asf","wmv2",None)])
def test_trim_real_input_containers(video, ext, codec, muxer, tmp_path):
    source = tmp_path / ("source."+ext)
    args = ["-i", video,"-an","-c:v",codec]
    if muxer: args += ["-f",muxer]
    Engine().ff([*args,source])
    out = Engine(output_dir=tmp_path/"out").execute([source],"trim",{"start":1.7,"duration":.8,"output_format":"mp4"})[0]
    info = Engine().media_info(out)
    assert .65 <= info["duration"] <= 1.05 and info["video_streams"] == 1
    assert info["audio_streams"] == 0


def test_one_hour_video_extracts_one_minute_late_in_file(tmp_path):
    source = tmp_path/"une heure.mp4"
    Engine().ff(["-f","lavfi","-i","color=green:s=96x64:r=1:d=3600","-c:v","libx264","-preset","ultrafast",source])
    out = Engine().execute([source],"trim",{"start":3500,"duration":60,"output_format":"mp4"})[0]
    assert 59.9 <= Engine().duration(out) <= 60.1


@pytest.mark.parametrize("start,duration", [(-1,1),(0,0),(0,-1),(float("nan"),1),(0,float("inf")),(4,1),(3,2)])
def test_invalid_intervals_never_publish(video, start, duration, tmp_path):
    with pytest.raises(ConversionError):
        Engine(output_dir=tmp_path).execute([video],"trim",{"start":start,"duration":duration})
    assert not list(tmp_path.iterdir())


def test_optional_audio_and_no_overwrite(video, tmp_path):
    options = {"start":1.6,"duration":.5,"output_format":"mp4","keep_audio":False}
    first = Path(Engine(output_dir=tmp_path).execute([video],"trim",options)[0])
    contents = first.read_bytes()
    second = Path(Engine(output_dir=tmp_path).execute([video],"trim",options)[0])
    assert first != second and first.read_bytes() == contents
    assert Engine().media_info(first)["audio_streams"] == 0


def test_all_recognized_video_extensions_offer_trim():
    for ext in VIDEOS:
        assert family("test."+ext) == "video"
        assert "trim" in {op.id for op in operations(["test."+ext],"tools")}


@pytest.fixture(scope="module")
def app(tmp_path_factory):
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["ZESTE_CONFIG_DIR"] = str(tmp_path_factory.mktemp("clip-profile"))
    instance = QApplication.instance() or QApplication([])
    instance.setQuitOnLastWindowClosed(False)
    yield instance
    QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)


def until(predicate, timeout=15000):
    end = time.monotonic() + timeout/1000
    while time.monotonic() < end:
        if predicate(): return
        QTest.qWait(25)
    assert predicate()


def test_visual_dialog_load_seek_presets_play_export_and_cleanup(app, video):
    dialog = VideoTrimmer(video)
    frames = []
    dialog.decoder.frame.connect(lambda image,position: frames.append((image,position)))
    dialog.show()
    try:
        until(lambda:dialog.total > 0 and len(frames)>0)
        assert dialog.export_button.isEnabled() and dialog.total == 4000
        dialog.set_selection(1700,3500)
        until(lambda:len(frames)>1 and frames[-1][1]==1700)
        color = frames[-1][0].pixelColor(320,180)
        assert color.blue()>150 and color.red()<70
        dialog.set_length(60)
        assert dialog.end.value()==4 and dialog.start.value()==1.7
        dialog.end.setValue(1)
        assert 0 <= dialog.start.value()<dialog.end.value()
        dialog.set_selection(1700,2500)
        previous=len(frames)
        dialog.toggle_play()
        until(lambda:len(frames)>=previous+3)
        until(lambda:not dialog.decoder.playing)
        assert dialog.options()=={"start":1.7,"duration":.8,"output_format":"mp4","keep_audio":True}
        dialog.accept()
        assert dialog.result()==dialog.DialogCode.Accepted and dialog.decoder.process is None
        assert not dialog.seek_timer.isActive() and not dialog.probe_timeout.isActive()
    finally:
        dialog.shutdown(); dialog.deleteLater()


def test_time_fields_and_timeline_never_invert_selection(app):
    field=TimeField("Début")
    field.setValue(3661.125)
    assert field.text()=="01:01:01.125" and field.valueFromText("01:02:30.500")==3750.5
    assert clock_text(90000)=="25:00:00.000"
    timeline=ClipTimeline(); timeline.resize(700,80); timeline.set_range(3600000,1800000,1860000); timeline.show()
    changes=[]; timeline.rangeChanged.connect(lambda start,end:changes.append((start,end)))
    QTest.mousePress(timeline,Qt.MouseButton.LeftButton,pos=QPoint(round(timeline.x(timeline.start)),35))
    QTest.mouseMove(timeline,QPoint(timeline.width()-16,35))
    QTest.mouseRelease(timeline,Qt.MouseButton.LeftButton,pos=QPoint(timeline.width()-16,35))
    assert changes and all(0<=a<b<=3600000 for a,b in changes)
    timeline.close(); timeline.deleteLater(); field.deleteLater()


def test_bad_file_disables_export_and_closes_cleanly(app, tmp_path):
    source=tmp_path/"broken.mp4"; source.write_bytes(b"not a video")
    dialog=VideoTrimmer(source);dialog.show()
    until(lambda:dialog.preview.text()=="Cette vidéo ne peut pas être ouverte.")
    assert not dialog.export_button.isEnabled()
    dialog.reject(); dialog.deleteLater()


@pytest.mark.parametrize("ext,codec,muxer", [("ts","libx264","mpegts"),("ogv","libtheora","ogg")])
def test_preview_transport_and_ogg_seek_then_play(app, video, tmp_path, ext, codec, muxer):
    source=tmp_path/("preview."+ext)
    Engine().ff(["-i",video,"-an","-c:v",codec,"-f",muxer,source])
    dialog=VideoTrimmer(source);frames=[]
    dialog.decoder.frame.connect(lambda image,position:frames.append((image,position)))
    dialog.show()
    try:
        until(lambda:dialog.total>0)
        dialog.set_selection(1700,2500)
        until(lambda:frames and frames[-1][1]==1700)
        assert frames[-1][0].pixelColor(320,180).blue()>150
        previous=len(frames)
        dialog.toggle_play()
        until(lambda:len(frames)>=previous+3)
        dialog.reject()
        assert dialog.decoder.process is None
    finally:
        dialog.shutdown();dialog.deleteLater()


def test_main_window_opens_visual_trimmer_and_queues_options(app, video, monkeypatch):
    from zeste.ui import MainWindow
    window=MainWindow();window.watcher.timer.stop();window.tray.hide()
    try:
        window.add_files([str(video)])
        assert window.quick_edit.text()=="Découper la vidéo" and window.quick_edit.isEnabled()
        def dialog_run(dialog):
            assert isinstance(dialog, VideoTrimmer)
            until(lambda:dialog.total>0)
            dialog.set_selection(1000,2000)
            dialog.accept()
            return True
        monkeypatch.setattr(window,"run_dialog",dialog_run)
        monkeypatch.setattr(window,"start_next",lambda:None)
        window.quick_edit.click()
        assert len(window.pending)==1 and window.pending[0][1]=="trim"
        assert window.pending[0][2]["duration"]==1
    finally:
        app.removeEventFilter(window);window.hide();window.deleteLater()
