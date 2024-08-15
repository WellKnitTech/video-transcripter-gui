import os
import yt_dlp
import whisper
import ffmpeg as ffmpeg_lib
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from tkinter.ttk import Progressbar
import logging
import time
import threading
import hashlib
from urllib.parse import urlparse
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def calculate_sha1(filepath):
    """Calculate SHA1 hash of a file."""
    sha1 = hashlib.sha1()
    with open(filepath, 'rb') as f:
        while True:
            data = f.read(65536)
            if not data:
                break
            sha1.update(data)
    return sha1.hexdigest()

def update_progress(data):
    """Update GUI progress bar based on download progress."""
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
    ydl_opts = {
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'format': 'bestvideo+bestaudio',
        'merge_output_format': 'mp4',
        'progress_hooks': [progress_callback],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            title = info_dict.get('title', 'downloaded_video')
            ext = info_dict.get('ext', 'mp4')
            video_file = os.path.join(output_dir, f"{title}.{ext}")

            timeout = 10
            while not os.path.exists(video_file) and timeout > 0:
                time.sleep(1)
                timeout -= 1

            if os.path.exists(video_file):
                return video_file
            else:
                logging.error(f"Expected video file not found: {video_file}")
                raise FileNotFoundError(f"Expected video file not found: {video_file}")

    except Exception as e:
        logging.error(f"Failed to download video: {e}")
        raise

def generate_transcript(video_file, delay=0.0, save_text=False, url=None):
    """Generate transcription for the given video file and optionally save as ASS with metadata."""
    if not os.path.exists(video_file):
        logging.error(f"Video file does not exist: {video_file}")
        return None, None

    try:
        model = whisper.load_model("base")
        result = model.transcribe(video_file)
        base_filename = video_file.rsplit('.', 1)[0]
        transcript_file = f"{base_filename}.ass"

        # Write transcript to ASS format
        with open(transcript_file, 'w', encoding='utf-8') as f:
            # ASS header
            f.write("[Script Info]\n")
            f.write("Title: Whisper Transcript\n")
            f.write("ScriptType: v4.00+\n")
            f.write("WrapStyle: 0\n")
            f.write("ScaledBorderAndShadow: yes\n")
            f.write("YCbCr Matrix: TV.601\n")
            f.write("\n[V4+ Styles]\n")
            f.write("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
                    "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
                    "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
            f.write("Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0.00,1,"
                    "1.00,0.00,2,10,10,10,1\n")
            f.write("\n[Events]\n")
            f.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")

            # Write each segment with delay applied
            for segment in result['segments']:
                start_time = max(segment['start'] + delay, 0)  # Ensure the start time isn't negative
                end_time = max(segment['end'] + delay, 0)
                text = segment['text']
                start_ass_time = convert_to_ass_time(start_time)
                end_ass_time = convert_to_ass_time(end_time)
                f.write(f"Dialogue: 0,{start_ass_time},{end_ass_time},Default,,0,0,0,,{text}\n")

        if save_text:
            text_file = f"{base_filename}.txt"
            video_length = result['segments'][-1]['end']
            sha1_hash = calculate_sha1(video_file)
            accessed_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            with open(text_file, 'w', encoding='utf-8') as f:
                f.write("===== Forensic Metadata =====\n")
                f.write(f"Source URL: {url}\n")
                f.write(f"Video Length: {video_length:.2f} seconds\n")
                f.write(f"SHA1 Hash: {sha1_hash}\n")
                f.write(f"Accessed Time: {accessed_time}\n")
                f.write(f"Original Filename: {os.path.basename(video_file)}\n")
                f.write("=============================\n\n")

                for segment in result['segments']:
                    start_time = segment['start']
                    end_time = segment['end']
                    f.write(f"[{start_time:.2f} - {end_time:.2f}] {segment['text']}\n")

            return transcript_file, text_file

        return transcript_file, None

    except Exception as e:
        logging.error(f"Failed to generate transcript: {e}")
        raise

def convert_to_ass_time(seconds):
    """Convert seconds to ASS timestamp format (H:MM:SS.CS)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centiseconds = int((seconds - int(seconds)) * 100)
    return f"{hours}:{minutes:02}:{secs:02}.{centiseconds:02}"

def verify_subtitle_file(subtitle_file):
    """Verify subtitle file existence, check if it's empty, and ensure correct format."""
    if not os.path.exists(subtitle_file):
        logging.error(f"Subtitle file does not exist: {subtitle_file}")
        return False

    if os.path.getsize(subtitle_file) == 0:
        logging.error(f"Subtitle file is empty: {subtitle_file}")
        return False

    return True

def embed_subtitles(video_file, subtitle_file):
    """Embed ASS subtitles into video file."""
    if not verify_subtitle_file(subtitle_file):
        return None

    try:
        output_file = f"{video_file.rsplit('.', 1)[0]}_subtitled.mp4"

        logging.info(f"Video file: {video_file}")
        logging.info(f"Subtitle file: {subtitle_file}")
        logging.info(f"Output file: {output_file}")

        (
            ffmpeg_lib
            .input(video_file)
            .output(output_file, vf=f"ass='{os.path.abspath(subtitle_file)}'", vcodec='libx264', acodec='aac')
            .run(overwrite_output=True)
        )

        if os.path.exists(output_file):
            logging.info(f"Subtitled video successfully created: {output_file}")
            return output_file
        else:
            logging.error(f"Failed to create subtitled video file: {output_file}")
            return None

    except Exception as e:
        logging.error(f"FFmpeg error: {str(e)}")
        return None

def is_url(input_string):
    """Check if the input string is a valid URL."""
    try:
        result = urlparse(input_string)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False

def process_video():
    """Process video from URL or local file for downloading, transcribing, and embedding subtitles."""
    input_path = url_entry.get()
    delay = float(delay_entry.get())
    embed_subs = embed_subs_var.get()

    home_dir = os.path.expanduser("~")
    default_output_dir = os.path.join(home_dir, "Downloads")

    output_dir = filedialog.askdirectory(title="Select Download Directory", initialdir=default_output_dir)
    save_text = save_text_var.get()

    if not input_path or not output_dir:
        messagebox.showwarning("Input Error", "Please provide a valid video input and download directory.")
        return

    if is_url(input_path):
        # Process as URL
        threading.Thread(target=lambda: threaded_process_url(input_path, output_dir, save_text, delay, embed_subs, input_path)).start()
    else:
        # Process as local or network file
        threading.Thread(target=lambda: threaded_process_file(input_path, output_dir, save_text, delay, embed_subs)).start()

def threaded_process_url(url, output_dir, save_text, delay, embed_subs, source_url):
    try:
        log_text.insert(tk.END, "Starting download...\n")
        video_file = download_video(url, output_dir, progress_callback=update_progress)

        log_text.insert(tk.END, "Transcribing video...\n")
        subtitle_file, text_file = generate_transcript(video_file, delay, save_text, source_url)

        if subtitle_file:
            if embed_subs:
                log_text.insert(tk.END, "Embedding subtitles...\n")
                subtitled_video = embed_subtitles(video_file, subtitle_file)
                message = f"Subtitled video saved as: {subtitled_video}"
            else:
                message = f"Subtitle file generated: {subtitle_file}"

            if text_file:
                message += f"\nTranscription saved as: {text_file}"

            log_text.insert(tk.END, "Processing completed.\n")
            messagebox.showinfo("Success", message)
        else:
            log_text.insert(tk.END, "Failed to create subtitle file.\n")
            messagebox.showerror("Error", "Failed to create subtitle file.")

    except Exception as e:
        log_text.insert(tk.END, f"Error: {str(e)}\n")
        messagebox.showerror("Error", f"An error occurred: {str(e)}")

def threaded_process_file(video_file, output_dir, save_text, delay, embed_subs):
    try:
        log_text.insert(tk.END, "Processing local video file...\n")

        log_text.insert(tk.END, "Transcribing video...\n")
        subtitle_file, text_file = generate_transcript(video_file, delay, save_text)

        if subtitle_file:
            if embed_subs:
                log_text.insert(tk.END, "Embedding subtitles...\n")
                subtitled_video = embed_subtitles(video_file, subtitle_file)
                message = f"Subtitled video saved as: {subtitled_video}"
            else:
                message = f"Subtitle file generated: {subtitle_file}"

            if text_file:
                message += f"\nTranscription saved as: {text_file}"

            log_text.insert(tk.END, "Processing completed.\n")
            messagebox.showinfo("Success", message)
        else:
            log_text.insert(tk.END, "Failed to create subtitle file.\n")
            messagebox.showerror("Error", "Failed to create subtitle file.")

    except Exception as e:
        log_text.insert(tk.END, f"Error: {str(e)}\n")
        messagebox.showerror("Error", f"An error occurred: {str(e)}")

def setup_gui():
    """Setup the GUI components."""
    global root, url_entry, delay_entry, save_text_var, embed_subs_var, progress_bar, log_text
    root = tk.Tk()
    root.title("Video Transcriber")

    frame = tk.Frame(root)
    frame.pack(pady=20, padx=20)

    # URL/File Path Entry
    tk.Label(frame, text="Video URL or File Path:").grid(row=0, column=0, padx=5, pady=5)
    url_entry = tk.Entry(frame, width=50)
    url_entry.grid(row=0, column=1, padx=5, pady=5)

    # Subtitle Delay Entry
    tk.Label(frame, text="Subtitle Delay (seconds):").grid(row=1, column=0, padx=5, pady=5)
    delay_entry = tk.Entry(frame, width=10)
    delay_entry.grid(row=1, column=1, padx=5, pady=5)
    delay_entry.insert(0, "0.0")  # Default delay of 0 seconds

    # Save Text Checkbox
    save_text_var = tk.BooleanVar()
    tk.Checkbutton(frame, text="Save transcription as a text file", variable=save_text_var).grid(row=2, columnspan=2, pady=10)

    # Embed Subtitles Checkbox
    embed_subs_var = tk.BooleanVar()
    tk.Checkbutton(frame, text="Embed subtitles into video", variable=embed_subs_var).grid(row=3, columnspan=2, pady=10)
    embed_subs_var.set(True)  # Default to embedding subtitles

    # Progress Bar
    progress_bar = Progressbar(frame, orient=tk.HORIZONTAL, length=300, mode='determinate')
    progress_bar.grid(row=4, columnspan=2, pady=10)

    # Process Video Button
    tk.Button(frame, text="Process Video", command=process_video).grid(row=5, columnspan=2, pady=10)

    # Log Text Box
    log_text = scrolledtext.ScrolledText(frame, height=10, width=50)
    log_text.grid(row=6, columnspan=2, pady=10)

    return root

if __name__ == "__main__":
    root = setup_gui()
    root.mainloop()
