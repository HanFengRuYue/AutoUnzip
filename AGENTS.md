# AGENTS.md

## Purpose

AutoUnzip is a Windows desktop utility for recursively extracting nested archives, including disguised files such as `.jpg` and `.psd`, split volumes, and password-protected archives. The repository is optimized for producing a standalone one-file EXE with an embedded 7-Zip runtime.

## Read First

Start here when changing behavior:

- `README.md`
- `pyproject.toml`
- `build-exe.ps1`
- `.github/workflows/release.yml`
- `scripts/build.ps1`
- `scripts/generate_release_notes.ps1`
- `src/launcher.py`
- `src/autounzip/main.py`
- `src/autounzip/engine.py`
- `src/autounzip/settings.py`
- `src/autounzip/archive_detection.py`
- `src/autounzip/ui/main_window.py`

## Repository Layout

- `src/launcher.py`: PyInstaller entrypoint. Keep this as the packaged entry script; packaging `src/autounzip/main.py` directly breaks relative imports.
- `src/autounzip/main.py`: application bootstrap, icon setup, settings load, elevation retry, and main window creation.
- `src/autounzip/engine.py`: recursive extraction pipeline and password retry logic.
- `src/autounzip/archive_detection.py`: archive discovery, split-volume grouping, disguised suffix handling, and signature probing.
- `src/autounzip/settings.py`: settings persistence, defaults, normalization, and EXE-directory config path selection.
- `src/autounzip/models.py`: shared dataclasses used across settings, engine, worker, and UI.
- `src/autounzip/worker.py`: background extraction worker and Qt signal bridge.
- `src/autounzip/ui/`: main window, dialogs, drop zone, and stylesheet.
- `scripts/fetch_7zip.py`: downloads and extracts official 7-Zip MSI contents into `vendor/7zip`.
- `scripts/generate_release_notes.ps1`: builds GitHub Release notes from the previous tag to the current tag using commit subjects.
- `scripts/generate_icon.py`: redraws `assets/app_icon.png` and `assets/app_icon.ico`.
- `dist/`: generated EXE output. Ignored by Git.
- `vendor/7zip/`: fetched vendor binaries. Ignored by Git and regenerated during build.
- `.github/workflows/release.yml`: Windows GitHub Actions release workflow triggered by pushed `v*` tags; it builds the EXE and uploads `dist/AutoUnzip/AutoUnzip.exe` to the matching GitHub Release.

## Build And Packaging

- Use `powershell -ExecutionPolicy Bypass -File .\build-exe.ps1` for the normal build flow.
- `build-exe.ps1` bootstraps `.venv` if needed, then delegates to `scripts/build.ps1`.
- `build-exe.ps1` keeps the bootstrap interpreter as a `Path` plus `Args` pair so virtual-environment creation also works on CI runners whose Python path contains spaces.
- `scripts/build.ps1` must continue to:
  - install the editable package with `.[build]`
  - regenerate icons with `scripts/generate_icon.py`
  - fetch 7-Zip with `scripts/fetch_7zip.py`
  - package `src/launcher.py` with PyInstaller `--onefile --windowed`
  - embed both `assets` and `vendor/7zip` via `--add-data`
- The final EXE path is `dist/AutoUnzip/AutoUnzip.exe`.
- `vendor/7zip` is intentionally not committed. Any build instructions or release automation must keep regenerating it locally.
- Pushing a Git tag that matches `v[0-9]*` triggers `.github/workflows/release.yml` on GitHub Actions.
- The workflow creates a GitHub Release whose title is the tag name and whose description is generated from commit subjects between the previous reachable tag and the current tag.
- `scripts/generate_release_notes.ps1` finds the previous version from tags reachable from the current tag; if none exists, it treats the release as the first version and lists all commits reachable from that tag.

## Runtime Layout

- User settings are stored in `settings.json` next to the EXE by default. In source runs, the same helper points to the repository root.
- If writing `settings.json` fails, startup in `main.py` attempts to relaunch with administrator rights through `elevation.py`.
- The embedded asset lookup uses `sys._MEIPASS` when frozen and the repository root when running from source.
- Temporary extraction stages are created under the system temp directory with the `autounzip-` prefix and removed when `cleanup_policy == "temporary_only"`.
- The top-level extraction result defaults to a sibling directory beside the selected file or folder; the UI does not expose a manual output path.
- Nested archives are extracted back into their current parent directory instead of creating another `*_unzipped` directory for each layer.
- After a nested archive finishes extracting successfully, the intermediate archive file or split-volume members are deleted from the result tree.
- `SevenZipTool` forces `-sccUTF-8` for both probe and extract commands, and Python reads that output as UTF-8 for log display and archive-type parsing.

## Core Behavior

- Discovery is limited to:
  - normal archive extensions from `archive_detection.py`
  - enabled disguised suffixes from `AppSettings.disguised_extensions`
  - split-volume groupings recognized by the regex rules in `archive_detection.py`
- Disguised suffix matches are still validated by signature sniffing and/or 7-Zip probing before extraction.
- Recursive extraction continues breadth-first until no nested archive candidates remain or `ExtractionJob.max_depth` is reached.
- Nested wrapper archives are unpacked in place, then removed once their contents have been committed successfully.
- Password attempts run in this order:
  - no password
  - last successful password from the current session
  - saved password library
  - up to 3 manual prompts
- The default password library is intentionally empty.

## Must Update Together

- If you change default disguised suffixes in `src/autounzip/settings.py`, also update:
  - `src/autounzip/ui/dialogs.py` expectations for suffix editing
  - `README.md` user-facing feature summary
- If you change default password behavior in `src/autounzip/settings.py` or retry order in `src/autounzip/engine.py`, also update:
  - `src/autounzip/ui/dialogs.py` save-to-library flow
  - `README.md`
- If you change where output directories are created in `src/autounzip/engine.py`, also update:
  - `src/autounzip/ui/main_window.py` button text and completion messaging
  - this file
- If you change 7-Zip command-line flags, stdout/stderr decoding, or probe parsing in `src/autounzip/engine.py`, also update:
  - this file
  - any user-facing logging or status text in `src/autounzip/ui/main_window.py` that assumes UTF-8 output
- If you change entrypoints or packaging targets, also update:
  - `build-exe.ps1`
  - `scripts/build.ps1`
  - this file
- If you change release tag matching, GitHub release creation, or release-note generation in `.github/workflows/release.yml` or `scripts/generate_release_notes.ps1`, also update:
  - this file
  - `README.md` if the user-facing release flow changes
- If you change vendored resource lookup in `src/autounzip/vendor.py`, also update PyInstaller `--add-data` arguments in `scripts/build.ps1`.

## Git Hygiene

- `.gitignore` currently excludes `.venv`, `dist`, `build`, `vendor/7zip`, `settings.json`, caches, and Python bytecode.
- Do not commit generated EXEs, runtime `settings.json`, or fetched 7-Zip binaries unless the repository policy changes explicitly.
- There is currently no test suite in the repository. If tests are reintroduced, update both this file and `pyproject.toml`.

## Verification Notes

- Verified from source:
  - entrypoints and packaging scripts
  - EXE-directory settings persistence and elevation fallback
  - default empty password library
  - default disguised suffixes `.jpg`, `.jpeg`, `.psd`
  - one-file EXE build output path
  - `v[0-9]*` tag-triggered GitHub release workflow and EXE upload
  - first-release fallback in `scripts/generate_release_notes.ps1`
- Not documented here:
  - speculative refactors
  - temporary debugging notes
