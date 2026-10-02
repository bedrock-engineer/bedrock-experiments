#!/usr/bin/env bash
# Try to build an obstore wheel for Pyodide 314.0.0 (the version marimo 0.25 WASM loads).
# Everything (pyodide-build venv, xbuildenv, emsdk, rustup) goes into .build/, nothing into $HOME.
# Result on 2026-10-01: fails compiling mio, see README.md finding 3.
set -euo pipefail
OBSTORE_VERSION=${OBSTORE_VERSION:-0.11.1}
PYODIDE_VERSION=${PYODIDE_VERSION:-314.0.0}
B="$(cd "$(dirname "$0")" && pwd)/.build"
mkdir -p "$B"
export PYODIDE_XBUILDENV_PATH="$B/xbuildenv" RUSTUP_HOME="$B/rustup" CARGO_HOME="$B/cargo"
export PATH="$B/cargo/bin:$PATH"

[ -d "$B/venv" ] || uv venv -q -p 3.14 "$B/venv"
uv pip install -q -p "$B/venv" pyodide-build
source "$B/venv/bin/activate"
pyodide xbuildenv install "$PYODIDE_VERSION"
pyodide xbuildenv install-emscripten
RUST_TOOLCHAIN=$(pyodide config get rust_toolchain)
[ -x "$B/cargo/bin/rustup" ] || curl -sSf https://sh.rustup.rs | sh -s -- -y -q --no-modify-path --profile minimal --default-toolchain none
rustup toolchain install "$RUST_TOOLCHAIN" --profile minimal -t wasm32-unknown-emscripten
rustup default "$RUST_TOOLCHAIN"

cd "$B"
[ -d "obstore-$OBSTORE_VERSION" ] || curl -sSL "https://files.pythonhosted.org/packages/source/o/obstore/obstore-$OBSTORE_VERSION.tar.gz" | tar xz
cd "obstore-$OBSTORE_VERSION"
pyodide build -o "$B/wheels" 2>&1 | tee "$B/build.log"
