.PHONY: install install-dev install-speakers install-diarization run test lint check

install:
	pip install -e .

install-dev:
	pip install -e .[dev]

install-speakers:
	pip install -e .[speakers]

# Deprecated alias; prefer `make install-speakers`.
install-diarization: install-speakers

run:
	python video_transcriber_gui.py

test:
	pytest

lint:
	ruff check .

check: lint test
