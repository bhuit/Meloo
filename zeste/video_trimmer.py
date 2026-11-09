"""Visual clip selection using the bundled FFmpeg, without another media runtime."""
from pathlib import Path
import math
import re
from PySide6.QtCore import Qt, QObject, QProcess, QTimer, Signal, QRectF
from PySide6.QtGui import QImage, QPixmap, QPainter, QColor, QPen, QValidator
from PySide6.QtWidgets import (QApplication, QDialog, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QDoubleSpinBox, QComboBox, QCheckBox, QDialogButtonBox)
from .catalog import VIDEO_OUTPUTS
from .engine import Engine, ffmpeg_path, media_seek_args, fast_media_seek


def clock_text(seconds):
    ms = max(0, round(seconds * 1000))
    seconds, fraction = divmod(ms, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}.{fraction:03}"


class TimeField(QDoubleSpinBox):
    """Hours can exceed 23; the widget edits elapsed time, not time of day."""
    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.setDecimals(3)
        self.setRange(0, 365 * 86400)
        self.setSingleStep(.1)
        self.setKeyboardTracking(False)
        self.setMinimumWidth(170)
        self.setAccessibleName(name)
        self.setToolTip("Heures:minutes:secondes.millisecondes, ou nombre de secondes")

    def textFromValue(self, value):
        return clock_text(value)

    def valueFromText(self, text):
        parts = text.strip().replace(",", ".").split(":")
        try:
            if not 1 <= len(parts) <= 3: return self.value()
            values = [float(part) for part in parts]
            if any(not math.isfinite(x) or x < 0 for x in values): return self.value()
            if len(values) > 1 and any(x >= 60 for x in values[1:]): return self.value()
            return sum(x * 60 ** i for i, x in enumerate(reversed(values)))
        except ValueError:
            return self.value()

    def validate(self, text, position):
        value = text.strip().replace(",", ".")
        valid = bool(re.fullmatch(r"\d+(?::[0-5]?\d){0,2}(?:\.\d{1,3})?", value))
        state = QValidator.State.Acceptable if valid else QValidator.State.Intermediate if re.fullmatch(r"[\d:.]*", value) else QValidator.State.Invalid
        return state, text, position


class ClipTimeline(QWidget):
    rangeChanged = Signal(int, int)
    seekRequested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.total, self.start, self.end, self.position = 1, 0, 1, 0
        self.dragging = None
        self.setMinimumHeight(78)
        self.setAccessibleName("Extrait à conserver : déplacer les poignées de début et de fin")
        self.setToolTip("Déplace les deux poignées pour choisir l’extrait. Clique dans la barre pour voir une image.")
        self.setMouseTracking(True)

    def x(self, value):
        return 16 + value / max(1, self.total) * max(1, self.width()-32)

    def time_at(self, x):
        return round(max(0, min(1, (x-16)/max(1, self.width()-32))) * self.total)

    def set_range(self, total, start, end):
        self.total, self.start, self.end = total, start, end
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        melina = QApplication.instance().property("color_style") == "melina"
        accent = QColor("#438368" if melina else "#f99560")
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#b8c9bd" if melina else "#344653"))
        p.drawRoundedRect(QRectF(16, 28, self.width()-32, 22), 9, 9)
        p.setBrush(accent)
        p.drawRoundedRect(QRectF(self.x(self.start), 28, max(2, self.x(self.end)-self.x(self.start)), 22), 6, 6)
        for value in (self.start, self.end):
            p.drawRoundedRect(QRectF(self.x(value)-6, 21, 12, 36), 4, 4)
        p.setPen(QPen(QColor("#152e26" if melina else "white"), 2))
        p.drawLine(round(self.x(self.position)), 15, round(self.x(self.position)), 61)
        p.setPen(self.palette().windowText().color())
        p.drawText(QRectF(16, 59, 145, 18), Qt.AlignmentFlag.AlignLeft, "00:00:00")
        p.drawText(QRectF(self.width()-170, 59, 154, 18), Qt.AlignmentFlag.AlignRight, clock_text(self.total/1000))

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or not self.isEnabled(): return
        point = event.position().x()
        if min(abs(point-self.x(self.start)), abs(point-self.x(self.end))) <= 14:
            self.dragging = "start" if abs(point-self.x(self.start)) <= abs(point-self.x(self.end)) else "end"
        else:
            self.dragging = "seek"
            self.seekRequested.emit(self.time_at(point))

    def mouseMoveEvent(self, event):
        if not self.dragging: return
        value = self.time_at(event.position().x())
        gap = min(100, self.total)
        if self.dragging == "start": self.start = min(value, self.end-gap)
        elif self.dragging == "end": self.end = max(value, self.start+gap)
        else:
            self.seekRequested.emit(value)
            return
        self.rangeChanged.emit(self.start, self.end)
        self.update()

    def mouseReleaseEvent(self, event):
        self.dragging = None


class PreviewDecoder(QObject):
    frame = Signal(QImage, int)
    stopped = Signal()
    failed = Signal(str)
    WIDTH, HEIGHT, FPS = 640, 360, 12

    def __init__(self, source, parent=None):
        super().__init__(parent)
        self.source = source
        self.process = None
        self.playing = False
        self.frames = []
        self.play_timer = QTimer(self)
        self.play_timer.setInterval(round(1000/self.FPS))
        self.play_timer.timeout.connect(self.tick)

    def tick(self):
        if self.frames:
            picture, position = self.frames.pop(0)
            self.frame.emit(picture, position)
        elif self.process is None:
            self.play_timer.stop()
            self.playing = False
            self.stopped.emit()

    def stop(self):
        process, self.process = self.process, None
        self.playing = False
        self.play_timer.stop()
        self.frames.clear()
        if process is not None:
            process.kill()
            process.waitForFinished(1000)
            process.deleteLater()
        self.stopped.emit()

    def request(self, position, end=None):
        self.stop()
        process = QProcess(self)
        self.process = process
        self.playing = end is not None
        buffer, errors = bytearray(), bytearray()
        count = 0
        frame_size = self.WIDTH*self.HEIGHT*3

        def read():
            nonlocal count
            if self.process is not process: return
            buffer.extend(bytes(process.readAllStandardOutput()))
            frames = len(buffer)//frame_size
            if frames:
                for index in range(frames):
                    data = bytes(buffer[index*frame_size:(index+1)*frame_size])
                    picture = QImage(data, self.WIDTH, self.HEIGHT, self.WIDTH*3, QImage.Format.Format_RGB888).copy()
                    timestamp = position + round(count*1000/self.FPS) if end is not None else position
                    count += 1
                    if end is not None:
                        self.frames.append((picture, timestamp))
                        # Bounded backlog, including when the UI is briefly busy.
                        del self.frames[:-self.FPS*3]
                    else:
                        self.frame.emit(picture, timestamp)
                del buffer[:frames*frame_size]
                if end is not None and not self.play_timer.isActive(): self.play_timer.start()

        def read_error():
            errors.extend(bytes(process.readAllStandardError()))
            del errors[:-8192]

        def finished(code, status):
            if self.process is not process: return
            read()
            read_error()
            self.process = None
            process.deleteLater()
            if code or not count:
                self.frames.clear()
                self.play_timer.stop()
                self.playing = False
                self.failed.emit("Aperçu indisponible pour ce fichier. Tu peux essayer l’export en MP4.")
                self.stopped.emit()
            elif end is None:
                self.playing = False
                self.stopped.emit()

        def error(kind):
            if kind == QProcess.ProcessError.FailedToStart and self.process is process:
                self.process = None
                process.deleteLater()
                self.playing = False
                self.failed.emit("Le moteur d’aperçu n’a pas pu démarrer.")
                self.stopped.emit()

        process.readyReadStandardOutput.connect(read)
        process.readyReadStandardError.connect(read_error)
        process.finished.connect(finished)
        process.errorOccurred.connect(error)
        args = ["-hide_banner", "-loglevel", "error", "-nostdin"]
        if end is not None:
            args += ["-re"]
            if not fast_media_seek(self.source): args += ["-readrate_initial_burst", str(position/1000)]
        for arg in media_seek_args(self.source, position/1000):
            if arg == "-i": args += ["-protocol_whitelist", "file,pipe"]
            args.append(arg)
        args += ["-map", "0:v:0", "-an", "-sn", "-dn"]
        if end is None: args += ["-frames:v", "1"]
        else: args += ["-t", str(max(.001, (end-position)/1000))]
        args += ["-vf", f"fps={self.FPS},scale={self.WIDTH}:{self.HEIGHT}:force_original_aspect_ratio=decrease,pad={self.WIDTH}:{self.HEIGHT}:(ow-iw)/2:(oh-ih)/2,setsar=1", "-pix_fmt", "rgb24", "-f", "rawvideo", "pipe:1"]
        process.start(ffmpeg_path(), args)


class VideoTrimmer(QDialog):
    def __init__(self, source, parent=None):
        super().__init__(parent)
        self.source = Path(source)
        self.total = 0
        self.position = 0
        self.closed = False
        self.setWindowTitle("Meloo · Découper une vidéo")
        self.resize(900, 740)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        title = QLabel("Garde seulement le passage qui t’intéresse")
        title.setStyleSheet("font-size:22px;font-weight:600;")
        layout.addWidget(title)
        self.source_label = QLabel(self.source.name)
        self.source_label.setTextFormat(Qt.TextFormat.PlainText)
        self.source_label.setWordWrap(True)
        layout.addWidget(self.source_label)
        self.preview = QLabel("Lecture des informations de la vidéo…")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(400, 225)
        self.preview.setStyleSheet("background:#101820;color:#e6f0f2;border-radius:10px;")
        layout.addWidget(self.preview, 1)
        self.decoder = PreviewDecoder(self.source, self)
        self.decoder.frame.connect(self.show_frame)
        self.decoder.stopped.connect(lambda: self.play_button.setText("Voir l’extrait"))
        self.decoder.failed.connect(self.show_preview_error)
        self.seek_timer = QTimer(self)
        self.seek_timer.setSingleShot(True)
        self.seek_timer.setInterval(140)
        self.seek_timer.timeout.connect(lambda: self.decoder.request(self.position))
        playback = QHBoxLayout()
        self.play_button = QPushButton("Voir l’extrait")
        self.play_button.clicked.connect(self.toggle_play)
        playback.addWidget(self.play_button)
        self.position_label = QLabel("00:00:00.000")
        playback.addWidget(self.position_label)
        playback.addStretch()
        playback.addWidget(QLabel("Aperçu visuel sans son"))
        layout.addLayout(playback)
        self.timeline = ClipTimeline(self)
        self.timeline.rangeChanged.connect(self.timeline_changed)
        self.timeline.seekRequested.connect(self.seek)
        layout.addWidget(self.timeline)
        fields = QHBoxLayout()
        self.start = TimeField("Début de l’extrait", self)
        self.end = TimeField("Fin de l’extrait", self)
        for text, widget in (("Début", self.start), ("Fin", self.end)):
            column = QVBoxLayout()
            column.addWidget(QLabel(text))
            column.addWidget(widget)
            fields.addLayout(column)
        self.selection_label = QLabel()
        fields.addWidget(self.selection_label, 1)
        layout.addLayout(fields)
        self.start.valueChanged.connect(lambda: self.fields_changed("start"))
        self.end.valueChanged.connect(lambda: self.fields_changed("end"))
        presets = QHBoxLayout()
        presets.addWidget(QLabel("À partir du début choisi :"))
        self.presets = []
        for text, seconds in (("5 s", 5), ("15 s", 15), ("30 s", 30), ("1 min", 60)):
            button = QPushButton(text)
            button.clicked.connect(lambda checked=False, seconds=seconds: self.set_length(seconds))
            self.presets.append(button)
            presets.addWidget(button)
        all_button = QPushButton("Tout")
        all_button.clicked.connect(lambda: self.set_selection(0, self.total))
        self.presets.append(all_button)
        presets.addWidget(all_button)
        layout.addLayout(presets)
        output = QHBoxLayout()
        output.addWidget(QLabel("Enregistrer en"))
        self.format = QComboBox()
        for ext in VIDEO_OUTPUTS:
            self.format.addItem(ext.upper() + (" · recommandé" if ext == "mp4" else ""), ext)
        output.addWidget(self.format, 1)
        self.keep_audio = QCheckBox("Conserver le son")
        self.keep_audio.setChecked(True)
        output.addWidget(self.keep_audio)
        layout.addLayout(output)
        self.status = QLabel("Chargement…")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.export_button = self.buttons.button(QDialogButtonBox.StandardButton.Save)
        self.export_button.setText("Créer l’extrait")
        self.export_button.setObjectName("primary")
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self.set_ready(False)
        self.probe = QProcess(self)
        self.probe_log = bytearray()
        self.probe.readyReadStandardError.connect(self.probe_read)
        self.probe.finished.connect(self.probe_finished)
        self.probe.errorOccurred.connect(self.probe_error)
        self.probe_timeout = QTimer(self)
        self.probe_timeout.setSingleShot(True)
        self.probe_timeout.timeout.connect(self.probe_expired)
        QTimer.singleShot(0, self, self.load)

    def set_ready(self, ready):
        for widget in [self.play_button, self.timeline, self.start, self.end, self.format, self.keep_audio, self.export_button, *self.presets]:
            widget.setEnabled(ready)

    def load(self):
        if self.closed: return
        self.probe_timeout.start(30000)
        self.probe.start(ffmpeg_path(), ["-hide_banner", "-nostdin", "-protocol_whitelist", "file,pipe", "-i", str(self.source)])

    def probe_read(self):
        self.probe_log.extend(bytes(self.probe.readAllStandardError()))
        del self.probe_log[:-65536]

    def probe_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.probe_timeout.stop()
            self.status.setText("Impossible de démarrer le moteur vidéo. Réinstalle la distribution complète de Meloo.")

    def probe_expired(self):
        self.probe.kill()
        self.status.setText("La lecture du fichier a pris trop de temps. Essaie une copie sur le disque local.")

    def probe_finished(self, *args):
        self.probe_timeout.stop()
        if self.closed: return
        self.probe_read()
        info = Engine.parse_media_info(self.probe_log.decode("utf-8", errors="replace"))
        duration = info["duration"]
        if duration is None or not math.isfinite(duration) or duration < .1 or not info["video_streams"]:
            self.preview.setText("Cette vidéo ne peut pas être ouverte.")
            self.status.setText("Durée ou piste vidéo introuvable. Le fichier doit être local, lisible et non protégé.")
            return
        self.total = round(duration*1000)
        self.start.setMaximum((self.total-100)/1000)
        self.end.setMaximum(self.total/1000)
        self.end.setMinimum(.1)
        self.set_ready(True)
        self.keep_audio.setEnabled(bool(info["audio_streams"]))
        self.keep_audio.setChecked(bool(info["audio_streams"]))
        self.source_label.setText(f"{self.source.name}  ·  Durée : {clock_text(duration)}")
        self.set_selection(0, min(60000, self.total))

    def set_selection(self, start, end):
        if not self.total: return
        start = max(0, min(start, self.total-100))
        end = max(start+100, min(end, self.total))
        for widget, value in ((self.start, start), (self.end, end)):
            widget.blockSignals(True)
            widget.setValue(value/1000)
            widget.blockSignals(False)
        self.timeline.set_range(self.total, start, end)
        self.selection_label.setText("Durée conservée\n" + clock_text((end-start)/1000))
        self.status.setText("Déplace les poignées ou saisis le début et la fin. Une nouvelle copie sera créée ; l’original est conservé.")
        self.seek(start)

    def fields_changed(self, edited):
        if not self.total: return
        start, end = round(self.start.value()*1000), round(self.end.value()*1000)
        if start >= end:
            if edited == "start": end = min(self.total, start+100)
            else: start = max(0, end-100)
        self.set_selection(start, end)
        if edited == "end": self.seek(max(start, end-1))

    def timeline_changed(self, start, end):
        edited = self.timeline.dragging
        self.set_selection(start, end)
        if edited == "end": self.seek(max(start, end-1))

    def set_length(self, seconds):
        start = round(self.start.value()*1000)
        self.set_selection(start, min(self.total, start+seconds*1000))

    def seek(self, position):
        if self.closed or not self.total: return
        self.decoder.stop()
        # Stay at least a frame away from EOF for a useful boundary preview.
        self.position = max(0, min(position, max(0, self.total-100)))
        self.timeline.position = self.position
        self.timeline.update()
        self.position_label.setText(clock_text(self.position/1000))
        self.seek_timer.start()

    def toggle_play(self):
        self.seek_timer.stop()
        if self.decoder.playing:
            self.decoder.stop()
            return
        start, end = round(self.start.value()*1000), round(self.end.value()*1000)
        self.decoder.request(start, end)
        self.play_button.setText("Arrêter l’aperçu")

    def show_frame(self, image, position):
        if self.closed: return
        self.position = min(position, self.total)
        self.picture = QPixmap.fromImage(image)
        self.preview.setPixmap(self.picture.scaled(self.preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.position_label.setText(clock_text(self.position/1000))
        self.timeline.position = self.position
        self.timeline.update()

    def show_preview_error(self, message):
        if not self.closed: self.status.setText(message)

    def options(self):
        return {"start": self.start.value(), "duration": round(self.end.value()-self.start.value(), 3),
                "output_format": self.format.currentData(), "keep_audio": self.keep_audio.isChecked()}

    def accept(self):
        if self.total and 0 <= self.start.value() < self.end.value() <= self.total/1000:
            super().accept()

    def shutdown(self):
        self.closed = True
        self.seek_timer.stop()
        self.probe_timeout.stop()
        self.decoder.stop()
        if self.probe.state() != QProcess.ProcessState.NotRunning:
            self.probe.kill()
            self.probe.waitForFinished(1000)

    def done(self, result):
        self.shutdown()
        super().done(result)
