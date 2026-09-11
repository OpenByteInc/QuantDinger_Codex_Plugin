#!/bin/bash
set -euo pipefail
umask 077

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
if [[ "$(uname -s)" != Darwin ]]; then
  printf '%s\n' 'macos_required' >&2
  exit 2
fi
architecture="$(uname -m)"
if [[ "$architecture" != arm64 ]]; then
  printf '%s\n' 'apple_silicon_required: use an arm64 terminal and Codex client' >&2
  exit 2
fi
unset PYTHONHOME PYTHONPATH VIRTUAL_ENV CONDA_PREFIX
unset UV_INDEX_URL UV_EXTRA_INDEX_URL UV_DEFAULT_INDEX UV_INDEX

uv_bin="$(command -v uv || true)"
if [[ -z "$uv_bin" ]]; then
  for candidate in "$HOME/.local/bin/uv" /opt/homebrew/bin/uv /usr/local/bin/uv; do
    if [[ -x "$candidate" ]]; then uv_bin="$candidate"; break; fi
  done
fi
if [[ -z "$uv_bin" ]]; then
  printf '%s\n' 'uv_required: https://docs.astral.sh/uv/getting-started/installation/' >&2
  exit 2
fi

lock_file="$script_dir/../runtime/requirements-macos.lock"
fingerprint="$(cat "$lock_file" "$script_dir/connector.py" "$script_dir/connector-tools.json" "$script_dir/runtime-check-macos.py" "$script_dir/launch-quantdinger.sh" | shasum -a 256 | cut -d ' ' -f 1)"
runtime_base="$HOME/Library/Application Support/QuantDinger/Connector/runtimes"
mkdir -p "$runtime_base"
runtime_base="$(cd -- "$runtime_base" && pwd -P)"
runtime="$runtime_base/macos-$architecture-$fingerprint"
install_lock="$runtime.lock"

runtime_ready() {
  [[ -f "$runtime/.complete" && -x "$runtime/bin/python" ]] || return 1
  [[ "$(cat "$runtime/.complete")" == "$fingerprint" ]] || return 1
  "$runtime/bin/python" -I "$script_dir/runtime-check-macos.py" "$lock_file" >/dev/null 2>&1
}

if ! runtime_ready; then
  attempts=0
  until mkdir "$install_lock" 2>/dev/null; do
    attempts=$((attempts + 1))
    if [[ "$attempts" -ge 300 ]]; then
      printf '%s\n' "runtime_install_lock_timeout: $install_lock" >&2
      exit 2
    fi
    sleep 1
  done
  trap 'rmdir "$install_lock" 2>/dev/null || true' EXIT
  if ! runtime_ready; then
    if [[ -e "$runtime" ]]; then
      mv -- "$runtime" "$runtime.quarantine-$(date +%s)-$$"
    fi
    export UV_PYTHON_INSTALL_DIR="$runtime_base/python"
    "$uv_bin" --no-config venv --managed-python --python 3.13 "$runtime" >&2
    "$uv_bin" --no-config pip install --python "$runtime/bin/python" \
      --require-hashes --only-binary :all: --index-url https://pypi.org/simple \
      -r "$lock_file" >&2
    "$runtime/bin/python" -I "$script_dir/runtime-check-macos.py" "$lock_file" >&2
    printf '%s\n' "$fingerprint" > "$runtime/.complete"
  fi
  rmdir "$install_lock"
  trap - EXIT
fi

if [[ "${1:-}" == --print-python ]]; then
  printf '%s\n' "$runtime/bin/python"
  exit 0
fi
exec "$runtime/bin/python" -I "$script_dir/connector.py" "$@"
