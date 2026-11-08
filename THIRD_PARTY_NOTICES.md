# Third-party notices

OpenFlow's original code and icon are distributed under the MIT license in `LICENSE`. The combined Windows executable also contains third-party software with its own licenses. Model weights are not included in the executable; they are downloaded separately from the official Whisper.cpp repository.

| Component | Role | Upstream / license information |
|---|---|---|
| Python 3.11 | Runtime | https://www.python.org/ — Python Software Foundation License |
| PySide6 Essentials / Qt 6 | GUI | https://code.qt.io/cgit/pyside/pyside-setup.git/ — LGPL-3.0-only / GPL commercial alternatives; this project uses the LGPL distribution |
| whisper.cpp | Native inference | https://github.com/ggml-org/whisper.cpp — MIT |
| pywhispercpp | Python bindings | https://github.com/absadiki/pywhispercpp — MIT |
| NumPy | Audio arrays | https://github.com/numpy/numpy — BSD-3-Clause |
| sounddevice | Microphone capture | https://github.com/spatialaudio/python-sounddevice — MIT |
| PortAudio | Native audio I/O | https://github.com/PortAudio/portaudio — MIT-style license |
| requests | Model downloads | https://github.com/psf/requests — Apache-2.0 |
| tqdm | Binding dependency | https://github.com/tqdm/tqdm — MPL-2.0 and MIT portions |
| platformdirs | Binding dependency | https://github.com/tox-dev/platformdirs — MIT |
| PyInstaller | Executable bootloader/build tool | https://github.com/pyinstaller/pyinstaller — GPL-2.0-or-later with bootloader exception; the exception permits distributing the combined application under its own license |
| OpenAI Whisper model weights | Speech recognition | https://github.com/openai/whisper and https://huggingface.co/ggerganov/whisper.cpp — MIT model release; downloaded separately |

The installed Python distributions include their upstream copyright and license texts in their `*.dist-info` metadata. The build also packages available Qt license files. Upstream projects remain the authoritative source for their license texts and corresponding source code.

## Qt / PySide6 LGPL notice

This application uses the LGPL-licensed PySide6/Qt libraries, dynamically loaded from the packaged application. You may inspect, modify and replace those libraries as permitted by LGPL-3.0. The corresponding Qt/PySide6 source and license texts are available from https://code.qt.io/ and https://download.qt.io/official_releases/QtForPython/ . OpenFlow does not impose restrictions on reverse engineering for debugging modifications to these libraries. The original OpenFlow application source is included in this repository.

Relevant license texts:

- LGPL-3.0: https://www.gnu.org/licenses/lgpl-3.0.txt
- GPL-3.0: https://www.gnu.org/licenses/gpl-3.0.txt
- MIT: https://opensource.org/license/mit
- BSD-3-Clause: https://opensource.org/license/bsd-3-clause
- Apache-2.0: https://www.apache.org/licenses/LICENSE-2.0
- PyInstaller bootloader exception: https://github.com/pyinstaller/pyinstaller/blob/develop/COPYING.txt

No endorsement by OpenAI, Wispr, Qt or any upstream contributor is implied.
