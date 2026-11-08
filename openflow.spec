# Build on Windows x64 with Python 3.11. Models are downloaded separately.
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs

block_cipher = None
datas = [('openflow/assets', 'openflow/assets')]
binaries = []
hiddenimports = ['_pywhispercpp', 'pywhispercpp.model', 'pywhispercpp.constants',
                 'pywhispercpp.utils', 'sounddevice', 'numpy', 'requests', 'tqdm',
                 'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets']
for package in ('pywhispercpp', 'sounddevice'):
    package_datas, package_binaries, package_hidden = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hidden
# Delvewheel places the native whisper/ggml DLLs in the wheel's platlib.
# collect_dynamic_libs also finds these when PyInstaller installs the wheel.
binaries += collect_dynamic_libs('pywhispercpp')

excludes = ['tkinter', 'matplotlib', 'pandas', 'scipy', 'torch', 'transformers',
            'IPython', 'pytest', 'PIL', 'PySide6.QtQml', 'PySide6.QtQuick',
            'PySide6.QtQuick3D', 'PySide6.QtQuickWidgets', 'PySide6.QtWebEngineCore',
            'PySide6.QtWebEngineWidgets', 'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets',
            'PySide6.QtPdf', 'PySide6.QtPdfWidgets', 'PySide6.QtCharts',
            'PySide6.QtDataVisualization', 'PySide6.QtVirtualKeyboard',
            'PySide6.QtBluetooth', 'PySide6.QtNfc', 'PySide6.QtSerialPort',
            'PySide6.QtPositioning', 'PySide6.QtSensors', 'PySide6.QtWebSockets',
            'PySide6.QtDesigner', 'PySide6.QtHelp', 'PySide6.QtTest',
            'PySide6.QtSql', 'PySide6.QtXml', 'PySide6.QtNetwork', 'PySide6.QtOpenGL',
            'PySide6.QtOpenGLWidgets', 'PySide6.QtSvg', 'PySide6.QtSvgWidgets',
            'PySide6.QtUiTools', 'PySide6.QtPrintSupport', 'PySide6.QtDBus']

a = Analysis(
    ['app.py'], pathex=[], binaries=binaries, datas=datas,
    hiddenimports=hiddenimports, hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=excludes, noarchive=False, optimize=1, cipher=block_cipher,
)
# Keep the executable lean: this app uses Qt Widgets, not QML/Quick or ffmpeg.
# Filter by basename so both Windows DLLs and Linux shared objects are handled.
unused_prefixes = ('qt6qml', 'qt6quick', 'qt6quick3d', 'qt6virtualkeyboard',
                   'qt6pdf', 'qt6charts', 'qt6datavisualization', 'qt6multimedia',
                   'qt6bluetooth', 'qt6nfc', 'qt6serialport', 'qt6positioning',
                   'qt6sensors', 'qt6websockets', 'qt6designer', 'qt6help',
                   'qt6test', 'qt6sql', 'qt6xml', 'qt6network', 'qt6opengl',
                   'qt6svg', 'qt6dbus', 'qt6printsupport', 'qt6shadertools')
a.binaries = [entry for entry in a.binaries
              if not os.path.basename(entry[0]).lower().startswith(unused_prefixes)]
# Exclude QML plugin trees and translation catalogues; all UI languages use
# native script labels, and Whisper itself supports the 100 speech languages.
a.datas = [entry for entry in a.datas
           if not any(part.lower() in {'qml', 'translations'} for part in Path(entry[0]).parts)]
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name='OpenFlow', debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, upx_exclude=[], runtime_tmpdir=None,
    console=False, disable_windowed_traceback=False,
    argv_emulation=False, target_arch=None, codesign_identity=None,
    entitlements_file=None, icon='openflow/assets/icon.ico',
    version='windows_version.txt',
)
