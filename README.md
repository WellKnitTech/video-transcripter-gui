# Video Transcriber GUI

Desktop app for downloading videos, generating subtitles with Whisper, optionally adding local speaker labeling, and exporting transcript artifacts to a chosen output directory.

## What Changed

This project has been reworked from a single-script prototype into a small package with:

- safer Tkinter threading via a worker queue and main-thread UI updates
- best-effort job cancellation between major processing stages and during downloads
- input validation for URLs, files, output directories, subtitle delay, and speaker counts
- consistent output handling for both downloaded and local files
- modular code under `src/video_transcriber/`
- cached Whisper model loading per app session
- selectable subtitle format (`ass`, `srt`, or `vtt`) and Whisper model size
- an editable transcript panel for post-run transcript fixes and re-exporting
- persisted recent settings
- tests, linting, package metadata, and CI

## Project Layout

```text
src/video_transcriber/
  gui.py            Tkinter app and event loop
  pipeline.py       Download/transcribe/embed orchestration
  transcription.py  Whisper integration
  subtitles.py      ASS, SRT, and text transcript writers
  diarization.py    Optional speaker labeling helpers
  validation.py     User input validation
  utils.py          Shared pure helpers and settings storage
tests/              Unit tests for pure and orchestration helpers
```

## Requirements

- Python 3.10+
- `ffmpeg` installed and available on your `PATH`
- Tkinter available in your Python installation

Tkinter is usually bundled by your OS Python package and is not installed from PyPI.

## Quick Start

If you just want to run the new version locally:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
python video_transcriber_gui.py
```

You can also launch it with the installed command after activation:

```bash
video-transcriber-gui
```

## Install

Create a virtual environment and install the project:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
```

To enable speaker labeling support, install the optional extras:

```bash
pip install -e .[speakers]
```

For development tools:

```bash
pip install -e .[dev]
```

## Run

After activating your virtual environment, you can launch the GUI in either of these ways:

```bash
python video_transcriber_gui.py
```

or

```bash
video-transcriber-gui
```

## Using the App

1. Choose an input mode: URL download or local file.
2. Select the output directory.
3. Choose the Whisper model size.
4. Pick subtitle format (`ass`, `srt`, or `vtt`).
5. Optionally enable speaker labeling, transcript text export, and subtitle embedding.
6. Start processing, monitor the status log and progress bar, and cancel if needed.
7. After the run completes, edit the timestamped transcript in the built-in editor and export revised text or subtitle files.

Generated outputs can include:

- subtitle file in the chosen format
- text transcript with forensic metadata
- embedded `.mp4` with burned-in subtitles
- edited transcript exports from the transcript editor

## Developer Commands

With the virtual environment active:

```bash
pytest
ruff check .
```

## CI

GitHub Actions now runs:

- `ruff` lint checks
- `pytest`
- Bandit security scans

## Known Limitations

- cancellation is best-effort and may finish the currently running model call before stopping
- speaker labeling is local, heuristic, and best-effort
- embedding depends on local `ffmpeg` capabilities
- Whisper model downloads can be large on first run

## Troubleshooting

- `ffmpeg is not installed or is not on PATH`
  - install `ffmpeg` with your package manager and confirm `ffmpeg -version` works
- GUI starts but transcription fails immediately
  - ensure the Whisper package is installed and the selected model can be downloaded
- speaker labeling fails
  - install the optional speakers extras and try again without speaker labeling to confirm the base pipeline works

## License

This project is licensed under the Unlicense. See `LICENSE` for details.
