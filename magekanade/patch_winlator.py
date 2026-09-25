#!/usr/bin/env python3
from pathlib import Path
import re, json, sys

root=Path(sys.argv[1]).resolve()
app=root/"app"

# Branding / package. com.magekana has the same byte length as com.winlator,
# which lets the separate package-path patch safely rewrite compiled runtime assets.
gradle=app/"build.gradle"
s=gradle.read_text(encoding="utf-8")
s=s.replace("applicationId 'com.winlator'","applicationId 'com.magekana'")
s=s.replace("versionCode 33","versionCode 100")
s=s.replace('versionName "11.2"','versionName "1.0-android-port1"')
gradle.write_text(s,encoding="utf-8")

manifest=app/"src/main/AndroidManifest.xml"
s=manifest.read_text(encoding="utf-8")
s=s.replace('android:authorities="com.winlator.FileProvider"','android:authorities="com.magekana.FileProvider"')
s=s.replace('    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE"/>\n','')
s=s.replace('    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE"/>\n','')
manifest.write_text(s,encoding="utf-8")

strings=app/"src/main/res/values/strings.xml"
s=strings.read_text(encoding="utf-8")
s=re.sub(r'<string name="app_name">.*?</string>', '<string name="app_name">Mage Kanade Dungeon Quest</string>', s, count=1)
strings.write_text(s,encoding="utf-8")

# Hybrid Unity touch profile: WASD + mouse + common action/menu keys.
profiles=app/"src/main/assets/inputcontrols/profiles"
profiles.mkdir(parents=True,exist_ok=True)
profile={
  "id":99,"name":"Mage Kanade","cursorSpeed":0.85,"disableMouseInput":False,
  "elements":[
    {"type":"D_PAD","shape":"CIRCLE","bindings":["KEY_W","KEY_D","KEY_S","KEY_A"],"scale":1.0,"x":0.105,"y":0.755,"toggleSwitch":False,"text":"","iconId":0},
    {"type":"BUTTON","shape":"CIRCLE","bindings":["MOUSE_LEFT_BUTTON","NONE","NONE","NONE"],"scale":1.05,"x":0.895,"y":0.795,"toggleSwitch":False,"text":"ATK","iconId":0,"mouseMoveMode":True},
    {"type":"BUTTON","shape":"CIRCLE","bindings":["KEY_E","NONE","NONE","NONE"],"scale":0.92,"x":0.810,"y":0.705,"toggleSwitch":False,"text":"USE","iconId":0},
    {"type":"BUTTON","shape":"CIRCLE","bindings":["KEY_SPACE","NONE","NONE","NONE"],"scale":0.92,"x":0.905,"y":0.610,"toggleSwitch":False,"text":"JUMP","iconId":0},
    {"type":"BUTTON","shape":"CIRCLE","bindings":["MOUSE_RIGHT_BUTTON","NONE","NONE","NONE"],"scale":0.82,"x":0.805,"y":0.535,"toggleSwitch":False,"text":"ALT","iconId":0},
    {"type":"BUTTON","shape":"ROUND_RECT","bindings":["KEY_SHIFT_L","NONE","NONE","NONE"],"scale":0.78,"x":0.730,"y":0.895,"toggleSwitch":False,"text":"RUN","iconId":0},
    {"type":"BUTTON","shape":"ROUND_RECT","bindings":["KEY_R","NONE","NONE","NONE"],"scale":0.72,"x":0.835,"y":0.895,"toggleSwitch":False,"text":"R","iconId":0},
    {"type":"BUTTON","shape":"ROUND_RECT","bindings":["KEY_Q","NONE","NONE","NONE"],"scale":0.68,"x":0.925,"y":0.445,"toggleSwitch":False,"text":"Q","iconId":0},
    {"type":"BUTTON","shape":"ROUND_RECT","bindings":["KEY_F","NONE","NONE","NONE"],"scale":0.68,"x":0.845,"y":0.445,"toggleSwitch":False,"text":"F","iconId":0},
    {"type":"BUTTON","shape":"ROUND_RECT","bindings":["KEY_I","NONE","NONE","NONE"],"scale":0.68,"x":0.765,"y":0.445,"toggleSwitch":False,"text":"INV","iconId":0},
    {"type":"BUTTON","shape":"ROUND_RECT","bindings":["KEY_TAB","NONE","NONE","NONE"],"scale":0.64,"x":0.145,"y":0.095,"toggleSwitch":False,"text":"TAB","iconId":0},
    {"type":"BUTTON","shape":"ROUND_RECT","bindings":["KEY_ENTER","NONE","NONE","NONE"],"scale":0.64,"x":0.500,"y":0.930,"toggleSwitch":False,"text":"ENTER","iconId":0},
    {"type":"BUTTON","shape":"ROUND_RECT","bindings":["KEY_ESC","NONE","NONE","NONE"],"scale":0.64,"x":0.055,"y":0.095,"toggleSwitch":False,"text":"ESC","iconId":0}
  ]
}
(profiles/"controls-99.icp").write_text(json.dumps(profile,separators=(",",":")),encoding="utf-8")

java_dir=app/"src/main/java/com/winlator"
bootstrap=java_dir/"MageKanadeBootstrap.java"
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

public final class MageKanadeBootstrap {
    private static final String CONTAINER_NAME = "Mage Kanade";
    private static final String GAME_DIR = "MageKanade";
    private static final String EXE_NAME = "Mage Kanades Futanari Dungeon Quest.exe";
    private static final String PAYLOAD_ASSET = "mage_payload.zip";
    private static final String PAYLOAD_MARKER = ".mage_payload_android_1";
    private static final int PROFILE_ID = 99;
    private static boolean started = false;
    private static boolean launching = false;

    private MageKanadeBootstrap() {}

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
            if (CONTAINER_NAME.equals(c.getName())) { found = c; break; }
        }
        if (found != null) {
            configureContainer(activity, found);
            provisionAndLaunch(activity, found);
            return;
        }
        try {
            JSONObject data = new JSONObject();
            data.put("name", CONTAINER_NAME);
            data.put("screenSize", "1280x720");
            data.put("graphicsDriver", GraphicsDrivers.getDefaultDriver(activity));
            data.put("dxwrapper", DXWrappers.DXVK);
            data.put("audioDriver", AudioDrivers.ALSA);
            data.put("wincomponents", Container.DEFAULT_WINCOMPONENTS);
            data.put("box64Preset", Box64Preset.PERFORMANCE);
            data.put("envVars", "WINEESYNC=1 MESA_SHADER_CACHE_DISABLE=false MESA_SHADER_CACHE_MAX_SIZE=512MB");
            manager.createContainerAsync(data, container -> {
                if (container == null) {
                    Toast.makeText(activity, "Could not create Mage Kanade runtime", Toast.LENGTH_LONG).show();
                    return;
                }
                configureContainer(activity, container);
                provisionAndLaunch(activity, container);
            });
        } catch (Exception e) {
            Toast.makeText(activity, "Mage Kanade setup failed: "+e.getMessage(), Toast.LENGTH_LONG).show();
        }
    }

    private static void configureContainer(MainActivity activity, Container container) {
        container.setScreenSize("1280x720");
        container.setGraphicsDriver(GraphicsDrivers.getDefaultDriver(activity));
        container.setDXWrapper(DXWrappers.DXVK);
        container.setDXWrapperConfig("dxvk.enableGraphicsPipelineLibrary=Auto,dxvk.maxFrameLatency=1");
        container.setAudioDriver(AudioDrivers.ALSA);
        container.setWinComponents(Container.DEFAULT_WINCOMPONENTS);
        container.setBox64Preset(Box64Preset.PERFORMANCE);
        container.setStartupSelection(Container.STARTUP_SELECTION_ESSENTIAL);
        container.setEnvVars("WINEESYNC=1 MESA_SHADER_CACHE_DISABLE=false MESA_SHADER_CACHE_MAX_SIZE=512MB");
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
                    if (!gameDir.mkdirs() && !gameDir.isDirectory()) throw new IllegalStateException("Could not create game directory");
                    extractZipAsset(activity, PAYLOAD_ASSET, gameDir);
                    File exe = new File(gameDir, EXE_NAME);
                    if (!exe.isFile() || exe.length() < 500000) throw new IllegalStateException("Game executable missing after extraction");
                    marker.createNewFile();
                }

                File gameExe = new File(gameDir, EXE_NAME);
                if (!gameExe.isFile()) throw new IllegalStateException("Mage Kanade executable missing");

                File desktop = new File(container.getUserDir(), "Desktop");
                if (!desktop.isDirectory()) desktop.mkdirs();
                File shortcut = new File(desktop, "Mage-Kanade.desktop");
                String content =
                    "[Desktop Entry]\n" +
                    "Name=Mage Kanade Dungeon Quest\n" +
                    "Exec=wine C:\\MageKanade\\Mage\ Kanades\ Futanari\ Dungeon\ Quest.exe\n" +
                    "Type=Application\n" +
                    "StartupWMClass=Mage Kanades Futanari Dungeon Quest.exe\n\n" +
                    "[Extra Data]\n" +
                    "controlsProfile=" + PROFILE_ID + "\n" +
                    "screenSize=1280x720\n" +
                    "forceFullscreen=1\n" +
                    "dxwrapper=dxvk\n" +
                    "audioDriver=alsa\n" +
                    "box64Preset=PERFORMANCE\n" +
                    "envVars=WINEESYNC=1 WINEDEBUG=-all\n";
                FileUtils.writeString(shortcut, content);

                activity.runOnUiThread(() -> {
                    Intent intent = new Intent(activity, XServerDisplayActivity.class);
                    intent.putExtra("container_id", container.id);
                    intent.putExtra("exec_path", gameExe.getPath());
                    intent.putExtra("mage_controls_profile", PROFILE_ID);
                    intent.putExtra("mage_force_fullscreen", true);
                    activity.startActivity(intent);
                });
            } catch (Throwable e) {
                launching = false;
                activity.runOnUiThread(() -> Toast.makeText(activity,
                    "Mage Kanade setup failed: "+e.getClass().getSimpleName()+": "+e.getMessage(),
                    Toast.LENGTH_LONG).show());
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
                String name = entry.getName().replace('\\','/');
                if (name.startsWith("/") || name.contains("../")) throw new SecurityException("Unsafe payload path: "+name);
                File out = new File(destination,name);
                String canonical = out.getCanonicalPath();
                if (!canonical.startsWith(canonicalRoot)) throw new SecurityException("Payload path escapes target");
                if (entry.isDirectory()) out.mkdirs();
                else {
                    File parent = out.getParentFile();
                    if (parent != null && !parent.isDirectory()) parent.mkdirs();
                    try (BufferedOutputStream fout = new BufferedOutputStream(new FileOutputStream(out),1024*1024)) {
                        int n;
                        while ((n=zin.read(buffer))>0) fout.write(buffer,0,n);
                    }
                }
                zin.closeEntry();
            }
        }
    }
}
''',encoding="utf-8")

# MainActivity: internal-storage-only standalone launcher.
main=java_dir/"MainActivity.java"
s=main.read_text(encoding="utf-8")
s=re.sub(r'private boolean requestAppPermissions\(\) \{.*?^\s*\}',
         'private boolean requestAppPermissions() {\n        return false;\n    }',
         s,count=1,flags=re.S|re.M)
old='if (!requestAppPermissions()) RootFSInstaller.installIfNeeded(this);'
new='''if (!requestAppPermissions()) {
                RootFSInstaller.installIfNeeded(this);
                MageKanadeBootstrap.startWhenReady(this);
            }'''
if old not in s: raise SystemExit("MainActivity bootstrap anchor missing")
main.write_text(s.replace(old,new,1),encoding="utf-8")

# Direct exec route: expose game-specific touch profile and fullscreen.
xserver=java_dir/"XServerDisplayActivity.java"
s=xserver.read_text(encoding="utf-8")
old='renderer.setForceWindowsFullscreen(shortcut != null && shortcut.getExtra("forceFullscreen", "0").equals("1"));'
new='''renderer.setForceWindowsFullscreen(
            (shortcut != null && shortcut.getExtra("forceFullscreen", "0").equals("1")) ||
            getIntent().getBooleanExtra("mage_force_fullscreen", false)
        );'''
if old not in s: raise SystemExit("fullscreen anchor missing")
s=s.replace(old,new,1)
old='''        if (shortcut != null) {
            String controlsProfile = shortcut.getExtra("controlsProfile");
            if (!controlsProfile.isEmpty()) {
                ControlsProfile profile = inputControlsManager.getProfile(Integer.parseInt(controlsProfile));
                if (profile != null) showInputControls(profile);
            }
        }'''
new='''        if (shortcut != null) {
            String controlsProfile = shortcut.getExtra("controlsProfile");
            if (!controlsProfile.isEmpty()) {
                ControlsProfile profile = inputControlsManager.getProfile(Integer.parseInt(controlsProfile));
                if (profile != null) showInputControls(profile);
            }
        }
        else {
            int mageProfileId = getIntent().getIntExtra("mage_controls_profile", 0);
            if (mageProfileId > 0) {
                ControlsProfile profile = inputControlsManager.getProfile(mageProfileId);
                if (profile != null) showInputControls(profile);
            }
        }'''
if old not in s: raise SystemExit("controls anchor missing")
xserver.write_text(s.replace(old,new,1),encoding="utf-8")

print("MAGE_KANADE_PATCH_OK")
print("package=com.magekana")
print("profile=99")
print("runtime=Winlator 11.2 + Box64 + DXVK")
