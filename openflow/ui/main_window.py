from __future__ import annotations

import dataclasses
import logging
import os
import queue
import threading
import time
import uuid
from pathlib import Path

from PySide6.QtCore import QObject, QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QProgressBar, QPushButton, QScrollArea, QSizePolicy,
    QStackedWidget, QSystemTrayIcon, QTextEdit, QVBoxLayout, QWidget, QMenu, QStatusBar,
)

from .. import __version__
from ..audio import Recorder, microphones
from ..config import Settings, app_directory
from ..history import History
from ..hotkeys import HOTKEYS, WindowsHotkeys
from ..languages import LANGUAGES, language_name
from ..models import MODEL_CATALOG, is_cached, model_directory, remove_model
from ..platform_windows import WindowsIntegration
from ..text import parse_dictionary, tidy_text, word_count
from ..worker import SpeechWorker
from .theme import STYLE
from .widgets import Card, StatusPill, Waveform, make_icon

LOG = logging.getLogger(__name__)
ASSETS = Path(__file__).resolve().parent.parent / "assets"


def label(text: str = "", name: str | None = None, wrap: bool = False) -> QLabel:
    widget = QLabel(text)
    widget.setTextFormat(Qt.PlainText)
    if name:
        widget.setObjectName(name)
    if wrap:
        widget.setWordWrap(True)
    return widget


def button(text: str, icon: str | None = None, name: str | None = None) -> QPushButton:
    widget = QPushButton(text)
    if icon:
        widget.setIcon(make_icon(icon, "#12352F" if name == "Primary" else "#A9BFCE"))
    if name:
        widget.setObjectName(name)
    widget.setCursor(Qt.PointingHandCursor)
    return widget


def scroll_page() -> tuple[QScrollArea, QWidget, QVBoxLayout]:
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    content = QWidget()
    content.setObjectName("Root")
    layout = QVBoxLayout(content)
    layout.setContentsMargins(28, 26, 28, 24)
    layout.setSpacing(16)
    scroll.setWidget(content)
    return scroll, content, layout


def clear_layout(layout: QVBoxLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
        elif item.layout():
            clear_layout(item.layout())


class PasteSignals(QObject):
    finished = Signal(str)


class MainWindow(QMainWindow):
    def __init__(self, preview: bool = False):
        super().__init__()
        self.preview = preview
        self.settings, settings_warning = Settings.load()
        self.history = History()
        self.recorder = Recorder()
        self.integration = WindowsIntegration()
        self.events: queue.Queue = queue.Queue(maxsize=256)
        self.hotkeys = WindowsHotkeys(self.settings.hotkey, self.events)
        self.worker = SpeechWorker(self)
        self.worker.event.connect(self._worker_event)
        self.paste_signals = PasteSignals()
        self.paste_signals.finished.connect(self._paste_done)
        self.worker_state = "idle"
        self.model_state = "missing"
        self.recording = False
        self.pasting = False
        self.really_close = False
        self.pending_remove: str | None = None
        self.pending_target = None
        self.record_settings = None
        self.job_id = ""
        self.tray = None
        self.busy_controls: list[QWidget] = []
        self.setWindowTitle("OpenFlow — Free local dictation")
        self.setWindowIcon(QIcon(str(ASSETS / "icon.png")))
        self.resize(1160, 880)
        self.setMinimumSize(960, 680)
        self.setStyleSheet(STYLE)
        self._build()
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Free forever. No account, no word limit, no cloud transcription.")
        self._sync_controls()
        self._refresh_history()
        self._update_stats()
        if settings_warning:
            self._notice(settings_warning)
        if self.history.warning:
            self._notice(self.history.warning)
        if preview:
            self.model_state = "ready"
            self.latest.setPlainText("Hej! Det her er OpenFlow. Jeg kan skrive med min stemme, uden abonnement og uden at sende min lyd til en server.")
            self.detected.setText("Dansk · eksempeltekst / sample text")
            self._update_ui()
            self.mic_button.setEnabled(True)
            return
        self.worker.start()
        self.hotkeys.start()
        self._setup_tray()
        self.event_timer = QTimer(self)
        self.event_timer.timeout.connect(self._pump_events)
        self.event_timer.start(30)
        self.focus_timer = QTimer(self)
        self.focus_timer.timeout.connect(self.integration.poll)
        self.focus_timer.start(250)
        self.meter_timer = QTimer(self)
        self.meter_timer.timeout.connect(self._update_meter)
        if is_cached(self.settings.model):
            self.model_state = "loading" if self.settings.preload else "missing"
            if self.settings.preload:
                self.worker.request("load", model=self.settings.model, threads=self.settings.threads)
        self._update_ui()

    # ----- interface construction -------------------------------------------------
    def _build(self) -> None:
        root = QWidget()
        root.setObjectName("Root")
        horizontal = QHBoxLayout(root)
        horizontal.setContentsMargins(0, 0, 0, 0)
        horizontal.setSpacing(0)
        horizontal.addWidget(self._sidebar())
        self.pages = QStackedWidget()
        self.pages.addWidget(self._dictation_page())
        self.pages.addWidget(self._history_page())
        self.pages.addWidget(self._vocabulary_page())
        self.pages.addWidget(self._settings_page())
        horizontal.addWidget(self.pages, 1)
        self.setCentralWidget(root)

    def _sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(218)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 28, 18, 22)
        layout.setSpacing(8)
        brand = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(QPixmap(str(ASSETS / "icon.png")).scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        brand.addWidget(icon)
        brand.addWidget(label("OpenFlow", "Brand"))
        brand.addStretch()
        layout.addLayout(brand)
        layout.addWidget(label("FREE LOCAL DICTATION", "Eyebrow"))
        layout.addSpacing(30)
        self.nav_buttons: list[QPushButton] = []
        for index, (name, icon_name) in enumerate((("Dictation", "mic"), ("History", "history"),
                                                  ("Vocabulary", "book"), ("Settings", "settings"))):
            nav = button(name, icon_name, "Nav")
            nav.setCheckable(True)
            nav.setChecked(index == 0)
            nav.clicked.connect(lambda checked=False, i=index: self._navigate(i))
            layout.addWidget(nav)
            self.nav_buttons.append(nav)
        layout.addStretch()
        privacy = Card("Privacy", (14, 14, 14, 14), 8)
        top = QHBoxLayout()
        shield = QLabel()
        shield.setPixmap(make_icon("shield", "#5EEAD4").pixmap(20, 20))
        top.addWidget(shield)
        top.addWidget(label("Private by design", "Accent"))
        top.addStretch()
        privacy.layout_.addLayout(top)
        privacy.layout_.addWidget(label("Your voice stays on this PC.\nNo cloud transcription.", "Small", True))
        layout.addWidget(privacy)
        layout.addSpacing(10)
        layout.addWidget(label("100% FREE  ·  v" + __version__, "Eyebrow"))
        return sidebar

    def _navigate(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        for number, nav in enumerate(self.nav_buttons):
            nav.setChecked(number == index)
        if index == 1:
            self._refresh_history()

    def _dictation_page(self) -> QWidget:
        scroll, content, layout = scroll_page()
        header = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(5)
        titles.addWidget(label("Your voice, in flow.", "Title"))
        titles.addWidget(label("Speak naturally. Get text wherever you work.", "Subtitle"))
        header.addLayout(titles)
        header.addStretch()
        self.engine_pill = StatusPill("●  Local engine")
        header.addWidget(self.engine_pill, 0, Qt.AlignTop)
        layout.addLayout(header)

        stats = QHBoxLayout()
        stats.setSpacing(12)
        self.words_stat = label("0", "StatValue")
        self.sessions_stat = label("0", "StatValue")
        for title, value, foot in (("WORDS TODAY", self.words_stat, "From your local history"),
                                   ("DICTATIONS", self.sessions_stat, "No weekly limits"),
                                   ("YOUR COST", label("$0", "StatValue"), "Free. Really.")):
            card = Card(margins=(17, 12, 17, 12), spacing=2)
            card.layout_.addWidget(label(title, "Eyebrow"))
            row = QHBoxLayout()
            row.addWidget(value)
            row.addStretch()
            row.addWidget(label(foot, "Small"))
            card.layout_.addLayout(row)
            stats.addWidget(card, 1)
        layout.addLayout(stats)

        hero = Card("Hero", (22, 20, 22, 20), 12)
        top = QHBoxLayout()
        top.addWidget(label("DICTATION STUDIO", "Eyebrow"))
        top.addStretch()
        self.model_chip = label("Small · not downloaded", "Small")
        top.addWidget(self.model_chip)
        hero.layout_.addLayout(top)
        record_row = QHBoxLayout()
        record_row.setSpacing(20)
        self.mic_button = QPushButton()
        self.mic_button.setObjectName("MicButton")
        self.mic_button.setFixedSize(86, 86)
        self.mic_button.setIcon(make_icon("mic", "#0B302B", 34))
        self.mic_button.setIconSize(QSize(34, 34))
        self.mic_button.setCursor(Qt.PointingHandCursor)
        self.mic_button.setToolTip("Start or stop dictation")
        self.mic_button.clicked.connect(self._toggle_recording)
        record_row.addWidget(self.mic_button, 0, Qt.AlignVCenter)
        right = QVBoxLayout()
        right.setSpacing(5)
        self.hero_title = label("Ready when you are", "HeroTitle")
        self.hero_subtitle = label("Hold Right Ctrl in any app, or click the mic.", "Subtitle", True)
        right.addWidget(self.hero_title)
        right.addWidget(self.hero_subtitle)
        self.waveform = Waveform()
        right.addWidget(self.waveform)
        controls = QHBoxLayout()
        self.language_combo = QComboBox()
        self.language_combo.addItem("Auto-detect language", "auto")
        for code, name in sorted(LANGUAGES.items(), key=lambda item: item[1]):
            self.language_combo.addItem(name, code)
        self.language_combo.setMinimumWidth(210)
        self.language_combo.setMaximumWidth(270)
        self.language_combo.currentIndexChanged.connect(lambda: self._language_changed(self.language_combo))
        controls.addWidget(self.language_combo)
        self.timer_label = label("00:00", "Muted")
        controls.addWidget(self.timer_label)
        controls.addStretch()
        self.cancel_action = button("Cancel", "close", "Ghost")
        self.cancel_action.clicked.connect(self._cancel)
        self.cancel_action.hide()
        controls.addWidget(self.cancel_action)
        right.addLayout(controls)
        record_row.addLayout(right, 1)
        hero.layout_.addLayout(record_row)
        layout.addWidget(hero)

        self.setup = Card("Setup", (16, 14, 16, 14), 8)
        setup_row = QHBoxLayout()
        text = QVBoxLayout()
        text.setSpacing(4)
        self.setup_title = label("One download. Then completely offline.", "SectionTitle")
        self.setup_detail = label("Get the free Small model (~181 MB) for Danish and 99 other languages.", "Small", True)
        text.addWidget(self.setup_title)
        text.addWidget(self.setup_detail)
        setup_row.addLayout(text, 1)
        self.download_button = button("Download model", "download", "Primary")
        self.download_button.clicked.connect(self._download_model)
        setup_row.addWidget(self.download_button)
        self.setup_cancel = button("Pause", None, "Ghost")
        self.setup_cancel.clicked.connect(self.worker.cancel_download)
        self.setup_cancel.hide()
        setup_row.addWidget(self.setup_cancel)
        self.setup.layout_.addLayout(setup_row)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFormat("%p%")
        self.progress.hide()
        self.setup.layout_.addWidget(self.progress)
        layout.addWidget(self.setup)

        transcript = Card(margins=(18, 16, 18, 16), spacing=10)
        heading = QHBoxLayout()
        heading.addWidget(label("Latest transcript", "SectionTitle"))
        heading.addStretch()
        self.detected = label("Waiting for your voice", "Small")
        heading.addWidget(self.detected)
        transcript.layout_.addLayout(heading)
        self.latest = QTextEdit()
        self.latest.setPlaceholderText("Your words will appear here…\n\nTry saying: Hej, hvordan har du det i dag?")
        self.latest.setMinimumHeight(112)
        self.latest.setMaximumHeight(160)
        self.latest.setAcceptRichText(False)
        self.latest.textChanged.connect(self._update_text_buttons)
        transcript.layout_.addWidget(self.latest)
        actions = QHBoxLayout()
        self.copy_button = button("Copy text", "copy")
        self.copy_button.clicked.connect(self._copy_latest)
        self.insert_button = button("Insert into app", "insert", "Primary")
        self.insert_button.setToolTip("Return to your previous app and paste this text")
        self.insert_button.clicked.connect(self._insert_latest)
        actions.addWidget(self.copy_button)
        actions.addWidget(self.insert_button)
        actions.addStretch()
        actions.addWidget(label("Edit here before copying", "Small"))
        transcript.layout_.addLayout(actions)
        layout.addWidget(transcript)
        layout.addWidget(label("Audio is never saved  ·  Transcripts stay on your device  ·  Powered by Whisper", "Small"))
        layout.addStretch()
        return scroll

    def _history_page(self) -> QWidget:
        scroll, content, self.history_layout = scroll_page()
        header = QHBoxLayout()
        text = QVBoxLayout()
        text.addWidget(label("Your recent words.", "PageTitle"))
        text.addWidget(label("Up to 100 transcripts, stored only on this device. Audio is never stored.", "Subtitle", True))
        header.addLayout(text, 1)
        clear = button("Clear history", None, "Danger")
        clear.clicked.connect(self._clear_history)
        header.addWidget(clear)
        self.history_layout.addLayout(header)
        self.history_cards = QVBoxLayout()
        self.history_cards.setSpacing(10)
        self.history_layout.addLayout(self.history_cards)
        self.history_layout.addStretch()
        return scroll

    def _vocabulary_page(self) -> QWidget:
        scroll, content, layout = scroll_page()
        layout.addWidget(label("Make it sound like you.", "PageTitle"))
        layout.addWidget(label("Teach OpenFlow your names, places and technical terms. Everything stays local.", "Subtitle", True))
        hints = Card()
        hints.layout_.addWidget(label("Recognition hints", "SectionTitle"))
        hints.layout_.addWidget(label("Comma-separated names and terms. These gently guide Whisper before it transcribes.", "Muted", True))
        self.hints_edit = QLineEdit()
        self.hints_edit.setPlaceholderText("OpenFlow, Aarhus, Anton, PostgreSQL")
        self.hints_edit.setMaxLength(1000)
        hints.layout_.addWidget(self.hints_edit)
        layout.addWidget(hints)
        rules = Card()
        rules.layout_.addWidget(label("Your personal dictionary", "SectionTitle"))
        rules.layout_.addWidget(label("One replacement per line: spoken text => written text. Matching ignores capitalization.", "Muted", True))
        self.rules_edit = QTextEdit()
        self.rules_edit.setObjectName("Rules")
        self.rules_edit.setPlaceholderText("whisper flow => Wispr Flow\nopen flow => OpenFlow\nanton => Anton")
        self.rules_edit.setMinimumHeight(180)
        rules.layout_.addWidget(self.rules_edit)
        self.rules_status = label("Up to 200 rules. Replacements do not chain into each other.", "Small", True)
        rules.layout_.addWidget(self.rules_status)
        layout.addWidget(rules)
        row = QHBoxLayout()
        save = button("Save vocabulary", "check", "Primary")
        save.clicked.connect(self._save_vocabulary)
        row.addWidget(save)
        row.addStretch()
        layout.addLayout(row)
        layout.addWidget(label("Tip: recognition hints help with unusual words; dictionary rules guarantee exact replacements after transcription.", "Small", True))
        layout.addStretch()
        return scroll

    def _settings_page(self) -> QWidget:
        scroll, content, layout = scroll_page()
        layout.addWidget(label("Set your flow.", "PageTitle"))
        layout.addWidget(label("Changes save automatically. No account, license key or paid API required.", "Subtitle", True))
        speech = Card()
        speech.layout_.addWidget(label("Speech & language", "SectionTitle"))
        self.settings_language = QComboBox()
        self.settings_language.addItem("Auto-detect language", "auto")
        for code, name in sorted(LANGUAGES.items(), key=lambda item: item[1]):
            self.settings_language.addItem(name, code)
        self.settings_language.currentIndexChanged.connect(lambda: self._language_changed(self.settings_language))
        self._field(speech.layout_, "Dictation language", self.settings_language,
                    "Danish is the default. Auto-detect identifies the language from the first 30 seconds.")
        self.model_combo = QComboBox()
        for spec in MODEL_CATALOG.values():
            self.model_combo.addItem(f"{spec.label}  ·  ~{spec.megabytes:,} MB", spec.id)
        self.model_combo.currentIndexChanged.connect(self._model_changed)
        self._field(speech.layout_, "Speech model", self.model_combo, "")
        self.model_description = label("", "Small", True)
        speech.layout_.addWidget(self.model_description)
        model_actions = QHBoxLayout()
        self.settings_download = button("Download / load", "download")
        self.settings_download.clicked.connect(self._download_model)
        self.remove_button = button("Remove model", None, "Ghost")
        self.remove_button.clicked.connect(self._remove_model)
        model_actions.addWidget(self.settings_download)
        model_actions.addWidget(self.remove_button)
        model_actions.addStretch()
        speech.layout_.addLayout(model_actions)
        self.threads_combo = QComboBox()
        for count in (2, 4, 8, 16):
            self.threads_combo.addItem(f"{count} CPU threads", count)
        self.threads_combo.currentIndexChanged.connect(self._threads_changed)
        self._field(speech.layout_, "CPU usage", self.threads_combo,
                    "More threads can be faster but use more CPU. The change applies when the model is next loaded.")
        self.preload_check = self._checkbox(speech.layout_, "Preload a downloaded model at startup", "preload")
        layout.addWidget(speech)

        recording = Card()
        recording.layout_.addWidget(label("Recording & text insertion", "SectionTitle"))
        self.hotkey_combo = QComboBox()
        for key, spec in HOTKEYS.items():
            self.hotkey_combo.addItem(spec.label, key)
        self.hotkey_combo.currentIndexChanged.connect(self._hotkey_changed)
        self._field(recording.layout_, "Hold-to-talk shortcut", self.hotkey_combo,
                    "Right Ctrl is least likely to interfere with other shortcuts. Ctrl+Alt+Space always toggles hands-free when available.")
        mic_row = QHBoxLayout()
        self.mic_combo = QComboBox()
        self.mic_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        mic_row.addWidget(self.mic_combo, 1)
        refresh = button("Refresh", None, "Ghost")
        refresh.clicked.connect(self._refresh_microphones)
        mic_row.addWidget(refresh)
        recording.layout_.addWidget(label("Microphone", "Muted"))
        recording.layout_.addLayout(mic_row)
        self.mic_combo.currentIndexChanged.connect(self._microphone_changed)
        self.auto_paste_check = self._checkbox(recording.layout_, "Automatically insert text into the app where I started speaking", "auto_paste")
        self.restore_check = self._checkbox(recording.layout_, "Restore my previous text clipboard after pasting", "restore_clipboard")
        self.filler_check = self._checkbox(recording.layout_, "Remove hesitation sounds (øh, øhm, um, uh…)", "clean_fillers")
        self.commands_check = self._checkbox(recording.layout_, "Spoken punctuation and line commands (Danish + English)", "voice_commands")
        recording.layout_.addWidget(label("Commands include “punktum”, “komma”, “nyt afsnit”, “new paragraph” and “question mark”. Off by default to avoid changing ordinary sentences.", "Small", True))
        recording.layout_.addWidget(label("Focus safety: if you switch apps while speaking, OpenFlow copies the result instead of pasting into the wrong window. Clipboard managers may retain copied text.", "Small", True))
        layout.addWidget(recording)

        privacy = Card()
        privacy.layout_.addWidget(label("Windows & privacy", "SectionTitle"))
        self.startup_check = self._checkbox(privacy.layout_, "Start OpenFlow when I sign in to Windows", "start_with_windows")
        self.startup_check.setEnabled(os.name == "nt")
        self.minimized_check = self._checkbox(privacy.layout_, "Start minimized to the system tray", "start_minimized")
        self.tray_check = self._checkbox(privacy.layout_, "Keep running in the tray when I close the window", "minimize_to_tray")
        self.history_check = self._checkbox(privacy.layout_, "Keep recent transcripts on this device", "save_history")
        privacy.layout_.addWidget(label("Turning history off stops new entries; use Clear history to remove existing ones. Microphone audio is always kept in memory only.", "Small", True))
        folder = button("Open data folder", None, "Ghost")
        folder.clicked.connect(self._open_folder)
        privacy.layout_.addWidget(folder, 0, Qt.AlignLeft)
        licenses = button("Third-party licenses", None, "Ghost")
        licenses.clicked.connect(self._open_licenses)
        privacy.layout_.addWidget(licenses, 0, Qt.AlignLeft)
        layout.addWidget(privacy)
        layout.addWidget(label("Windows 10/11, 64-bit. Apps running as administrator may require OpenFlow to run as administrator too. Ctrl+Alt+Escape cancels recording or transcription.", "Small", True))
        layout.addStretch()
        self.busy_controls.extend([self.model_combo, self.settings_language, self.hotkey_combo,
                                   self.mic_combo, self.threads_combo, self.settings_download, self.remove_button])
        return scroll

    def _field(self, layout: QVBoxLayout, title: str, widget: QWidget, help_text: str) -> None:
        layout.addWidget(label(title, "Muted"))
        layout.addWidget(widget)
        if help_text:
            layout.addWidget(label(help_text, "Small", True))

    def _checkbox(self, layout: QVBoxLayout, text: str, key: str) -> QCheckBox:
        widget = QCheckBox(text)
        widget.setChecked(getattr(self.settings, key))
        widget.toggled.connect(lambda value, k=key: self._bool_changed(k, value))
        layout.addWidget(widget)
        return widget

    def _setup_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(make_icon("mic", "#5EEAD4", 32), self)
        self.tray.setToolTip("OpenFlow — free local dictation")
        menu = QMenu()
        menu.addAction("Open OpenFlow", self.show_window)
        menu.addAction("Start / stop dictation", self._toggle_recording)
        menu.addSeparator()
        menu.addAction("Quit", self.quit)
        self.tray_menu = menu
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: self.show_window() if reason in (QSystemTrayIcon.DoubleClick, QSystemTrayIcon.Trigger) else None)
        self.tray.show()
        QApplication.setQuitOnLastWindowClosed(False)

    # ----- settings ---------------------------------------------------------------
    def _sync_controls(self) -> None:
        for combo in (self.language_combo, self.settings_language):
            combo.blockSignals(True)
            combo.setCurrentIndex(max(0, combo.findData(self.settings.language)))
            combo.blockSignals(False)
        for combo, key in ((self.model_combo, "model"), (self.hotkey_combo, "hotkey"), (self.threads_combo, "threads")):
            combo.blockSignals(True)
            combo.setCurrentIndex(max(0, combo.findData(getattr(self.settings, key))))
            combo.blockSignals(False)
        self.hints_edit.setText(self.settings.hints)
        self.rules_edit.setPlainText(self.settings.vocabulary)
        self._refresh_microphones()
        self._update_model_description()

    def _save(self) -> None:
        try:
            self.settings.save()
        except OSError as exc:
            self._notice(f"Could not save settings: {exc}")

    def _bool_changed(self, key: str, value: bool) -> None:
        if self.preview:
            return
        old = getattr(self.settings, key)
        setattr(self.settings, key, value)
        if key == "start_with_windows" or (key == "start_minimized" and self.settings.start_with_windows):
            if not self._apply_startup():
                setattr(self.settings, key, old)
                check = self.startup_check if key == "start_with_windows" else self.minimized_check
                check.blockSignals(True); check.setChecked(old); check.blockSignals(False)
                return
        if key == "minimize_to_tray":
            QApplication.setQuitOnLastWindowClosed(not value or self.tray is None)
        self._save()
        self._update_stats()

    def _apply_startup(self) -> bool:
        if os.name != "nt":
            return False
        import sys
        import winreg
        from .. import APP_NAME
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
                if self.settings.start_with_windows:
                    if getattr(sys, "frozen", False):
                        command = f'"{sys.executable}"'
                    else:
                        script = Path(__file__).resolve().parent.parent.parent / "app.py"
                        command = f'"{sys.executable}" "{script}"'
                    if self.settings.start_minimized:
                        command += " --minimized"
                    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)
                else:
                    try:
                        winreg.DeleteValue(key, APP_NAME)
                    except FileNotFoundError:
                        pass
            return True
        except OSError as exc:
            self._notice(f"Could not change Windows startup: {exc}")
            return False

    def _language_changed(self, source: QComboBox) -> None:
        if self.recording or self.worker_state != "idle":
            self._sync_controls(); return
        self.settings.language = source.currentData()
        for combo in (self.language_combo, self.settings_language):
            combo.blockSignals(True); combo.setCurrentIndex(max(0, combo.findData(self.settings.language))); combo.blockSignals(False)
        self._save()
        self.statusBar().showMessage(f"Dictation language: {language_name(self.settings.language)}")

    def _model_changed(self) -> None:
        model = self.model_combo.currentData()
        if not model or model == self.settings.model:
            return
        if self.recording or self.worker_state != "idle":
            self._sync_controls(); return
        self.settings.model = model
        self.model_state = "missing"
        self.worker.request("unload")
        self._save()
        self._update_model_description()
        self._update_ui()

    def _threads_changed(self) -> None:
        self.settings.threads = self.threads_combo.currentData() or 4
        self._save()
        if not self.recording and self.worker_state == "idle":
            self.worker.request("unload")
            self.model_state = "missing"
            self._update_ui()

    def _hotkey_changed(self) -> None:
        value = self.hotkey_combo.currentData()
        if not value or value == self.settings.hotkey:
            return
        self.hotkeys.stop()
        self.settings.hotkey = value
        self.events = queue.Queue(maxsize=256)
        self.hotkeys = WindowsHotkeys(value, self.events)
        if not self.preview:
            self.hotkeys.start()
        self._save()
        self._update_ui()

    def _refresh_microphones(self) -> None:
        self.mic_combo.blockSignals(True)
        self.mic_combo.clear()
        self.mic_combo.addItem("System default microphone", "")
        for mic in microphones():
            self.mic_combo.addItem(mic.name + (" · default" if mic.default else ""), mic.name)
        index = self.mic_combo.findData(self.settings.microphone)
        self.mic_combo.setCurrentIndex(max(0, index))
        self.mic_combo.blockSignals(False)

    def _microphone_changed(self) -> None:
        self.settings.microphone = self.mic_combo.currentData() or ""
        self._save()

    def _save_vocabulary(self) -> None:
        rules, invalid = parse_dictionary(self.rules_edit.toPlainText())
        self.settings.vocabulary = self.rules_edit.toPlainText()[:12000]
        self.settings.hints = self.hints_edit.text().strip()[:1000]
        self._save()
        self.rules_status.setText(f"Saved {len(rules)} rules locally." + (f" Check these lines: {invalid}." if invalid else " Recognition hints saved too."))
        self.statusBar().showMessage("Vocabulary saved. It will be used for your next dictation.")

    def _update_model_description(self) -> None:
        spec = MODEL_CATALOG[self.settings.model]
        self.model_description.setText(spec.description + " Downloads are approximate and vary by model.")

    def _open_folder(self) -> None:
        app_directory().mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(app_directory())))

    def _open_licenses(self) -> None:
        import sys
        base = Path(getattr(sys, "_MEIPASS", ASSETS.parent.parent))
        path = base / "openflow" / "assets" / "licenses"
        if not path.exists():
            path = ASSETS / "licenses"
        if path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        else:
            QDesktopServices.openUrl(QUrl("https://github.com/Antoniscool123/Whisper/blob/main/THIRD_PARTY_NOTICES.md"))

    # ----- model lifecycle --------------------------------------------------------
    def _download_model(self) -> None:
        if self.recording or self.worker_state != "idle":
            return
        spec = MODEL_CATALOG[self.settings.model]
        cached = is_cached(spec.id)
        self.model_state = "loading" if cached else "downloading"
        self.progress.setRange(0, 0)
        self.progress.show()
        self.worker.request("load", model=spec.id, download=not cached, threads=self.settings.threads)
        self._update_ui()

    def _remove_model(self) -> None:
        if self.recording or self.worker_state != "idle":
            return
        spec = MODEL_CATALOG[self.settings.model]
        answer = QMessageBox.question(self, "Remove this model?",
            f"Remove {spec.label} and any partial download from this PC?\nYou can download it again for free. Your settings and transcripts are kept.")
        if answer != QMessageBox.Yes:
            return
        self.pending_remove = spec.id
        self.worker.request("unload")
        self._update_ui()

    def _worker_event(self, kind: str, payload) -> None:
        if kind == "state":
            self.worker_state = payload
            self._update_ui()
        elif kind == "progress":
            done, total = payload
            self.progress.setRange(0, 100)
            self.progress.setValue(int(done * 100 / total) if total else 0)
            self.progress.setFormat(f"{done / 1048576:.1f} / {total / 1048576:.1f} MB · %p%")
            self.setup_detail.setText("Downloading from the official Whisper repository. You can pause and resume.")
        elif kind == "model_ready":
            if payload == self.settings.model:
                self.model_state = "ready"
                self.statusBar().showMessage("Model ready. Your next dictation can run completely offline.")
            self._update_ui()
        elif kind == "model_unloaded":
            if self.pending_remove:
                try:
                    remove_model(self.pending_remove)
                    self.statusBar().showMessage("Model removed. Your settings and transcripts were kept.")
                except OSError as exc:
                    self._notice(f"Could not remove model: {exc}")
                self.pending_remove = None
            if self.model_state != "downloading":
                self.model_state = "missing"
            self._update_ui()
        elif kind == "result":
            self._result(*payload)
        elif kind == "cancelled":
            command, message = payload
            if command == "load":
                self.model_state = "missing"
            self.statusBar().showMessage(message)
            self._update_ui()
        elif kind == "error":
            command, message = payload
            if command == "load":
                self.model_state = "error"
                self.setup_detail.setText(message)
            self._notice(message)
            self._update_ui()

    # ----- dictation --------------------------------------------------------------
    def _toggle_recording(self) -> None:
        if self.recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self) -> None:
        if self.preview or self.recording or self.worker_state != "idle" or self.pasting:
            return
        if self.model_state != "ready":
            self._notice("Download and load a speech model first. It is free, and only needs internet once.")
            self._navigate(0)
            return
        self.integration.poll()
        target = self.integration.foreground()
        if not target or target.pid == getattr(self.integration, "pid", -1):
            target = self.integration.last_external
        self.record_settings = dataclasses.asdict(self.settings)
        self.pending_target = target
        try:
            self.recorder.start(self.settings.microphone)
        except Exception as exc:
            self._notice(str(exc)); return
        self.recording = True
        self.job_id = uuid.uuid4().hex
        self.latest.clear()
        self.detected.setText("Listening · audio stays in memory")
        self.timer_label.setText("00:00")
        self.mic_button.setIcon(make_icon("stop", "#42191E", 32))
        self.meter_timer.start(50)
        if self.tray:
            self.tray.setIcon(make_icon("mic", "#F87171", 32))
            self.tray.setToolTip("OpenFlow — recording")
        self.statusBar().showMessage("Recording. Release your hold shortcut or click the mic to finish. Ctrl+Alt+Escape cancels.")
        self._update_ui()

    def _stop_recording(self) -> None:
        if not self.recording:
            return
        self.recording = False
        self.meter_timer.stop()
        try:
            audio = self.recorder.stop()
        except Exception as exc:
            self._notice(f"Could not finish recording: {exc}")
            self._update_ui()
            return
        self.mic_button.setIcon(make_icon("mic", "#0B302B", 34))
        self.waveform.push(0, False)
        if self.tray:
            self.tray.setIcon(make_icon("mic", "#5EEAD4", 32))
            self.tray.setToolTip("OpenFlow — transcribing")
        if len(audio) < 4000:
            self.statusBar().showMessage("That was too short. Hold the shortcut while you speak, then release it.")
            self._update_ui(); return
        self.worker_state = "transcribing"
        self.worker.request("transcribe", audio=audio, settings=self.record_settings, job_id=self.job_id)
        self._update_ui()

    def _cancel(self) -> None:
        if self.recording:
            self.recording = False
            self.recorder.cancel()
            self.meter_timer.stop()
            self.mic_button.setIcon(make_icon("mic", "#0B302B", 34))
            self.waveform.push(0, False)
            self.statusBar().showMessage("Recording cancelled. Audio discarded.")
        elif self.worker_state == "transcribing":
            self.worker.cancel_transcription()
            self.statusBar().showMessage("Cancelling transcription…")
        elif self.worker_state in ("downloading", "loading"):
            self.worker.cancel_download()
        self._update_ui()

    def _result(self, result, settings: dict, job_id: str) -> None:
        if job_id != self.job_id:
            return
        text = tidy_text(result.text, fillers=settings["clean_fillers"], commands=settings["voice_commands"],
                         dictionary=settings["vocabulary"], language=result.language)
        if not text:
            self.detected.setText("No speech recognized")
            self.statusBar().showMessage("No clear speech found. Check the microphone, move closer, and try again.")
            self._update_ui(); return
        self.latest.setPlainText(text)
        confidence = f" · {result.probability:.0%}" if settings["language"] == "auto" else ""
        self.detected.setText(f"{language_name(result.language)}{confidence} · {result.seconds:.1f}s audio · {result.inference_seconds:.1f}s processing")
        try:
            self.history.add(text, result.language, result.seconds, settings["save_history"])
        except OSError as exc:
            self._notice(f"Transcript ready, but history could not be saved: {exc}")
        self._update_stats()
        self._refresh_history()
        if self.tray:
            self.tray.setToolTip("OpenFlow — ready")
        self.statusBar().showMessage(f"Done · {word_count(text)} words · processed locally")
        if settings["auto_paste"] and os.name == "nt":
            self._paste(text, self.pending_target, settings["restore_clipboard"], require_same=True)
        else:
            QApplication.clipboard().setText(text)
            self.statusBar().showMessage("Transcript ready and copied. Click in your app and press Ctrl+V.")
        self._update_ui()

    def _update_text_buttons(self) -> None:
        has_text = bool(self.latest.toPlainText().strip())
        self.copy_button.setEnabled(has_text and not self.recording)
        self.insert_button.setEnabled(has_text and not self.recording and not self.pasting)

    def _copy_latest(self) -> None:
        text = self.latest.toPlainText().strip()
        if text:
            QApplication.clipboard().setText(text)
            self.statusBar().showMessage("Copied to clipboard.")

    def _insert_latest(self) -> None:
        text = self.latest.toPlainText().strip()
        if not text or self.pasting:
            return
        if os.name != "nt":
            self._copy_latest(); return
        self.integration.poll()
        self._paste(text, self.integration.last_external, self.settings.restore_clipboard, require_same=False)

    def _paste(self, text: str, target, restore: bool, require_same: bool) -> None:
        if self.pasting or not target:
            QApplication.clipboard().setText(text)
            self.statusBar().showMessage("Text copied. No previous app was identified; paste with Ctrl+V.")
            return
        self.pasting = True
        self._update_ui()
        def run():
            try:
                if require_same and not self.integration.same_target(target):
                    outcome = "focus_changed"
                else:
                    outcome = self.integration.paste(text, target, restore)
            except Exception as exc:
                LOG.error("Text insertion failed: %s", type(exc).__name__)
                outcome = "copied_blocked"
            self.paste_signals.finished.emit(outcome)
        threading.Thread(target=run, name="openflow-paste", daemon=True).start()

    def _paste_done(self, outcome: str) -> None:
        self.pasting = False
        messages = {
            "inserted": "Inserted into your app. Previous text clipboard restored when possible.",
            "focus_changed": "Focus changed, so nothing was pasted into the wrong app. Your text is copied; press Ctrl+V.",
            "no_target": "The original app is no longer available. Your text is copied; press Ctrl+V.",
            "clipboard_busy": "Another app is holding the clipboard. Use Copy text and try again.",
            "copied_blocked": "Windows blocked automatic pasting. Your text is copied; press Ctrl+V manually.",
            "unavailable": "Automatic insertion is supported on Windows. Text copied instead.",
        }
        if outcome != "inserted" and outcome != "clipboard_busy":
            text = self.latest.toPlainText().strip()
            if text:
                QApplication.clipboard().setText(text)
        self.statusBar().showMessage(messages.get(outcome, "Text is ready."))
        self._update_ui()

    def _update_meter(self) -> None:
        if not self.recording:
            return
        level, seconds, overflows = self.recorder.snapshot()
        self.waveform.push(level, True)
        self.timer_label.setText(f"{int(seconds // 60):02d}:{int(seconds % 60):02d}")
        if overflows:
            self.detected.setText(f"Listening · {overflows} audio buffer overflow(s); try closing heavy apps")
        if seconds >= 600:
            self._stop_recording()
            self.statusBar().showMessage("Ten-minute safety limit reached. Your recording is being transcribed.")

    def _pump_events(self) -> None:
        for _ in range(50):
            try:
                kind, payload = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "info":
                self.statusBar().showMessage(payload)
            elif kind == "hotkey":
                if payload == "press" and not self.recording:
                    self._start_recording()
                elif payload == "release" and self.recording:
                    self._stop_recording()
                elif payload == "toggle":
                    self._toggle_recording()
                elif payload == "cancel":
                    self._cancel()

    def _update_ui(self) -> None:
        busy = self.worker_state != "idle"
        ready = self.model_state == "ready"
        spec = MODEL_CATALOG[self.settings.model]
        short = spec.label.split(" · ")[0]
        state_label = {"ready": "ready", "missing": "not downloaded", "loading": "loading",
                       "downloading": "downloading", "error": "needs attention"}.get(self.model_state, self.model_state)
        self.model_chip.setText(f"{short} · {state_label}")
        self.mic_button.setEnabled(not self.preview and (self.recording or (ready and not busy and not self.pasting)))
        self.mic_button.setProperty("state", "recording" if self.recording else "idle")
        self.mic_button.style().unpolish(self.mic_button); self.mic_button.style().polish(self.mic_button)
        self.language_combo.setEnabled(not busy and not self.recording)
        for widget in self.busy_controls:
            widget.setEnabled(not busy and not self.recording and not self.pending_remove)
        self.startup_check.setEnabled(os.name == "nt")
        self.copy_button.setEnabled(bool(self.latest.toPlainText().strip()) and not self.recording)
        self.insert_button.setEnabled(bool(self.latest.toPlainText().strip()) and not self.recording and not self.pasting)
        self.setup.setVisible(not ready)
        self.setup_cancel.setVisible(self.worker_state in ("downloading", "loading"))
        self.download_button.setEnabled(not busy and not self.pending_remove)
        self.download_button.setText("Load model" if is_cached(spec.id) else "Download model")
        self.progress.setVisible(self.worker_state in ("downloading", "loading"))
        if self.model_state == "missing":
            self.setup_title.setText("One download. Then completely offline.")
            size = f"~{spec.megabytes:,} MB" if spec.megabytes < 1000 else f"~{spec.megabytes / 1000:.1f} GB"
            self.setup_detail.setText(f"Get the free {short} model ({size}). Danish + 99 other language choices. No subscription.")
        elif self.model_state == "loading":
            self.setup_title.setText("Getting your local engine ready…")
            self.setup_detail.setText("Verifying and loading the model. No microphone audio is being recorded.")
        elif self.model_state == "downloading":
            self.setup_title.setText("Downloading your free speech model…")
        if self.recording:
            self.hero_title.setText("Listening. Just speak.")
            self.hero_subtitle.setText(f"Release {HOTKEYS[self.settings.hotkey].label.removeprefix('Hold ')} or click the mic to finish. Up to 10 minutes.")
            self.engine_pill.set_status("●  Recording", "#FCA5A5")
            self.cancel_action.setText("Cancel recording"); self.cancel_action.show()
        elif self.worker_state == "transcribing":
            self.hero_title.setText("Turning speech into text…")
            self.hero_subtitle.setText("Running locally on your CPU. Your audio never leaves this device.")
            self.engine_pill.set_status("●  Transcribing", "#93C5FD")
            self.cancel_action.setText("Cancel transcription"); self.cancel_action.show()
        elif busy:
            self.hero_title.setText("Preparing your local engine…")
            self.hero_subtitle.setText("The first setup needs internet. After that, dictation works offline.")
            self.engine_pill.set_status("●  Preparing", "#FCD34D")
            self.cancel_action.hide()
        else:
            self.hero_title.setText("Ready when you are" if ready else "Your free voice studio awaits")
            self.hero_subtitle.setText(f"{HOTKEYS[self.settings.hotkey].label} in any app, or click the mic. Ctrl+Alt+Space toggles hands-free."
                                       if ready else "Download a model below to start. No account or payment details needed.")
            self.engine_pill.set_status("●  Local · ready" if ready else "●  Setup needed", "#5EEAD4" if ready else "#FCD34D")
            self.cancel_action.hide()
        if not self.recording and self.worker_state == "idle":
            self.timer_label.setText("00:00")

    # ----- history and lifecycle --------------------------------------------------
    def _update_stats(self) -> None:
        self.words_stat.setText(f"{self.history.today_words():,}")
        today = time.localtime()
        count = sum(time.localtime(e.created).tm_yday == today.tm_yday and time.localtime(e.created).tm_year == today.tm_year
                    for e in self.history.entries)
        self.sessions_stat.setText(f"{count:,}")
        if not self.settings.save_history:
            self.words_stat.setToolTip("History is off. Existing saved entries are still counted.")

    def _refresh_history(self) -> None:
        clear_layout(self.history_cards)
        if not self.history.entries:
            empty = Card()
            empty.layout_.addWidget(label("A fresh start.", "SectionTitle"))
            empty.layout_.addWidget(label("Your dictations will appear here. You can turn history off in Settings.", "Muted", True))
            self.history_cards.addWidget(empty)
            return
        for entry in self.history.entries:
            card = Card(margins=(16, 12, 16, 12), spacing=7)
            top = QHBoxLayout()
            when = time.strftime("%d %b · %H:%M", time.localtime(entry.created))
            top.addWidget(label(f"{when}  ·  {language_name(entry.language)}  ·  {entry.seconds:.1f}s  ·  {word_count(entry.text)} words", "Small"))
            top.addStretch()
            copy = button("Copy", "copy", "Ghost")
            copy.clicked.connect(lambda checked=False, text=entry.text: (QApplication.clipboard().setText(text), self.statusBar().showMessage("Transcript copied.")))
            delete = button("Delete", None, "Ghost")
            delete.clicked.connect(lambda checked=False, entry_id=entry.id: self._delete_entry(entry_id))
            top.addWidget(copy); top.addWidget(delete)
            card.layout_.addLayout(top)
            text = label(entry.text, wrap=True)
            text.setTextInteractionFlags(Qt.TextSelectableByMouse)
            card.layout_.addWidget(text)
            self.history_cards.addWidget(card)

    def _delete_entry(self, entry_id: str) -> None:
        try:
            self.history.delete(entry_id)
        except OSError as exc:
            self._notice(str(exc)); return
        self._refresh_history(); self._update_stats()

    def _clear_history(self) -> None:
        if QMessageBox.question(self, "Clear local history?", "Delete all saved transcripts from this device? This cannot be undone.") != QMessageBox.Yes:
            return
        try:
            self.history.clear()
        except OSError as exc:
            self._notice(str(exc)); return
        self._refresh_history(); self._update_stats()

    def _notice(self, message: str) -> None:
        self.statusBar().showMessage(message)
        if self.isVisible() and not self.preview:
            QMessageBox.warning(self, "OpenFlow", message)
        elif self.tray:
            self.tray.showMessage("OpenFlow", message, QSystemTrayIcon.Warning, 6000)

    def show_window(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event) -> None:
        if self.settings.minimize_to_tray and self.tray and not self.really_close:
            event.ignore()
            self.hide()
            self.tray.showMessage("OpenFlow is still here", "Dictation shortcuts still work. Use the tray icon to reopen or quit.", QSystemTrayIcon.Information, 3500)
        else:
            self.quit()
            event.ignore()

    def quit(self) -> None:
        if self.really_close:
            return
        self.really_close = True
        if self.preview:
            QApplication.quit(); return
        self.recording = False
        self.recorder.cancel()
        self.hotkeys.stop()
        for timer in (self.event_timer, self.focus_timer, self.meter_timer):
            timer.stop()
        self.worker.stop()
        if self.tray:
            self.tray.hide()
        QApplication.quit()
