import os
import yt_dlp
import whisper
import ffmpeg
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from tkinter.ttk import Progressbar
import logging
import re
import threading

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def sanitize_filename(title):
    """Sanitize filenames by replacing spaces, dots and special sequences."""
    sanitized = re.sub(r'[ \.\.\.]+', '_', title)  # Replace spaces and ellipses with underscores
    return sanitized

def update_progress(data):
    """Callback function to update GUI progress bar based on download progress."""
    if data['status'] == 'downloading':
        percentage = data['downloaded_bytes'] / data['total_bytes'] * 100
        progress_bar['value'] = int(percentage)
        root.update_idletasks()
    elif data['status'] == 'finished':
        log_text.insert(tk.END, "Download completed.\n")
        progress_bar['value'] = 100
        root.update_idletasks()

def download_video(url, output_dir='downloads', progress_callback=None):
    """Download video from URL with progress updates."""
    try:
        ydl_opts = {
            'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
            'format': 'bestvideo+bestaudio',
            'merge_output_format': 'mp4',
            'progress_hooks': [progress_callback],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            title = sanitize_filename(info_dict.get('title', 'downloaded_video'))
            video_file = os.path.join(output_dir, f"{title}.mp4")

            if not os.path.exists(video_file):
                for f in os.listdir(output_dir):
                    if f.startswith(title) and f.endswith('.mp4'):
                        return os.path.join(output_dir, f)
                raise FileNotFoundError(f"Expected video file not found: {video_file}")
            return video_file
    except Exception as e:
        logging.error(f"Failed to download video: {e}")
        raise

def generate_transcript(video_file, save_text=False):
    """Generate transcription for the given video file and optionally save as text."""
    if not os.path.exists(video_file):
        logging.error(f"Video file does not exist: {video_file}")
        return None, None

    try:
        model = whisper.load_model("base")
        result = model.transcribe(video_file)
        base_filename = video_file.rsplit('.', 1)[0]
        transcript_file = f"{base_filename}.srt"

        with open(transcript_file, 'w') as f:
            for segment in result['segments']:
                f.write(f"{segment['id']}\n")
                f.write(f"{segment['start']} --> {segment['end']}\n")
                f.write(f"{segment['text']}\n\n")

        if save_text:
            text_file = f"{base_filename}.txt"
            with open(text_file, 'w') as f:
                for segment in result['segments']:
                    f.write(f"{segment['text']}\n")
            return transcript_file, text_file
        return transcript_file, None
    except Exception as e:
        logging.error(f"Failed to generate transcript: {e}")
        raise

def embed_subtitles(video_file, subtitle_file):
    """Embed subtitles into video file."""
    if not os.path.exists(video_file) or not os.path.exists(subtitle_file):
        logging.error(f"Files not found: {video_file} or {subtitle_file}")
        return None

    try:
        output_file = f"{video_file.rsplit('.', 1)[0]}_subtitled.mp4"
        ffmpeg.input(video_file).output(output_file, vf='subtitles={subtitle_file}', vcodec='libx264', acodec='aac').run()
        return output_file
    except ffmpeg.Error as e:
        logging.error(f"FFmpeg error: {e.stderr.decode()}")
        raise

def process_video():
    """Process video from URL for downloading, transcribing, and embedding subtitles."""
    url = url_entry.get()
    output_dir = filedialog.askdirectory(title="Select Download Directory")
    save_text = save_text_var.get()

    if not url or not output_dir:
        messagebox.showwarning("Input Error", "Please provide a valid URL and download directory.")
        return

    threading.Thread(target=lambda: threaded_process(url, output_dir, save_text)).start()

def threaded_process(url, output_dir, save_text):
    try:
        video_file = download_video(url, output_dir, progress_callback=update_progress)
        log_text.insert(tk.END, "Transcribing video...\n")
        subtitle_file, text_file = generate_transcript(video_file, save_text)
        log_text.insert(tk.END, "Embedding subtitles...\n")
        subtitled_video = embed_subtitles(video_file, subtitle_file)

        message = f"Subtitled video saved as: {subtitled_video}"
        if text_file:
            message += f"\nTranscription saved as: {text_file}"

        log_text.insert(tk.END, "Processing completed.\n")
        messagebox.showinfo("Success", message)
    except Exception as e:
        log_text.insert(tk.END, f"Error: {str(e)}\n")
        messagebox.showerror("Error", f"An error occurred: {str(e)}")

# Setup GUI
def setup_gui():
    global root, url_entry, save_text_var, progress_bar, log_text
    root = tk.Tk()
    root.title("Video Transcriber")

    frame = tk.Frame(root)
    frame.pack(pady=20, padx=20)

    url_label = tk.Label(frame, text="Video URL:")
    url_label.grid(row=0, column=0, padx=5, pady=5)

    url_entry = tk.Entry(frame, width=50)
    url_entry.grid(row=0, column=1, padx=5, pady=5)

    save_text_var = tk.BooleanVar()
    save_text_checkbox = tk.Checkbutton(frame, text="Save transcription as a text file", variable=save_text_var)
    save_text_checkbox.grid(row=1, columnspan=2, pady=10)

    progress_bar = Progressbar(frame, orient=tk.HORIZONTAL, length=300, mode='determinate')
    progress_bar.grid(row=2, columnspan=2, pady=10)

    download_button = tk.Button(frame, text="Download and Transcribe", command=process_video)
    download_button.grid(row=3, columnspan=2, pady=10)

    log_text = scrolledtext.ScrolledText(frame, height=10, width=50)
    log_text.grid(row=4, columnspan=2, pady=10)

    return root

if __name__ == "__main__":
    root = setup_gui()
    root.mainloop()
