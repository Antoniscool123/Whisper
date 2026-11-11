# OpenFlow 1.2.0

Free, local, multilingual voice typing for Windows 10/11 x64. Danish is the default, with 100 Whisper language choices. No account, subscription, API key or word limit.

## Install

1. Download `OpenFlow.exe` below and place it in a folder you own.
2. Launch it. If SmartScreen warns about an unknown publisher, inspect the source and verify the SHA-256 checksum before choosing **More info → Run anyway**. This build is unsigned; do not disable antivirus protection.
3. Click **Download model** to get the recommended Small model (~181 MB, one time).
4. Allow microphone access, click in your target app, hold **Right Ctrl**, speak, and release.

After the model is downloaded, dictation works offline. Models are separate from the executable. The app is a Wispr Flow-style open-source alternative, not an affiliated or feature-identical clone; it does not provide cloud LLM rewriting or screen-context capture.

## What's new in 1.2.0

- Experimental faster processing of short recordings (on by default; turn off in Settings if recognition gets worse).
- Quiet speech is gently boosted without clipping, and cleared vocabulary hints no longer persist accidentally.
- For Danish, select Danish rather than Auto to avoid an extra language-detection pass. Small remains the default quality model; Base is faster but may be less accurate.

## Previous improvements

- Fix model loading in the windowed executable when standard error is unavailable.
- A non-activating, always-on-top status overlay shows dictation state. Disable it in Settings if desired.
- Fix Windows clipboard insertion. Automatic insertion requires the original target to stay focused; unsupported or elevated apps may require manual paste.

## Included

- Hold-to-talk and hands-free dictation; Ctrl+Alt+Space toggles, Ctrl+Alt+Escape cancels
- Focus-aware Windows text insertion and clipboard fallback
- Danish/multilingual speech recognition, optional hesitation cleanup and spoken punctuation
- Personal vocabulary, recognition hints, editable transcript and optional local history
- Tray mode, optional Windows startup, seven local Whisper model choices
- Resumable, SHA-256-verified model downloads

See README.md for privacy details, limitations, source build instructions and testing notes. `SHA256SUMS.txt` contains the executable checksum.
