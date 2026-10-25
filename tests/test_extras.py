import hashlib
from pathlib import Path

import pytest
from PIL import Image
import pymupdf as fitz

from zeste.engine import Engine, ConversionError, Cancelled
from zeste.extras import CHUNK, dispatch_extra


def run(tmp_path, source, operation, options=None, engine=None):
    dest = tmp_path / "result"
    dest.mkdir(exist_ok=True)
    assert dispatch_extra(engine or Engine(), [Path(source)], operation, options or {}, dest)
    return sorted(dest.iterdir())


@pytest.fixture
def picture(tmp_path):
    source = tmp_path / "été.png"
    Image.new("RGBA", (100, 80), (210, 80, 40, 255)).save(source)
    return source


@pytest.fixture(scope="module")
def media(tmp_path_factory):
    root = tmp_path_factory.mktemp("extras-media")
    engine = Engine()
    video = root / "silencieuse.mp4"
    audio = root / "son.wav"
    av = root / "avec-son.mp4"
    engine.ff(["-f", "lavfi", "-i", "color=c=red:s=160x120:r=10:d=2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", video])
    engine.ff(["-f", "lavfi", "-i", "sine=frequency=440:duration=2", audio])
    engine.ff(["-i", video, "-i", audio, "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-shortest", av])
    return video, audio, av


def frame_at(engine, source, seconds, dest):
    engine.ff(["-ss", str(seconds), "-i", source, "-frames:v", "1", dest])
    with Image.open(dest) as im:
        return im.convert("RGB").copy()


def test_unknown_operation_does_not_touch_inputs(tmp_path):
    assert dispatch_extra(None, [], "not-extra", {}, tmp_path) is False


def test_frame_rounding_background_and_original(picture, tmp_path):
    before = picture.read_bytes()
    out = run(tmp_path, picture, "frame_image", {"padding": 20, "radius": 15, "background": "#ffffff", "shadow": False})[0]
    with Image.open(out) as im:
        assert im.size == (140, 120)
        assert im.getpixel((0, 0)) == (255, 255, 255, 255)
        assert im.getpixel((20, 20)) == (255, 255, 255, 255)
        assert im.getpixel((70, 60)) == (210, 80, 40, 255)
    assert picture.read_bytes() == before


def test_frame_shadow_is_rendered(picture, tmp_path):
    out = run(tmp_path, picture, "frame_image", {"padding": 30, "radius": 12, "background": "#ffffff", "shadow": True, "shadow_offset": 8, "shadow_blur": 4, "shadow_opacity": 180})[0]
    with Image.open(out) as im:
        assert im.getpixel((80, 115))[0] < 230
        assert im.getpixel((0, 0))[0] == 255


@pytest.mark.parametrize("options", [{"padding": -1}, {"radius": 100}, {"shadow": "yes"}, {"background": "invalid"}, {"padding": float("nan")}, {"unsupported": 1}])
def test_frame_invalid_values_rejected(picture, tmp_path, options):
    with pytest.raises(ConversionError):
        run(tmp_path, picture, "frame_image", options)


def test_frame_rejects_animation(tmp_path):
    source = tmp_path / "animation.gif"
    Image.new("RGB", (20, 20), "red").save(source, save_all=True, append_images=[Image.new("RGB", (20, 20), "blue")], duration=100, loop=0)
    with pytest.raises(ConversionError, match="animées"):
        run(tmp_path, source, "frame_image")


@pytest.mark.parametrize("index", [0, 2])
def test_redaction_pixels_and_silent_or_audio_video(media, index, tmp_path):
    source = media[index]
    before = hashlib.sha256(source.read_bytes()).digest()
    out = run(tmp_path, source, "redact_video", {"x": 20, "y": 20, "width": 60, "height": 40, "start": .5, "end": 1.5})[0]
    engine = Engine()
    early = frame_at(engine, out, .2, tmp_path / "before.png")
    during = frame_at(engine, out, .8, tmp_path / "during.png")
    late = frame_at(engine, out, 1.7, tmp_path / "after.png")
    assert max(during.getpixel((40, 40))) <= 8
    assert early.getpixel((40, 40))[0] >= 240
    assert late.getpixel((40, 40))[0] >= 240
    assert during.getpixel((110, 90))[0] >= 240
    assert 1.9 <= engine.duration(out) <= 2.2
    assert hashlib.sha256(source.read_bytes()).digest() == before
    info = engine.media_info(out)
    assert info["video_streams"] == 1
    assert info["audio_streams"] == (0 if index == 0 else 1)


@pytest.mark.parametrize("options", [{"x": 150, "width": 60}, {"start": 1.5, "end": 1}, {"end": 3}, {"width": 20.5}, {"start": float("inf")}])
def test_redaction_invalid_range(media, tmp_path, options):
    with pytest.raises(ConversionError):
        run(tmp_path, media[0], "redact_video", options)
    assert not list((tmp_path / "result").iterdir())


def test_visualizer_contains_wave_and_audio(media, tmp_path):
    source = media[1]
    out = run(tmp_path, source, "visualizer", {"width": 320, "height": 180, "fps": 20, "color": "#ff5c00", "background": "#15151d"})[0]
    engine = Engine()
    frame = frame_at(engine, out, .5, tmp_path / "wave.png")
    assert frame.size == (320, 180)
    assert abs(frame.getpixel((0, 0))[0] - 21) < 8
    assert any(r > 120 and r > g * 1.3 and b < 80 for r, g, b in frame.get_flattened_data())
    info = engine.media_info(out)
    assert info["audio_streams"] == 1 and info["video_streams"] == 1
    assert 1.9 <= engine.duration(out) <= 2.2


@pytest.mark.parametrize("options", [{"width": 321}, {"color": "red;movie=bad"}, {"fps": 0}])
def test_visualizer_invalid_values(media, tmp_path, options):
    with pytest.raises(ConversionError):
        run(tmp_path, media[1], "visualizer", options)


@pytest.mark.parametrize("ext", ["jpg", "tiff"])
def test_image_metadata_roundtrip_preserves_pixels(tmp_path, ext):
    source = tmp_path / ("photo." + ext)
    Image.new("RGB", (60, 40), "#c34a51").save(source)
    before = source.read_bytes()
    out = run(tmp_path, source, "edit_metadata", {"author": "Zoé", "comment": "Essai été", "datetime": "2026:10:22 14:30:00"})[0]
    with Image.open(source) as original, Image.open(out) as edited:
        assert original.tobytes() == edited.tobytes()
        exif = edited.getexif()
        assert bytes(exif[40093]).decode("utf-16-le").rstrip("\0") == "Zoé"
        assert bytes(exif[40092]).decode("utf-16-le").rstrip("\0") == "Essai été"
        assert exif.get_ifd(34665)[37510] == b"UNICODE\0\xfe\xff" + "Essai été".encode("utf-16-be")
        assert exif[306] == "2026:10:22 14:30:00"
    assert source.read_bytes() == before


def test_image_metadata_replaces_existing_exif(tmp_path):
    source = tmp_path / "photo.jpg"
    exif = Image.Exif()
    exif[315] = "Old author"
    exif[270] = "Old comment"
    Image.new("RGB", (40, 30), "green").save(source, exif=exif)
    out = run(tmp_path, source, "edit_metadata", {"author": "New author", "comment": ""})[0]
    with Image.open(out) as edited:
        assert edited.getexif()[315] == "New author"
        assert 270 not in edited.getexif() and 40092 not in edited.getexif()
    assert out.read_bytes().count(b"Exif\x00\x00") == 1


def test_pdf_metadata_preserves_content(tmp_path):
    source = tmp_path / "document.pdf"
    with fitz.open() as doc:
        doc.new_page().insert_text((40, 40), "Texte original")
        doc.set_metadata({"author": "Ancien", "title": "Avant"})
        doc.save(source)
    before = source.read_bytes()
    out = run(tmp_path, source, "edit_metadata", {"author": "Zoé", "title": "Rapport", "subject": "Test"})[0]
    with fitz.open(out) as doc:
        assert doc.metadata["author"] == "Zoé"
        assert doc.metadata["title"] == "Rapport"
        assert doc.metadata["subject"] == "Test"
        assert "Texte original" in doc[0].get_text()
    assert source.read_bytes() == before


@pytest.mark.parametrize("index", [1, 2])
def test_media_metadata_roundtrip(media, tmp_path, index):
    source = media[index]
    before = source.read_bytes()
    out = run(tmp_path, source, "edit_metadata", {"author": "Zeste Test", "title": "Titre test", "comment": "Commentaire test"})[0]
    tags = Engine().ff(["-i", out, "-f", "ffmetadata", "-"])
    assert "artist=Zeste Test" in tags and "title=Titre test" in tags and "comment=Commentaire test" in tags
    assert source.read_bytes() == before


def test_unsupported_metadata_and_fields(picture, tmp_path):
    output=run(tmp_path,picture,'edit_metadata',{'author':'X'})[0]
    with Image.open(output) as im: assert im.text['Author']=='X'
    jpeg = tmp_path / "x.jpg"
    Image.new("RGB", (20, 20)).save(jpeg)
    with pytest.raises(ConversionError, match="non pris en charge"):
        run(tmp_path, jpeg, "edit_metadata", {"title": "X"})
    with pytest.raises(ConversionError, match="Date EXIF"):
        run(tmp_path, jpeg, "edit_metadata", {"datetime": "2026:02:31 12:00:00"})


def test_checksum_streaming_and_duplicate_names(tmp_path):
    source = tmp_path / "payload.bin"
    data = b"0123456789" * (CHUNK // 5)
    source.write_bytes(data)
    out = run(tmp_path, source, "checksum")[0]
    assert out.name.endswith(".sha256.txt")
    assert out.read_text(encoding="utf-8") == hashlib.sha256(data).hexdigest() + "  payload.bin\n"
    previous = out.read_bytes()
    outputs = run(tmp_path, source, "checksum")
    assert len(outputs) == 2 and out.read_bytes() == previous


def test_checksum_cancellation_during_stream_does_not_publish(tmp_path):
    source = tmp_path / "large.bin"
    source.write_bytes(b"x" * CHUNK * 3)
    class CancellingEngine(Engine):
        calls = 0
        def check(self):
            self.calls += 1
            if self.calls == 3:
                raise Cancelled("test")
    with pytest.raises(Cancelled):
        run(tmp_path, source, "checksum", engine=CancellingEngine())
    assert list((tmp_path / "result").iterdir()) == []
    assert source.stat().st_size == CHUNK * 3


def test_duplicate_file_and_directory_no_overwrite(tmp_path):
    source = tmp_path / "original.bin"
    source.write_bytes(b"original bytes")
    first = run(tmp_path, source, "duplicate")[0]
    first.write_bytes(b"already present, preserve me")
    outputs = run(tmp_path, source, "duplicate")
    assert len(outputs) == 2 and first.read_bytes() == b"already present, preserve me"
    assert any(p.read_bytes() == source.read_bytes() for p in outputs)
    directory = tmp_path / "tree"
    (directory / "nested").mkdir(parents=True)
    (directory / "nested/data.txt").write_text("nested content")
    (directory / "empty").mkdir()
    outputs = run(tmp_path, directory, "duplicate")
    copied = next(p for p in outputs if p.is_dir())
    assert (copied / "nested/data.txt").read_text() == "nested content"
    assert (copied / "empty").is_dir()


def test_duplicate_refuses_destination_inside_source(tmp_path):
    source = tmp_path / "tree"
    dest = source / "result"
    dest.mkdir(parents=True)
    with pytest.raises(ConversionError, match="hors du dossier"):
        dispatch_extra(Engine(), [source], "duplicate", {}, dest)
    assert list(dest.iterdir()) == []


def test_engine_dispatch_and_publication_integration(picture, tmp_path):
    output_dir = tmp_path / "published"
    engine = Engine(output_dir=output_dir)
    framed = Path(engine.execute([picture], "frame_image", {"radius": 10})[0])
    assert framed.parent == output_dir and framed.suffix == ".png"
    checksum = Path(engine.execute([picture], "checksum")[0])
    assert checksum.read_text(encoding="utf-8").startswith(hashlib.sha256(picture.read_bytes()).hexdigest())
    folder = tmp_path / "directory"
    folder.mkdir()
    (folder / "child.txt").write_text("copied")
    copied = Path(engine.execute([folder], "duplicate")[0])
    assert copied.parent == output_dir and (copied / "child.txt").read_text() == "copied"
    assert not list(output_dir.glob(".zeste-*"))
