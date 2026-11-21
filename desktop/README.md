# Desktop (M3 — in progress)

The desktop app is a thin Tauri v2 shell around the Python core, following the
same shape as Limn and Canturía. The 0.1.0 builds are published from GitHub
Releases; they are unsigned, and not notarized yet.

## How it works

1. **First launch.** Find or download `uv`, create a private Python runtime in
   the app-data directory, install the released `tavola[serve,render]` wheel,
   install Chromium for the renderer, and start `tavola serve` on a random
   localhost port.
2. **Window.** The served UI sits in the OS webview under a small header bar.
   No bundled browser engine.
3. **Settings.** The first-run sheet writes the selected provider, base URL,
   model, and API key into `~/.tavola.yaml` (`chmod 600` on Unix), preserving
   other keys. Layout/style/format choices stay in the web UI.
4. **Saves** land in `~/Pictures/Tavola` by default.
5. **Lifecycle.** The Python sidecar watches the stdin pipe held by the shell,
   so it exits if the desktop process crashes or is killed.

The runtime pin lives in `src-tauri/src/main.rs` as `TAVOLA_WHEEL_URL`. It points
at the wheel attached to the `v0.1.0` GitHub release. There is no PyPI release
yet.

## Build

```bash
export CARGO_TARGET_DIR="$HOME/.cache/tavola-target"   # exFAT-safe
cd desktop
npx --yes @tauri-apps/cli@^2 build
```

For local development, point the shell at the checkout; it installs the repo
in editable mode into the private runtime instead of the release wheel:

```bash
export TAVOLA_DEV_PATH="/Volumes/Crucial X9/Projects/infographic-gen"
cargo run --manifest-path src-tauri/Cargo.toml
```

## Release

`.github/workflows/release.yml` runs on `v*` tags. It tests, builds the wheel,
builds unsigned macOS arm64/x86_64, Windows, and Linux installers with
`tauri-action`, and uploads the wheel to the same release. Signing and
notarization are deliberately not configured yet.

## Why Tauri

The Python package is the library, the CLI, and the server. Tauri wraps that
server with the OS webview. Electron would add a bundled browser for no gain.
Shipping a 1 GB Python bundle would duplicate what `uv` already does well.
