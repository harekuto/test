from __future__ import annotations
import re, sys, xml.etree.ElementTree as ET
from pathlib import Path

if len(sys.argv)!=2:
    raise SystemExit('Usage: configure_android_v3.py <android_project_dir>')
root=Path(sys.argv[1])

p=root/'build.gradle'
s=p.read_text(); s=s.replace('version "8.7.3"','version "8.10.0"'); p.write_text(s)

p=root/'gradle/wrapper/gradle-wrapper.properties'
s=p.read_text(); s=re.sub(r'gradle-[^/]+-bin\.zip','gradle-8.11.1-bin.zip',s); p.write_text(s)

p=root/'app/build.gradle'
s=p.read_text().replace('compileSdk 35','compileSdk 36').replace('targetSdk 35','targetSdk 36')
s=s.replace('applicationId "com.nekobot.rpgnekos"','applicationId "com.harekuto.conquestfrontline"')
s=s.replace('versionName "1.0.0"','versionName "0.15-android-stable-v3"')
marker='    compileOptions {'
insert='''    androidResources {
        noCompress += ["ogg", "m4a", "mp3", "wav", "mp4", "webm", "png", "jpg", "jpeg"]
    }

'''
if 'androidResources {' not in s: s=s.replace(marker,insert+marker)
p.write_text(s)

p=root/'app/src/main/res/values/strings.xml'
s=p.read_text(); s=re.sub(r'<string name="app_name">.*?</string>','<string name="app_name">Conquest: Femdom Frontline</string>',s); p.write_text(s)

p=root/'app/src/main/AndroidManifest.xml'
s=p.read_text()
# The wrapper already defines hardwareAccelerated and usesCleartextTraffic. Modify existing attributes instead of duplicating them.
s=s.replace('android:usesCleartextTraffic="false"','android:usesCleartextTraffic="true"')
if 'android:largeHeap=' not in s:
    s=s.replace('android:allowBackup="false"','android:allowBackup="false"\n        android:largeHeap="true"')
if 'android:enableOnBackInvokedCallback=' not in s:
    s=s.replace('android:hardwareAccelerated="true"','android:hardwareAccelerated="true"\n        android:enableOnBackInvokedCallback="false"')
p.write_text(s)
# Fail before Gradle if any XML attribute or syntax error exists.
ET.parse(p)

p=root/'gradle.properties'
s=p.read_text()
if 'org.gradle.jvmargs=' not in s: s+='\norg.gradle.jvmargs=-Xmx5g -XX:MaxMetaspaceSize=1g -Dfile.encoding=UTF-8\n'
p.write_text(s)
print('Android project configured for stable v3; manifest XML validated')
