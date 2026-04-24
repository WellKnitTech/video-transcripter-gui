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
import numpy as np
from scipy import signal
import librosa
from sklearn.cluster import KMeans
import soundfile as sf

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AudioDiarizer:
    """Handle speaker diarization for audio segments."""

    def __init__(self, num_speakers=2):
        self.num_speakers = num_speakers
        self.sample_rate = 16000

    def process_audio(self, audio_path):
        """Process audio file and return speaker segments."""
        # Load and resample audio
        y, _ = librosa.load(audio_path, sr=self.sample_rate)

        # Extract features
        mfcc = librosa.feature.mfcc(y=y, sr=self.sample_rate, n_mfcc=20)

        # Segment the audio into fixed windows
        window_size = int(0.5 * self.sample_rate)  # 500ms windows
        hop_length = int(0.25 * self.sample_rate)  # 250ms hop

        # Get segments
        segments = []
        timestamps = []

        for i in range(0, len(y) - window_size, hop_length):
            segment = y[i:i + window_size]
            if len(segment) == window_size:
                energy = np.sum(segment ** 2)
                if energy > 0.001:  # Basic voice activity detection
                    segments.append(segment)
                    timestamps.append(i / self.sample_rate)

        if not segments:
            return []

        # Extract features for each segment
        features = []
        for segment in segments:
            segment_mfcc = librosa.feature.mfcc(y=segment, sr=self.sample_rate, n_mfcc=20)
            features.append(np.mean(segment_mfcc.T, axis=0))

        features = np.array(features)

        # Cluster the features
        kmeans = KMeans(n_clusters=self.num_speakers, random_state=42)
        labels = kmeans.fit_predict(features)

        # Create diarization results
        results = []
        current_speaker = labels[0]
        start_time = timestamps[0]

        for i in range(1, len(labels)):
            if labels[i] != current_speaker:
                results.append({
                    'start': start_time,
                    'end': timestamps[i],
                    'speaker': current_speaker
                })
                current_speaker = labels[i]
                start_time = timestamps[i]

        # Add final segment
        results.append({
            'start': start_time,
            'end': timestamps[-1] + 0.5,
            'speaker': current_speaker
        })

        return results
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

def convert_to_ass_time(seconds):
    """Convert seconds to ASS timestamp format (H:MM:SS.CS)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centiseconds = int((seconds - int(seconds)) * 100)
    return f"{hours}:{minutes:02}:{secs:02}.{centiseconds:02}"

def verify_subtitle_file(subtitle_file):
    """Verify subtitle file existence and validity."""
    if not os.path.exists(subtitle_file):
        logging.error(f"Subtitle file does not exist: {subtitle_file}")
        return False

    if os.path.getsize(subtitle_file) == 0:
        logging.error(f"Subtitle file is empty: {subtitle_file}")
        return False

    return True

def estimate_processing_time(video_file, enable_diarization=False):
    """Estimate processing time based on video duration."""
    try:
        # Get video duration using ffmpeg
        probe = ffmpeg_lib.probe(video_file)
        duration = float(probe['format']['duration'])

        # Base estimates (in seconds)
        # Whisper processing is roughly 0.1x realtime on CPU
        transcription_time = duration * 0.1

        # Diarization is roughly 0.05x realtime
        diarization_time = duration * 0.05 if enable_diarization else 0

        # Additional overhead for file operations
        overhead = 5

        total_estimate = transcription_time + diarization_time + overhead
        return total_estimate
    except Exception as e:
        logging.error(f"Failed to estimate processing time: {e}")
        return None

def update_progress_text(message, current_step, total_steps, time_left=None):
    """Update progress text in GUI with time estimation."""
    progress_text = f"Step {current_step}/{total_steps}: {message}"
    if time_left is not None:
        minutes = int(time_left // 60)
        seconds = int(time_left % 60)
        progress_text += f" (Estimated time remaining: {minutes}m {seconds}s)"

    log_text.insert(tk.END, progress_text + "\n")
    log_text.see(tk.END)
    root.update_idletasks()

def process_with_progress(video_file, enable_diarization, total_estimate):
    """Update progress bar based on processing stage."""
    if total_estimate:
        steps_completed = 0
        total_steps = 3 if enable_diarization else 2

        # Update progress bar to show overall progress
        def update_progress(step, step_progress):
            overall_progress = ((steps_completed + step_progress) / total_steps) * 100
            progress_bar['value'] = overall_progress
            root.update_idletasks()

        return update_progress, total_steps
    return None, None

def generate_transcript(video_file, delay=0.0, save_text=False, url=None, enable_diarization=False, num_speakers=2, progress_callback=None):
    """Generate transcription for the given video file with optional diarization."""
    if not os.path.exists(video_file):
        logging.error(f"Video file does not exist: {video_file}")
        return None, None

    try:
        # Convert video to WAV for diarization if needed
        audio_path = None
        if enable_diarization:
            audio_path = f"{video_file.rsplit('.', 1)[0]}_audio.wav"
            try:
                (
                    ffmpeg_lib
                    .input(video_file)
                    .output(audio_path, acodec='pcm_s16le', ac=1, ar=16000)
                    .run(capture_stdout=True, capture_stderr=True)
                )
            except Exception as e:
                logging.error(f"Failed to extract audio: {e}")
                enable_diarization = False

        # Initialize Whisper
        model = whisper.load_model("base")

        # Update progress if callback provided
        if progress_callback:
            progress_callback(0, 0.2)  # 20% progress for model loading

        result = model.transcribe(video_file)

        # Update progress for transcription completion
        if progress_callback:
            progress_callback(0, 0.6)  # 60% progress after transcription

        # Get diarization results if enabled
        speaker_segments = []
        if enable_diarization and audio_path and os.path.exists(audio_path):
            diarizer = AudioDiarizer(num_speakers=num_speakers)
            speaker_segments = diarizer.process_audio(audio_path)

            # Update progress for diarization
            if progress_callback:
                progress_callback(0, 0.8)  # 80% progress after diarization

            # Clean up temporary audio file
            try:
                os.remove(audio_path)
            except:
                pass

        base_filename = video_file.rsplit('.', 1)[0]
        transcript_file = f"{base_filename}.ass"

        # Write transcript to ASS format
        with open(transcript_file, 'w', encoding='utf-8') as f:
            # Write ASS header
            f.write("[Script Info]\n")
            f.write("Title: Whisper Transcript\n")
            f.write("ScriptType: v4.00+\n")
            f.write("WrapStyle: 0\n")
            f.write("ScaledBorderAndShadow: yes\n")
            f.write("\n[V4+ Styles]\n")
            f.write("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
                    "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
                    "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")

            # Define styles for different speakers
            speaker_colors = [
                "&H0000FF00",  # Green
                "&H000000FF",  # Red
                "&H00FF0000",  # Blue
                "&H00FF00FF",  # Purple
            ]

            # Default style
            f.write("Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0.00,1,"
                    "1.00,0.00,2,10,10,10,1\n")

            # Speaker styles
            if enable_diarization:
                for i in range(num_speakers):
                    color = speaker_colors[i % len(speaker_colors)]
                    f.write(f"Style: Speaker{i},Arial,20,{color},&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0.00,1,"
                           "1.00,0.00,2,10,10,10,1\n")

            f.write("\n[Events]\n")
            f.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")

            # Write segments with speaker identification if available
            for segment in result['segments']:
                start_time = max(segment['start'] + delay, 0)
                end_time = max(segment['end'] + delay, 0)
                text = segment['text']

                # Find matching speaker if diarization is enabled
                style = "Default"
                if enable_diarization and speaker_segments:
                    for speaker_segment in speaker_segments:
                        if (start_time >= speaker_segment['start'] and
                            start_time < speaker_segment['end']):
                            style = f"Speaker{speaker_segment['speaker']}"
                            break

                start_ass_time = convert_to_ass_time(start_time)
                end_ass_time = convert_to_ass_time(end_time)
                f.write(f"Dialogue: 0,{start_ass_time},{end_ass_time},{style},,0,0,0,,{text}\n")

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
                if enable_diarization:
                    f.write(f"Number of Speakers: {num_speakers}\n")
                f.write("=============================\n\n")

                for segment in result['segments']:
                    start_time = segment['start']
                    end_time = segment['end']
                    text = segment['text']

                    speaker_label = "Unknown"
                    if enable_diarization and speaker_segments:
                        for speaker_segment in speaker_segments:
                            if (start_time >= speaker_segment['start'] and
                                start_time < speaker_segment['end']):
                                speaker_label = f"Speaker {speaker_segment['speaker']}"
                                break

                    f.write(f"[{start_time:.2f} - {end_time:.2f}] {speaker_label}: {text}\n")

            # Final progress update
            if progress_callback:
                progress_callback(0, 1.0)  # 100% progress at completion

            return transcript_file, text_file

        # Final progress update
        if progress_callback:
            progress_callback(0, 1.0)  # 100% progress at completion

        return transcript_file, None

    except Exception as e:
        logging.error(f"Failed to generate transcript: {e}")
        raise

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
    """Process video with download, transcription, and optional diarization."""
    input_path = url_entry.get()
    delay = float(delay_entry.get())
    embed_subs = embed_subs_var.get()
    enable_diarization = enable_diarization_var.get()
    num_speakers = int(num_speakers_var.get())

    home_dir = os.path.expanduser("~")
    default_output_dir = os.path.join(home_dir, "Downloads")

    output_dir = filedialog.askdirectory(title="Select Download Directory", initialdir=default_output_dir)
    save_text = save_text_var.get()

    if not input_path or not output_dir:
        messagebox.showwarning("Input Error", "Please provide a valid video input and download directory.")
        return

    if is_url(input_path):
        threading.Thread(target=lambda: threaded_process_url(
            input_path, output_dir, save_text, delay, embed_subs,
            enable_diarization, num_speakers, input_path)).start()
    else:
        threading.Thread(target=lambda: threaded_process_file(
            input_path, output_dir, save_text, delay, embed_subs,
            enable_diarization, num_speakers)).start()

def threaded_process_url(url, output_dir, save_text, delay, embed_subs, enable_diarization, num_speakers, source_url):
    """Enhanced URL processing with progress tracking."""
    try:
        log_text.insert(tk.END, "Starting download...\n")
        video_file = download_video(url, output_dir, progress_callback=update_progress)

        # Reset progress bar for processing
        progress_bar['value'] = 0
        root.update_idletasks()

        # Get time estimate after download
        total_estimate = estimate_processing_time(video_file, enable_diarization)
        if total_estimate:
            minutes = int(total_estimate // 60)
            seconds = int(total_estimate % 60)
            log_text.insert(tk.END, f"Estimated processing time: {minutes}m {seconds}s\n")

        progress_updater, total_steps = process_with_progress(video_file, enable_diarization, total_estimate)
        current_step = 1

        # Start processing timer
        start_time = time.time()
        update_progress_text("Transcribing video", current_step, total_steps, total_estimate)

        subtitle_file, text_file = generate_transcript(
            video_file, delay, save_text, source_url,
            enable_diarization=enable_diarization,
            num_speakers=num_speakers,
            progress_callback=progress_updater
        )

        if enable_diarization:
            current_step += 1
            elapsed = time.time() - start_time
            time_left = max(0, total_estimate - elapsed)
            update_progress_text("Processing speaker diarization", current_step, total_steps, time_left)

        current_step += 1
        if subtitle_file:
            if embed_subs:
                elapsed = time.time() - start_time
                time_left = max(0, total_estimate - elapsed)
                update_progress_text("Embedding subtitles", current_step, total_steps, time_left)

                subtitled_video = embed_subtitles(video_file, subtitle_file)
                message = f"Subtitled video saved as: {subtitled_video}"
            else:
                message = f"Subtitle file generated: {subtitle_file}"

            if text_file:
                message += f"\nTranscription saved as: {text_file}"

            total_time = time.time() - start_time
            minutes = int(total_time // 60)
            seconds = int(total_time % 60)

            log_text.insert(tk.END, f"\nProcessing completed in {minutes}m {seconds}s.\n")
            messagebox.showinfo("Success", message)
        else:
            log_text.insert(tk.END, "Failed to create subtitle file.\n")
            messagebox.showerror("Error", "Failed to create subtitle file.")

    except Exception as e:
        log_text.insert(tk.END, f"Error: {str(e)}\n")
        messagebox.showerror("Error", f"An error occurred: {str(e)}")

def threaded_process_file(video_file, output_dir, save_text, delay, embed_subs, enable_diarization, num_speakers):
    """Enhanced file processing with progress tracking."""
    try:
        log_text.insert(tk.END, "Analyzing video file...\n")

        # Get initial time estimate
        total_estimate = estimate_processing_time(video_file, enable_diarization)
        if total_estimate:
            minutes = int(total_estimate // 60)
            seconds = int(total_estimate % 60)
            log_text.insert(tk.END, f"Estimated total processing time: {minutes}m {seconds}s\n")

        progress_updater, total_steps = process_with_progress(video_file, enable_diarization, total_estimate)
        current_step = 1

        # Transcription step
        start_time = time.time()
        update_progress_text("Transcribing video", current_step, total_steps, total_estimate)

        subtitle_file, text_file = generate_transcript(
            video_file, delay, save_text, None,
            enable_diarization=enable_diarization,
            num_speakers=num_speakers,
            progress_callback=progress_updater
        )

        if enable_diarization:
            current_step += 1
            elapsed = time.time() - start_time
            time_left = max(0, total_estimate - elapsed)
            update_progress_text("Processing speaker diarization", current_step, total_steps, time_left)

        current_step += 1
        if subtitle_file:
            if embed_subs:
                elapsed = time.time() - start_time
                time_left = max(0, total_estimate - elapsed)
                update_progress_text("Embedding subtitles", current_step, total_steps, time_left)

                subtitled_video = embed_subtitles(video_file, subtitle_file)
                message = f"Subtitled video saved as: {subtitled_video}"
            else:
                message = f"Subtitle file generated: {subtitle_file}"

            if text_file:
                message += f"\nTranscription saved as: {text_file}"

            total_time = time.time() - start_time
            minutes = int(total_time // 60)
            seconds = int(total_time % 60)

            log_text.insert(tk.END, f"\nProcessing completed in {minutes}m {seconds}s.\n")
            messagebox.showinfo("Success", message)
        else:
            log_text.insert(tk.END, "Failed to create subtitle file.\n")
            messagebox.showerror("Error", "Failed to create subtitle file.")

    except Exception as e:
        log_text.insert(tk.END, f"Error: {str(e)}\n")
        messagebox.showerror("Error", f"An error occurred: {str(e)}")

def setup_gui():
    """Setup the GUI components with diarization options."""
    global root, url_entry, delay_entry, save_text_var, embed_subs_var
    global enable_diarization_var, num_speakers_var, progress_bar, log_text

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
    delay_entry.grid(row=1, column=1, padx=5, pady=5, sticky='w')
    delay_entry.insert(0, "0.0")

    # Number of Speakers Entry
    tk.Label(frame, text="Number of Speakers:").grid(row=2, column=0, padx=5, pady=5)
    num_speakers_var = tk.StringVar(value="2")
    num_speakers_entry = tk.Entry(frame, width=5, textvariable=num_speakers_var)
    num_speakers_entry.grid(row=2, column=1, padx=5, pady=5, sticky='w')

    # Enable Diarization Checkbox
    enable_diarization_var = tk.BooleanVar()
    tk.Checkbutton(frame, text="Enable Speaker Diarization", variable=enable_diarization_var).grid(row=3, columnspan=2, pady=5)

    # Save Text Checkbox
    save_text_var = tk.BooleanVar()
    tk.Checkbutton(frame, text="Save transcription as a text file", variable=save_text_var).grid(row=4, columnspan=2, pady=5)

    # Embed Subtitles Checkbox
    embed_subs_var = tk.BooleanVar()
    tk.Checkbutton(frame, text="Embed subtitles into video", variable=embed_subs_var).grid(row=5, columnspan=2, pady=5)
    embed_subs_var.set(True)

    # Progress Bar
    progress_bar = Progressbar(frame, orient=tk.HORIZONTAL, length=300, mode='determinate')
    progress_bar.grid(row=6, columnspan=2, pady=10)

    # Process Video Button
    tk.Button(frame, text="Process Video", command=process_video).grid(row=7, columnspan=2, pady=10)

    # Log Text Box
    log_text = scrolledtext.ScrolledText(frame, height=10, width=50)
    log_text.grid(row=8, columnspan=2, pady=10)

    return root

if __name__ == "__main__":
    root = setup_gui()
    root.mainloop()
