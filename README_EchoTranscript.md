# EchoTranscript Android 1.0.1

On-device user interface for **online** transcription of an imported audio recording (.m4a, .mp3, .wav) with the OpenAI Audio API.

Build: switch to `echo-transcript-android` branch and open **Actions > EchoTranscript Android APK**. After a successful run open **Artifacts > EchoTranscript-1.0.1-debug-apk**.

- Android 8.0+ (min SDK 26).
- Audio is uploaded to OpenAI. The app does not change or delete the original recording.
- A separately billed OpenAI API key is required; the ChatGPT subscription is unrelated.
- Only one file can be processed at a time, maximum 25 MB per audio upload.
- Transcript is saved to an explicitly chosen TXT destination. Check accuracy before relying on exact quotes.
- Original files are not included in the APK or repository.
- No speaker diarization, timestamps, or offline speech recognition.
- The API key is never written to disk or logs, and this application explicitly disables backup.

**Privacy:** Do not upload conversations without considering the privacy rights and consent requirements applicable to the recording.
