import tkinter as tk
from tkinter import filedialog, messagebox
import os
import cv2
import threading
import configparser
import re

from moviepy import VideoFileClip, ImageSequenceClip, AudioFileClip


class VideoFrameTool:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Video ⇄ Frames Tool (LOSSLESS)")
        self.root.geometry("520x420")
        self.root.configure(bg="#1e1e1e")

        self.build_ui()
        self.root.mainloop()

    # ---------------- UI ---------------- #
    def build_ui(self):
        tk.Label(
            self.root,
            text="Video ⇄ Image Frames (LOSSLESS)",
            fg="white",
            bg="#1e1e1e",
            font=("Segoe UI", 16, "bold")
        ).pack(pady=15)

        self.mode = tk.StringVar(value="decode")

        tk.Radiobutton(
            self.root, text="Decode Video → Frames + Audio",
            variable=self.mode, value="decode",
            fg="white", bg="#1e1e1e", selectcolor="#333"
        ).pack(anchor="w", padx=40)

        tk.Radiobutton(
            self.root, text="Encode Frames → Video (LOSSLESS)",
            variable=self.mode, value="encode",
            fg="white", bg="#1e1e1e", selectcolor="#333"
        ).pack(anchor="w", padx=40)

        self.input_entry = self.entry("Input File / Folder")
        self.output_entry = self.entry("Output Folder / File")

        tk.Button(self.root, text="Browse Input", command=self.browse_input).pack(pady=3)
        tk.Button(self.root, text="Browse Output", command=self.browse_output).pack(pady=3)

        tk.Button(
            self.root,
            text="START",
            command=self.start,
            bg="#00b894",
            fg="black",
            font=("Segoe UI", 11, "bold"),
            width=25
        ).pack(pady=20)

        self.status = tk.Label(self.root, text="", fg="#00ffcc", bg="#1e1e1e")
        self.status.pack()

    def entry(self, label):
        tk.Label(self.root, text=label, fg="white", bg="#1e1e1e").pack()
        e = tk.Entry(self.root, width=60)
        e.pack(pady=3)
        return e

    # ---------------- Browse ---------------- #
    def browse_input(self):
        if self.mode.get() == "decode":
            path = filedialog.askopenfilename(
                filetypes=[("Video Files", "*.mp4 *.mkv *.mov *.avi")]
            )
        else:
            path = filedialog.askdirectory()
        if path:
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, path)

    def browse_output(self):
        if self.mode.get() == "decode":
            path = filedialog.askdirectory()
        else:
            path = filedialog.asksaveasfilename(defaultextension=".mp4")
        if path:
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, path)

    # ---------------- Control ---------------- #
    def start(self):
        threading.Thread(target=self.run, daemon=True).start()

    def run(self):
        try:
            if self.mode.get() == "decode":
                self.decode_video()
            else:
                self.encode_video()
            messagebox.showinfo("Done", "Operation completed successfully")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ---------------- Decode ---------------- #
    def decode_video(self):
        video_path = self.input_entry.get()
        out_dir = self.output_entry.get()
        os.makedirs(out_dir, exist_ok=True)

        clip = VideoFileClip(video_path)

        fps = clip.fps
        width, height = clip.size
        duration = clip.duration

        count = 0
        for frame in clip.iter_frames(dtype="uint8"):
            path = os.path.join(out_dir, f"frame_{count:06d}.png")
            cv2.imwrite(path, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
            count += 1

        if clip.audio:
            clip.audio.write_audiofile(
                os.path.join(out_dir, "audio.wav"),
                codec="pcm_s16le",
                logger=None
            )

        config = configparser.ConfigParser()
        config["VIDEO"] = {
            "fps": fps,
            "width": width,
            "height": height,
            "frames": count,
            "duration": duration
        }

        with open(os.path.join(out_dir, "video_metadata.ini"), "w") as f:
            config.write(f)

        clip.close()

    # ---------------- Encode ---------------- #
    def encode_video(self):
        in_dir = self.input_entry.get()
        out_video = self.output_entry.get()

        config = configparser.ConfigParser()
        config.read(os.path.join(in_dir, "video_metadata.ini"))

        meta = config["VIDEO"]
        fps = float(meta["fps"])
        duration = float(meta["duration"])

        frame_re = re.compile(r"^frame_(\d+)\.png$")
        frames = []

        for f in os.listdir(in_dir):
            m = frame_re.match(f)
            if m:
                frames.append((int(m.group(1)), os.path.join(in_dir, f)))

        frames.sort(key=lambda x: x[0])
        frame_paths = [f[1] for f in frames]

        clip = ImageSequenceClip(frame_paths, fps=fps)

        audio_path = os.path.join(in_dir, "audio.wav")
        if os.path.exists(audio_path):
            audio = AudioFileClip(audio_path)
            clip = clip.with_audio(audio)

        clip = clip.with_duration(duration)

        clip.write_videofile(
            out_video,
            codec="libx264",
            audio_codec="pcm_s16le",
            fps=fps,
            ffmpeg_params=[
                "-crf", "0",
                "-preset", "veryslow",
                "-pix_fmt", "yuv444p"
            ]
        )

        clip.close()


if __name__ == "__main__":
    VideoFrameTool()
