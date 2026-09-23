#!/usr/bin/env python3
from pathlib import Path
import re, json, sys

root = Path(sys.argv[1]).resolve()
app = root / "app"

# ---- Branding / package ----
gradle = app / "build.gradle"
s = gradle.read_text(encoding="utf-8")
s = s.replace("applicationId 'com.winlator'", "applicationId 'com.harekuto.labstillalive'")
s = s.replace('versionCode 33', 'versionCode 127')
s = s.replace('versionName "11.2"', 'versionName "1.25-android-port3-autogpu"')
gradle.write_text(s, encoding="utf-8")

manifest = app / "src/main/AndroidManifest.xml"
s = manifest.read_text(encoding="utf-8")
s = s.replace('android:authorities="com.winlator.FileProvider"', 'android:authorities="com.harekuto.labstillalive.FileProvider"')
manifest.write_text(s, encoding="utf-8")

strings = app / "src/main/res/values/strings.xml"
s = strings.read_text(encoding="utf-8")
s = re.sub(r'<string name="app_name">.*?</string>', '<string name="app_name">LAB Still Alive</string>', s, count=1)
strings.write_text(s, encoding="utf-8")

# ---- Dedicated touch profile ----
profiles = app / "src/main/assets/inputcontrols/profiles"
profiles.mkdir(parents=True, exist_ok=True)
profile = {
    "id": 99,
    "name": "LAB Still Alive",
    "cursorSpeed": 1.0,
    "disableMouseInput": True,
    "elements": [
        {
            "type":"D_PAD","shape":"CIRCLE",
            "bindings":["KEY_UP","KEY_RIGHT","KEY_DOWN","KEY_LEFT"],
            "scale":1.05,"x":0.115,"y":0.735,
            "toggleSwitch":False,"text":"","iconId":0
        },
        {
            "type":"BUTTON","shape":"CIRCLE",
            "bindings":["KEY_X","NONE","NONE","NONE"],
            "scale":1.05,"x":0.900,"y":0.810,
            "toggleSwitch":False,"text":"JUMP","iconId":0
        },
        {
            "type":"BUTTON","shape":"CIRCLE",
            "bindings":["KEY_A","NONE","NONE","NONE"],
            "scale":0.95,"x":0.825,"y":0.735,
            "toggleSwitch":False,"text":"MELEE","iconId":0
        },
        {
            "type":"BUTTON","shape":"CIRCLE",
            "bindings":["KEY_D","NONE","NONE","NONE"],
            "scale":0.95,"x":0.930,"y":0.650,
            "toggleSwitch":False,"text":"GUN","iconId":0
        },
        {
            "type":"BUTTON","shape":"CIRCLE",
            "bindings":["KEY_W","NONE","NONE","NONE"],
            "scale":0.85,"x":0.825,"y":0.575,
            "toggleSwitch":False,"text":"RELOAD","iconId":0
        },
        {
            "type":"BUTTON","shape":"ROUND_RECT",
            "bindings":["KEY_SHIFT_L","NONE","NONE","NONE"],
            "scale":0.82,"x":0.765,"y":0.895,
            "toggleSwitch":False,"text":"BACK","iconId":0
        },
        {
            "type":"BUTTON","shape":"ROUND_RECT",
            "bindings":["KEY_SHIFT_R","NONE","NONE","NONE"],
            "scale":0.82,"x":0.865,"y":0.895,
            "toggleSwitch":False,"text":"GUARD","iconId":0
        },
        {
            "type":"BUTTON","shape":"ROUND_RECT",
            "bindings":["KEY_SPACE","NONE","NONE","NONE"],
            "scale":0.82,"x":0.540,"y":0.930,
            "toggleSwitch":False,"text":"MENU","iconId":0
        },
        {
            "type":"BUTTON","shape":"ROUND_RECT",
            "bindings":["KEY_TAB","NONE","NONE","NONE"],
            "scale":0.72,"x":0.460,"y":0.930,
            "toggleSwitch":False,"text":"TAB","iconId":0
        },
        {
            "type":"BUTTON","shape":"ROUND_RECT",
            "bindings":["KEY_CTRL_L","NONE","NONE","NONE"],
            "scale":0.68,"x":0.885,"y":0.095,
            "toggleSwitch":False,"text":"LCTRL","iconId":0
        },
        {
            "type":"BUTTON","shape":"ROUND_RECT",
            "bindings":["KEY_CTRL_R","NONE","NONE","NONE"],
            "scale":0.68,"x":0.955,"y":0.095,
            "toggleSwitch":False,"text":"RCTRL","iconId":0
        }
    ]
}
(profiles / "controls-99.icp").write_text(json.dumps(profile, separators=(",",":")), encoding="utf-8")

# ---- Auto-provision and launch ----
java_dir = app / "src/main/java/com/winlator"
bootstrap = java_dir / "LabStillAliveBootstrap.java"
bootstrap.write_text(r'''package com.winlator;

import android.content.Intent;
import android.os.Handler;
import android.os.Looper;
import android.widget.Toast;

import com.winlator.box64.Box64Preset;
import com.winlator.container.AudioDrivers;
import com.winlator.container.Container;
import com.winlator.container.ContainerManager;
import com.winlator.container.DXWrappers;
import com.winlator.container.GraphicsDrivers;
import com.winlator.core.FileUtils;
import com.winlator.xenvironment.RootFS;
import com.winlator.xenvironment.RootFSInstaller;

import org.json.JSONObject;

import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.util.concurrent.Executors;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

public final class LabStillAliveBootstrap {
    private static final String CONTAINER_NAME = "LAB Still Alive";
    private static final String GAME_DIR = "LAB-Still-Alive";
    private static final String EXE_NAME = "LAB-Still Alive- Ver.1.25.exe";
    private static final String PAYLOAD_ASSET = "lab_payload.zip";
    private static final String PAYLOAD_MARKER = ".lab_payload_125_android_1";
    private static final int PROFILE_ID = 99;
    private static boolean started = false;
    private static boolean launching = false;

    private LabStillAliveBootstrap() {}

    public static synchronized void startWhenReady(MainActivity activity) {
        if (started) return;
        started = true;
        Handler handler = new Handler(Looper.getMainLooper());
        Runnable[] task = new Runnable[1];
        task[0] = () -> {
            if (activity.isFinishing()) return;
            RootFS rootFS = RootFS.find(activity);
            if (!rootFS.isValid() || rootFS.getVersion() < RootFSInstaller.LATEST_VERSION) {
                handler.postDelayed(task[0], 700);
                return;
            }
            ensureContainer(activity);
        };
        handler.postDelayed(task[0], 350);
    }

    private static void ensureContainer(MainActivity activity) {
        ContainerManager manager = new ContainerManager(activity);
        Container found = null;
        for (Container c : manager.getContainers()) {
            if (CONTAINER_NAME.equals(c.getName())) {
                found = c;
                break;
            }
        }
        if (found != null) {
            configureContainer(activity, found);
            provisionAndLaunch(activity, found);
            return;
        }

        try {
            JSONObject data = new JSONObject();
            data.put("name", CONTAINER_NAME);
            data.put("screenSize", "640x480");
            data.put("graphicsDriver", GraphicsDrivers.getDefaultDriver(activity));
            data.put("dxwrapper", DXWrappers.WINED3D);
            data.put("audioDriver", AudioDrivers.ALSA);
            data.put("wincomponents", Container.DEFAULT_WINCOMPONENTS);
            data.put("box64Preset", Box64Preset.STABILITY);
            data.put("envVars", Container.DEFAULT_ENV_VARS + " WINEESYNC=0 MESA_EXTENSION_MAX_YEAR=2003 WINEDEBUG=-all");
            manager.createContainerAsync(data, container -> {
                if (container == null) {
                    Toast.makeText(activity, "Could not create LAB runtime", Toast.LENGTH_LONG).show();
                    return;
                }
                configureContainer(activity, container);
                provisionAndLaunch(activity, container);
            });
        }
        catch (Exception e) {
            Toast.makeText(activity, "LAB setup failed: " + e.getMessage(), Toast.LENGTH_LONG).show();
        }
    }

    private static void configureContainer(MainActivity activity, Container container) {
        container.setScreenSize("640x480");
        container.setGraphicsDriver(GraphicsDrivers.getDefaultDriver(activity));
        container.setDXWrapper(DXWrappers.WINED3D);
        container.setAudioDriver(AudioDrivers.ALSA);
        container.setWinComponents(Container.DEFAULT_WINCOMPONENTS);
        container.setBox64Preset(Box64Preset.STABILITY);
        container.setStartupSelection(Container.STARTUP_SELECTION_NORMAL);
        container.setEnvVars(Container.DEFAULT_ENV_VARS + " WINEESYNC=0 MESA_EXTENSION_MAX_YEAR=2003");
        container.saveData();
    }
    private static void provisionAndLaunch(MainActivity activity, Container container) {
        if (launching) return;
        launching = true;
        Executors.newSingleThreadExecutor().execute(() -> {
            try {
                File driveC = new File(container.getRootDir(), ".wine/drive_c");
                File gameDir = new File(driveC, GAME_DIR);
                File marker = new File(container.getRootDir(), PAYLOAD_MARKER);

                if (!marker.isFile()) {
                    if (gameDir.exists()) FileUtils.delete(gameDir);
                    if (!gameDir.mkdirs() && !gameDir.isDirectory()) {
                        throw new IllegalStateException("Could not create game directory");
                    }
                    extractZipAsset(activity, PAYLOAD_ASSET, gameDir);
                    File exe = new File(gameDir, EXE_NAME);
                    if (!exe.isFile() || exe.length() < 500000) {
                        throw new IllegalStateException("Game executable missing after extraction");
                    }
                    marker.createNewFile();
                }

                File gameExe = new File(gameDir, EXE_NAME);
                if (!gameExe.isFile()) throw new IllegalStateException("LAB executable missing");

                File desktop = new File(container.getUserDir(), "Desktop");
                if (!desktop.isDirectory()) desktop.mkdirs();
                File shortcut = new File(desktop, "LAB-Still-Alive.desktop");

                String content =
                    "[Desktop Entry]\\n" +
                    "Name=LAB Still Alive\\n" +
                    "Exec=wine C:\\\\LAB-Still-Alive\\\\LAB-Still\\ Alive-\\ Ver.1.25.exe\\n" +
                    "Type=Application\\n" +
                    "StartupWMClass=LAB-Still Alive- Ver.1.25.exe\\n\\n" +
                    "[Extra Data]\\n" +
                    "controlsProfile=" + PROFILE_ID + "\\n" +
                    "screenSize=640x480\\n" +
                    "forceFullscreen=1\\n" +
                    "dxwrapper=wined3d\\n" +
                    "audioDriver=alsa\\n" +
                    "box64Preset=STABILITY\\n" +
                    "envVars=WINEESYNC=0 MESA_EXTENSION_MAX_YEAR=2003 WINEDEBUG=-all\\n";
                FileUtils.writeString(shortcut, content);

                activity.runOnUiThread(() -> {
                    Intent intent = new Intent(activity, XServerDisplayActivity.class);
                    intent.putExtra("container_id", container.id);
                    intent.putExtra("exec_path", gameExe.getPath());
                    intent.putExtra("lab_controls_profile", PROFILE_ID);
                    intent.putExtra("lab_force_fullscreen", false);
                    intent.putExtra("lab_debug", true);
                    activity.startActivity(intent);
                });
            }
            catch (Throwable e) {
                launching = false;
                activity.runOnUiThread(() ->
                    Toast.makeText(activity, "LAB setup failed: " + e.getClass().getSimpleName() + ": " + e.getMessage(), Toast.LENGTH_LONG).show()
                );
            }
        });
    }

    private static void extractZipAsset(MainActivity activity, String assetName, File destination) throws Exception {
        try (InputStream raw = activity.getAssets().open(assetName);
             ZipInputStream zin = new ZipInputStream(new BufferedInputStream(raw))) {
            ZipEntry entry;
            byte[] buffer = new byte[1024 * 1024];
            String canonicalRoot = destination.getCanonicalPath() + File.separator;
            while ((entry = zin.getNextEntry()) != null) {
                String name = entry.getName().replace('\\', '/');
                if (name.startsWith("/") || name.contains("../")) {
                    throw new SecurityException("Unsafe payload path: " + name);
                }
                File out = new File(destination, name);
                String canonical = out.getCanonicalPath();
                if (!canonical.startsWith(canonicalRoot)) {
                    throw new SecurityException("Payload path escapes target");
                }
                if (entry.isDirectory()) {
                    out.mkdirs();
                }
                else {
                    File parent = out.getParentFile();
                    if (parent != null && !parent.isDirectory()) parent.mkdirs();
                    try (BufferedOutputStream fout = new BufferedOutputStream(new FileOutputStream(out), 1024 * 1024)) {
                        int n;
                        while ((n = zin.read(buffer)) > 0) fout.write(buffer, 0, n);
                    }
                }
                zin.closeEntry();
            }
        }
    }
}
''', encoding="utf-8")

main = java_dir / "MainActivity.java"
s = main.read_text(encoding="utf-8")

# Dedicated package uses only internal storage, so do not block startup on legacy external-storage permissions.
s = re.sub(
    r'private boolean requestAppPermissions\(\) \{.*?^\s*\}',
    'private boolean requestAppPermissions() {\\n        return false;\\n    }',
    s,
    count=1,
    flags=re.S | re.M
)

old = 'if (!requestAppPermissions()) RootFSInstaller.installIfNeeded(this);'
new = '''if (!requestAppPermissions()) {
                RootFSInstaller.installIfNeeded(this);
                LabStillAliveBootstrap.startWhenReady(this);
            }'''
if old not in s:
    raise SystemExit("MainActivity bootstrap anchor missing")
s = s.replace(old, new, 1)
main.write_text(s, encoding="utf-8")

# Preserve fullscreen and the LAB touch profile on Winlator's direct exec_path route.
xserver = java_dir / "XServerDisplayActivity.java"
s = xserver.read_text(encoding="utf-8")

old_force = 'renderer.setForceWindowsFullscreen(shortcut != null && shortcut.getExtra("forceFullscreen", "0").equals("1"));'
new_force = '''renderer.setForceWindowsFullscreen(
            (shortcut != null && shortcut.getExtra("forceFullscreen", "0").equals("1")) ||
            getIntent().getBooleanExtra("lab_force_fullscreen", false)
        );'''
if old_force not in s:
    raise SystemExit("XServer fullscreen anchor missing")
s = s.replace(old_force, new_force, 1)

old_controls = '''        if (shortcut != null) {
            String controlsProfile = shortcut.getExtra("controlsProfile");
            if (!controlsProfile.isEmpty()) {
                ControlsProfile profile = inputControlsManager.getProfile(Integer.parseInt(controlsProfile));
                if (profile != null) showInputControls(profile);
            }
        }'''
new_controls = '''        if (shortcut != null) {
            String controlsProfile = shortcut.getExtra("controlsProfile");
            if (!controlsProfile.isEmpty()) {
                ControlsProfile profile = inputControlsManager.getProfile(Integer.parseInt(controlsProfile));
                if (profile != null) showInputControls(profile);
            }
        }
        else {
            int labProfileId = getIntent().getIntExtra("lab_controls_profile", 0);
            if (labProfileId > 0) {
                ControlsProfile profile = inputControlsManager.getProfile(labProfileId);
                if (profile != null) showInputControls(profile);
            }
        }'''
if old_controls not in s:
    raise SystemExit("XServer controls anchor missing")
s = s.replace(old_controls, new_controls, 1)
xserver.write_text(s, encoding="utf-8")

# Remove obsolete broad storage permissions from this standalone build.
s = manifest.read_text(encoding="utf-8")
s = s.replace('    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE"/>\\n', '')
s = s.replace('    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE"/>\\n', '')
manifest.write_text(s, encoding="utf-8")

print("LAB_PATCH_OK")
print("applicationId=com.harekuto.labstillalive")
print("profile=99 (controls-99.icp)")
print("launch=direct exec_path; graphics=auto-detect; box64=STABILITY; debug-watchdog=35s")
print("payload=assets/lab_payload.zip (injected after build)")
