# Video Transcriber GUI

## Overview

The **Video Transcriber GUI** is a Python-based graphical user interface (GUI) tool designed to download, transcribe, and embed subtitles into video files. The tool leverages various powerful libraries like `yt-dlp`, `whisper`, and `ffmpeg` to accomplish its tasks, providing an intuitive interface for users to interact with these processes.

## Features

- **Download Videos:** Download videos from supported URLs using `yt-dlp`.
- **Generate Transcripts:** Automatically transcribe downloaded or locally stored videos using OpenAI's Whisper model.
- **Embed Subtitles:** Optionally embed generated subtitles directly into the video file.
- **Save Forensic Metadata:** Save transcripts along with forensic metadata, such as SHA1 hash, source URL, and video length, ensuring the transcript's integrity.
- **Customizable:** Users can adjust subtitle delay and choose whether to embed subtitles or save the transcription as a text file.

## Prerequisites

Before running the application, ensure you have the following installed:

- Python 3.x
- Required Python packages (can be installed using `pip`):
  - yt-dlp
  - whisper
  - ffmpeg-python
  - tkinter

You can install the necessary Python packages using:

```bash
pip install yt-dlp whisper ffmpeg-python tkinter
```

Additionally, ensure `ffmpeg` is installed on your system and accessible via the command line.

## How to Use

1. **Run the Application:**
   - You can start the GUI by executing the script `video_transcriber_gui.py`.

   ```bash
   python video_transcriber_gui.py
   ```

2. **Provide Input:**
   - Enter a video URL or select a local video file path.
   - Set the subtitle delay if needed (default is `0.0` seconds).
   - Choose whether to save the transcription as a text file.
   - Decide if you want the subtitles embedded directly into the video.

3. **Select Output Directory:**
   - Choose the directory where the video and transcription files will be saved.

4. **Process the Video:**
   - Click on "Process Video" to start downloading (if applicable), transcribing, and embedding subtitles.

5. **Monitor Progress:**
   - The progress of the download and transcription will be displayed in the progress bar and log section.

## Logging and Error Handling

The application logs all actions and errors to help you debug if anything goes wrong. Logs are printed directly to the GUI's log text box.

## License

This project is licensed under the Unlicense. See the LICENSE file for more details.

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue for any bugs or feature requests.

## Disclaimer

This tool is provided as-is without any guarantees. Use it at your own risk, especially when handling sensitive or large video files.
