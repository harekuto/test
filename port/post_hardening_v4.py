from __future__ import annotations

import re
import sys
from pathlib import Path

if len(sys.argv) != 3:
    raise SystemExit('Usage: post_hardening_v4.py <www_root> <MainActivity.java>')

root = Path(sys.argv[1])
java = Path(sys.argv[2])
index = root / 'index.html'

# --- Web runtime hardening ---
s = index.read_text(encoding='utf-8-sig', errors='replace')
old_process = "if(typeof window.process==='undefined') window.process={versions:{'node-webkit':'0.0.0'},platform:'android',env:{}};\n  else {process.versions=process.versions||{};if(!process.versions['node-webkit'])process.versions['node-webkit']='0.0.0';}"
new_process = "if(typeof window.process==='undefined') window.process={versions:{},platform:'android',env:{}};\n  else {process.versions=process.versions||{};process.platform=process.platform||'android';process.env=process.env||{};}"
if old_process not in s:
    raise SystemExit('Expected Android process shim was not found')
s = s.replace(old_process, new_process, 1)

# Do not advertise a fake NW.js runtime. Some plugins use this as a desktop-only gate.
if "process.versions['node-webkit']='0.0.0'" in s:
    raise SystemExit('Fake NW.js marker still present after hardening')

# Avoid controls under display cut-outs / gesture navigation areas.
s = s.replace(
    '#android-port-controls{position:fixed;right:14px;bottom:14px;',
    '#android-port-controls{position:fixed;right:max(14px,env(safe-area-inset-right));bottom:max(14px,env(safe-area-inset-bottom));',
    1,
)

# Clear virtual keys when Android/WebView loses focus so a pointer interruption cannot leave a key stuck.
guard = r'''
  function releaseAndroidPortKeys(){
    try{
      if(window.Input&&Input._currentState){
        Input._currentState.ok=false;
        Input._currentState.escape=false;
      }
    }catch(e){}
    try{
      var keys=document.querySelectorAll('.android-port-key.pressed');
      for(var i=0;i<keys.length;i++)keys[i].classList.remove('pressed');
    }catch(e){}
  }
  window.addEventListener('blur',releaseAndroidPortKeys);
  window.addEventListener('pagehide',releaseAndroidPortKeys);
  document.addEventListener('visibilitychange',function(){if(document.hidden)releaseAndroidPortKeys();});
'''
needle = "  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',installControls);else installControls();"
if needle not in s:
    raise SystemExit('Control install marker not found')
s = s.replace(needle, guard + '\n' + needle, 1)
index.write_text(s, encoding='utf-8')

# --- Native WebView hardening ---
j = java.read_text(encoding='utf-8')

if 'webView.setKeepScreenOn(true);' not in j:
    j = j.replace(
        'webView.setBackgroundColor(Color.BLACK);',
        'webView.setBackgroundColor(Color.BLACK);\n        webView.setKeepScreenOn(true);\n        webView.setOverScrollMode(View.OVER_SCROLL_NEVER);\n        webView.setVerticalScrollBarEnabled(false);\n        webView.setHorizontalScrollBarEnabled(false);',
        1,
    )

if 'settings.setSupportZoom(false);' not in j:
    j = j.replace(
        'settings.setUseWideViewPort(true);',
        'settings.setUseWideViewPort(true);\n        settings.setSupportZoom(false);',
        1,
    )

# Only hand genuine external links to Android. blob:/data:/about: and unknown game/plugin schemes
# stay inside WebView rather than being sent to an Activity that cannot handle them.
old_external = '''            Uri uri = request.getUrl();
            if ("file".equals(uri.getScheme())) return false;
            try {
                startActivity(new Intent(Intent.ACTION_VIEW, uri));
            } catch (Exception error) {
                Log.w("RPGWEB", "Cannot open external URL: " + uri, error);
            }
            return true;'''
new_external = '''            Uri uri = request.getUrl();
            String scheme = uri.getScheme();
            if (scheme == null || "file".equalsIgnoreCase(scheme)
                    || "data".equalsIgnoreCase(scheme)
                    || "blob".equalsIgnoreCase(scheme)
                    || "about".equalsIgnoreCase(scheme)
                    || "javascript".equalsIgnoreCase(scheme)) {
                return false;
            }
            if ("http".equalsIgnoreCase(scheme) || "https".equalsIgnoreCase(scheme)
                    || "mailto".equalsIgnoreCase(scheme) || "market".equalsIgnoreCase(scheme)
                    || "intent".equalsIgnoreCase(scheme)) {
                try {
                    startActivity(new Intent(Intent.ACTION_VIEW, uri));
                } catch (Exception error) {
                    Log.w("RPGWEB", "Cannot open external URL: " + uri, error);
                }
                return true;
            }
            Log.w("RPGWEB", "Keeping unknown scheme inside WebView: " + uri);
            return false;'''
if old_external in j:
    j = j.replace(old_external, new_external, 1)
elif 'Keeping unknown scheme inside WebView' not in j:
    raise SystemExit('Expected URL routing block not found')

java.write_text(j, encoding='utf-8')

checks = {
    'fake_nwjs_removed': "process.versions['node-webkit']='0.0.0'" not in s,
    'focus_key_release': 'releaseAndroidPortKeys' in s,
    'enter_button': "add('ENTER','ok',13,'Enter')" in s,
    'esc_button': "add('ESC','escape',27,'Escape')" in s,
    'keep_screen_on': 'setKeepScreenOn(true)' in j,
    'overscroll_disabled': 'OVER_SCROLL_NEVER' in j,
    'safe_external_routing': 'Keeping unknown scheme inside WebView' in j,
}
if not all(checks.values()):
    raise SystemExit(f'v4 hardening checks failed: {checks}')
print('\n'.join(f'{k}={v}' for k, v in checks.items()))
