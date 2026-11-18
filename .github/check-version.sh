#!/usr/bin/env bash
# version.txt must be major.minor.patch. For a push to main (a release), it must also be new and
# higher than the latest release, and its tag must not exist yet. Stops before any approval.
# Any answer from GitHub other than "not found" stops it too: unsure means no release.
set -euo pipefail
EVENT="$1"; REF="$2"; REPO="$3"
V="$(tr -d '[:space:]' < version.txt)"
[[ "$V" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "::error::version.txt must be major.minor.patch, got '$V'"; exit 1; }
# Every version says what is new, in both languages, in the store and in the release
IFS=. read -r MA MI PA <<<"$V"
CODE=$((MA * 10000 + MI * 100 + PA))
for L in uk en-US; do
  [ -s "fastlane/metadata/android/$L/changelogs/$CODE.txt" ] || { echo "::error::fastlane/metadata/android/$L/changelogs/$CODE.txt is missing"; exit 1; }
done
grep -qF "$V" .github/release-notes.md || { echo "::error::.github/release-notes.md does not name $V"; exit 1; }
[ "$EVENT" = push ] && [ "$REF" = refs/heads/main ] || exit 0

# Prints the answer; exits 0 with nothing for "not found", 1 for any other failure
ask() {
  local out
  if out="$(gh api "$1" --jq "$2" 2>&1)"; then printf '%s' "$out"; return 0; fi
  if grep -q "HTTP 404" <<<"$out"; then return 0; fi
  echo "::error::Could not ask GitHub ($1): $out" >&2
  return 1
}

# Assigned first: a failed answer then stops the script (set -e), which a test inside "if" would not
TAG="$(ask "repos/$REPO/git/ref/tags/v$V" '.ref')"
if [ -n "$TAG" ]; then
  echo "::error::v$V already exists; raise version.txt first."; exit 1
fi
LATEST="$(ask "repos/$REPO/releases/latest" '.tag_name // empty')"
LATEST="${LATEST#v}"
if [ -n "$LATEST" ]; then
  [[ "$LATEST" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "::error::Unexpected latest release '$LATEST'"; exit 1; }
  if [ "$LATEST" = "$V" ] || [ "$(printf '%s\n%s\n' "$LATEST" "$V" | sort -V | tail -1)" != "$V" ]; then
    echo "::error::v$V is not higher than the latest release v$LATEST."; exit 1
  fi
fi
echo "Version $V OK"
