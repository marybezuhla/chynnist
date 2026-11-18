#!/usr/bin/env bash
# The app carries a copy of the Suvii library for Kotlin. Checks the copy is exactly the library at the
# commit named in .github/suvii-commit.txt (checked out at $1): nothing changed, nothing left out or added.
set -euo pipefail
source_dir="$1/kotlin/src/main/kotlin/io/github/marybezuhla/suvii"
copy_dir="app/src/main/java/io/github/marybezuhla/suvii"
test -d "$source_dir" || { echo "No Suvii library at $source_dir"; exit 1; }
if diff -r "$source_dir" "$copy_dir"; then
  echo "The copy of the Suvii library matches suvii@$(cat .github/suvii-commit.txt)"
else
  echo "The copy in $copy_dir differs from the Suvii library at that commit (above)."
  echo "Change the library in the suvii repository, then copy it here and update .github/suvii-commit.txt."
  exit 1
fi
