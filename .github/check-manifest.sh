#!/usr/bin/env bash
# The final manifest inside the APK (after every library's part is merged in) must keep the app's
# data at home and its doors shut: no backups, no plain HTTP, not debuggable, and nothing opened to
# other apps but the launcher screen (or what Android itself guards with a permission).
set -euo pipefail
APK="$1"
AAPT=$(ls "$ANDROID_HOME"/build-tools/*/aapt2 | sort -V | tail -1)
"$AAPT" dump xmltree --file AndroidManifest.xml "$APK" > manifest.txt
python3 - manifest.txt <<'PY'
import re, sys
lines = open(sys.argv[1]).read().splitlines()
errors = []
# Each element with its attributes, by indentation
stack, elems = [], []
for line in lines:
    m = re.match(r'^(\s*)E: ([\w-]+)', line)
    if m:
        depth = len(m.group(1))
        while stack and stack[-1][0] >= depth:
            stack.pop()
        e = {"tag": m.group(2), "attrs": {}, "parent": stack[-1][1] if stack else None}
        stack.append((depth, e)); elems.append(e)
        continue
    a = re.match(r'^\s*A: (?:http://schemas.android.com/apk/res/android:)?([\w]+)(?:\(0x[0-9a-f]+\))?=(.*)$', line)
    if a and stack:
        stack[-1][1]["attrs"][a.group(1)] = a.group(2).strip()

def val(v):
    v = v or ""
    return v.split(" ")[0].strip('"').lower()

app = next((e for e in elems if e["tag"] == "application"), None)
if app is None:
    errors.append("no <application>")
else:
    if val(app["attrs"].get("allowBackup")) not in ("false", "0x0"):
        errors.append("android:allowBackup must be false")
    if val(app["attrs"].get("usesCleartextTraffic")) in ("true", "0xffffffff"):
        errors.append("android:usesCleartextTraffic must not be true")
    if val(app["attrs"].get("debuggable")) in ("true", "0xffffffff"):
        errors.append("android:debuggable must not be true")
    if "networkSecurityConfig" not in app["attrs"]:
        errors.append("android:networkSecurityConfig is missing")
    if "dataExtractionRules" not in app["attrs"]:
        errors.append("android:dataExtractionRules is missing")

ALLOWED = {"ua.chynnist.ui.MainActivity"}
# Open to others only behind a permission that only the system holds (a library's own normal permission
# could be asked for by any app): android.permission.DUMP guards AndroidX's profile installer
SYSTEM_ONLY = {"android.permission.DUMP"}
for e in elems:
    if e["tag"] not in ("activity", "activity-alias", "service", "receiver", "provider"):
        continue
    name = e["attrs"].get("name", "").split(" ")[0].strip('"')
    exported = val(e["attrs"].get("exported")) in ("true", "0xffffffff")
    permission = e["attrs"].get("permission", "").split(" ")[0].strip('"')
    if exported and name not in ALLOWED and permission not in SYSTEM_ONLY:
        errors.append(f"{e['tag']} {name} is exported without a system-only permission ({permission or 'none'})")

if errors:
    for err in errors:
        print(f"::error::Manifest: {err}")
    sys.exit(1)
print("Manifest OK")
PY
