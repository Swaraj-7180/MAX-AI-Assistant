import math
import queue
import tkinter as tk

import customtkinter as ctk


class MaxGUI:
    def __init__(self) -> None:
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title("MAX - AI Assistant")
        self.root.geometry("520x600")
        self.root.minsize(520, 600)

        self._ui_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self._hud_state = "idle"
        self._t = 0.0
        self._running = True  # controls animation loop

        self._cur = {"r": 0.0, "g": 204.0, "b": 255.0}
        self._targets = {
            "idle":      {"r": 0,  "g": 204, "b": 255},
            "listening": {"r": 0,  "g": 255, "b": 204},
            "thinking":  {"r": 68, "g": 136, "b": 255},
            "speaking":  {"r": 0,  "g": 238, "b": 255},
        }
        self._speeds = {"idle": 0.4, "listening": 1.2, "thinking": 2.0, "speaking": 1.5}
        self._amps   = {"idle": 1.0, "listening": 1.6, "thinking": 1.3, "speaking": 1.9}

        self._build_arcs()
        self._build_ticks()
        self._build_layout()
        self._ui_after_id = self.root.after(80, self._process_ui_queue)
        self._hud_after_id = self.root.after(16, self._animate_hud)

    def _build_arcs(self):
        self._arcs = [
            (180,0.1,1.1,1.5,0.9,0.004),(180,1.3,2.0,1.5,0.7,-0.003),
            (180,2.2,3.0,1.5,0.8,0.005),(180,3.3,4.5,1.5,0.6,-0.004),
            (180,4.8,5.8,1.5,0.9,0.003),(162,0.3,1.8,2.0,0.5,-0.006),
            (162,2.1,3.4,2.0,0.4,0.005),(162,3.7,5.2,2.0,0.6,-0.004),
            (145,0.0,0.8,3.0,0.8,0.008),(145,1.2,2.5,3.0,0.6,-0.007),
            (145,2.9,4.1,3.0,0.7,0.006),(145,4.5,5.9,3.0,0.5,-0.005),
            (128,0.5,2.2,1.5,0.4,0.010),(128,2.6,4.0,1.5,0.5,-0.009),
            (128,4.4,5.7,1.5,0.3,0.008),(110,0.2,1.5,4.0,0.9,-0.012),
            (110,1.9,3.5,4.0,0.7,0.011),(110,3.9,5.6,4.0,0.8,-0.010),
            (92, 0.0,2.8,2.0,0.5,0.015),(92, 3.2,5.8,2.0,0.4,-0.013),
            (75, 0.4,1.8,5.0,0.85,-0.018),(75,2.3,4.0,5.0,0.7,0.016),
            (75, 4.5,6.0,5.0,0.9,-0.014),(58, 0.0,3.5,2.0,0.5,0.022),
            (58, 4.0,6.28,2.0,0.4,-0.019),(42,0.5,2.5,6.0,0.95,-0.025),
            (42, 3.2,5.5,6.0,0.8,0.022),
        ]

    def _build_ticks(self):
        self._ticks = []
        for i in range(72):
            a = (i / 72) * math.pi * 2
            length = 14 if i % 6 == 0 else (8 if i % 3 == 0 else 4)
            self._ticks.append((a, length, 195))

    def _build_layout(self) -> None:
        self.root.grid_rowconfigure(0, weight=0)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Header
        self.header = ctk.CTkFrame(self.root, corner_radius=0, height=64)
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.grid_propagate(False)
        self.header.grid_columnconfigure(1, weight=1)

        title = ctk.CTkLabel(self.header, text="MAX",
            font=ctk.CTkFont(size=24, weight="bold"))
        title.grid(row=0, column=0, padx=(18,10), pady=12, sticky="w")

        subtitle = ctk.CTkLabel(self.header,
            text="Voice-first desktop assistant",
            font=ctk.CTkFont(size=13), text_color="#9ea3aa")
        subtitle.grid(row=0, column=1, sticky="w")

        self.status_label = ctk.CTkLabel(self.header, text="Idle",
            font=ctk.CTkFont(size=15, weight="bold"), text_color="#7ed957")
        self.status_label.grid(row=0, column=2, padx=(10,18), pady=12, sticky="e")

        # HUD fullscreen
        hud_frame = ctk.CTkFrame(self.root, fg_color="#000000", corner_radius=0)
        hud_frame.grid(row=1, column=0, sticky="nsew")

        self.hud = tk.Canvas(hud_frame, bg="#000000", highlightthickness=0)
        self.hud.pack(fill="both", expand=True)

    def _animate_hud(self):
        if not self._running:
            return  # stop loop if shutting down

        self._t += 0.016
        t = self._t
        s = self._hud_state
        spd = self._speeds[s]
        amp = self._amps[s]
        tgt = self._targets[s]

        self._cur["r"] = self._lerp(self._cur["r"], tgt["r"], 0.05)
        self._cur["g"] = self._lerp(self._cur["g"], tgt["g"], 0.05)
        self._cur["b"] = self._lerp(self._cur["b"], tgt["b"], 0.05)
        R = int(self._cur["r"]); G = int(self._cur["g"]); B = int(self._cur["b"])

        w = self.hud.winfo_width() or 520
        h = self.hud.winfo_height() or 536
        cx = w // 2
        cy = h // 2

        self.hud.delete("all")

        # Grid
        for i in range(0, max(w,h), 20):
            self.hud.create_line(i,0,i,h, fill=self._rgba(R,G,B,0.04), width=0.5)
            self.hud.create_line(0,i,w,i, fill=self._rgba(R,G,B,0.04), width=0.5)

        # Tick marks
        for (a, length, r) in self._ticks:
            angle = a + t * 0.05 * spd
            ax = cx + math.cos(angle) * r
            ay = cy + math.sin(angle) * r
            bx = cx + math.cos(angle) * (r - length)
            by = cy + math.sin(angle) * (r - length)
            alpha = 0.9 if length > 10 else 0.4
            lw = 1.5 if length > 10 else 0.8
            self.hud.create_line(ax,ay,bx,by, fill=self._rgba(R,G,B,alpha), width=lw)

        # Rotating arcs
        for i,(r,start,end,lw,alpha,speed) in enumerate(self._arcs):
            offset = t * speed * spd * amp
            pulse = 0.7 + 0.3 * math.sin(t * spd + i * 0.4)
            self._draw_arc(cx,cy,r,start+offset,end+offset,
                self._rgba(R,G,B,alpha*pulse), lw)

        # Outer circle
        self.hud.create_oval(cx-200,cy-200,cx+200,cy+200,
            outline=self._rgba(R,G,B,0.3), width=0.8)

        # Inner rings
        for ri, rr in enumerate([28,22]):
            self.hud.create_oval(cx-rr,cy-rr,cx+rr,cy+rr,
                outline=self._rgba(R,G,B,0.6+ri*0.2),
                width=2 if ri==0 else 1)

        # Core reactor
        cp = 1 + math.sin(t * spd * 2) * 0.08 * amp
        cr = int(18 * cp)
        self.hud.create_oval(cx-cr,cy-cr,cx+cr,cy+cr,
            outline=f"#{R:02x}{G:02x}{B:02x}", width=2.5,
            fill=self._rgba(R,G,B,0.15+math.sin(t*spd)*0.1))

        # Core dot
        wa = int((0.8+math.sin(t*spd*3)*0.2)*255)
        self.hud.create_oval(cx-5,cy-5,cx+5,cy+5,
            fill=f"#{wa:02x}{wa:02x}{wa:02x}", outline="")

        # Crosshairs
        self.hud.create_line(cx-210,cy,cx+210,cy,
            fill=self._rgba(R,G,B,0.25), width=0.8, dash=(4,8))
        self.hud.create_line(cx,cy-210,cx,cy+210,
            fill=self._rgba(R,G,B,0.25), width=0.8, dash=(4,8))

        # Waveform ring
        if s in ("speaking","listening"):
            pts = []
            for ai in range(0, 361, 3):
                a = math.radians(ai)
                wave = math.sin(a*12 + t*8)*6*amp
                pts.append(cx + math.cos(a)*(205+wave))
                pts.append(cy + math.sin(a)*(205+wave))
            if len(pts) >= 4:
                self.hud.create_line(*pts, fill=self._rgba(R,G,B,0.6),
                    width=1.5, smooth=True)

        # Data readouts
        readouts = [
            (cx-200, cy-60, "NEURAL", f"{87+math.sin(t*0.3)*8:.1f}%"),
            (cx-200, cy-30, "VOICE",  f"{92+math.sin(t*0.5)*5:.1f}%"),
            (cx-200, cy,    "SYS",    f"{99+math.sin(t*0.2)*0.9:.2f}%"),
            (cx+105, cy-60, "POWER",  "100%"),
            (cx+105, cy-30, "TEMP",   f"{36+math.sin(t*0.4)*2:.1f}C"),
            (cx+105, cy,    "PING",   f"{int(12+math.sin(t*1.2)*4)}ms"),
        ]
        for (rx,ry,label,val) in readouts:
            self.hud.create_text(rx,ry, text=label,
                fill=self._rgba(R,G,B,0.5), font=("Courier",8), anchor="w")
            self.hud.create_text(rx,ry+13, text=val,
                fill=self._rgba(R,G,B,0.9), font=("Courier",9,"bold"), anchor="w")

        # MAX label
        self.hud.create_text(cx,cy+50, text="M A X",
            fill=self._rgba(R,G,B,0.9), font=("Courier",13,"bold"))
        self.hud.create_text(cx,cy+65, text="AI ASSISTANT v1.0",
            fill=self._rgba(R,G,B,0.4), font=("Courier",8))

        # Scan line
        scan_y = (cy-200) + ((t*30*spd) % 400)
        self.hud.create_line(cx-200,scan_y,cx+200,scan_y,
            fill=self._rgba(R,G,B,0.15), width=1)

        self._hud_after_id = self.root.after(16, self._animate_hud)

    def _lerp(self, a, b, f): return a + (b - a) * f

    def _rgba(self, r, g, b, alpha):
        rr = int(r*alpha); gg = int(g*alpha); bb = int(b*alpha)
        return f"#{rr:02x}{gg:02x}{bb:02x}"

    def _draw_arc(self, cx, cy, radius, start, end, color, width):
        steps = max(8, int(abs(end-start)*20))
        pts = []
        for i in range(steps+1):
            a = start + (end-start)*(i/steps)
            pts.append(cx + math.cos(a)*radius)
            pts.append(cy + math.sin(a)*radius)
        if len(pts) >= 4:
            self.hud.create_line(*pts, fill=color, width=width, smooth=True)

    def set_hud_state(self, state: str) -> None:
        mapping = {
            "Idle": "idle", "Listening...": "listening",
            "Thinking...": "thinking", "Speaking": "speaking"
        }
        self._hud_state = mapping.get(state, "idle")

    def enqueue_status(self, status: str) -> None:
        self._ui_queue.put(("status", status))

    def enqueue_message(self, speaker: str, message: str) -> None:
        self._ui_queue.put(("message", f"{speaker}: {message}"))

    def _process_ui_queue(self) -> None:
        if not self._running:
            return  # stop loop if shutting down
        while not self._ui_queue.empty():
            action, payload = self._ui_queue.get()
            if action == "status":
                self._set_status(payload)
            elif action == "message":
                self._append_message(payload)
        self._ui_after_id = self.root.after(80, self._process_ui_queue)

    def _set_status(self, status: str) -> None:
        color_map = {
            "Idle": "#7ed957",
            "Listening...": "#f4b942",
            "Thinking...": "#5da9ff",
        }
        self.status_label.configure(
            text=status, text_color=color_map.get(status, "#c9ced6"))
        self.set_hud_state(status)

    def _append_message(self, line: str) -> None:
        pass  # chat removed

    def shutdown(self) -> None:
        """Cleanly cancel all after-callbacks then destroy window."""
        self._running = False
        try:
            self.root.after_cancel(self._ui_after_id)
        except Exception:
            pass
        try:
            self.root.after_cancel(self._hud_after_id)
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def run(self) -> None:
        self.root.mainloop()