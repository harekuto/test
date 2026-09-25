package com.nekobot.rpgnekos;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.util.Log;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.ConsoleMessage;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;

public class MainActivity extends Activity {
    private static final String TAG = "RPGWEB";
    private static final String GAME_URL = "file:///android_asset/www/index.html";
    private static final String[] PATCH_ASSETS = {
        "patches/nekobot-pixi-texture-patch.js",
        "patches/nekobot-rpgmaker-mz-mobile-patch.js",
        "patches/nekobot-mobile-ogg-audio-patch.js"
    };

    private WebView webView;
    private String runtimePatches;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        configureWindow();
        runtimePatches = readRuntimePatches();
        webView = new WebView(this);
        webView.setBackgroundColor(Color.BLACK);
        webView.setLayerType(View.LAYER_TYPE_HARDWARE, null);
        setContentView(webView);
        configureWebView(webView);
        webView.loadUrl(GAME_URL);
    }

    @SuppressLint("SetJavaScriptEnabled")
    private void configureWebView(WebView view) {
        WebSettings settings = view.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(false);
        settings.setAllowFileAccessFromFileURLs(true);
        settings.setAllowUniversalAccessFromFileURLs(false);
        settings.setLoadWithOverviewMode(true);
        settings.setUseWideViewPort(true);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);
        WebView.setWebContentsDebuggingEnabled(BuildConfig.DEBUG);

        view.setWebViewClient(new LocalContentWebViewClient());
        view.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onConsoleMessage(ConsoleMessage message) {
                Log.d(TAG, message.message() + " @" + message.sourceId() + ":" + message.lineNumber());
                return true;
            }
        });
    }

    private final class LocalContentWebViewClient extends WebViewClient {
        @Override
        public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
            Uri uri = request.getUrl();
            return !"file".equals(uri.getScheme());
        }

        @Override
        public void onPageFinished(WebView view, String url) {
            super.onPageFinished(view, url);
            Log.i(TAG, "PAGE_FINISHED " + url);
            injectRuntimePatches(view);
        }

        @Override
        public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
            Log.e(TAG, "WEB_ERROR " + request.getUrl() + " " + error);
            super.onReceivedError(view, request, error);
        }
    }

    private void injectRuntimePatches(WebView view) {
        if (runtimePatches == null || runtimePatches.trim().isEmpty()) return;
        view.evaluateJavascript(runtimePatches, null);
    }

    private String readRuntimePatches() {
        StringBuilder builder = new StringBuilder();
        for (String assetPath : PATCH_ASSETS) {
            builder.append(readAsset(assetPath)).append('\n');
        }
        return builder.toString();
    }

    private String readAsset(String assetPath) {
        try (InputStream input = getAssets().open(assetPath);
             BufferedReader reader = new BufferedReader(new InputStreamReader(input, StandardCharsets.UTF_8))) {
            StringBuilder builder = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) builder.append(line).append('\n');
            return builder.toString();
        } catch (IOException error) {
            return "";
        }
    }

    private void sendEscapeToGame() {
        if (webView == null) return;
        webView.evaluateJavascript(
            "(function(){try{" +
            "if(window.Input&&Input._onKeyDown){Input._onKeyDown({keyCode:88,preventDefault:function(){}});" +
            "setTimeout(function(){Input._onKeyUp({keyCode:88});},80);return 'ok';}" +
            "}catch(e){console.error(e);}return 'no';})()", null);
    }

    private void configureWindow() {
        getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN, WindowManager.LayoutParams.FLAG_FULLSCREEN);
        getWindow().getDecorView().setSystemUiVisibility(
            View.SYSTEM_UI_FLAG_FULLSCREEN |
            View.SYSTEM_UI_FLAG_HIDE_NAVIGATION |
            View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY |
            View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN |
            View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION |
            View.SYSTEM_UI_FLAG_LAYOUT_STABLE
        );
    }

    @Override
    public void onBackPressed() {
        sendEscapeToGame();
    }

    @Override
    protected void onResume() {
        super.onResume();
        configureWindow();
        if (webView != null) webView.onResume();
    }

    @Override
    protected void onPause() {
        if (webView != null) webView.onPause();
        super.onPause();
    }

    @Override
    protected void onDestroy() {
        if (webView != null) {
            webView.destroy();
            webView = null;
        }
        super.onDestroy();
    }
}
