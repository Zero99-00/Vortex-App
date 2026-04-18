import os
import time
import json
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk
from PIL import Image, ImageTk

# Optional Arduino interface
try:
    from pyfirmata2 import Arduino
except Exception:
    Arduino = None

# ------------------------- Config
WINDOW_W, WINDOW_H = 1300, 700
LEFT_W = 200
RIGHT_W = 200
CENTER_W = WINDOW_W - LEFT_W - RIGHT_W
TOP_H = 60

SERVO_PINS = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11]

WRITE_THRESHOLD = 0.5        
HARDWARE_WRITE_INTERVAL = 0.05  

DEFAULT_ANGLES = {
    1: 30.0, 2: 90.0, 3: 10.0, 4: 90.0, 5: 90.0,
    6: 90.0, 7: 90.0, 8: 170.0, 9: 90.0, 10: 160.0,
}

DEFAULT_MARK_DUR = 0.6  

# FIXED: Hardcoded save directory
SAVE_DIR = Path(r"C:\Users\c\Desktop\Vortex\motion_movment_saved")

def now():
    return time.time()

class ServoPanel(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")

        self.container = ctk.CTkFrame(self, width=WINDOW_W, height=WINDOW_H, fg_color="transparent")
        self.container.pack(expand=True, fill="both")

        self.board = None
        self.servos: Dict[int, object] = {}
        self.has_hw = False

        self.targets = {i: float(DEFAULT_ANGLES.get(i, 90.0)) for i in range(1, 11)}
        self.currents = {i: float(DEFAULT_ANGLES.get(i, 90.0)) for i in range(1, 11)}
        self.velocities = {i: 0.0 for i in range(1, 11)}

        self.smooth_speed = 0.8
        self.acceleration = 2.0

        self.recording = False
        self.current_record: List[Dict[str, Any]] = []
        self.record_start = 0.0

        self.imported_recordings: Dict[str, List[Dict[str, Any]]] = {}

        self.playing = False            
        self._playback_thread: Optional[threading.Thread] = None
        self._playback_name: Optional[str] = None
        self._playback_index: int = 0
        self._playback_remaining: float = 0.0  
        self._playback_data: Optional[List[Dict[str, Any]]] = None

        self.last_written: Dict[int, float] = {i: -999.0 for i in range(1, 11)}
        self.last_hw_write: float = 0.0

        self._build_ui_place_style()

        self._running = True
        
        # Load existing files right away when opening the window
        self._auto_load_saved_folder()
        
        self._main_loop()

    def _build_ui_place_style(self):
        PANEL_W = 980
        
        # 1. Top Control Bar 
        top_frame = ctk.CTkFrame(self.container, width=940, height=50)
        top_frame.place(x=20, y=10)

        self.com_label = ctk.CTkLabel(top_frame, text="COM:", width=30, height=30)
        self.com_label.place(x=20, y=10)
        self.port_box = ctk.CTkComboBox(top_frame, values=["Select COM"], width=130, height=30)
        self.port_box.set("Select COM")
        self.port_box.place(x=60, y=10)

        self.connect_btn = ctk.CTkButton(top_frame, text="Connect", width=90, height=30, command=self._connect_arduino)
        self.connect_btn.place(x=200, y=10)
        self.refresh_btn = ctk.CTkButton(top_frame, text='Refresh', width=90, height=30, command=self._refresh_ports)
        self.refresh_btn.place(x=300, y=10)
        self.disconnect_btn = ctk.CTkButton(top_frame, text='Disconnect', width=90, height=30, command=self.disconnect_arduino)
        self.disconnect_btn.place(x=400, y=10)

        self.status_lbl = ctk.CTkLabel(top_frame, text="Status: Disconnected", text_color="red", width=180, height=30)
        self.status_lbl.place(x=500, y=10)

        # 2. Left Sliders (S4, S3, S2, S1)
        left_start_y = 80
        slider_h = 90
        gap = 10
        for idx, sid in enumerate([4,3,2,1]):
            y = left_start_y + idx*(slider_h + gap)
            lbl = ctk.CTkLabel(self.container, text=f"S{sid}", width=30, height=20, font=("Arial", 14, "bold"))
            lbl.place(x=20, y=y+35)
            sl = ctk.CTkSlider(self.container, from_=0, to=180, orientation="vertical", width=20, height=slider_h, command=lambda v, s=sid: self._on_slider(s, float(v)))
            sl.set(DEFAULT_ANGLES[sid])
            sl.place(x=60, y=y)
            setattr(self, f"slider_{sid}", sl)

        # 3. Right Sliders (S7, S8, S9, S10)
        for idx, sid in enumerate([7,8,9,10]):
            y = left_start_y + idx*(slider_h + gap)
            lbl = ctk.CTkLabel(self.container, text=f"S{sid}", width=30, height=20, font=("Arial", 14, "bold"))
            lbl.place(x=920, y=y+35)
            sl = ctk.CTkSlider(self.container, from_=0, to=180, orientation="vertical", width=20, height=slider_h, command=lambda v, s=sid: self._on_slider(s, float(v)))
            sl.set(DEFAULT_ANGLES[sid])
            sl.place(x=880, y=y)
            setattr(self, f"slider_{sid}", sl)

        # 4. Center Robot Image Frame
        frame_w = 600
        frame_h = 390
        frame_x = (PANEL_W - frame_w) // 2  
        
        self.main_frame = ctk.CTkFrame(self.container, width=frame_w, height=frame_h, fg_color="#1e1e1e", corner_radius=15)
        self.main_frame.place(x=frame_x, y=70)
        self.main_frame.pack_propagate(False)
        
        # Load Robot Image safely
        try:
            from models.logic_units.absolute_path import get_asset_path
            img_path = get_asset_path('robot.png')
            if os.path.exists(img_path):
                img = Image.open(img_path).convert("RGBA")
                img.thumbnail((500, 360), Image.LANCZOS)
                self.photo = ImageTk.PhotoImage(img)
                self.img_label = ctk.CTkLabel(self.main_frame, image=self.photo, text="")
                self.img_label.image = self.photo
                self.img_label.pack(expand=True)
            else:
                raise FileNotFoundError
        except Exception:
            self.img_label = ctk.CTkLabel(self.main_frame, text="🤖\nRobot Image Not Found", font=("Arial", 24), text_color="gray")
            self.img_label.pack(expand=True)

        # Robot Image Angle Counters
        self.s_counters = {}
        coords = {
            1: (120, 220), 2: (120, 160), 3: (140, 90), 4: (190, 50),
            5: (260, 70),  6: (340, 70),  7: (410, 50), 8: (460, 90),
            9: (480, 160), 10:(480, 220),
        }
        for sid, (x,y) in coords.items():
            font = ("Arial", 12, "bold") if sid not in (5,6) else ("Arial", 10, "bold")
            w = 35 if sid not in (5,6) else 25
            h = 25 if sid not in (5,6) else 15
            lbl = ctk.CTkLabel(self.main_frame, text="90°", font=font, text_color="white", fg_color="#3E3E3E", corner_radius=6, width=w, height=h)
            lbl.place(x=x, y=y)
            self.s_counters[sid] = lbl

        # 5. Bottom Sliders (Servo 5 and 6)
        s5_lbl = ctk.CTkLabel(self.container, text="Servo 5", width=60, height=18, font=("Arial", 14, "bold"))
        s5_lbl.place(x=frame_x + 30, y=475)
        s5 = ctk.CTkSlider(self.container, from_=0, to=180, width=180, height=20, command=lambda v: self._on_slider(5, float(v)))
        s5.set(DEFAULT_ANGLES.get(5, 90))
        s5.place(x=frame_x + 100, y=475)
        self.slider_5 = s5

        s6_lbl = ctk.CTkLabel(self.container, text="Servo 6", width=60, height=18, font=("Arial", 14, "bold"))
        s6_lbl.place(x=frame_x + 310, y=475)
        s6 = ctk.CTkSlider(self.container, from_=0, to=180, width=180, height=20, command=lambda v: self._on_slider(6, float(v)))
        s6.set(DEFAULT_ANGLES.get(6, 90))
        s6.place(x=frame_x + 380, y=475)
        self.slider_6 = s6

        # 6. Addons (Bottom Controls Dashboard)
        addons_w = 940
        addons_x = 20
        addons = ctk.CTkFrame(self.container, width=addons_w, height=105, fg_color="#1e1e1e", corner_radius=15)
        addons.place(x=addons_x, y=515)
        
        # --- Column 1: Speed & Acceleration ---
        speed_label = ctk.CTkLabel(addons, text='Motion Speed')
        speed_label.place(x=15, y=15)
        self.speed_slider = ctk.CTkSlider(addons, from_=0.05, to=2.0, width=110, command=self._on_speed)
        self.speed_slider.set(self.smooth_speed)
        self.speed_slider.place(x=105, y=20)

        accel_label = ctk.CTkLabel(addons, text='Acceleration')
        accel_label.place(x=15, y=60)
        self.accel_slider = ctk.CTkSlider(addons, from_=0.5, to=4.0, width=110, command=self._on_accel)
        self.accel_slider.set(self.acceleration)
        self.accel_slider.place(x=105, y=65)

        # --- Column 2: Recording Controls ---
        self.record_name_entry = ctk.CTkEntry(addons, width=110, placeholder_text="Optional Name")
        self.record_name_entry.place(x=240, y=15)

        self.record_btn = ctk.CTkButton(addons, text='● Start', fg_color='#e74c3c', width=80, command=self.toggle_recording)
        self.record_btn.place(x=360, y=15)

        self.mark_btn = ctk.CTkButton(addons, text='Mark Pose', width=100, command=self.mark_snapshot)
        self.mark_btn.place(x=240, y=60)

        self.time_mark_btk = ctk.CTkEntry(addons, width=80)
        self.time_mark_btk.insert(0, str(DEFAULT_MARK_DUR))
        self.time_mark_btk.place(x=360, y=60)
        
        # --- Column 3: Playback Listbox ---
        self.lb = tk.Listbox(addons, bg="#2b2b2b", fg="white", selectbackground="#2b5b84", width=22, height=4, borderwidth=0)
        self.lb.place(x=470, y=15)

        # --- Column 4: Play/Stop Buttons ---
        self.play_import_btn = ctk.CTkButton(addons, text='▶ Play', fg_color='#2ecc71', width=80, command=self.play_selected_import)
        self.play_import_btn.place(x=630, y=15)
        
        self.stop_play_btn = ctk.CTkButton(addons, text='■ Stop', fg_color='#f39c12', width=80, command=self.pause_playback)
        self.stop_play_btn.place(x=630, y=60)

        # --- Column 5: Reset & Delete ---
        self.reset_btn = ctk.CTkButton(addons, text='Reset All', width=120, height=30, fg_color="#34495e", command=self.reset_all)
        self.reset_btn.place(x=760, y=15)

        self.delete_btn = ctk.CTkButton(addons, text='Delete Rec', width=120, height=30, fg_color="#c0392b", hover_color="#922b21", command=self.delete_selected_import)
        self.delete_btn.place(x=760, y=60)

    def _on_slider(self, sid: int, v: float):
        val = max(0.0, min(180.0, float(v)))
        self.targets[sid] = val

        if sid in self.s_counters:
            try:
                self.s_counters[sid].configure(text=f"{int(round(val))}°")
            except Exception:
                pass

        if self.has_hw:
            nowt = now()
            if (nowt - self.last_hw_write) >= HARDWARE_WRITE_INTERVAL or abs(val - self.last_written.get(sid, -999.0)) >= WRITE_THRESHOLD:
                try:
                    pin = self.servos.get(sid)
                    if pin is not None:
                        pin.write(float(val))
                        self.last_written[sid] = float(val)
                        self.last_hw_write = nowt
                except Exception as e:
                    print(f"[HW WRITE ERROR] servo {sid}: {e}")

    def mark_snapshot(self):
        if not self.recording:
            messagebox.showwarning("Not recording", "Press Start recording first.")
            return

        raw = self.time_mark_btk.get().strip()
        try:
            dur = float(raw)
            if dur <= 0:
                raise ValueError("duration must be > 0")
        except Exception:
            messagebox.showerror("Invalid duration", "Enter a positive number for duration (seconds).")
            return

        t_rel = round(now() - self.record_start, 3)
        snap = {str(i): float(self.targets[i]) for i in range(1,11)}
        entry = {"t": t_rel, "pose": snap, "dur": float(dur)}
        self.current_record.append(entry)

        try:
            orig = self.mark_btn.cget("text")
            self.mark_btn.configure(text="Marked ✓")
            self.after(600, lambda: self.mark_btn.configure(text=orig))
        except Exception:
            pass

    def _on_speed(self, v):
        self.smooth_speed = float(v)

    def _on_accel(self, v):
        self.acceleration = float(v)

    def toggle_recording(self):
        if not self.recording:
            self.start_recording()
        else:
            self.stop_recording_and_export()

    def start_recording(self):
        self.recording = True
        self.current_record = []
        self.record_start = now()
        self.record_btn.configure(text='⏹ Save', fg_color='#f39c12')

    def stop_recording_and_export(self):
        if not self.recording:
            return

        self.recording = False
        self.record_btn.configure(text='● Start', fg_color='#e74c3c')

        date_str = datetime.now().strftime("%Y_%m_%d___%H_%M_%S")
        base_name = self.record_name_entry.get().strip()

        if not base_name:
            final_name = f"rec_{date_str}"
        else:
            final_name = f"{base_name}_{date_str}"

        try:
            SAVE_DIR.mkdir(parents=True, exist_ok=True)
            save_path = SAVE_DIR / f"{final_name}.json"
            
            data = {final_name: self.current_record}
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            self.record_name_entry.delete(0, "end")
            
            # Immediately refresh list after saving!
            self._auto_load_saved_folder()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save to {SAVE_DIR}:\n{e}")

    def _auto_load_saved_folder(self):
        # Create directory if it doesn't exist yet to prevent errors
        SAVE_DIR.mkdir(parents=True, exist_ok=True)
            
        self.imported_recordings.clear()
        self.lb.delete(0, tk.END)
        
        # Look for all json files in the dir
        for full_path in SAVE_DIR.glob("*.json"):
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                if isinstance(data, dict):
                    for key, value in data.items():
                        normalized = self._normalize_import_value(value)
                        # We now accept the normalized array even if it's empty
                        if normalized is not None:
                            self.imported_recordings[key] = normalized
                            self.lb.insert(tk.END, key)
            except Exception as e:
                print(f"Skipping {full_path.name}: {e}")
                continue

    def _normalize_import_value(self, value: Any) -> Optional[List[Dict[str, Any]]]:
        # RELAXED VALIDATION: Allow saving/loading even if the list is empty 
        # (e.g. started record and immediately stopped without marking poses)
        try:
            if isinstance(value, list):
                out = []
                for entry in value:
                    if isinstance(entry, dict) and 'pose' in entry:
                        dur = float(entry.get('dur', DEFAULT_MARK_DUR))
                        pose = entry.get('pose')
                        t = float(entry.get('t', 0.0))
                        out.append({"t": t, "pose": pose, "dur": dur})
                return out 
            return None
        except Exception:
            return None

    def play_selected_import(self):
        sel = self.lb.curselection()
        if not sel:
            messagebox.showwarning("Select", "Select a recording from the list")
            return
        name = self.lb.get(sel[0])
        data = self.imported_recordings.get(name)
        
        if not data:
            messagebox.showinfo("Empty", "This recording has no saved poses.")
            return

        if self._playback_name and self._playback_name != name:
            self.playing = False
            time.sleep(0.02)

        self._playback_name = name
        self._playback_data = data

        if self.playing:
            return

        if getattr(self, "_playback_index", 0) is None or getattr(self, "_playback_index", 0) < 0:
            self._playback_index = 0
            self._playback_remaining = 0.0

        self.playing = True

        def runner():
            idx = getattr(self, "_playback_index", 0)
            data_list = self._playback_data or []
            
            while idx < len(data_list) and self.playing:
                entry = data_list[idx]
                target_pose = entry.get("pose")  
                dur = float(entry.get("dur", DEFAULT_MARK_DUR))
                remaining = getattr(self, "_playback_remaining", 0.0) or dur

                start_pose = {str(i): float(self.targets.get(i, self.currents.get(i, 90.0))) for i in range(1,11)}
                end_pose = {str(i): float(target_pose.get(str(i), start_pose[str(i)])) for i in range(1,11)}

                start_time = now()
                elapsed = 0.0
                step = 0.02
                
                while elapsed < remaining and self.playing:
                    frac = min(1.0, elapsed / remaining) if remaining > 0 else 1.0
                    for sid_str in end_pose.keys():
                        sid = int(sid_str)
                        s = start_pose[sid_str]
                        e = end_pose[sid_str]
                        interp = s + (e - s) * frac
                        self.targets[sid] = interp
                        
                        self.after(0, self._update_slider_ui, sid, interp)
                        
                    time.sleep(step)
                    elapsed = now() - start_time
                    
                if not self.playing:
                    progressed = elapsed
                    rem = max(0.0, remaining - progressed)
                    self._playback_index = idx
                    self._playback_remaining = rem
                    break
                    
                for sid_str, angle in end_pose.items():
                    sid = int(sid_str)
                    self.targets[sid] = float(angle)
                    self.after(0, self._update_slider_ui, sid, float(angle))
                    
                idx += 1
                self._playback_remaining = 0.0
                self._playback_index = idx

            if idx >= len(data_list):
                self.playing = False
                self._playback_index = 0
                self._playback_remaining = 0.0
                self._playback_name = None
                self._playback_data = None

        self._playback_thread = threading.Thread(target=runner, daemon=True)
        self._playback_thread.start()

    def _update_slider_ui(self, sid, val):
        slider = getattr(self, f"slider_{sid}", None)
        if slider:
            slider.set(val)
        if sid in self.s_counters:
            try:
                self.s_counters[sid].configure(text=f"{int(round(val))}°")
            except Exception:
                pass

    def pause_playback(self):
        if not self.playing:
            return
        self.playing = False

    def delete_selected_import(self):
        sel = self.lb.curselection()
        if not sel:
            messagebox.showwarning("Select", "Select a recording to delete")
            return
            
        name = self.lb.get(sel[0])
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete '{name}'?"):
            try:
                file_path = SAVE_DIR / f"{name}.json"
                if file_path.exists():
                    os.remove(file_path)
                # Immediately refresh list after deleting!
                self._auto_load_saved_folder()  
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete:\n{e}")

    def _refresh_ports(self):
        self.port_box.configure(values=["COM3","COM4","COM5"])
        self.port_box.set("COM3")

    def _connect_arduino(self):
        port = self.port_box.get()
        if not port or 'Select' in port:
            self.status_lbl.configure(text='Select COM port', text_color='orange')
            return

        if Arduino is None:
            messagebox.showwarning('Library missing', 'pyfirmata2 not installed. Run:\n\npip install pyfirmata2 pyserial')
            self.has_hw = False
            self.status_lbl.configure(text='Demo mode (no HW)', text_color='orange')
            return

        try:
            import serial.tools.list_ports
            available = [p.device for p in serial.tools.list_ports.comports()]
        except Exception:
            available = []

        if port not in available:
            msg = f"Selected port '{port}' not found.\nAvailable: {available}" if available else "No COM ports detected."
            messagebox.showerror('Port not found', msg)
            self.status_lbl.configure(text='Port not found', text_color='red')

    def disconnect_arduino(self):
        self.has_hw = False
        self.status_lbl.configure(text="Status: Disconnected", text_color="red")
        print("[HW] Arduino Disconnected")

    def reset_all(self):
        for sid in range(1, 11):
            val = float(DEFAULT_ANGLES.get(sid, 90.0))
            self.targets[sid] = val
            self._update_slider_ui(sid, val)

    def _main_loop(self):
        if not self._running:
            return
        self.after(50, self._main_loop)