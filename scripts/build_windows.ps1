# Run from the repository root in Windows PowerShell. Python 3.11 x64 required.
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true
python -c "import sys,struct; assert sys.version_info[:2]==(3,11) and struct.calcsize('P')==8, 'Use 64-bit Python 3.11'"
python -m pip install --upgrade pip
python -m pip install -r requirements-build.txt
python scripts/make_icon.py
python -m PyInstaller --clean --noconfirm openflow.spec
if (!(Test-Path "dist/OpenFlow.exe")) { throw "OpenFlow.exe was not produced" }
$hash = (Get-FileHash "dist/OpenFlow.exe" -Algorithm SHA256).Hash.ToLower()
"$hash  OpenFlow.exe" | Set-Content -Encoding ascii "dist/SHA256SUMS.txt"
Write-Host "Built dist/OpenFlow.exe $((Get-Item dist/OpenFlow.exe).Length) bytes"
Write-Host "SHA256: $hash"
