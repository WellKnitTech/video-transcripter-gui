## Purpose

- This file gives coding agents repository-specific guidance for working in `video-transcripter-gui`.
- Prefer small, targeted changes that preserve the current package structure under `src/video_transcriber/`.
- Do not overwrite unrelated user changes already present in the worktree.

## Tech Stack

- Language: Python 3.10+
- Packaging: `setuptools` via `pyproject.toml`
- UI: Tkinter desktop GUI
- Test runner: `pytest`
- Linter/import sorting: `ruff`
- Security scan: `bandit`
- Type-check config: `pyrightconfig.json` exists, but pyright is not wired into Makefile, dev extras, or CI

## Repository Layout

- `src/video_transcriber/gui.py` - Tkinter app, widgets, event loop, dialogs
- `src/video_transcriber/main.py` - app entry point
- `src/video_transcriber/pipeline.py` - processing orchestration and progress events
- `src/video_transcriber/transcription.py` - Whisper integration
- `src/video_transcriber/download.py` - `yt-dlp` download integration
- `src/video_transcriber/diarization.py` - optional speaker labeling
- `src/video_transcriber/subtitles.py` - subtitle/text writers
- `src/video_transcriber/validation.py` - input validation and normalization
- `src/video_transcriber/utils.py` - pure helpers and settings persistence
- `src/video_transcriber/models.py` - dataclasses and type aliases
- `src/video_transcriber/exceptions.py` - project exception hierarchy
- `tests/` - pytest unit tests

## Setup And Run

- Create a venv: `python -m venv .venv`
- Activate it: `. .venv/bin/activate`
- Install app deps: `pip install -e .`
- Install dev tools: `pip install -e .[dev]`
- Optional speaker-labeling extras: `pip install -e .[speakers]`
- Run GUI directly: `python video_transcriber_gui.py`
- Run installed entry point: `video-transcriber-gui`

## Build, Lint, Test, And Checks

- Install package: `make install`
- Install dev deps: `make install-dev`
- Start app: `make run`
- Run tests: `make test` or `pytest`
- Run lint: `make lint` or `ruff check .`
- Run lint + tests: `make check`
- Run Bandit manually: `bandit -r src`
- Build a distribution manually if `build` is installed: `python -m build`

## Single-Test Commands

- Run one test file: `pytest tests/test_utils.py`
- Run one test function: `pytest tests/test_utils.py::test_is_url_accepts_http_and_https`
- Run one pipeline test: `pytest tests/test_pipeline.py::test_process_raises_when_cancelled_before_start`
- Filter by test name substring: `pytest -k cancelled`
- Stop after first failure: `pytest -x`

## Type Checking

- `pyrightconfig.json` includes `src`, `tests`, and `video_transcriber_gui.py` and adds `src` to extra paths.
- `reportMissingImports` is disabled because optional runtime deps may not be installed in all environments.
- There is no official repo command for pyright today.
- If pyright is installed globally or in your venv, a reasonable ad hoc command is: `pyright`
- Do not add a mandatory typecheck step unless the user asks for it.

## CI Behavior

- CI runs on Python 3.10, 3.11, and 3.12.
- CI installs `.[dev] --no-deps`, then runs `ruff check .` and `pytest`.
- This means tests should remain import-safe without requiring heavy runtime dependencies.
- Security scanning is separate and runs `bandit -r src`.

## Important Repo Gotchas

- Keep optional dependencies lazily imported inside runtime code paths.
- Avoid importing `whisper`, `yt_dlp`, `ffmpeg`, or speaker-labeling dependencies at module import time unless already required by the file's current design.
- Tests should not require network access, model downloads, GUI display access, or real ffmpeg execution.
- Prefer stubbing collaborators in `pipeline.py` tests instead of invoking full media processing.
- `validate_job_config()` creates the output directory; be aware of filesystem side effects.
- Settings persist to `~/.video_transcriber_gui.json`; tests should monkeypatch `SETTINGS_PATH` or related helpers.
- `default_output_dir()` may point to the real `~/Downloads`; avoid touching user directories in tests.
- The Makefile target `install-diarization` currently references `.[diarization]`, but the actual extra in `pyproject.toml` is `.[speakers]`.

## Cursor And Copilot Rules

- No `.cursorrules` file was found.
- No `.cursor/rules/` directory was found.
- No `.github/copilot-instructions.md` file was found.
- There are currently no extra repository-local Cursor or Copilot instructions to merge into this file.

## Code Style

- Follow existing Python style already enforced by Ruff.
- Keep line length at 100 characters.
- Use `from __future__ import annotations` in new Python modules, matching the existing codebase.
- Prefer standard library imports first, then third-party imports, then local package imports.
- Let Ruff handle import ordering; do not hand-format imports inconsistently.
- Use package-relative imports within `src/video_transcriber/` such as `from .models import JobConfig`.
- Keep module docstrings short and descriptive when a file already follows that pattern.

## Typing Guidelines

- Add type annotations to new public functions, methods, and module-level constants when practical.
- Prefer modern built-in generics like `list[str]`, `dict[str, object]`, and `tuple[int, ...]`.
- Prefer union syntax like `Path | None` over `Optional[Path]`.
- Use `Literal` for constrained string modes when the set of values is stable.
- Use `Protocol` for injectable behavior when only a narrow interface is needed.
- Match the existing dataclass-heavy modeling style for structured data.
- Prefer `@dataclass(slots=True)` for simple domain containers.

## Naming Conventions

- Use `snake_case` for functions, methods, variables, and module names.
- Use `PascalCase` for classes and exceptions.
- Use `UPPER_CASE` for constants.
- Use leading underscores for private helpers.
- Choose descriptive names tied to the domain: `JobConfig`, `TranscriptSegment`, `ProcessingService`, etc.

## Error Handling

- Prefer raising project-specific exceptions from `src/video_transcriber/exceptions.py`.
- Wrap dependency failures as `DependencyError`.
- Wrap runtime/media failures as `ProcessingError`.
- Raise `ValidationError` for user input problems with clear, user-facing messages.
- Preserve root causes with `raise ... from exc`.
- Use guard clauses for validation and early exits.
- Catch broad exceptions only when interacting with external systems and when converting them to domain errors.
- Avoid silently swallowing errors unless the existing code already treats that path as best-effort.

## Testing Conventions

- Use plain function-based `pytest` tests.
- Keep tests colocated by feature in `tests/test_<module>.py`.
- Annotate test functions with `-> None` when adding new tests.
- Use `tmp_path` for filesystem work.
- Use `monkeypatch` to isolate environment, settings paths, and collaborators.
- Use `pytest.raises(...)` for exception assertions.
- Prefer small stubs and fakes over large fixture hierarchies.
- Keep tests deterministic and offline.

## Change Guidelines For Agents

- Prefer minimal edits that match surrounding code rather than broad refactors.
- Preserve public behavior unless the task explicitly changes it.
- Update or add tests whenever behavior changes.
- If you introduce a new command or workflow, reflect it in `README.md` and this file when appropriate.
- Do not edit caches, virtualenv contents, or generated metadata directories.
- If you touch dependency-sensitive code, verify imports still work in a minimal dev environment.

## Collaboration And Handoff

- When working as a delegated or collaborating agent, send concise progress updates only at meaningful checkpoints: after repo inspection, after code changes, and after verification.
- If blocked, stop early and report the exact blocker, what you already checked, and the smallest decision or input needed from the orchestrating agent or user.
- In your final handoff, include: files touched, behavior changed, tests/checks run with outcomes, and any follow-up risks or TODOs.
- If you could not run a check or finish a change, say so explicitly instead of implying completion.
- Preserve worktree safety: never overwrite, revert, or reformat unrelated user changes, and call out any pre-existing worktree modifications that may affect your task.

## Suggested Verification After Changes

- Run `ruff check .`
- Run targeted `pytest` commands for the files you changed
- Run full `pytest` for broader changes
- For security-sensitive changes, run `bandit -r src`
- For GUI changes, prefer focused logic tests plus a quick manual smoke run of `python video_transcriber_gui.py`
