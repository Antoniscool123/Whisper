"""Application entry point, single-instance handling and diagnostic modes."""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
import tempfile
from logging.handlers import RotatingFileHandler
from pathlib import Path

from . import APP_NAME, __version__
from .config import app_directory


def register_fonts() -> str:
    from PySide6.QtGui import QFontDatabase
    family = "DejaVu Sans"
    directory = Path(__file__).resolve().parent / "assets" / "fonts"
    for filename in ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf"):
        path = directory / filename
        if path.exists() and QFontDatabase.addApplicationFont(str(path)) < 0:
            logging.getLogger(__name__).warning("Could not register bundled font %s", filename)
    return family


def configure_logging() -> None:
    directory = app_directory()
    directory.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(directory / "openflow.log", maxBytes=1_000_000, backupCount=2, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    logging.getLogger("pywhispercpp").setLevel(logging.WARNING)


def smoke_test(output: str) -> int:
    """Run inside the packaged Windows exe: verify the real native dependencies."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    import numpy
    import requests
    import sounddevice
    import _pywhispercpp
    from PySide6.QtCore import qVersion
    from PySide6.QtWidgets import QApplication
    from pywhispercpp.model import Model
    app = QApplication.instance() or QApplication([])
    languages = Model.available_languages()
    assert "da" in languages and len(languages) >= 100
    assert QApplication.platformName() == "offscreen"
    result = {"ok": True, "app": APP_NAME, "version": __version__, "python": sys.version.split()[0],
              "qt": qVersion(), "numpy": numpy.__version__, "languages": len(languages),
              "danish": "da" in languages, "native_whisper": True,
              "portaudio": sounddevice.get_portaudio_version()[1], "frozen": getattr(sys, "frozen", False)}
    Path(output).write_text(json.dumps(result, indent=2), encoding="utf-8")
    app.quit()
    return 0


def render_preview(output: str) -> int:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    with tempfile.TemporaryDirectory(prefix="openflow-preview-") as directory:
        os.environ["OPENFLOW_DATA_DIR"] = directory
        from PySide6.QtWidgets import QApplication
        from .ui.main_window import MainWindow
        app = QApplication([])
        app.setStyle("Fusion")
        from PySide6.QtGui import QFont
        app.setFont(QFont(register_fonts(), 10))
        window = MainWindow(preview=True)
        window.resize(1160, 880)
        window.show()
        for _ in range(8):
            app.processEvents()
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not window.grab().save(str(path)):
            raise RuntimeError("Qt could not render the interface preview")
        window.quit()
        app.processEvents()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="OpenFlow — free, local, multilingual dictation")
    parser.add_argument("--minimized", action="store_true", help="Start in the system tray")
    parser.add_argument("--smoke-test", nargs="?", const="smoke-result.json", metavar="JSON_PATH",
                        help="Verify packaged dependencies and exit (for CI)")
    parser.add_argument("--render-preview", metavar="PNG_PATH", help="Render an interface preview and exit")
    parser.add_argument("--startup-test", metavar="JSON_PATH", help="Exercise normal startup and exit (for CI)")
    args = parser.parse_args(argv)
    if args.smoke_test:
        return smoke_test(args.smoke_test)
    if args.render_preview:
        return render_preview(args.render_preview)
    if args.startup_test:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    def checkpoint(message):
        if args.startup_test:
            with open("startup-progress.txt", "a", encoding="utf-8") as stream:
                stream.write(message + "\n")
    checkpoint("before logging")
    configure_logging()
    checkpoint("before imports")
    from PySide6.QtGui import QColor, QFont, QPalette
    from PySide6.QtCore import QLockFile, QTimer
    from PySide6.QtNetwork import QLocalServer, QLocalSocket
    from PySide6.QtWidgets import QApplication, QMessageBox
    from .ui.main_window import MainWindow
    checkpoint("after imports")
    app = QApplication(sys.argv[:1])
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setOrganizationName("OpenFlow")
    app.setStyle("Fusion")
    app.setFont(QFont(register_fonts(), 10))
    palette = QPalette()
    for role, color in ((QPalette.Window, "#0B111B"), (QPalette.WindowText, "#E8EFF7"),
                        (QPalette.Base, "#0E1824"), (QPalette.AlternateBase, "#172536"),
                        (QPalette.Text, "#E8EFF7"), (QPalette.Button, "#1C2B3D"),
                        (QPalette.ButtonText, "#E8EFF7"), (QPalette.Highlight, "#245C56"),
                        (QPalette.HighlightedText, "#B9FFF0"), (QPalette.ToolTipBase, "#203247"),
                        (QPalette.ToolTipText, "#E8EFF7")):
        palette.setColor(role, QColor(color))
    app.setPalette(palette)
    checkpoint("before lock")
    name = "openflow-" + hashlib.sha256(str(app_directory()).encode()).hexdigest()[:16]
    lock = QLockFile(str(app_directory() / "openflow.lock"))
    lock.setStaleLockTime(15000)
    if not lock.tryLock(150):
        socket = QLocalSocket()
        socket.connectToServer(name)
        if socket.waitForConnected(700):
            socket.write(b"show")
            socket.waitForBytesWritten(700)
            socket.disconnectFromServer()
            return 0
        QMessageBox.information(None, "OpenFlow", "OpenFlow is already running. Check your system tray.")
        return 0
    server = QLocalServer()
    QLocalServer.removeServer(name)
    server.listen(name)
    checkpoint("before window")
    window = MainWindow()
    checkpoint("after window")
    app.setWindowIcon(window.windowIcon())
    server.newConnection.connect(lambda: window.show_window())
    def exception_hook(kind, value, traceback):
        logging.getLogger(__name__).error("Unhandled UI exception", exc_info=(kind, value, traceback))
        if args.startup_test:
            import traceback as traceback_module
            Path("startup-error.txt").write_text("".join(traceback_module.format_exception(kind, value, traceback)), encoding="utf-8")
            app.exit(1)
        else:
            QMessageBox.critical(None, "OpenFlow", f"An unexpected error occurred. Details are in {app_directory() / 'openflow.log'}.")
    sys.excepthook = exception_hook
    if (args.minimized or window.settings.start_minimized) and window.tray:
        window.hide()
    else:
        window.show()
    if args.startup_test:
        def finish_startup_test():
            checkpoint("before quit")
            window.quit()
            checkpoint("after quit")
            Path(args.startup_test).write_text(json.dumps({"ok": True, "frozen": getattr(sys, "frozen", False)}), encoding="utf-8")
        QTimer.singleShot(500, finish_startup_test)
    checkpoint("before event loop")
    code = app.exec()
    server.close()
    lock.unlock()
    return code
