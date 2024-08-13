# Video Transcriber GUI

This is a Python application that downloads a video from a specified URL, transcribes the audio using OpenAI's Whisper model, and optionally embeds the transcript as subtitles into the video.

## Features

- Download videos from various platforms like YouTube, Twitter, etc.
- Transcribe the audio to generate a transcript.
- Optionally save the transcript as a `.txt` file.
- Embed the transcript as subtitles in the video.

## Requirements

- Python 3.x
- `yt-dlp`
- `whisper`
- `ffmpeg`
- `tkinter`

## Usage

Run the `video_transcriber_gui.py` script to start the GUI application.

```bash
python video_transcriber_gui.py
