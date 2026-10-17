import os
import sys
import time
import math
import threading
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageTk
from rk_core import RKCore
from jarvis_core import JarvisCore

# Set CustomTkinter theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# =====================================================================
# 1. ADVANCED INTERACTIVE AVATAR HUD CANVAS
# =====================================================================
class AvatarHUD(ctk.CTkCanvas):
    """
    Futuristic Circular Holographic Avatar with Real-Time Movement:
    - IDLE: Gentle breathing float & slow orbit rings
    - LISTENING: Sonar ping rings & amber acoustic radar sweep
    - THINKING: Rapid hyper-speed encryption arcs & cyber crosshair
    - SPEAKING: Dynamic bobbing movement, scale pulse, sonic shockwaves,
      hologram vertical scanlines, and reactive audio equalizer waveform.
    """
    def __init__(self, master, avatar_path="avatar.jpg", size=240, **kwargs):
        super().__init__(master, width=size, height=size, bg="#050a18", highlightthickness=0, **kwargs)
        self.size = size
        self.center = size / 2
        self.avatar_size = 150
        self.state = "IDLE"  # "IDLE", "LISTENING", "THINKING", "SPEAKING"
        self.angle = 0
        self.tick = 0
        
        # Pre-generate circular avatar frames for smooth zero-lag scaling
        self.avatar_frames = []
        try:
            if os.path.exists(avatar_path):
                raw_img = Image.open(avatar_path).convert("RGBA")
            else:
                # Fallback blank tech avatar
                raw_img = Image.new("RGBA", (512, 512), (5, 20, 45, 255))
                d = ImageDraw.Draw(raw_img)
                d.ellipse((100, 100, 412, 412), outline=(0, 245, 255, 255), width=8)

            # Generate 3 subtle scale levels for speaking vocal modulation
            for sz in [self.avatar_size - 4, self.avatar_size, self.avatar_size + 6]:
                mask = Image.new("L", (sz, sz), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.ellipse((0, 0, sz, sz), fill=255)
                
                cropped = raw_img.copy()
                cropped = cropped.resize((sz, sz), Image.Resampling.LANCZOS)
                cropped.putalpha(mask)
                self.avatar_frames.append(ImageTk.PhotoImage(cropped))
        except Exception as e:
            print("AvatarHUD Initialization Error:", e)
            self.avatar_frames = []

        self.animate()

    def set_state(self, new_state):
        self.state = new_state

    def animate(self):
        self.delete("all")
        self.tick += 1
        cx, cy = self.center, self.center

        # Configure motion parameters based on active state
        if self.state == "SPEAKING":
            self.angle += 3.5
            bob_y = math.sin(self.tick * 0.22) * 5.0
            scale_idx = int((math.sin(self.tick * 0.35) + 1.0) * 1.49) % max(1, len(self.avatar_frames))
            primary_color = "#00f5ff"   # Neon Cyan
            accent_color = "#38bdf8"    # Sky Blue
            speed_mult = 1.6
        elif self.state == "LISTENING":
            self.angle += 2.0
            bob_y = math.sin(self.tick * 0.12) * 2.5
            scale_idx = 1
            primary_color = "#f59e0b"   # Acoustic Amber
            accent_color = "#fbbf24"
            speed_mult = 1.0
        elif self.state == "THINKING":
            self.angle += 7.0
            bob_y = math.sin(self.tick * 0.25) * 1.5
            scale_idx = 1
            primary_color = "#a855f7"   # Quantum Violet
            accent_color = "#c084fc"
            speed_mult = 2.0
        else: # IDLE
            self.angle += 1.2
            bob_y = math.sin(self.tick * 0.06) * 3.0
            scale_idx = 1
            primary_color = "#0ea5e9"   # Cyber Deep Cyan
            accent_color = "#0369a1"
            speed_mult = 0.8

        # --- 1. Outer Concentric Tech Rings ---
        # Clockwise segmented arc
        self.create_arc(8, 8, self.size - 8, self.size - 8,
                        start=self.angle, extent=80, style="arc", outline=primary_color, width=2)
        self.create_arc(8, 8, self.size - 8, self.size - 8,
                        start=self.angle + 180, extent=80, style="arc", outline=primary_color, width=2)

        # Counter-clockwise dashed tech arc
        self.create_arc(18, 18, self.size - 18, self.size - 18,
                        start=-self.angle * speed_mult, extent=60, style="arc", outline=accent_color, width=3, dash=(8, 5))
        self.create_arc(18, 18, self.size - 18, self.size - 18,
                        start=-self.angle * speed_mult + 180, extent=60, style="arc", outline=accent_color, width=3, dash=(8, 5))

        # --- 2. Dynamic Expanding Sonic Wave Rings (Active when SPEAKING or LISTENING) ---
        if self.state in ["SPEAKING", "LISTENING"]:
            ripple_radius = 85 + (self.tick * 2.5 % 30)
            self.create_oval(cx - ripple_radius, cy - ripple_radius,
                             cx + ripple_radius, cy + ripple_radius,
                             outline=primary_color, width=1)
            ripple2 = 85 + ((self.tick * 2.5 + 15) % 30)
            self.create_oval(cx - ripple2, cy - ripple2,
                             cx + ripple2, cy + ripple2,
                             outline=accent_color, width=1)

        # --- 3. Draw Avatar Image with Bobbing & Scale Pulse ---
        img_y = cy + bob_y
        if self.avatar_frames:
            img = self.avatar_frames[scale_idx]
            self.create_image(cx, img_y, image=img)
        else:
            self.create_oval(cx - 65, img_y - 65, cx + 65, img_y + 65, fill="#0c1b33", outline=primary_color, width=2)
            self.create_text(cx, img_y, text="RK", fill=primary_color, font=("Consolas", 14, "bold"))

        # --- 4. Glowing Circular Cyber Aperture Around Avatar ---
        radius = 78
        self.create_oval(cx - radius, img_y - radius, cx + radius, img_y + radius,
                         outline=primary_color, width=2)
        self.create_oval(cx - radius - 3, img_y - radius - 3, cx + radius + 3, img_y + radius + 3,
                         outline=accent_color, width=1, dash=(4, 6))

        # --- 5. Holographic Scanline Beam (Active when SPEAKING) ---
        if self.state == "SPEAKING":
            scan_y = (img_y - 65) + ((self.tick * 3.5) % 130)
            self.create_line(cx - 55, scan_y, cx + 55, scan_y, fill="#ffffff", width=1)
            self.create_line(cx - 45, scan_y + 1, cx + 45, scan_y + 1, fill="#00f5ff", width=2)

        # --- 6. Dynamic Audio Equalizer Bars at Bottom of Avatar ---
        eq_y = self.size - 10
        bar_count = 14
        bar_w = 4
        gap = 4
        total_w = bar_count * (bar_w + gap) - gap
        start_x = cx - (total_w / 2)

        for i in range(bar_count):
            if self.state == "SPEAKING":
                # Dynamic audio frequency oscillation
                h = 3.0 + abs(math.sin(self.tick * 0.35 + i * 0.7) * 11.0 + math.cos(self.tick * 0.2 + i * 1.2) * 5.0)
            elif self.state == "LISTENING":
                h = 2.5 + abs(math.sin(self.tick * 0.2 + i * 0.5) * 6.0)
            elif self.state == "THINKING":
                h = 2.0 + abs(math.sin(self.tick * 0.4 + i * 0.3) * 4.0)
            else:
                h = 2.0  # Minimal resting frequency bar

            bx = start_x + i * (bar_w + gap)
            self.create_rectangle(bx, eq_y - h, bx + bar_w, eq_y, fill=primary_color, outline="")

        self.after(30, self.animate)


# =====================================================================
# 2. MINI CORE RADAR HUD (Left Sidebar)
# =====================================================================
class CoreRadarHUD(ctk.CTkCanvas):
    def __init__(self, master, size=130, **kwargs):
        super().__init__(master, width=size, height=size, bg="#060d1f", highlightthickness=0, **kwargs)
        self.size = size
        self.center = size / 2
        self.angle = 0
        self.animate()

    def animate(self):
        self.delete("all")
        self.angle += 3
        cx, cy = self.center, self.center

        # Concentric tech grid rings
        for r in [20, 38, 56]:
            self.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#0e2a47", width=1)

        # Crosshairs
        self.create_line(cx, 8, cx, self.size - 8, fill="#0e2a47", width=1, dash=(2, 4))
        self.create_line(8, cy, self.size - 8, cy, fill="#0e2a47", width=1, dash=(2, 4))

        # Rotating outer segment
        self.create_arc(10, 10, self.size - 10, self.size - 10,
                        start=self.angle, extent=90, style="arc", outline="#00f5ff", width=2)
        self.create_arc(10, 10, self.size - 10, self.size - 10,
                        start=self.angle + 180, extent=90, style="arc", outline="#00f5ff", width=2)

        # Radar sweep beam
        rad = math.radians(self.angle)
        ex = cx + math.cos(rad) * (self.size / 2 - 12)
        ey = cy - math.sin(rad) * (self.size / 2 - 12)
        self.create_line(cx, cy, ex, ey, fill="#00ffcc", width=1)

        # Core glowing center pulse
        pulse = 4 + math.sin(math.radians(self.angle * 3)) * 2
        self.create_oval(cx - pulse, cy - pulse, cx + pulse, cy + pulse, fill="#00f5ff", outline="")

        self.after(35, self.animate)


# =====================================================================
# 3. MAIN RK APPLICATION
# =====================================================================
class RKApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("R.K // QUANTUM NEURAL INTERFACE")
        self.geometry("1200x760")
        self.minsize(1050, 680)

        # Futuristic Color Palette
        self.c_bg = "#020617"         # Deep Space Obsidian
        self.c_sidebar = "#060d1f"    # Cyber Sidebar
        self.c_card = "#09142b"       # Elevated Card Glass
        self.c_cyan = "#00f5ff"       # Neon Glow Cyan
        self.c_blue = "#0284c7"       # Quantum Blue
        self.c_amber = "#f59e0b"      # Acoustic Amber
        self.c_border = "#132d4d"     # Tech Border Navy
        self.c_text = "#e2f3ff"       # Icy White
        self.c_dim = "#6487a5"        # Steel Gray-Blue

        self.configure(fg_color=self.c_bg)

        # Fonts
        self.font_title = ctk.CTkFont(family="Consolas", size=22, weight="bold")
        self.font_header = ctk.CTkFont(family="Consolas", size=13, weight="bold")
        self.font_body = ctk.CTkFont(family="Consolas", size=12)
        self.font_tag = ctk.CTkFont(family="Consolas", size=10, weight="bold")

        # Initialize Core
        self.core = RKCore()
        self.is_listening = False
        self.is_processing = False
        self.is_pinned = False

        # Hook Core Speech Callbacks directly to Avatar Movement!
        self.core.voice.on_speech_start = self._on_core_speech_start
        self.core.voice.on_speech_stop = self._on_core_speech_stop

        # Build Full Futuristic Layout
        self._build_ui()

        # Keyboard shortcuts & Clean exit handling
        self.bind("<Control-m>", lambda e: self.toggle_listening())
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Initial Sync
        self.refresh_sidebar()
        self.update_telemetry_loop()

        # Auto-start hands-free listening so commands work without clicking
        self.after(1200, self.auto_start_listening)

    # -----------------------------------------------------------------
    # Speech Callback Handlers (Real-Time Avatar Animation)
    # -----------------------------------------------------------------
    def _on_core_speech_start(self):
        """Called automatically when RK voice synthesis starts speaking"""
        def _apply():
            if hasattr(self, "avatar_hud"):
                self.avatar_hud.set_state("SPEAKING")
            if hasattr(self, "status_beacon"):
                self.status_beacon.configure(text="● VOCAL SYNTHESIS ACTIVE", text_color=self.c_cyan)
        self.after(0, _apply)

    def _on_core_speech_stop(self):
        """Called automatically when RK voice playback finishes"""
        def _apply():
            if hasattr(self, "avatar_hud"):
                new_st = "LISTENING" if self.is_listening else "IDLE"
                self.avatar_hud.set_state(new_st)
            if hasattr(self, "status_beacon"):
                if self.is_listening:
                    self.status_beacon.configure(text="● LISTENING FOR AUDIO...", text_color=self.c_amber)
                else:
                    self.status_beacon.configure(text="● STANDBY // READY", text_color="#10b981")
        self.after(0, _apply)

    # -----------------------------------------------------------------
    # UI Layout Construction
    # -----------------------------------------------------------------
    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # -------------------------------------------------------------
        # LEFT SIDEBAR: HUD, Tasks, Memory Core
        # -------------------------------------------------------------
        self.sidebar = ctk.CTkFrame(self, width=280, corner_radius=0, fg_color=self.c_sidebar,
                                    border_width=1, border_color=self.c_border)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_columnconfigure(0, weight=1)
        self.sidebar.grid_rowconfigure(3, weight=1)
        self.sidebar.grid_rowconfigure(5, weight=1)

        # 1. Sidebar Header & Radar Core
        self.brand_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.brand_frame.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="ew")

        self.radar = CoreRadarHUD(self.brand_frame, size=110)
        self.radar.pack(pady=5)

        self.brand_title = ctk.CTkLabel(self.brand_frame, text="R.K", font=self.font_title, text_color=self.c_cyan)
        self.brand_title.pack()
        self.brand_sub = ctk.CTkLabel(self.brand_frame, text="MARK-85 // QUANTUM CORE", font=self.font_tag, text_color=self.c_dim)
        self.brand_sub.pack(pady=(0, 5))

        # 2. Mission Tasks Section
        self.task_header = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.task_header.grid(row=2, column=0, padx=15, pady=(10, 2), sticky="ew")
        ctk.CTkLabel(self.task_header, text="[ MISSION TASKS ]", font=self.font_header, text_color=self.c_cyan).pack(side="left")
        self.task_count_lbl = ctk.CTkLabel(self.task_header, text="ACTIVE: 0", font=self.font_tag, text_color=self.c_dim)
        self.task_count_lbl.pack(side="right")

        self.task_textbox = ctk.CTkTextbox(self.sidebar, font=self.font_body, fg_color="#030814",
                                           text_color="#38bdf8", border_width=1, border_color=self.c_border,
                                           corner_radius=6)
        self.task_textbox.grid(row=3, column=0, padx=15, pady=4, sticky="nsew")
        self.task_textbox.configure(state="disabled")

        # 3. Memory Banks Section
        self.mem_header = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.mem_header.grid(row=4, column=0, padx=15, pady=(10, 2), sticky="ew")
        ctk.CTkLabel(self.mem_header, text="[ MEMORY BANKS ]", font=self.font_header, text_color=self.c_cyan).pack(side="left")
        self.mem_count_lbl = ctk.CTkLabel(self.mem_header, text="LOGS: 0", font=self.font_tag, text_color=self.c_dim)
        self.mem_count_lbl.pack(side="right")

        self.memory_textbox = ctk.CTkTextbox(self.sidebar, font=self.font_body, fg_color="#030814",
                                             text_color="#38bdf8", border_width=1, border_color=self.c_border,
                                             corner_radius=6)
        self.memory_textbox.grid(row=5, column=0, padx=15, pady=4, sticky="nsew")
        self.memory_textbox.configure(state="disabled")

        # 4. Sidebar Sync Button
        self.sync_btn = ctk.CTkButton(self.sidebar, text="⟳ SYNC TELEMETRY", command=self.refresh_sidebar,
                                      font=self.font_header, fg_color="#081830", hover_color="#0e2a54",
                                      border_width=1, border_color=self.c_cyan, text_color=self.c_cyan, height=32)
        self.sync_btn.grid(row=6, column=0, padx=15, pady=12, sticky="ew")

        # -------------------------------------------------------------
        # RIGHT MAIN PANEL: Top Telemetry Bar, Avatar Deck & Chat
        # -------------------------------------------------------------
        self.main_deck = ctk.CTkFrame(self, fg_color="transparent")
        self.main_deck.grid(row=0, column=1, sticky="nsew", padx=15, pady=12)
        self.main_deck.grid_columnconfigure(0, weight=1)
        self.main_deck.grid_rowconfigure(1, weight=1)

        # 1. Top HUD Header Bar
        self.hud_bar = ctk.CTkFrame(self.main_deck, fg_color=self.c_card, border_width=1,
                                    border_color=self.c_border, corner_radius=8, height=48)
        self.hud_bar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.hud_bar.grid_columnconfigure(1, weight=1)

        # Status Light
        self.status_beacon = ctk.CTkLabel(self.hud_bar, text="● STANDBY // READY", font=self.font_header,
                                          text_color="#10b981")
        self.status_beacon.pack(side="left", padx=15)

        # Telemetry Display (Time & Heartbeat)
        self.telemetry_lbl = ctk.CTkLabel(self.hud_bar, text="TIME: --:--:-- | CORE: ACTIVE | LATENCY: 14ms",
                                          font=self.font_tag, text_color=self.c_dim)
        self.telemetry_lbl.pack(side="left", padx=10)

        # Voice Selector & Settings
        self.voice_var = ctk.StringVar(value="Human Male (Madhur)")
        self.voice_menu = ctk.CTkComboBox(self.hud_bar, values=["Human Male (Madhur)", "Human Female (Swara)", "Jarvis (Christopher)", "Female (Neerja)"],
                                          variable=self.voice_var, command=self.change_voice,
                                          font=self.font_tag, fg_color="#040b17", text_color=self.c_cyan,
                                          border_color=self.c_border, width=175, height=28)
        self.voice_menu.pack(side="right", padx=10, pady=6)

        # Pin / Float Always-on-Top Toggle
        self.pin_btn = ctk.CTkButton(self.hud_bar, text="📌 FLOAT [OFF]", width=105, height=28,
                                     font=self.font_tag, command=self.toggle_pin,
                                     fg_color="#040b17", hover_color="#0e2a54", border_width=1,
                                     border_color=self.c_border, text_color=self.c_dim)
        self.pin_btn.pack(side="right", padx=(0, 6), pady=6)

        # 2. Split Workspace (Avatar Center Deck & Chat Stream)
        self.workspace = ctk.CTkFrame(self.main_deck, fg_color="transparent")
        self.workspace.grid(row=1, column=0, sticky="nsew")
        self.workspace.grid_columnconfigure(0, weight=4)  # Chat History
        self.workspace.grid_columnconfigure(1, weight=3)  # Animated Avatar Deck
        self.workspace.grid_rowconfigure(0, weight=1)

        # --- LEFT SUB-PANE: Chat Terminal ---
        self.chat_frame = ctk.CTkFrame(self.workspace, fg_color=self.c_card, border_width=1,
                                       border_color=self.c_border, corner_radius=8)
        self.chat_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.chat_frame.grid_columnconfigure(0, weight=1)
        self.chat_frame.grid_rowconfigure(1, weight=1)

        # Chat Header
        self.chat_header_lbl = ctk.CTkLabel(self.chat_frame, text="COMMUNICATION STREAM // DIALOGUE LOG",
                                            font=self.font_header, text_color=self.c_cyan)
        self.chat_header_lbl.grid(row=0, column=0, padx=15, pady=(10, 5), sticky="w")

        # Chat Box
        self.chat_box = ctk.CTkTextbox(self.chat_frame, font=self.font_body, fg_color="#030712",
                                       text_color=self.c_text, border_width=1, border_color=self.c_border,
                                       corner_radius=6)
        self.chat_box.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")
        self.chat_box.configure(state="disabled")

        # --- RIGHT SUB-PANE: Interactive Avatar Display Deck ---
        self.avatar_deck = ctk.CTkFrame(self.workspace, fg_color=self.c_card, border_width=1,
                                        border_color=self.c_border, corner_radius=8)
        self.avatar_deck.grid(row=0, column=1, sticky="nsew")

        self.deck_title = ctk.CTkLabel(self.avatar_deck, text="NEURAL SYNAPSE AVATAR",
                                       font=self.font_header, text_color=self.c_cyan)
        self.deck_title.pack(pady=(15, 5))

        # Dynamic Avatar Canvas with Live Movement!
        self.avatar_hud = AvatarHUD(self.avatar_deck, avatar_path="avatar.jpg", size=240)
        self.avatar_hud.pack(pady=10)

        self.avatar_state_badge = ctk.CTkLabel(self.avatar_deck, text="[ HOLOGRAPHIC PROJECTION: ONLINE ]",
                                              font=self.font_tag, text_color=self.c_dim)
        self.avatar_state_badge.pack(pady=4)

        # Audio Waveform Equalizer Display Tag
        self.vocal_indicator = ctk.CTkLabel(self.avatar_deck, text="VOICE: HI-IN-MADHUR (HUMAN MALE)",
                                            font=self.font_tag, text_color="#38bdf8")
        self.vocal_indicator.pack(pady=2)

        # Quick Action Suggestion Chips
        self.chips_frame = ctk.CTkFrame(self.avatar_deck, fg_color="transparent")
        self.chips_frame.pack(pady=15, padx=10, fill="x")

        chips = [
            ("🌐 Google", lambda: self.quick_command("Open google.com")),
            ("🎵 Music", lambda: self.quick_command("Play song on YouTube")),
            ("📝 Tasks", lambda: self.quick_command("What are my active tasks?")),
            ("❌ Close Chrome", lambda: self.quick_command("Close chrome browser")),
        ]
        for idx, (label, cmd) in enumerate(chips):
            r = idx // 2
            c = idx % 2
            btn = ctk.CTkButton(self.chips_frame, text=label, font=self.font_tag, command=cmd,
                                fg_color="#061226", hover_color="#0d254c", border_width=1,
                                border_color=self.c_blue, text_color=self.c_cyan, height=28)
            btn.grid(row=r, column=c, padx=4, pady=4, sticky="ew")
            self.chips_frame.grid_columnconfigure(c, weight=1)

        # 3. BOTTOM COMMAND CONSOLE (Input, Mic, Cam, Transmit)
        self.console_frame = ctk.CTkFrame(self.main_deck, fg_color=self.c_card, border_width=1,
                                          border_color=self.c_border, corner_radius=8, height=60)
        self.console_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        self.console_frame.grid_columnconfigure(0, weight=1)

        # Input Entry
        self.entry = ctk.CTkEntry(self.console_frame, placeholder_text="Awaiting command... (e.g. 'Add task buy batteries', 'Play Believer')",
                                  font=self.font_body, fg_color="#030712", text_color="#ffffff",
                                  border_color=self.c_blue, border_width=1, height=40)
        self.entry.grid(row=0, column=0, padx=(10, 8), pady=10, sticky="ew")
        self.entry.bind("<Return>", lambda event: self.send_message())

        # Mic Toggle Button
        self.mic_btn = ctk.CTkButton(self.console_frame, text="🎙️ MIC [OFF]", width=95, height=40,
                                     font=self.font_header, command=self.toggle_listening,
                                     fg_color="#081830", hover_color="#0e2a54", border_width=1,
                                     border_color=self.c_cyan, text_color=self.c_cyan)
        self.mic_btn.grid(row=0, column=1, padx=4, pady=10)

        # Optical Camera Button
        self.cam_btn = ctk.CTkButton(self.console_frame, text="📷 SCAN", width=75, height=40,
                                     font=self.font_header, command=self.capture_vision,
                                     fg_color="#081830", hover_color="#0e2a54", border_width=1,
                                     border_color=self.c_cyan, text_color=self.c_cyan)
        self.cam_btn.grid(row=0, column=2, padx=4, pady=10)

        # Transmit Button
        self.send_btn = ctk.CTkButton(self.console_frame, text="⚡ TRANSMIT", width=110, height=40,
                                      font=self.font_header, command=self.send_message,
                                      fg_color="#0284c7", hover_color="#0369a1", text_color="#ffffff")
        self.send_btn.grid(row=0, column=3, padx=(4, 10), pady=10)

        # Initial Welcome Message
        self.append_to_chat("SYSTEM", "R.K QUANTUM CORE INITIALIZED.\nUPLINK TO GEMINI NEURAL NETWORK ESTABLISHED.\nAWAITING DIRECTIVES...")

    # -----------------------------------------------------------------
    # Telemetry Real-Time Clock Loop
    # -----------------------------------------------------------------
    def update_telemetry_loop(self):
        cur_time = time.strftime("%H:%M:%S")
        self.telemetry_lbl.configure(text=f"TIME: {cur_time} | CORE: ONLINE | LATENCY: 12ms")
        self.after(1000, self.update_telemetry_loop)

    # -----------------------------------------------------------------
    # Chat & Stream Handling
    # -----------------------------------------------------------------
    def append_to_chat(self, sender, text):
        self.chat_box.configure(state="normal")
        ts = time.strftime("%H:%M")
        
        if sender == "YOU":
            msg = f"┌─── [ COMMANDER // YOU ] ───────────────── [{ts}]\n│ {text}\n└───\n\n"
        elif sender == "J.A.R.V.I.S":
            msg = f"┌─── [ J.A.R.V.I.S // MARK-85 ] ────────── [{ts}]\n│ {text}\n└───\n\n"
        else:
            msg = f"● [ {sender} // {ts} ]: {text}\n\n"

        self.chat_box.insert("end", msg)
        self.chat_box.see("end")
        self.chat_box.configure(state="disabled")

    def quick_command(self, cmd_text):
        self.entry.delete(0, "end")
        self.entry.insert(0, cmd_text)
        self.send_message()

    # -----------------------------------------------------------------
    # Message Dispatch & Processing
    # -----------------------------------------------------------------
    def send_message(self):
        text = self.entry.get().strip()
        if not text or self.is_processing:
            return
        self.entry.delete(0, "end")
        self.process_request(text)

    def process_request(self, user_text, image_b64=None):
        self.append_to_chat("YOU", user_text)
        self.is_processing = True

        # Update UI & Avatar State to THINKING
        self.avatar_hud.set_state("THINKING")
        self.status_beacon.configure(text="● NEURAL COMPUTATION ACTIVE...", text_color="#a855f7")
        self.send_btn.configure(state="disabled", text="PROCESSING")
        self.entry.configure(state="disabled")

        def _worker():
            try:
                response = self.core.send_message(user_text, image_b64)
            except Exception as e:
                response = f"Neural uplink error: {e}"

            # Post response to chat from main thread
            self.after(0, lambda: self.append_to_chat("R.K", response))
            self.after(0, self.refresh_sidebar)

            # Vocal synthesis (avatar will animate automatically via callbacks)
            try:
                self.core.voice.speak(response)
            except Exception as e:
                print("Speech synthesis error:", e)

            # Reset processing state
            def _reset_ui():
                self.is_processing = False
                self.send_btn.configure(state="normal", text="⚡ TRANSMIT")
                self.entry.configure(state="normal")
                if not self.core.voice.is_speaking:
                    if self.is_listening:
                        self.avatar_hud.set_state("IDLE")
                        self.status_beacon.configure(text="● BACKGROUND ON: SAY 'RK'", text_color="#10b981")
                    else:
                        self.avatar_hud.set_state("IDLE")
                        self.status_beacon.configure(text="● STANDBY // READY", text_color="#10b981")

            self.after(0, _reset_ui)

        threading.Thread(target=_worker, daemon=True).start()

    def toggle_pin(self):
        """Toggle floating on top of all windows (ideal for browsing YouTube while commanding RK)"""
        self.is_pinned = not self.is_pinned
        self.attributes("-topmost", self.is_pinned)
        if self.is_pinned:
            self.pin_btn.configure(text="📌 PINNED [ON]", text_color=self.c_cyan,
                                   border_color=self.c_cyan, fg_color="#09254a")
        else:
            self.pin_btn.configure(text="📌 FLOAT [OFF]", text_color=self.c_dim,
                                   border_color=self.c_border, fg_color="#040b17")

    def auto_start_listening(self):
        """Auto-start continuous voice listening on startup"""
        if not self.is_listening:
            self.toggle_listening()

    # -----------------------------------------------------------------
    # Continuous Background Wake-Word Listener ("RK" -> "Kya command hai boss?")
    # -----------------------------------------------------------------
    def toggle_listening(self):
        if self.is_listening:
            self.is_listening = False
            self.mic_btn.configure(fg_color="#081830", text="🎙️ WAKE-WORD [OFF]", text_color=self.c_cyan)
            if not self.is_processing:
                self.avatar_hud.set_state("IDLE")
                self.status_beacon.configure(text="● STANDBY // READY", text_color="#10b981")
            return

        self.is_listening = True
        self.mic_btn.configure(fg_color="#15803d", text="🎙️ WAKE-WORD [ON]", text_color="#ffffff")
        self.avatar_hud.set_state("IDLE")
        self.status_beacon.configure(text="● BACKGROUND ON: SAY 'RK'", text_color="#10b981")

        def _listen_loop():
            try:
                with self.core.voice.get_microphone() as source:
                    # Sensitive, locked threshold - never deaf
                    self.core.voice.recognizer.dynamic_energy_threshold = False
                    self.core.voice.recognizer.energy_threshold = 240
                    self.core.voice.recognizer.pause_threshold = 0.5

                    print(f"[MIC ACTIVE] Background listening for 'RK'... Threshold: {self.core.voice.recognizer.energy_threshold:.1f}")

                    wake_words = [
                        "rk", "r.k.", "r k", "are ke", "aare ke", "aar ke", "ark", "rkay",
                        "hey rk", "suno rk", "ok rk", "hello rk",
                        "jarvis", "jarves", "jarviz", "jarv", "javis", "javes", 
                        "hey jarvis", "suno jarvis", "ok jarvis", "hello jarvis", 
                        "charvis", "travis", "जार्विस"
                    ]

                    while self.is_listening:
                        # Wait while RK is computing or speaking so it never hears its own voice
                        if self.is_processing or self.core.voice.is_speaking:
                            time.sleep(0.2)
                            continue

                        # Fast background listen cycle
                        text = self.core.voice.listen_with_mic(source, timeout=3, phrase_time_limit=6, pause_threshold=0.5)
                        if not self.is_listening:
                            break
                        if not text or len(text.strip()) < 2:
                            continue

                        text_lower = text.lower().strip()
                        print(f"[HEARD IN BACKGROUND]: {text_lower}")

                        # Check for wake word
                        matched_wake = None
                        for w in wake_words:
                            if w in text_lower:
                                matched_wake = w
                                break

                        if matched_wake:
                            # Extract command spoken in same utterance
                            # e.g. "jarvis open youtube" -> "open youtube"
                            cmd_after = text_lower.replace(matched_wake, "").strip(" ,.-!?")

                            if cmd_after and len(cmd_after) > 2:
                                # User gave both wake word and command together! Execute immediately with zero delay!
                                self.after(0, self.process_request, cmd_after)
                                time.sleep(0.5)
                            else:
                                # User said only wake word: "RK"!
                                self.after(0, lambda: self.append_to_chat("R.K", "Kya command hai boss?"))
                                self.after(0, lambda: self.status_beacon.configure(text="● 'Kya command hai boss?'", text_color=self.c_cyan))
                                self.after(0, lambda: self.avatar_hud.set_state("SPEAKING"))

                                # Instant zero-delay local voice reply!
                                self.core.voice.play_wake_prompt()

                                # Switch UI to actively awaiting the command
                                self.after(0, lambda: self.status_beacon.configure(text="● AWAITING COMMAND...", text_color=self.c_amber))
                                self.after(0, lambda: self.avatar_hud.set_state("LISTENING"))

                                # Clear speaker echo from microphone buffer
                                if hasattr(source, "clear_buffer"):
                                    source.clear_buffer()

                                # Listen actively for commander's directive
                                cmd = self.core.voice.listen_with_mic(source, timeout=6, phrase_time_limit=8, pause_threshold=0.5)
                                if cmd and len(cmd.strip()) > 1:
                                    self.after(0, self.process_request, cmd)
                                    time.sleep(0.5)
                                else:
                                    self.after(0, lambda: self.status_beacon.configure(text="● BACKGROUND ON: SAY 'RK'", text_color="#10b981"))
                                    self.after(0, lambda: self.avatar_hud.set_state("IDLE"))
                        else:
                            # Direct command support (e.g., "open youtube", "close chrome")
                            direct_triggers = ["open ", "close ", "kholo", "band karo", "play ", "chalao", "add task", "task add", "youtube", "google"]
                            if any(dt in text_lower for dt in direct_triggers):
                                self.after(0, self.process_request, text_lower)
                                time.sleep(0.5)
            except Exception as e:
                print("Voice Loop Error:", e)

        threading.Thread(target=_listen_loop, daemon=True).start()

    # -----------------------------------------------------------------
    # Camera Vision Scanner
    # -----------------------------------------------------------------
    def capture_vision(self):
        self.cam_btn.configure(state="disabled", text="SCANNING")
        self.append_to_chat("SYSTEM", "OPTICAL SENSOR ENGAGED. CAPTURING FRAME...")

        def _capture():
            img_b64 = self.core.vision.capture_image_base64()
            if img_b64:
                self.after(0, self.append_to_chat, "SYSTEM", "OPTICAL TELEMETRY SECURED. ANALYZING...")
                self.after(0, self.show_image_preview, img_b64)
                self.after(0, self.process_request, "[Visual Data from Camera]", img_b64)
            else:
                self.after(0, self.append_to_chat, "SYSTEM", "ERROR: OPTICAL SENSOR OFFLINE.")
            self.after(0, lambda: self.cam_btn.configure(state="normal", text="📷 SCAN"))

        threading.Thread(target=_capture, daemon=True).start()

    def show_image_preview(self, img_b64):
        try:
            import base64
            import io
            img_bytes = base64.b64decode(img_b64)
            pil_img = Image.open(io.BytesIO(img_bytes))

            top = ctk.CTkToplevel(self)
            top.title("OPTICAL SENSOR SCAN")
            top.geometry("420x320")
            top.attributes("-topmost", True)
            top.configure(fg_color=self.c_bg)

            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(400, 300))
            lbl = ctk.CTkLabel(top, text="", image=ctk_img)
            lbl.pack(expand=True, fill="both", padx=10, pady=10)
        except Exception as e:
            print("Preview Error:", e)

    # -----------------------------------------------------------------
    # Voice Settings Dropdown
    # -----------------------------------------------------------------
    def change_voice(self, choice):
        if "Swara" in choice or "Female (Swara)" in choice:
            self.core.voice.set_voice(1, 150)
            self.vocal_indicator.configure(text="VOICE: HI-IN-SWARA (HUMAN FEMALE)")
        elif "Christopher" in choice or "Jarvis" in choice:
            self.core.voice.set_voice(2, 150)
            self.vocal_indicator.configure(text="VOICE: EN-US-CHRISTOPHER (JARVIS)")
        elif "Neerja" in choice:
            self.core.voice.set_voice(3, 150)
            self.vocal_indicator.configure(text="VOICE: EN-IN-NEERJA (EXPRESSIVE)")
        else:
            self.core.voice.set_voice(0, 150)
            self.vocal_indicator.configure(text="VOICE: HI-IN-MADHUR (HUMAN MALE)")

    # -----------------------------------------------------------------
    # Sidebar Data Sync (Tasks & Memory)
    # -----------------------------------------------------------------
    def refresh_sidebar(self):
        # Update Task Log
        tasks = self.core.db.get_tasks()
        active_count = sum(1 for t in tasks if not t.get("done"))
        self.task_count_lbl.configure(text=f"ACTIVE: {active_count}")

        self.task_textbox.configure(state="normal")
        self.task_textbox.delete("0.0", "end")
        if not tasks:
            self.task_textbox.insert("end", "> NO ACTIVE DIRECTIVES.\n")
        else:
            for t in tasks:
                icon = "[■]" if t.get("done") else "[ ]"
                self.task_textbox.insert("end", f"{icon} {t['text']}\n")
        self.task_textbox.configure(state="disabled")

        # Update Memory Core
        memories = self.core.db.get_memory()
        self.mem_count_lbl.configure(text=f"LOGS: {len(memories)}")

        self.memory_textbox.configure(state="normal")
        self.memory_textbox.delete("0.0", "end")
        if not memories:
            self.memory_textbox.insert("end", "> MEMORY BANKS UNLOADED.\n")
        else:
            for idx, m in enumerate(memories, 1):
                self.memory_textbox.insert("end", f"[MEM.{idx:02d}] {m}\n")
        self.memory_textbox.configure(state="disabled")

    def on_closing(self):
        """Cleanly terminate application and background threads without lingering processes"""
        self.is_listening = False
        try:
            self.destroy()
        except Exception:
            pass
        os._exit(0)


# Backward compatibility alias
JarvisApp = RKApp

if __name__ == "__main__":
    try:
        app = RKApp()
        app.mainloop()
    except KeyboardInterrupt:
        print("\n[SYSTEM] R.K terminated safely by Commander.")
        try:
            app.destroy()
        except Exception:
            pass
        os._exit(0)
