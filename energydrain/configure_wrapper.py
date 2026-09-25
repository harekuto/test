from pathlib import Path
import re
import xml.etree.ElementTree as ET
import sys

root=Path(sys.argv[1])
gradle=root/'app/build.gradle'
s=gradle.read_text(encoding='utf-8')
s=re.sub(r'applicationId\s+"[^"]+"', 'applicationId "com.harekuto.energydrain"', s)
s=re.sub(r'versionCode\s+\d+', 'versionCode 1', s)
s=re.sub(r'versionName\s+"[^"]+"', 'versionName "1.0.0-android-port1"', s)
gradle.write_text(s, encoding='utf-8')

strings=root/'app/src/main/res/values/strings.xml'
strings.write_text('<resources>\n    <string name="app_name">Energy Drain</string>\n</resources>\n', encoding='utf-8')

manifest=root/'app/src/main/AndroidManifest.xml'
ms=manifest.read_text(encoding='utf-8')
if 'android:largeHeap=' not in ms:
    ms=ms.replace('android:hardwareAccelerated="true"', 'android:hardwareAccelerated="true"\n        android:largeHeap="true"')
manifest.write_text(ms, encoding='utf-8')
ET.parse(manifest)

main=root/'app/src/main/java/com/nekobot/rpgnekos/MainActivity.java'
js=main.read_text(encoding='utf-8')
old_console='return super.onConsoleMessage(consoleMessage);'
new_console='android.util.Log.e("RPGWEB", consoleMessage.message() + " @" + consoleMessage.sourceId() + ":" + consoleMessage.lineNumber());\n                return true;'
if old_console in js:
    js=js.replace(old_console,new_console)

old_back="""    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
            return;
        }
        super.onBackPressed();
    }"""
new_back="""    @Override
    public void onBackPressed() {
        if (webView != null) {
            webView.evaluateJavascript(
                "(function(){if(window.Input){Input._currentState['escape']=true;setTimeout(function(){Input._currentState['escape']=false;},80);}document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',keyCode:27,which:27,bubbles:true}));setTimeout(function(){document.dispatchEvent(new KeyboardEvent('keyup',{key:'Escape',keyCode:27,which:27,bubbles:true}));},80);})();",
                null
            );
            return;
        }
        super.onBackPressed();
    }"""
if old_back not in js:
    raise SystemExit('onBackPressed target missing')
js=js.replace(old_back,new_back)
main.write_text(js, encoding='utf-8')

placeholder=root/'app/src/main/assets/www/index.html'
placeholder.parent.mkdir(parents=True,exist_ok=True)
placeholder.write_text('<!doctype html><html><head><meta charset="utf-8"></head><body style="background:#000;color:#fff">Energy Drain Android wrapper</body></html>\n',encoding='utf-8')

print('wrapper_config=PASS')
