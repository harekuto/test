# Echo Transcript — Offline Android Transcriber

An Android (arm64, API 26+) application for locally transcribing long private recordings, including EchoVault M4A and ZIP exports.

- Import single or multiple audio files and ZIP archives via Android Storage Access Framework.
- Decode M4A/AAC (and other Android-supported audio) to 16 kHz mono PCM on-device.
- Download a multilingual Whisper GGML model **to the phone only** (Tiny ~75 MB / Base ~142 MB / Small ~466 MB).
- Offline local transcription in overlapping 28-second slices; partial results are committed to app storage after each slice.
- Pause after the current slice; resume from an existing checkpoint; export timestamped TXT and SRT.
- Original files are copied to private app storage and are never overwritten by the app.
- No cloud speech service, API token, advertising or analytics. **Do not upload private recordings to GitHub.**

## Usage

Install `EchoTranscript-debug.apk`. Import the ZIP with your three recordings. Choose the multilingual **Base** model for better Kazakh/Russian than Tiny (accuracy is not guaranteed; code-switching and speaker overlap can cause mistakes). Download the model over Wi-Fi. Select a recording, set language to Auto / Russian / Kazakh, and tap Start / Resume. Keep the application open with the screen on while transcribing. The transcript is saved after every 28-second chunk. Export TXT after finishing, and upload **only the text** to ChatGPT for analysis.

## Build

Android SDK 35, JDK 17, Gradle 8.11.1. Run `gradle :app:testDebugUnitTest :app:assembleDebug`. GitHub Actions builds an APK artifact on push to the dedicated branch.

## Limitations

- Only **arm64-v8a** is supported by the free Whisper Android binary.
- Whisper is probabilistic and may omit or hallucinate speech, especially inaudible recordings and overlapping voices. It does not identify individual speakers.
- Android can stop apps when backgrounded; leave the screen on. Partial transcript is persisted, but an unfinished audio conversion restarts after interruption.
- The imported audio and generated text stay in app-private files; **uninstalling Android apps removes their private data**. Export your text separately.
- Model downloads require internet once. Speech transcription does not.
- Long recordings may need free space for an uncompressed PCM copy (about 115 MB per hour) during processing.

Implementation is independently authored and integrates `dev.ffmpegkit-maintained:whisper-android:1.0.0` (MIT).
