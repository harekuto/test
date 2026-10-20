package com.harekuto.echotranscript;

import android.app.Activity;
import android.os.Bundle;
import android.content.Intent;
import android.net.Uri;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.text.InputType;
import android.provider.OpenableColumns;
import android.database.Cursor;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import org.json.JSONObject;

public final class MainActivity extends Activity {
    private static final int PICK = 1;
    private static final int SAVE = 2;
    private static final long MAX_BYTES = 25_000_000L;
    private Uri audio;
    private EditText key;
    private EditText result;
    private TextView status;
    private Button run;
    private String name = "recording.m4a";
    private volatile boolean busy = false;

    @Override
    public void onCreate(Bundle state) {
        super.onCreate(state);
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        int pad = Math.round(getResources().getDisplayMetrics().density * 18);
        layout.setPadding(pad, pad, pad, pad);
        ScrollView sc = new ScrollView(this);
        sc.setFillViewport(true);
        sc.addView(layout);
        setContentView(sc);

        TextView title = new TextView(this);
        title.setText("EchoTranscript");
        title.setTextSize(25);
        title.setPadding(0, 0, 0, pad / 2);
        layout.addView(title);

        TextView info = new TextView(this);
        info.setText("Audio → text • Звук → текст\n\nSelect M4A/MP3/WAV from EchoVault. Online recognition uploads the selected audio to OpenAI and requires a separately billed API key. Original recordings are never deleted.");
        layout.addView(info);

        key = new EditText(this);
        key.setHint("OpenAI API key (not saved)");
        key.setSingleLine(true);
        key.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        layout.addView(key);

        Button pick = new Button(this);
        pick.setText("Choose audio / Выбрать аудио");
        layout.addView(pick);

        status = new TextView(this);
        status.setText("No audio selected");
        status.setPadding(0, pad / 2, 0, pad / 2);
        layout.addView(status);

        run = new Button(this);
        run.setText("Transcribe / Распознать");
        layout.addView(run);

        Button save = new Button(this);
        save.setText("Save TXT / Сохранить текст");
        layout.addView(save);

        result = new EditText(this);
        result.setHint("Full transcript will appear here");
        result.setMinLines(14);
        result.setGravity(Gravity.TOP);
        result.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_MULTI_LINE | InputType.TYPE_TEXT_FLAG_CAP_SENTENCES);
        layout.addView(result);

        pick.setOnClickListener(v -> {
            if (busy) return;
            Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT);
            i.setType("audio/*");
            i.addCategory(Intent.CATEGORY_OPENABLE);
            startActivityForResult(i, PICK);
        });
        run.setOnClickListener(v -> transcribe());
        save.setOnClickListener(v -> {
            if (result.length() == 0) {
                status.setText("No transcript to save");
                return;
            }
            Intent i = new Intent(Intent.ACTION_CREATE_DOCUMENT);
            i.setType("text/plain");
            i.addCategory(Intent.CATEGORY_OPENABLE);
            String safeName = name.replaceFirst("\\.[^.]+$", "");
            i.putExtra(Intent.EXTRA_TITLE, safeName + ".txt");
            startActivityForResult(i, SAVE);
        });
        if (state != null) {
            name = state.getString("name", name);
            result.setText(state.getString("transcript", ""));
            status.setText(state.getString("status", "Choose an audio file"));
            String uri = state.getString("audioUri");
            if (uri != null) audio = Uri.parse(uri);
        }
    }

    @Override
    protected void onSaveInstanceState(Bundle out) {
        super.onSaveInstanceState(out);
        out.putString("name", name);
        out.putString("transcript", result.getText().toString());
        out.putString("status", status.getText().toString());
        if (audio != null) out.putString("audioUri", audio.toString());
    }

    @Override
    protected void onActivityResult(int req, int res, Intent data) {
        super.onActivityResult(req, res, data);
        if (res != RESULT_OK || data == null || data.getData() == null) return;
        if (req == PICK) {
            audio = data.getData();
            try {
                getContentResolver().takePersistableUriPermission(audio, Intent.FLAG_GRANT_READ_URI_PERMISSION);
            } catch (SecurityException ignored) { }
            name = "recording.m4a";
            try (Cursor c = getContentResolver().query(audio, new String[]{OpenableColumns.DISPLAY_NAME}, null, null, null)) {
                if (c != null && c.moveToFirst() && c.getString(0) != null) name = c.getString(0);
            } catch (Exception ignored) { }
            status.setText("Selected: " + name);
        } else if (req == SAVE) {
            try (OutputStream out = getContentResolver().openOutputStream(data.getData(), "wt")) {
                if (out == null) throw new IOException("Destination unavailable");
                out.write(result.getText().toString().getBytes(StandardCharsets.UTF_8));
                status.setText("Transcript saved successfully");
            } catch (Exception e) {
                status.setText("Save failed: " + e.getMessage());
            }
        }
    }

    private void transcribe() {
        if (busy) return;
        if (audio == null) { status.setText("Choose an audio file first"); return; }
        String token = key.getText().toString().trim();
        if (token.isEmpty()) { status.setText("Enter your OpenAI API key"); return; }
        busy = true;
        run.setEnabled(false);
        status.setText("Uploading and transcribing. Keep the app open…");
        final Uri selected = audio;
        final String selectedName = name;
        new Thread(() -> {
            try {
                String transcription = send(token, selected, selectedName);
                runOnUiThread(() -> {
                    result.setText(transcription);
                    status.setText("Complete. Review transcription before quoting it.");
                    busy = false;
                    run.setEnabled(true);
                });
            } catch (Exception ex) {
                String error = ex.getMessage();
                runOnUiThread(() -> {
                    status.setText("Transcription error: " + error);
                    busy = false;
                    run.setEnabled(true);
                });
            }
        }, "EchoTranscript-Uploader").start();
    }

    private String send(String token, Uri selected, String selectedName) throws Exception {
        String boundary = "EchoTranscriptBoundary" + System.nanoTime();
        HttpURLConnection c = (HttpURLConnection) new URL("https://api.openai.com/v1/audio/transcriptions").openConnection();
        c.setRequestMethod("POST");
        c.setConnectTimeout(30000);
        c.setReadTimeout(600000);
        c.setDoOutput(true);
        c.setChunkedStreamingMode(65536);
        c.setRequestProperty("Authorization", "Bearer " + token);
        c.setRequestProperty("Content-Type", "multipart/form-data; boundary=" + boundary);
        try {
            try (OutputStream out = c.getOutputStream()) {
                field(out, boundary, "model", "gpt-4o-transcribe");
                String fileName = selectedName.replace("\r", "_").replace("\n", "_").replace("\"", "_");
                String mime = fileName.toLowerCase().endsWith(".wav") ? "audio/wav" :
                              fileName.toLowerCase().endsWith(".mp3") ? "audio/mpeg" : "audio/mp4";
                out.write(("--" + boundary + "\r\nContent-Disposition: form-data; name=\"file\"; filename=\"" + fileName + "\"\r\nContent-Type: " + mime + "\r\n\r\n").getBytes(StandardCharsets.UTF_8));
                long total = 0;
                try (InputStream in = getContentResolver().openInputStream(selected)) {
                    if (in == null) throw new IOException("Cannot open audio");
                    byte[] buf = new byte[65536];
                    int n;
                    while ((n = in.read(buf)) != -1) {
                        total += n;
                        if (total > MAX_BYTES) throw new IOException("Audio exceeds 25 MB. Split the file before upload.");
                        out.write(buf, 0, n);
                    }
                }
                out.write(("\r\n--" + boundary + "--\r\n").getBytes(StandardCharsets.UTF_8));
            }
            int code = c.getResponseCode();
            InputStream stream = (code < 300) ? c.getInputStream() : c.getErrorStream();
            if (stream == null) throw new IOException("HTTP " + code + " without response");
            try (InputStream in = stream) {
                ByteArrayOutputStream b = new ByteArrayOutputStream();
                byte[] buf = new byte[8192];
                int n;
                while ((n = in.read(buf)) != -1) {
                    if (b.size() + n > 1_000_000) throw new IOException("Server response too large");
                    b.write(buf, 0, n);
                }
                String response = b.toString("UTF-8");
                if (code >= 300) {
                    try {
                        JSONObject error = new JSONObject(response).optJSONObject("error");
                        String message = error == null ? "Request rejected" : error.optString("message", "Request rejected");
                        throw new IOException("HTTP " + code + ": " + message);
                    } catch (org.json.JSONException ignored) {
                        throw new IOException("HTTP " + code + ": " + response.substring(0, Math.min(200, response.length())));
                    }
                }
                return new JSONObject(response).getString("text");
            }
        } finally {
            c.disconnect();
        }
    }

    private static void field(OutputStream out, String boundary, String n, String v) throws IOException {
        out.write(("--" + boundary + "\r\nContent-Disposition: form-data; name=\"" + n + "\"\r\n\r\n" + v + "\r\n").getBytes(StandardCharsets.UTF_8));
    }
}
