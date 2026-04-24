.PHONY: install install-dev install-diarization run test lint check

install:
	pip install -e .

install-dev:
	pip install -e .[dev]

install-diarization:
	pip install -e .[diarization]

run:
	python video_transcriber_gui.py

test:
	pytest

lint:
	ruff check .

check: lint test
