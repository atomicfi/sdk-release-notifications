#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

echo "Running ruff check"
ruff check .

echo "Running pyright linting"
pyright

echo "Validating all files compile"

python_files=()
while IFS= read -r python_file; do
  python_files+=("$python_file")
done < <(git ls-files -- '*.py')

if (( ${#python_files[@]} > 0 )); then
  python -m py_compile "${python_files[@]}"
fi

echo "Checking for whitespace errors"
git diff --check
