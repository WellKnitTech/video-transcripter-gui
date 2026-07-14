# Video Transcriber GUI

Desktop app for downloading videos, generating subtitles with [faster-whisper](https://github.com/SYSTRAN/faster-whisper), optionally adding local speaker labeling, and exporting transcript artifacts to a chosen output directory.

## What Changed

This project has been reworked from a single-script prototype into a small package with:

- safer Tkinter threading via a worker queue and main-thread UI updates
- best-effort job cancellation between stages, plus killable transcription/embed workers
- banded overall progress so download percent does not jump the rest of the job
- input validation for URLs, files, output directories, subtitle delay, language, device, and speaker counts
- overwrite confirmation when predicted outputs already exist
- modular code under `src/video_transcriber/`
- cached faster-whisper model loading per app session (in the worker process)
- selectable subtitle format (`ass`, `srt`, or `vtt`), Whisper model size, language, and device
- CPU defaults: INT8 compute, Silero VAD, and auto CPU thread count
- an editable transcript panel for post-run transcript fixes and re-exporting
- persisted recent settings
- tests, linting, package metadata, and CI

## Project Layout

```text
src/video_transcriber/
  gui.py                   Tkinter app orchestration
  gui_views.py             Passive view builders
  gui_theme.py             Theme and option lists
  gui_logic.py             Form/settings translation
  gui_events.py            Queue polling helpers
  gui_transcript_editor.py Transcript editor helpers
  pipeline.py              Download/transcribe/embed orchestration
  transcription.py         faster-whisper integration
  progress.py              Overall progress banding
  download.py              yt-dlp download integration
  subtitles.py             ASS, SRT, VTT, and text writers
  diarization.py           Optional heuristic speaker labeling
  audio_preprocess.py      Audio extract/cleanup for speakers
  validation.py            User input validation
  utils.py                 Shared pure helpers and settings storage
  models.py                Dataclasses and type aliases
tests/                     Unit tests for pure and orchestration helpers
```

## Requirements

- Python 3.10+
- `ffmpeg` installed and available on your `PATH`
- Tkinter available in your Python installation

Tkinter is usually bundled by your OS Python package and is not installed from PyPI.

## Quick Start

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
# or: make install-speakers
```

For development tools:

```bash
pip install -e .[dev]
```

## Run

After activating your virtual environment:

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
3. Choose the Whisper model size (`tiny` / `base` / `small` / `medium` / `large-v3` / `distil-large-v3`).
4. Pick language (`auto` or a language code) and device (`auto` / `cpu` / `cuda`).
5. Pick subtitle format (`ass`, `srt`, or `vtt`).
6. Optionally enable speaker labeling, transcript text export, and subtitle embedding.
7. Start processing, monitor the status log and progress bar, and cancel if needed.
8. After the run completes, edit the timestamped transcript in the built-in editor and export revised text or subtitle files.

Generated outputs can include:

- subtitle file in the chosen format
- text transcript with forensic metadata
- embedded `.mp4` with burned-in subtitles
- edited transcript exports from the transcript editor

## CPU Tips

- Prefer `tiny`, `base`, `small`, or `distil-large-v3` when running without a GPU.
- Leave device on `auto` or set it to `cpu`; the app uses INT8, VAD filtering, and multi-threaded CTranslate2 on CPU.
- Setting an explicit language (for example `en`) avoids expensive auto-detect mistakes on noisy audio.

## Developer Commands

With the virtual environment active:

```bash
pytest
ruff check .
```

## CI

GitHub Actions runs:

- `ruff` lint checks
- `pytest`
- Bandit security scans

## Known Limitations

- Cancellation stops between stages and can terminate the transcription child process or ffmpeg embed process; very short races may still finish a step briefly after Cancel.
- Speaker labeling is local, heuristic (MFCC + clustering), and best-effort.
- Embedding depends on local `ffmpeg` capabilities.
- Whisper model downloads can be large on first run (Hugging Face / CTranslate2 converted weights).

## Troubleshooting

- `ffmpeg is not installed or is not on PATH`
  - install `ffmpeg` with your package manager and confirm `ffmpeg -version` works
- GUI starts but transcription fails immediately
  - ensure `faster-whisper` is installed and the selected model can be downloaded
- speaker labeling fails
  - install the optional speakers extras and try again without speaker labeling to confirm the base pipeline works

## License

This project is licensed under the Unlicense. See `LICENSE` for details.
