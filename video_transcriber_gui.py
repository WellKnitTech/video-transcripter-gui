import os
import yt_dlp
import whisper
import ffmpeg
import tkinter as tk
from tkinter import filedialog, messagebox

def download_video(url, output_dir='downloads'):
    ydl_opts = {
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'format': 'best',
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        video_file = ydl.prepare_filename(info_dict)
        return video_file

def generate_transcript(video_file, save_text=False):
    model = whisper.load_model("base")
    result = model.transcribe(video_file)
    base_filename = video_file.rsplit('.', 1)[0]
    transcript_file = base_filename + '.srt'

    with open(transcript_file, 'w') as f:
        for segment in result['segments']:
            f.write(f"{segment['id']}\n")
            f.write(f"{segment['start']} --> {segment['end']}\n")
            f.write(f"{segment['text']}\n\n")

    if save_text:
        text_file = base_filename + '.txt'
        with open(text_file, 'w') as f:
            for segment in result['segments']:
                f.write(f"{segment['text']}\n")
        return transcript_file, text_file

    return transcript_file, None

def embed_subtitles(video_file, subtitle_file):
    output_file = video_file.rsplit('.', 1)[0] + '_subtitled.mp4'
    ffmpeg.input(video_file).output(output_file, vf=f"subtitles={subtitle_file}").run()
    return output_file

def process_video():
    url = url_entry.get()
    output_dir = filedialog.askdirectory(title="Select Download Directory")
    save_text = save_text_var.get()

    if not url or not output_dir:
        messagebox.showwarning("Input Error", "Please provide a valid URL and download directory.")
        return

    try:
        video_file = download_video(url, output_dir)
        subtitle_file, text_file = generate_transcript(video_file, save_text=save_text)
        subtitled_video = embed_subtitles(video_file, subtitle_file)

        message = f"Subtitled video saved as: {subtitled_video}"
        if text_file:
            message += f"\nTranscription saved as: {text_file}"

        messagebox.showinfo("Success", message)
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {str(e)}")

# Setting up the GUI
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

download_button = tk.Button(frame, text="Download and Transcribe", command=process_video)
download_button.grid(row=2, columnspan=2, pady=10)

root.mainloop()
