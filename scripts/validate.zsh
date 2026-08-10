#!/usr/bin/env zsh

set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_root"

echo "Running ruff check"
ruff check .

echo "Running pyright linting"
pyright

echo "Validating all files compile"
python_files=("${(@f)$(git ls-files -- '*.py')}")
if (( ${#python_files} > 0 )); then
  python -m py_compile "${python_files[@]}"
fi
