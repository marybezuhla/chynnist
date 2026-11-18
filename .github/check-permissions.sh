#!/usr/bin/env bash
# Every permission in the APK must be on this list; anything else fails.
set -euo pipefail
APK="$1"
AAPT=$(ls "$ANDROID_HOME"/build-tools/*/aapt2 | sort -V | tail -1)
"$AAPT" dump permissions "$APK" > permissions.txt
cat permissions.txt
grep -q '^package:' permissions.txt || { echo "::error::Could not read permissions"; exit 1; }
# For now Chynnist asks for nothing: no internet, no files, no notifications. Allowed: only the one Android
# adds for the app's own receivers (from the AndroidX libraries).
ALLOWED=" ua.chynnist.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION "
for p in $(grep -oE "name='[^']+'" permissions.txt | sed "s/name='//;s/'//"); do
  case "$ALLOWED" in
    *" $p "*) ;;
    *) echo "::error::Unexpected permission: $p"; exit 1 ;;
  esac
done
# Chynnist declares no permissions of its own, apart from the one Android adds for its receivers
for p in $(grep -E "^permission:" permissions.txt | sed -E 's/^permission: *//'); do
  [ "$p" = ua.chynnist.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION ] || { echo "::error::Unexpected declared permission: $p"; exit 1; }
done
echo "Permissions OK"
