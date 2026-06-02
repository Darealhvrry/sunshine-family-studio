import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import subprocess
import threading
import os
import json
import sys

# ── Color palette ──────────────────────────────────────────────
BG        = "#FFF9F0"
CARD      = "#FFFFFF"
SUN       = "#FFD23F"
SKY       = "#5BC8F5"
GRASS     = "#4CAF82"
PINK      = "#FF7EB3"
DARK      = "#2C2C3E"
MUTED     = "#8888A0"
SHADOW    = "#E8E0D0"

FFMPEG  = r"C:\Users\gizmo\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe"
FFPROBE = r"C:\Users\gizmo\AppData\Local\Microsoft\WinGet\Links\ffprobe.exe"

CHARACTERS = {
    "Narrator":   {"color": SUN,   "emoji": "⭐", "voice": "en_US/ljspeech_low"},
    "Mommy Mia":  {"color": PINK,  "emoji": "👩", "voice": "en_US/ljspeech_low"},
    "Daddy Ben":  {"color": SKY,   "emoji": "👨", "voice": "en_US/ljspeech_low"},
    "Tommy":      {"color": GRASS, "emoji": "👦", "voice": "en_US/ljspeech_low"},
    "Lilly":      {"color": "#FF9EBB", "emoji": "👧", "voice": "en_US/ljspeech_low"},
    "Sunny":      {"color": "#FFB347", "emoji": "🐶", "voice": "en_US/ljspeech_low"},
}

SAMPLE_SCRIPT = """Narrator: Welcome to The Sunshine Family! 🌟
Narrator: Today we're learning our ABCs with Tommy and Lilly!

Tommy: A is for APPLE, big and red!
Lilly: B is for BALL we bounce on our head!
Mommy Mia: C is for CAT that goes meow meow meow!
Daddy Ben: D is for DOG — and Sunny, take a bow!
Sunny: Woof woof woof!

All: E F G, H I J K!
Tommy: L M N O P!
Lilly: Q R S!
Mommy Mia: T U V!
Daddy Ben: W X Y and Z!

Narrator: Now we know our ABCs — sing along with the Sunshine Family! ⭐
"""

class SunshineLauncher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("☀️ Sunshine Family Studio")
        self.geometry("1000x750")
        self.configure(bg=BG)
        self.resizable(True, True)
        self._build_ui()

    # ── UI BUILDER ─────────────────────────────────────────────
    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg=SUN, height=80)
        hdr.pack(fill="x")
        tk.Label(hdr, text="☀️  Sunshine Family Studio", font=("Georgia", 22, "bold"),
                 bg=SUN, fg=DARK).pack(side="left", padx=24, pady=18)
        tk.Label(hdr, text="Educational Nursery Rhyme Generator",
                 font=("Georgia", 11), bg=SUN, fg="#665500").pack(side="left", pady=24)
        tk.Button(hdr, text="⬆ Update", font=("Helvetica", 9, "bold"),
                  bg="#FF9F1C", fg="white", bd=0, padx=12, pady=6,
                  cursor="hand2", command=self._check_update).pack(side="right", padx=16, pady=20)

        # Main columns
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        self._build_left(body)
        self._build_right(body)

        # Status bar
        self.status_var = tk.StringVar(value="Ready — write your script and hit Generate! 🎬")
        sb = tk.Label(self, textvariable=self.status_var, bg=SHADOW, fg=MUTED,
                      font=("Helvetica", 9), anchor="w", padx=12, pady=6)
        sb.pack(fill="x", side="bottom")

    def _build_left(self, parent):
        lf = tk.Frame(parent, bg=BG)
        lf.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        lf.rowconfigure(1, weight=1)

        # Script label + buttons
        top = tk.Frame(lf, bg=BG)
        top.pack(fill="x", pady=(0, 6))
        tk.Label(top, text="📝  Episode Script", font=("Georgia", 13, "bold"),
                 bg=BG, fg=DARK).pack(side="left")
        tk.Button(top, text="Load Sample", font=("Helvetica", 9),
                  bg=SKY, fg="white", bd=0, padx=10, pady=4,
                  cursor="hand2", command=self._load_sample).pack(side="right", padx=4)
        tk.Button(top, text="Open File", font=("Helvetica", 9),
                  bg=GRASS, fg="white", bd=0, padx=10, pady=4,
                  cursor="hand2", command=self._open_file).pack(side="right")

        # Script text area
        self.script_box = scrolledtext.ScrolledText(
            lf, font=("Courier", 11), bg=CARD, fg=DARK,
            insertbackground=DARK, relief="flat", bd=0,
            padx=12, pady=10, wrap="word",
            highlightthickness=2, highlightbackground=SHADOW,
            highlightcolor=SUN
        )
        self.script_box.pack(fill="both", expand=True)
        self.script_box.insert("1.0", SAMPLE_SCRIPT)

        # Format hint
        tk.Label(lf, text='Format each line as:  CharacterName: dialogue',
                 font=("Helvetica", 8), bg=BG, fg=MUTED).pack(anchor="w", pady=(4,0))

        # Log output
        tk.Label(lf, text="📋  Build Log", font=("Georgia", 11, "bold"),
                 bg=BG, fg=DARK).pack(anchor="w", pady=(12, 4))
        self.log_box = scrolledtext.ScrolledText(
            lf, font=("Courier", 9), bg="#1E1E2E", fg="#A8E6CF",
            height=8, relief="flat", bd=0, padx=10, pady=8,
            state="disabled", highlightthickness=0
        )
        self.log_box.pack(fill="x")

    def _build_right(self, parent):
        rf = tk.Frame(parent, bg=BG)
        rf.grid(row=0, column=1, sticky="nsew")

        # Cast card
        cast_frame = tk.LabelFrame(rf, text="  🎭  Your Cast  ", font=("Georgia", 11, "bold"),
                                   bg=BG, fg=DARK, bd=2, relief="groove",
                                   labelanchor="n", padx=10, pady=10)
        cast_frame.pack(fill="x", pady=(0, 12))
        for name, info in CHARACTERS.items():
            row = tk.Frame(cast_frame, bg=CARD, pady=6, padx=8)
            row.pack(fill="x", pady=3)
            dot = tk.Label(row, text=info["emoji"], bg=CARD, font=("Helvetica", 14))
            dot.pack(side="left")
            tk.Label(row, text=name, font=("Helvetica", 10, "bold"),
                     bg=CARD, fg=DARK).pack(side="left", padx=8)
            clr = tk.Label(row, text="●", bg=CARD, fg=info["color"],
                           font=("Helvetica", 14))
            clr.pack(side="right")

        # Settings card
        cfg_frame = tk.LabelFrame(rf, text="  ⚙️  Settings  ", font=("Georgia", 11, "bold"),
                                  bg=BG, fg=DARK, bd=2, relief="groove",
                                  labelanchor="n", padx=10, pady=10)
        cfg_frame.pack(fill="x", pady=(0, 12))

        self._setting_row(cfg_frame, "🎵 Background Music:", ["Upbeat Kids", "Soft Piano", "None"])
        self._setting_row(cfg_frame, "📺 Resolution:", ["1080p (YouTube)", "720p", "480p"])
        self._setting_row(cfg_frame, "🎤 Voice Speed:", ["Normal", "Slow", "Fast"])

        # Output folder
        out_row = tk.Frame(cfg_frame, bg=BG)
        out_row.pack(fill="x", pady=4)
        tk.Label(out_row, text="📁 Output Folder:", bg=BG, fg=DARK,
                 font=("Helvetica", 9, "bold"), width=18, anchor="w").pack(side="left")
        self.out_var = tk.StringVar(value=os.path.expanduser("~/Videos/SunshineFamily"))
        tk.Entry(out_row, textvariable=self.out_var, font=("Helvetica", 8),
                 bg=CARD, fg=DARK, relief="flat", bd=1).pack(side="left", fill="x", expand=True)
        tk.Button(out_row, text="📂", bg=SUN, bd=0, cursor="hand2",
                  command=self._pick_folder).pack(side="right")

        # BIG Generate button
        self.gen_btn = tk.Button(
            rf, text="🎬  GENERATE VIDEO",
            font=("Georgia", 15, "bold"),
            bg=SUN, fg=DARK, bd=0,
            activebackground="#FFC107",
            padx=20, pady=16,
            cursor="hand2",
            command=self._generate
        )
        self.gen_btn.pack(fill="x", pady=(8, 6))

        self.progress = ttk.Progressbar(rf, mode="indeterminate", length=300)
        self.progress.pack(fill="x")

        # Tips
        tips = tk.LabelFrame(rf, text="  💡  Tips  ", font=("Georgia", 10, "bold"),
                             bg=BG, fg=DARK, bd=1, relief="groove",
                             labelanchor="n", padx=8, pady=8)
        tips.pack(fill="x", pady=(12, 0))
        tip_lines = [
            "• Use 'All:' for everyone singing together",
            "• Keep rhymes 8–16 lines for 2-3 min videos",
            "• Start with 'Narrator:' to set the scene",
            "• Sunny's lines should be short (woof, bark!)",
        ]
        for t in tip_lines:
            tk.Label(tips, text=t, bg=BG, fg=MUTED,
                     font=("Helvetica", 8), anchor="w").pack(fill="x")

    def _setting_row(self, parent, label, options):
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", pady=4)
        tk.Label(row, text=label, bg=BG, fg=DARK,
                 font=("Helvetica", 9, "bold"), width=18, anchor="w").pack(side="left")
        cb = ttk.Combobox(row, values=options, state="readonly",
                          font=("Helvetica", 9), width=16)
        cb.current(0)
        cb.pack(side="left")

    # ── ACTIONS ────────────────────────────────────────────────
    def _check_update(self):
        """Download latest launcher.py from GitHub and apply it."""
        import urllib.request, shutil
        GITHUB_URL = "https://raw.githubusercontent.com/Darealhvrry/sunshine-family-studio/main/launcher.py"
        script_dir = os.path.dirname(os.path.abspath(__file__))
        launcher   = os.path.join(script_dir, "launcher.py")
        backup     = os.path.join(script_dir, "launcher_backup.py")
        tmp        = os.path.join(script_dir, "launcher_new.py")

        self.status_var.set("⬆ Checking for update...")
        self.update_idletasks()
        try:
            urllib.request.urlretrieve(GITHUB_URL, tmp)
            # Verify it downloaded something real
            if os.path.getsize(tmp) < 500:
                os.remove(tmp)
                messagebox.showerror("Update Failed", "Downloaded file seems invalid. Try again later.")
                self.status_var.set("Ready")
                return
            # Backup old, apply new
            shutil.copy2(launcher, backup)
            shutil.copy2(tmp, launcher)
            os.remove(tmp)
            self.status_var.set("✅ Updated! Please restart.")
            messagebox.showinfo("✅ Update Applied!",
                "Launcher updated from GitHub!\n\nOld version saved as launcher_backup.py\n\nClose and reopen the app to use the new version.")
        except Exception as e:
            self.status_var.set("❌ Update failed")
            messagebox.showerror("Update Failed", f"Could not reach GitHub:\n{e}\n\nMake sure you are connected to the internet.")
            try:
                os.remove(tmp)
            except:
                pass

    def _load_sample(self):
        self.script_box.delete("1.0", "end")
        self.script_box.insert("1.0", SAMPLE_SCRIPT)

    def _open_file(self):
        path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All", "*.*")])
        if path:
            with open(path, "r") as f:
                self.script_box.delete("1.0", "end")
                self.script_box.insert("1.0", f.read())

    def _pick_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.out_var.set(folder)

    def _log(self, msg):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _generate(self):
        script = self.script_box.get("1.0", "end").strip()
        if not script:
            messagebox.showwarning("Empty Script", "Please write a script first!")
            return
        self.gen_btn.configure(state="disabled", text="⏳  Generating...")
        self.progress.start(10)
        self.status_var.set("Generating your Sunshine Family episode... 🎬")
        threading.Thread(target=self._run_pipeline, args=(script,), daemon=True).start()

    def _run_pipeline(self, script):
        try:
            output_dir = self.out_var.get()
            os.makedirs(output_dir, exist_ok=True)
            self._log("📂 Output folder ready: " + output_dir)

            # Parse script
            lines = [l.strip() for l in script.split("\n") if ":" in l and l.strip()]
            self._log(f"📝 Parsed {len(lines)} dialogue lines")

            # Generate TTS for each line
            self._log("🎤 Generating voices with Piper TTS...")
            audio_files = []
            for i, line in enumerate(lines):
                char, dialogue = line.split(":", 1)
                char = char.strip()
                dialogue = dialogue.strip()
                if not dialogue:
                    continue
                wav_path = os.path.join(output_dir, f"line_{i:03d}.wav")
                success = self._generate_tts(dialogue, wav_path, char)
                if success:
                    audio_files.append((char, dialogue, wav_path))
                    self._log(f"  ✅ {char}: {dialogue[:40]}...")
                else:
                    self._log(f"  ⚠️ TTS failed for line {i}, skipping")

            # Concatenate audio
            self._log("🎵 Assembling audio track...")
            concat_path = os.path.join(output_dir, "full_audio.wav")
            self._concat_audio(audio_files, concat_path, output_dir)

            # Assemble video with character images
            self._log("🎬 Assembling video...")
            video_path = os.path.join(output_dir, "episode.mp4")
            self._assemble_video(audio_files, concat_path, video_path)

            self._log(f"\n🎉 DONE! Video saved to:\n   {video_path}")
            self.status_var.set(f"✅ Video ready! → {video_path}")
            self._show_done(video_path)

        except Exception as e:
            self._log(f"\n❌ Error: {str(e)}")
            self._log("See SETUP_GUIDE.txt for troubleshooting tips.")
            self.status_var.set("❌ Error — check the build log")
        finally:
            self.gen_btn.configure(state="normal", text="🎬  GENERATE VIDEO")
            self.progress.stop()

    def _generate_tts(self, text, wav_path, character):
        """Generate TTS using Windows SAPI via a temp VBScript file."""
        try:
            # Clean text — remove emoji and special chars that break SAPI
            import re
            clean = re.sub(r'[^\x00-\x7F]+', '', text).replace('"', '').replace("'", '').strip()
            if not clean:
                clean = "..."

            # Write a VBScript file — most reliable Windows TTS method
            vbs_path = wav_path.replace(".wav", "_tts.vbs")
            vbs = (
                f'Dim sapi\n'
                f'Set sapi = CreateObject("SAPI.SpVoice")\n'
                f'Dim stream\n'
                f'Set stream = CreateObject("SAPI.SpFileStream")\n'
                f'stream.Open "{wav_path}", 3, False\n'
                f'sapi.AudioOutputStream = stream\n'
                f'sapi.Rate = 1\n'
                f'sapi.Speak "{clean}"\n'
                f'stream.Close\n'
            )
            with open(vbs_path, "w") as f:
                f.write(vbs)

            result = subprocess.run(
                ["cscript", "//NoLogo", vbs_path],
                capture_output=True, timeout=30
            )
            # Clean up temp vbs
            try:
                os.remove(vbs_path)
            except:
                pass

            return os.path.exists(wav_path)
        except Exception as e:
            self._log(f"    TTS error: {e}")
            return False

    def _concat_audio(self, audio_files, output_path, work_dir):
        """Concatenate all WAV files using FFmpeg."""
        list_file = os.path.join(work_dir, "audio_list.txt")
        existing = [(c, d, p) for c, d, p in audio_files if os.path.exists(p)]
        if not existing:
            self._log("  ⚠️ No audio files to concatenate")
            return
        with open(list_file, "w") as f:
            for _, _, wav in existing:
                f.write(f"file '{wav}'\n")
        subprocess.run(
            [FFMPEG, "-y", "-f", "concat", "-safe", "0",
             "-i", list_file, "-c", "copy", output_path],
            capture_output=True
        )

    def _assemble_video(self, audio_files, audio_path, video_path):
        """Create video: character image + audio using FFmpeg."""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        chars_dir = os.path.join(script_dir, "Characters")
        if not os.path.exists(chars_dir):
            chars_dir = os.path.join(script_dir, "characters")
        self._log(f"  Characters folder: {chars_dir} (exists: {os.path.exists(chars_dir)})")

        work_dir = os.path.dirname(audio_path)
        img_list = os.path.join(work_dir, "img_list.txt")

        valid_entries = 0
        with open(img_list, "w", encoding="utf-8") as f:
            for char, dialogue, wav in audio_files:
                if not os.path.exists(wav):
                    continue
                dur = self._get_duration(wav)
                char_key = char.lower().replace(" ", "_")
                char_img = os.path.join(chars_dir, f"{char_key}.png")
                self._log(f"  {char} -> {char_key}.png (found: {os.path.exists(char_img)})")
                if os.path.exists(char_img):
                    f.write(f"file '{char_img}'\n")
                    f.write(f"duration {dur:.2f}\n")
                    valid_entries += 1

        if valid_entries == 0:
            self._log("  No images matched - check filenames in Characters folder")
            return

        if not os.path.exists(audio_path):
            self._log("  No audio track found - video skipped")
            return

        # Step 1: Build video-only from image slideshow
        video_only = video_path.replace(".mp4", "_videoonly.mp4")
        result1 = subprocess.run([
            FFMPEG, "-y",
            "-f", "concat", "-safe", "0",
            "-i", img_list,
            "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=#FFF9F0,format=yuv420p",
            "-c:v", "libx264", "-preset", "slow", "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "-r", "24",
            video_only
        ], capture_output=True, text=True)
        if result1.returncode != 0:
            self._log(f"  FFmpeg video error: {result1.stderr[-400:]}")
            return

        self._log(f"  Video track built OK")

        # Step 2: Mux video + audio together
        result2 = subprocess.run([
            FFMPEG, "-y",
            "-i", video_only,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            "-movflags", "+faststart",
            video_path
        ], capture_output=True, text=True)
        if result2.returncode != 0:
            self._log(f"  FFmpeg mux error: {result2.stderr[-400:]}")
        else:
            self._log(f"  Video + audio muxed OK!")
            try:
                os.remove(video_only)
            except:
                pass

    def _get_duration(self, wav_path):
        """Get WAV duration in seconds using FFprobe."""
        try:
            result = subprocess.run(
                [FFPROBE, "-v", "error", "-show_entries",
                 "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", wav_path],
                capture_output=True, text=True
            )
            return float(result.stdout.strip())
        except:
            return 3.0  # default 3 seconds

    def _show_done(self, path):
        if messagebox.askyesno("🎉 Episode Ready!",
                               f"Your video is ready!\n\n{path}\n\nOpen the output folder?"):
            subprocess.Popen(f'explorer "{os.path.dirname(path)}"')


if __name__ == "__main__":
    app = SunshineLauncher()
    app.mainloop()
