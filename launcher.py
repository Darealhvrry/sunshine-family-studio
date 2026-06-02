import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import subprocess
import threading
import os
import sys
import re
import json
import time
import hmac
import hashlib
import base64
import urllib.request
import urllib.parse

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
    "Narrator":   {"color": SUN,       "emoji": "⭐"},
    "Mommy Mia":  {"color": PINK,      "emoji": "👩"},
    "Daddy Ben":  {"color": SKY,       "emoji": "👨"},
    "Tommy":      {"color": GRASS,     "emoji": "👦"},
    "Lilly":      {"color": "#FF9EBB", "emoji": "👧"},
    "Sunny":      {"color": "#FFB347", "emoji": "🐶"},
    "All":        {"color": SUN,       "emoji": "🎵"},
}

# ElevenLabs Voice IDs
VOICE_IDS = {
    "Mommy Mia":  "052jzHJceQiZr7ltnY0C",  # Mia
    "Daddy Ben":  "wSqOdjeNqDrHcoK0zorF",  # Lukas
    "Tommy":      "s3TPKV1kjDlVtZbl4Ksh",  # Adam
    "Lilly":      "vGQNBgLaiM3EdZtxIiuY",  # Aerisita
    "Sunny":      "eppqEXVumQ3CfdndcIBd",  # Minnie
    "All":        "052jzHJceQiZr7ltnY0C",  # Mia
}

# Narrator rotates through all character voices
NARRATOR_VOICES = [
    "052jzHJceQiZr7ltnY0C",  # Mia
    "wSqOdjeNqDrHcoK0zorF",  # Lukas
    "s3TPKV1kjDlVtZbl4Ksh",  # Adam
    "vGQNBgLaiM3EdZtxIiuY",  # Aerisita
    "eppqEXVumQ3CfdndcIBd",  # Minnie
]
_narrator_index = [0]  # mutable counter

SAMPLE_SCRIPT = """Narrator: Good morning! Time to wake up with the Sunshine Family!
Daddy Ben: opens the bedroom door and peeks inside smiling
Tommy: jumps out of bed excited pointing at the sunny window
Lilly: stretches arms wide and yawns sleepily in bed
Mommy Mia: stands in kitchen smiling making breakfast
Sunny: runs into the kitchen wagging tail happily
All: Good morning, good morning, what a beautiful day!
Narrator: Come along and sing with the Sunshine Family every day!
"""

class SunshineLauncher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("☀️ Sunshine Family Studio")
        self.geometry("1100x800")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.elements = {}  # character name -> element_id
        self._build_ui()
        self.after(500, self._load_keys_and_elements)

    def _load_keys_and_elements(self):
        """Load API keys and fetch element IDs from Kling."""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        keys_file = os.path.join(script_dir, "kling_keys.txt")
        if not os.path.exists(keys_file):
            self._log("⚠️ kling_keys.txt not found — create it in your sunshine_family folder")
            self._log("   Format:\n   ACCESS_KEY=your_key\n   SECRET_KEY=your_secret")
            return
        self.access_key = ""
        self.secret_key = ""
        self.elevenlabs_key = ""
        with open(keys_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("ACCESS_KEY="):
                    self.access_key = line.split("=", 1)[1].strip()
                elif line.startswith("SECRET_KEY="):
                    self.secret_key = line.split("=", 1)[1].strip()
                elif line.startswith("ELEVENLABS_KEY="):
                    self.elevenlabs_key = line.split("=", 1)[1].strip()

        if self.access_key and self.secret_key:
            self._log("✅ Kling API keys loaded!")
            if self.elevenlabs_key:
                self._log("✅ ElevenLabs key loaded!")
            else:
                self._log("⚠️ No ElevenLabs key — using Windows TTS fallback")
            threading.Thread(target=self._fetch_elements, daemon=True).start()
        else:
            self._log("❌ Could not read API keys from kling_keys.txt")

    def _make_jwt(self):
        """Generate Kling JWT token."""
        import struct
        header = base64.urlsafe_b64encode(
            json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
        ).rstrip(b"=").decode()
        now = int(time.time())
        payload = base64.urlsafe_b64encode(
            json.dumps({
                "iss": self.access_key,
                "exp": now + 1800,
                "nbf": now - 5
            }).encode()
        ).rstrip(b"=").decode()
        sig_input = f"{header}.{payload}".encode()
        sig = base64.urlsafe_b64encode(
            hmac.new(self.secret_key.encode(), sig_input, hashlib.sha256).digest()
        ).rstrip(b"=").decode()
        return f"{header}.{payload}.{sig}"

    def _kling_get(self, path):
        """Make a GET request to Kling API."""
        token = self._make_jwt()
        url = f"https://api.klingai.com{path}"
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())

    def _kling_post(self, path, data):
        """Make a POST request to Kling API."""
        token = self._make_jwt()
        url = f"https://api.klingai.com{path}"
        body = json.dumps(data).encode()
        req = urllib.request.Request(url, data=body, headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        })
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())

    def _fetch_elements(self):
        """Verify API keys work and set up character image mapping."""
        try:
            self._log("🔍 Verifying Kling API connection...")
            # Test connection with account endpoint
            resp = self._kling_get("/v1/account/costs")
            self._log("✅ Kling API connected successfully!")
        except Exception as e:
            # Try alternative verification
            try:
                resp = self._kling_get("/v1/videos/text2video?pageSize=1")
                self._log("✅ Kling API connected successfully!")
            except Exception as e2:
                self._log(f"⚠️ API connection issue: {e2}")
                self._log("   Will attempt generation anyway...")

        # Map characters to their image files
        script_dir = os.path.dirname(os.path.abspath(__file__))
        chars_dir = os.path.join(script_dir, "Characters")
        if not os.path.exists(chars_dir):
            chars_dir = os.path.join(script_dir, "characters")

        char_map = {
            "Mommy Mia": "mommy_mia.png",
            "Daddy Ben": "daddy_ben.png",
            "Tommy":     "tommy.png",
            "Lilly":     "lilly.png",
            "Sunny":     "sunny.png",
        }
        self.elements = {}
        for char, filename in char_map.items():
            img_path = os.path.join(chars_dir, filename)
            if os.path.exists(img_path):
                self.elements[char] = img_path
                self._log(f"  ✅ {char} → {filename}")
            else:
                self._log(f"  ⚠️ {char} image not found: {filename}")

        # Map visuals folder
        self.visuals_dir = os.path.join(script_dir, "Visuals")
        if not os.path.exists(self.visuals_dir):
            self.visuals_dir = os.path.join(script_dir, "visuals")
        if os.path.exists(self.visuals_dir):
            visual_count = len([f for f in os.listdir(self.visuals_dir)
                               if f.lower().endswith(('.png','.jpg','.jpeg','.webp'))])
            self._log(f"  ✅ Visuals folder found: {visual_count} scene images")
        else:
            self._log(f"  ⚠️ No Visuals folder found")
            self.visuals_dir = None

        # Map clips folder (manually downloaded from Kling website)
        self.clips_dir = os.path.join(script_dir, "Clips")
        if not os.path.exists(self.clips_dir):
            os.makedirs(self.clips_dir)
        clip_count = len([f for f in os.listdir(self.clips_dir)
                         if f.lower().endswith('.mp4')])
        self._log(f"  ✅ Clips folder ready: {clip_count} clips found")
        self._log(f"     → Add clips as clip_2.mp4, clip_3.mp4 etc.")

        self._log(f"\n🎭 {len(self.elements)} characters ready!")
        self._update_cast_display()

    def _find_element_id(self, character):
        """Find character image path by name matching."""
        char_lower = character.lower()
        for name, path in self.elements.items():
            if char_lower in name.lower() or name.lower() in char_lower:
                return path
        return None

    def _find_clip(self, line_number):
        """Find a manually downloaded Kling clip for a line number."""
        if not hasattr(self, 'clips_dir') or not self.clips_dir:
            return None
        for ext in ['.mp4', '.MP4', '.mov', '.MOV']:
            for name in [f"clip_{line_number}", f"clip_{line_number:03d}",
                         str(line_number)]:
                path = os.path.join(self.clips_dir, f"{name}{ext}")
                if os.path.exists(path):
                    return path
        return None

    def _find_visual(self, line_number, character=None):
        """Find scene visual for a line number.
        Falls back to: nearest visual → character image → None.
        """
        # 1. Try exact match for this line number
        if hasattr(self, 'visuals_dir') and self.visuals_dir:
            for ext in ['.png', '.jpg', '.jpeg', '.webp',
                        '.PNG', '.JPG', '.JPEG', '.avif', '.AVIF']:
                path = os.path.join(self.visuals_dir, f"{line_number}{ext}")
                if os.path.exists(path):
                    return path

            # 2. Try nearest lower line number (e.g. line 7 missing → try 6, 5, 4...)
            for fallback in range(line_number - 1, 0, -1):
                for ext in ['.png', '.jpg', '.jpeg', '.webp',
                            '.PNG', '.JPG', '.JPEG', '.avif', '.AVIF']:
                    path = os.path.join(self.visuals_dir, f"{fallback}{ext}")
                    if os.path.exists(path):
                        return path

        # 3. Fall back to character image
        if character and hasattr(self, 'elements') and character in self.elements:
            return self.elements[character]

        return None

    # ── UI BUILDER ─────────────────────────────────────────────
    def _build_ui(self):
        hdr = tk.Frame(self, bg=SUN, height=80)
        hdr.pack(fill="x")
        tk.Label(hdr, text="☀️  Sunshine Family Studio",
                 font=("Georgia", 22, "bold"), bg=SUN, fg=DARK).pack(side="left", padx=24, pady=18)
        tk.Label(hdr, text="AI-Powered Nursery Rhyme Generator",
                 font=("Georgia", 11), bg=SUN, fg="#665500").pack(side="left", pady=24)
        tk.Button(hdr, text="⬆ Update", font=("Helvetica", 9, "bold"),
                  bg="#FF9F1C", fg="white", bd=0, padx=12, pady=6,
                  cursor="hand2", command=self._check_update).pack(side="right", padx=16, pady=20)

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        self._build_left(body)
        self._build_right(body)

        self.status_var = tk.StringVar(value="Ready — write your script and hit Generate! 🎬")
        tk.Label(self, textvariable=self.status_var, bg=SHADOW, fg=MUTED,
                 font=("Helvetica", 9), anchor="w", padx=12, pady=6).pack(fill="x", side="bottom")

    def _build_left(self, parent):
        lf = tk.Frame(parent, bg=BG)
        lf.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        lf.rowconfigure(1, weight=1)

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

        self.script_box = scrolledtext.ScrolledText(
            lf, font=("Courier", 11), bg=CARD, fg=DARK,
            insertbackground=DARK, relief="flat", bd=0,
            padx=12, pady=10, wrap="word",
            highlightthickness=2, highlightbackground=SHADOW,
            highlightcolor=SUN
        )
        self.script_box.pack(fill="both", expand=True)
        self.script_box.insert("1.0", SAMPLE_SCRIPT)

        tk.Label(lf,
                 text='Narrator lines = voiceover only  |  Character lines = AI video + voice',
                 font=("Helvetica", 8), bg=BG, fg=MUTED).pack(anchor="w", pady=(4, 0))

        tk.Label(lf, text="📋  Build Log", font=("Georgia", 11, "bold"),
                 bg=BG, fg=DARK).pack(anchor="w", pady=(12, 4))
        self.log_box = scrolledtext.ScrolledText(
            lf, font=("Courier", 9), bg="#1E1E2E", fg="#A8E6CF",
            height=10, relief="flat", bd=0, padx=10, pady=8,
            state="disabled", highlightthickness=0
        )
        self.log_box.pack(fill="x")

    def _build_right(self, parent):
        rf = tk.Frame(parent, bg=BG)
        rf.grid(row=0, column=1, sticky="nsew")

        cast_frame = tk.LabelFrame(rf, text="  🎭  Your Cast  ",
                                   font=("Georgia", 11, "bold"),
                                   bg=BG, fg=DARK, bd=2, relief="groove",
                                   labelanchor="n", padx=10, pady=10)
        cast_frame.pack(fill="x", pady=(0, 12))
        self.cast_labels = {}
        for name, info in CHARACTERS.items():
            row = tk.Frame(cast_frame, bg=CARD, pady=6, padx=8)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=info["emoji"], bg=CARD,
                     font=("Helvetica", 14)).pack(side="left")
            tk.Label(row, text=name, font=("Helvetica", 10, "bold"),
                     bg=CARD, fg=DARK).pack(side="left", padx=8)
            status = tk.Label(row, text="○ no element", bg=CARD,
                              fg=MUTED, font=("Helvetica", 8))
            status.pack(side="right")
            self.cast_labels[name] = status

        cfg_frame = tk.LabelFrame(rf, text="  ⚙️  Settings  ",
                                  font=("Georgia", 11, "bold"),
                                  bg=BG, fg=DARK, bd=2, relief="groove",
                                  labelanchor="n", padx=10, pady=10)
        cfg_frame.pack(fill="x", pady=(0, 12))

        self._setting_row(cfg_frame, "📺 Resolution:", ["1080p", "720p"])
        self._setting_row(cfg_frame, "⏱ Clip Length:", ["5s", "8s", "10s"])
        self._setting_row(cfg_frame, "🎤 Voice Speed:", ["Normal", "Slow", "Fast"])

        out_row = tk.Frame(cfg_frame, bg=BG)
        out_row.pack(fill="x", pady=4)
        tk.Label(out_row, text="📁 Output Folder:", bg=BG, fg=DARK,
                 font=("Helvetica", 9, "bold"), width=18, anchor="w").pack(side="left")
        self.out_var = tk.StringVar(value=os.path.expanduser("~/Videos/SunshineFamily"))
        tk.Entry(out_row, textvariable=self.out_var, font=("Helvetica", 8),
                 bg=CARD, fg=DARK, relief="flat", bd=1).pack(side="left", fill="x", expand=True)
        tk.Button(out_row, text="📂", bg=SUN, bd=0, cursor="hand2",
                  command=self._pick_folder).pack(side="right")

        self.gen_btn = tk.Button(
            rf, text="🎬  GENERATE EPISODE",
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

        tips = tk.LabelFrame(rf, text="  💡  Script Tips  ",
                             font=("Georgia", 10, "bold"),
                             bg=BG, fg=DARK, bd=1, relief="groove",
                             labelanchor="n", padx=8, pady=8)
        tips.pack(fill="x", pady=(12, 0))
        for t in [
            "• Narrator lines = voice only, no video",
            "• Generate clips on Kling website",
            "• Save as clip_2.mp4, clip_3.mp4 etc.",
            "• Drop clips into sunshine_family/Clips/",
            "• App adds voices & assembles episode",
        ]:
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

    def _update_cast_display(self):
        """Update cast status labels with element connection status."""
        name_map = {
            "Narrator":  None,
            "Mommy Mia": "Mommy Mia",
            "Daddy Ben": "Daddy Ben",
            "Tommy":     "Tommy",
            "Lilly":     "Lilly",
            "Sunny":     "Sunny",
            "All":       None,
        }
        for char, kling_name in name_map.items():
            if char not in self.cast_labels:
                continue
            if kling_name is None:
                self.cast_labels[char].config(text="○ narrator", fg=MUTED)
                continue
            eid = self._find_element_id(kling_name)
            if eid:
                self.cast_labels[char].config(text="✅ connected", fg=GRASS)
            else:
                self.cast_labels[char].config(text="⚠️ no element", fg="#FF6B6B")

    # ── ACTIONS ─────────────────────────────────────────────────
    def _check_update(self):
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
            if os.path.getsize(tmp) < 500:
                os.remove(tmp)
                messagebox.showerror("Update Failed", "Downloaded file seems invalid.")
                self.status_var.set("Ready")
                return
            shutil.copy2(launcher, backup)
            shutil.copy2(tmp, launcher)
            os.remove(tmp)
            self.status_var.set("✅ Updated! Please restart.")
            messagebox.showinfo("✅ Update Applied!",
                "Launcher updated!\n\nClose and reopen the app.")
        except Exception as e:
            self.status_var.set("❌ Update failed")
            messagebox.showerror("Update Failed", f"Could not reach GitHub:\n{e}")
            try:
                os.remove(tmp)
            except:
                pass

    def _load_sample(self):
        self.script_box.delete("1.0", "end")
        self.script_box.insert("1.0", SAMPLE_SCRIPT)

    def _open_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("All", "*.*")])
        if path:
            with open(path) as f:
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
        if not hasattr(self, 'access_key') or not self.access_key:
            messagebox.showerror("No API Keys",
                "Please create kling_keys.txt in your sunshine_family folder!\n\n"
                "ACCESS_KEY=your_key\nSECRET_KEY=your_secret")
            return
        self.gen_btn.configure(state="disabled", text="⏳  Generating...")
        self.progress.start(10)
        self.status_var.set("Generating your Sunshine Family episode... 🎬")
        threading.Thread(target=self._run_pipeline,
                         args=(script,), daemon=True).start()

    def _run_pipeline(self, script):
        try:
            output_dir = self.out_var.get()
            os.makedirs(output_dir, exist_ok=True)
            self._log(f"📂 Output folder: {output_dir}")

            lines = [l.strip() for l in script.split("\n")
                     if ":" in l and l.strip() and not l.strip().startswith("#")]
            self._log(f"📝 Parsed {len(lines)} script lines")

            video_clips = []
            audio_files = []

            for i, line in enumerate(lines):
                char, action = line.split(":", 1)
                char   = char.strip()
                action = action.strip()
                if not action:
                    continue

                self._log(f"\n── Line {i+1}: {char} ──")

                # Generate voice for every line
                wav_path = os.path.join(output_dir, f"line_{i:03d}.wav")
                self._log(f"  🎤 Generating voice...")
                tts_ok = self._generate_tts(action, wav_path, char)
                if tts_ok:
                    self._log(f"  ✅ Voice ready")
                    audio_files.append((char, action, wav_path))
                else:
                    self._log(f"  ⚠️ Voice failed")

                # Generate video for non-narrator lines
                if char.lower() not in ("narrator",):
                    # Check for manually downloaded Kling clip first
                    manual_clip = self._find_clip(i + 1)
                    if manual_clip:
                        self._log(f"  🎬 Using manual clip: {os.path.basename(manual_clip)}")
                        video_clips.append((char, action, manual_clip, wav_path))
                    else:
                        self._log(f"  🖼 No clip found for line {i+1} — using image fallback")
                        self._log(f"     → Generate in Kling and save as clip_{i+1}.mp4 in Clips folder")
                        video_clips.append((char, action, None, wav_path))
                else:
                    video_clips.append((char, action, None, wav_path))

            # Assemble final episode
            self._log(f"\n🎬 Assembling final episode...")
            episode_path = os.path.join(output_dir, "episode.mp4")
            self._assemble_episode(video_clips, episode_path, output_dir)

            self._log(f"\n🎉 DONE! Episode saved to:\n   {episode_path}")
            self.status_var.set(f"✅ Episode ready!")
            self._show_done(episode_path)

        except Exception as e:
            import traceback
            self._log(f"\n❌ Error: {str(e)}")
            self._log(traceback.format_exc())
            self.status_var.set("❌ Error — check the build log")
        finally:
            self.gen_btn.configure(state="normal", text="🎬  GENERATE EPISODE")
            self.progress.stop()

    def _generate_kling_clip(self, action, img_path, output_path, character, scene_img=None):
        """Generate a video clip using Kling image-to-video API."""
        try:
            style = "3D Pixar animated style, cinematic lighting, smooth animation, family friendly, Disney Pixar quality"
            prompt = f"{action}, {style}"

            # Use scene image if available, otherwise use character image
            source_img = scene_img if scene_img and os.path.exists(scene_img) else img_path
            if scene_img and os.path.exists(scene_img):
                self._log(f"    Using scene visual: {os.path.basename(scene_img)}")
            else:
                self._log(f"    Using character image: {os.path.basename(img_path)}")

            # Encode image as base64
            with open(source_img, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()

            payload = {
                "model_name": "kling-v1-6",
                "image": img_b64,
                "prompt": prompt,
                "duration": "5",
                "mode": "std",
                "aspect_ratio": "16:9",
            }

            self._log(f"    Sending to Kling image-to-video API...")
            # Retry up to 3 times on rate limit
            resp = None
            for attempt in range(3):
                try:
                    resp = self._kling_post("/v1/videos/image2video", payload)
                    break
                except Exception as e:
                    if "429" in str(e) and attempt < 2:
                        wait = 30 * (attempt + 1)
                        self._log(f"    Rate limited — waiting {wait}s before retry {attempt+2}/3...")
                        time.sleep(wait)
                    else:
                        raise
            if not resp:
                return False
            task_id = resp.get("data", {}).get("taskId", "")
            if not task_id:
                self._log(f"    No task ID: {resp}")
                return False

            self._log(f"    Task {task_id} submitted — waiting...")

            for attempt in range(60):
                time.sleep(10)
                status_resp = self._kling_get(f"/v1/videos/image2video/{task_id}")
                status = status_resp.get("data", {}).get("taskStatus", "")
                self._log(f"    Status: {status} ({attempt+1}/60)")

                if status == "succeed":
                    videos = status_resp.get("data", {}).get("taskResult", {}).get("videos", [])
                    if videos:
                        video_url = videos[0].get("url", "")
                        if video_url:
                            self._log(f"    Downloading clip...")
                            urllib.request.urlretrieve(video_url, output_path)
                            return os.path.exists(output_path)
                    return False
                elif status in ("failed", "error"):
                    self._log(f"    Kling generation failed: {status_resp}")
                    return False

            self._log("    Timed out")
            return False

        except Exception as e:
            self._log(f"    Kling error: {e}")
            return False

    def _generate_tts(self, text, wav_path, character):
        """Generate TTS using ElevenLabs API."""
        try:
            clean = re.sub(r'[^\x00-\x7F]+', '', text).strip()
            if not clean:
                clean = "la la la"

            # Get voice ID for this character
            if character == "Narrator":
                voice_id = NARRATOR_VOICES[_narrator_index[0] % len(NARRATOR_VOICES)]
                _narrator_index[0] += 1
            else:
                voice_id = VOICE_IDS.get(character, VOICE_IDS.get("Mommy Mia"))

            # Check if ElevenLabs key exists
            if not hasattr(self, 'elevenlabs_key') or not self.elevenlabs_key:
                return self._generate_tts_fallback(text, wav_path)

            # Call ElevenLabs API
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            payload = json.dumps({
                "text": clean,
                "model_id": "eleven_turbo_v2",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                    "style": 0.3,
                    "use_speaker_boost": True
                }
            }).encode()

            req = urllib.request.Request(url, data=payload, headers={
                "xi-api-key": self.elevenlabs_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg"
            })

            with urllib.request.urlopen(req, timeout=30) as resp:
                mp3_data = resp.read()

            # Save as mp3 first then convert to wav
            mp3_path = wav_path.replace(".wav", ".mp3")
            with open(mp3_path, "wb") as f:
                f.write(mp3_data)

            # Convert mp3 to wav using FFmpeg
            subprocess.run([
                FFMPEG, "-y", "-i", mp3_path,
                "-ar", "44100", "-ac", "1",
                wav_path
            ], capture_output=True, timeout=30)

            try:
                os.remove(mp3_path)
            except:
                pass

            return os.path.exists(wav_path) and os.path.getsize(wav_path) > 1000

        except Exception as e:
            self._log(f"    ElevenLabs error: {e} — trying fallback")
            return self._generate_tts_fallback(text, wav_path)

    def _generate_tts_fallback(self, text, wav_path):
        """Fallback TTS using Windows SAPI via PowerShell."""
        try:
            clean = re.sub(r'[^\x00-\x7F]+', '', text).replace("'", "").replace('"', '').strip()
            if not clean:
                clean = "la la la"
            ps_path = wav_path.replace(".wav", "_tts.ps1")
            ps = (
                f"Add-Type -AssemblyName System.Speech\n"
                f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer\n"
                f"$s.Rate = 2\n"
                f"$s.SetOutputToWaveFile('{wav_path}')\n"
                f"$s.Speak('{clean}')\n"
                f"$s.Dispose()\n"
            )
            with open(ps_path, "w") as f:
                f.write(ps)
            subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-File", ps_path],
                capture_output=True, timeout=30
            )
            try:
                os.remove(ps_path)
            except:
                pass
            return os.path.exists(wav_path) and os.path.getsize(wav_path) > 1000
        except Exception as e:
            self._log(f"    Fallback TTS error: {e}")
            return False

    def _assemble_episode(self, video_clips, episode_path, work_dir):
        """Assemble all clips and audio into final episode."""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        chars_dir  = os.path.join(script_dir, "Characters")
        if not os.path.exists(chars_dir):
            chars_dir = os.path.join(script_dir, "characters")

        clip_list_file = os.path.join(work_dir, "clip_list.txt")
        temp_clips = []

        for i, (char, action, clip_path, wav_path) in enumerate(video_clips):
            combined = os.path.join(work_dir, f"combined_{i:03d}.mp4")

            if clip_path and os.path.exists(clip_path):
                # Mux Kling video with TTS audio
                if wav_path and os.path.exists(wav_path) and os.path.getsize(wav_path) > 1000:
                    result = subprocess.run([
                        FFMPEG, "-y",
                        "-i", clip_path,
                        "-i", wav_path,
                        "-c:v", "copy",
                        "-c:a", "aac", "-b:a", "192k",
                        "-shortest", "-movflags", "+faststart",
                        combined
                    ], capture_output=True, text=True)
                else:
                    result = subprocess.run([
                        FFMPEG, "-y", "-i", clip_path,
                        "-c:v", "copy", combined
                    ], capture_output=True, text=True)
            else:
                # Fallback: static character image + audio
                dur = self._get_duration(wav_path) if wav_path and os.path.exists(wav_path) else 3.0
                char_key = char.lower().replace(" ", "_")
                char_img = os.path.join(chars_dir, f"{char_key}.png")
                if not os.path.exists(char_img):
                    # Use first available image
                    imgs = [f for f in os.listdir(chars_dir) if f.endswith(".png")] if os.path.exists(chars_dir) else []
                    char_img = os.path.join(chars_dir, imgs[0]) if imgs else None

                if char_img and os.path.exists(char_img):
                    if wav_path and os.path.exists(wav_path) and os.path.getsize(wav_path) > 1000:
                        subprocess.run([
                            FFMPEG, "-y",
                            "-loop", "1", "-i", char_img,
                            "-i", wav_path,
                            "-vf", "format=rgba,colorchannelmixer=aa=1,format=yuv420p,scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=#FFF9F0",
                            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
                            "-pix_fmt", "yuv420p", "-r", "24",
                            "-c:a", "aac", "-b:a", "192k",
                            "-shortest", "-movflags", "+faststart",
                            combined
                        ], capture_output=True)
                    else:
                        subprocess.run([
                            FFMPEG, "-y",
                            "-loop", "1", "-i", char_img,
                            "-t", str(dur),
                            "-vf", "format=rgba,colorchannelmixer=aa=1,format=yuv420p,scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=#FFF9F0",
                            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
                            "-pix_fmt", "yuv420p", "-r", "24",
                            "-movflags", "+faststart",
                            combined
                        ], capture_output=True)
                else:
                    continue

            if os.path.exists(combined) and os.path.getsize(combined) > 1000:
                temp_clips.append(combined)
                self._log(f"  ✅ Clip {i+1} assembled")
            else:
                self._log(f"  ⚠️ Clip {i+1} failed to assemble")

        if not temp_clips:
            self._log("❌ No clips to assemble!")
            return

        # Concatenate all clips
        with open(clip_list_file, "w") as f:
            for clip in temp_clips:
                f.write(f"file '{clip}'\n")

        result = subprocess.run([
            FFMPEG, "-y",
            "-f", "concat", "-safe", "0",
            "-i", clip_list_file,
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            episode_path
        ], capture_output=True, text=True)

        if os.path.exists(episode_path) and os.path.getsize(episode_path) > 10000:
            self._log(f"  ✅ Episode assembled! Size: {os.path.getsize(episode_path):,} bytes")
        else:
            self._log(f"  ❌ Assembly failed: {result.stderr[-300:]}")

    def _get_duration(self, wav_path):
        try:
            result = subprocess.run(
                [FFPROBE, "-v", "error", "-show_entries",
                 "format=duration", "-of",
                 "default=noprint_wrappers=1:nokey=1", wav_path],
                capture_output=True, text=True
            )
            return float(result.stdout.strip())
        except:
            return 3.0

    def _show_done(self, path):
        if messagebox.askyesno("🎉 Episode Ready!",
                               f"Your episode is ready!\n\n{path}\n\nOpen the output folder?"):
            subprocess.Popen(f'explorer "{os.path.dirname(path)}"')


if __name__ == "__main__":
    app = SunshineLauncher()
    app.mainloop()
