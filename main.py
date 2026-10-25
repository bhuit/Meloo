import argparse
import json
import os
import sys
from pathlib import Path


def open_workshop(args, tray_available=True):
    return bool(args.window or args.screenshot or args.smoke or args.files or not tray_available)


def main():
    parser = argparse.ArgumentParser(description="Meloo · convertisseur local Windows")
    parser.add_argument("files", nargs="*")
    parser.add_argument("--screenshot", metavar="PNG")
    parser.add_argument("--convert", metavar="OPERATION")
    parser.add_argument("--output")
    parser.add_argument("--options", default="{}")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--tray", action="store_true")
    parser.add_argument("--window", action="store_true", help="Ouvrir l’atelier (par défaut : icône de notification)")
    parser.add_argument("--quit", action="store_true", help="Quitter l’instance en arrière-plan")
    parser.add_argument("--status-file", metavar="JSON", help="Enregistrer l’état de l’instance locale")
    args = parser.parse_args()
    if args.screenshot or args.smoke:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        os.environ.setdefault("ZESTE_CONFIG_DIR", str(Path(__file__).parent / "tests/artifacts/settings"))
    if args.convert:
        from zeste.engine import Engine
        engine = Engine(output_dir=args.output)
        print(json.dumps({"outputs": engine.execute(args.files, args.convert, json.loads(args.options)), "warnings": engine.warnings}, ensure_ascii=False))
        return 0
    from PySide6.QtCore import QTimer, QSettings
    from PySide6.QtWidgets import QApplication
    from zeste.ui import MainWindow, STYLE
    app = QApplication(sys.argv[:1])
    app.setApplicationName("Meloo")
    app.setOrganizationName("Zeste")
    app.setStyle("Fusion")
    from PySide6.QtGui import QFontDatabase
    font_root = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    for name in ["segoeui.ttf", "segoeuib.ttf", "seguisym.ttf"]:
        if (font_root / name).exists(): QFontDatabase.addApplicationFont(str(font_root / name))
    app.setStyleSheet(STYLE)
    app.setQuitOnLastWindowClosed(False)
    server = None
    if not (args.screenshot or args.smoke):
        from PySide6.QtNetwork import QLocalServer, QLocalSocket
        import hashlib
        profile_id = os.environ.get("ZESTE_CONFIG_DIR", "default")
        identity = hashlib.sha256((os.environ.get("USERNAME", "local") + "|" + profile_id).encode()).hexdigest()[:12]
        server_name = "ZesteWindows-" + identity
        socket = QLocalSocket()
        socket.connectToServer(server_name)
        if socket.waitForConnected(200):
            socket.write(json.dumps({"files": args.files, "command": "status" if args.status_file else "quit" if args.quit else "show" if args.window or args.files else "notify"}).encode() + b"\n")
            socket.waitForBytesWritten(1000)
            if args.status_file:
                if not socket.waitForReadyRead(5000): raise RuntimeError("La session locale n’a pas répondu.")
                status = json.loads(bytes(socket.readLine()))
                Path(args.status_file).write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf8")
            socket.disconnectFromServer()
            return 0
        if args.status_file:
            Path(args.status_file).write_text('{"running": false}', encoding="utf8")
            return 0
        if args.quit: return 0
        server = QLocalServer(app)
        QLocalServer.removeServer(server_name)
        if not server.listen(server_name): raise RuntimeError("Impossible de créer la session locale Meloo.")
    if args.screenshot or args.smoke:
        # Test and preview never touch the user's settings or history.
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(Path(__file__).parent / "tests/artifacts/settings"))
    window = MainWindow()
    window.add_files(args.files)
    if server:
        def incoming():
            client = server.nextPendingConnection()
            client.buffer = bytearray()
            def receive():
                client.buffer.extend(bytes(client.readAll()))
                if len(client.buffer) > 1024*1024: client.abort(); return
                if b"\n" not in client.buffer: return
                try:
                    message = json.loads(client.buffer.split(b"\n", 1)[0])
                    files = message if isinstance(message, list) else message.get("files", [])
                    if isinstance(files, list) and all(isinstance(p, str) for p in files): window.add_files(files)
                    command = "show" if isinstance(message, list) else message.get("command")
                    if command == "status":
                        from zeste import __version__
                        from zeste.window_visibility import native_visible
                        status = {"app_name": "Meloo", "color_style": window.popup.color_style, "running": True, "version": __version__, "window_visible": window.isVisible(), "tray_visible": window.tray.isVisible(), "watcher_active": window.watcher.timer.isActive(), "global_drag": window.settings.value("global_drag", True, bool), "trigger": "Ctrl", "default_mode": "quick", "glass_strength": window.popup.glass_strength}
                        watcher = window.watcher
                        status.update(input_backend="raw-input" if watcher.input.active else "polling", input_error=watcher.input.error, mouse_presses=watcher.input.state.mouse_presses, ctrl_presses=watcher.input.state.ctrl_presses, wheel_opens=watcher.opens, wheel_visible=window.popup.isVisible(), gesture_eligible=watcher.gesture.eligible, last_source=watcher.last_source)
                        status.update(raw_mouse_messages=watcher.input.mouse_messages, raw_keyboard_messages=watcher.input.keyboard_messages, input_registration=watcher.input.registration_status(), result_panel_visible=window.result_panel.isVisible())
                        modal = QApplication.activeModalWidget()
                        status.update(job_active=window.thread is not None, queued_jobs=len(window.pending), modal_active=modal is not None, modal_title=modal.windowTitle() if modal else "")
                        status.update(window_native_visible=native_visible(window), wheel_native_visible=native_visible(window.popup), current_page=window.stack.currentIndex(), platform=app.platformName())
                        client.write(json.dumps(status).encode()+b"\n")
                    elif command == "quit": window.quit_app()
                    elif command == "show": window.show_main()
                    elif command == "notify": pass  # Re-launch stays silent in resident mode.
                except (ValueError, TypeError, AttributeError): pass
                client.disconnectFromServer()
            client.readyRead.connect(receive)
            client.disconnected.connect(client.deleteLater)
            receive()
        server.newConnection.connect(incoming)
    from PySide6.QtWidgets import QSystemTrayIcon
    if open_workshop(args, QSystemTrayIcon.isSystemTrayAvailable()): window.show_main()
    elif not window.settings.value("background_hint_shown", False, bool):
        QTimer.singleShot(900, window.notify_background)
        window.settings.setValue("background_hint_shown", True)
    if args.screenshot:
        def capture():
            window.grab().save(args.screenshot)
            app.quit()
        QTimer.singleShot(500, capture)
    elif args.smoke: QTimer.singleShot(500, app.quit)
    return app.exec()


if __name__ == "__main__":
    try: sys.exit(main())
    except Exception:
        import traceback
        log = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Zeste"
        log.mkdir(parents=True, exist_ok=True)
        (log / "startup-error.log").write_text(traceback.format_exc(), encoding="utf-8")
        if sys.stderr: traceback.print_exc()
        if os.name == "nt" and not any(x in sys.argv for x in ["--smoke", "--screenshot", "--convert"]):
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, f"Meloo n’a pas pu démarrer.\nDiagnostic : {log / 'startup-error.log'}", "Meloo", 0x10)
        sys.exit(1)
