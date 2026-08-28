#!/usr/bin/env python3
import sys
import os
import json
import math
import time
import threading
import subprocess
import socket
from pathlib import Path
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gtk, Gdk, GLib, GtkLayerShell
import cairo

SOCKET_PATH = "/tmp/whisper_overlay.sock"
COLORS_JSON_PATH = os.path.expanduser("~/.local/state/quickshell/user/generated/colors.json")
CONFIG_PATH = os.path.expanduser("~/.config/hyprvox/config.toml")

def load_user_config():
    defaults = {
        "audio": {
            "reactive_audio": True,
            "noise_gate": 0.18,
            "mic_sensitivity": 3.0,
        },
        "ui": {
            "font_family": "Google Sans Flex",
            "font_size": 16,
            "transparency": 0.65,
            "position": "bottom",
            "margin": 50,
        }
    }
    if os.path.exists(CONFIG_PATH):
        try:
            import tomllib
            with open(CONFIG_PATH, "rb") as f:
                cfg = tomllib.load(f)
                defaults["audio"].update(cfg.get("audio", {}))
                defaults["ui"].update(cfg.get("ui", {}))
        except Exception:
            pass
    return defaults

user_cfg = load_user_config()

def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 6:
        return tuple(int(hex_str[i:i+2], 16) / 255.0 for i in (0, 2, 4))
    return (0.7, 0.7, 0.8)

def hex_to_rgba_css(hex_str, alpha=1.0):
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 6:
        r, g, b = (int(hex_str[i:i+2], 16) for i in (0, 2, 4))
        return f"rgba({r}, {g}, {b}, {alpha})"
    return f"rgba(18, 19, 24, {alpha})"

def load_quickshell_theme():
    theme = {
        "bg": "#121318",
        "surface": "#1e1f25",
        "primary": "#aec6ff",
        "secondary": "#bfc6dc",
        "tertiary": "#dfbbde",
        "on_surface": "#e2e2e9",
        "on_surface_variant": "#c5c6d0",
        "outline_variant": "#44474f",
    }
    if os.path.exists(COLORS_JSON_PATH):
        try:
            with open(COLORS_JSON_PATH, "r") as f:
                data = json.load(f)
                theme["bg"] = data.get("background", theme["bg"])
                theme["surface"] = data.get("surface_container", theme["surface"])
                theme["primary"] = data.get("primary", theme["primary"])
                theme["secondary"] = data.get("secondary", theme["secondary"])
                theme["tertiary"] = data.get("tertiary", theme["tertiary"])
                theme["on_surface"] = data.get("on_surface", theme["on_surface"])
                theme["on_surface_variant"] = data.get("on_surface_variant", theme["on_surface_variant"])
                theme["outline_variant"] = data.get("outline_variant", theme["outline_variant"])
        except Exception:
            pass
    return theme

theme = load_quickshell_theme()

font_fam = user_cfg["ui"].get("font_family", "Google Sans Flex")
font_sz = user_cfg["ui"].get("font_size", 16)
bg_alpha = user_cfg["ui"].get("transparency", 0.65)

CSS = f"""
window {{
    background-color: transparent;
    background: transparent;
}}

#pill {{
    background-color: {hex_to_rgba_css(theme["bg"], bg_alpha)};
    border: 1px solid {hex_to_rgba_css(theme["outline_variant"], 0.40)};
    border-radius: 30px;
    padding: 12px 24px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35);
}}

#title {{
    font-family: '{font_fam}', 'Inter', 'Segoe UI', sans-serif;
    font-size: {font_sz}px;
    font-weight: 600;
    color: {theme["on_surface"]};
}}

#subtitle {{
    font-family: '{font_fam}', 'Inter', 'Segoe UI', sans-serif;
    font-size: 12px;
    color: {theme["on_surface_variant"]};
    margin-top: 2px;
}}

#dict_btn {{
    font-family: '{font_fam}', 'Inter', sans-serif;
    font-size: 13px;
    font-weight: 600;
    color: {theme["primary"]};
    background-color: {hex_to_rgba_css(theme["surface"], 0.85)};
    border: 1px solid {hex_to_rgba_css(theme["outline_variant"], 0.45)};
    border-radius: 16px;
    padding: 6px 14px;
    margin-left: 8px;
}}

#dict_btn:hover {{
    color: #121318;
    background-color: {theme["primary"]};
    border: 1px solid {theme["primary"]};
}}
""".encode('utf-8')

class VoiceVisualizer(Gtk.DrawingArea):
    def __init__(self, theme_data):
        super().__init__()
        self.set_size_request(38, 28)
        self.connect("draw", self.on_draw)
        self.num_bars = 5
        self.mode = "RECORDING"
        self.start_time = time.time()
        self.rms_level = 0.0
        self.smoothed_rms = 0.0
        
        self.bar_colors = [
            hex_to_rgb(theme_data["primary"]),
            hex_to_rgb(theme_data["tertiary"]),
            hex_to_rgb(theme_data["secondary"]),
            hex_to_rgb(theme_data["primary"]),
            hex_to_rgb(theme_data["tertiary"]),
        ]

    def set_volume_level(self, level):
        self.rms_level = max(0.0, min(1.0, level))

    def on_draw(self, widget, cr):
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()
        t = time.time() - self.start_time

        if self.rms_level > self.smoothed_rms:
            self.smoothed_rms = 0.50 * self.smoothed_rms + 0.50 * self.rms_level
        else:
            self.smoothed_rms = 0.85 * self.smoothed_rms + 0.15 * self.rms_level

        bar_width = 3.5
        spacing = 4.0
        total_bars_width = (self.num_bars * bar_width) + ((self.num_bars - 1) * spacing)
        start_x = (width - total_bars_width) / 2.0
        center_y = height / 2.0

        for i in range(self.num_bars):
            x = start_x + i * (bar_width + spacing)

            if self.mode == "RECORDING":
                base_motion = 0.14 + 0.06 * math.sin(t * 3.0 + i * 1.2)
                voice_boost = self.smoothed_rms * (0.80 + 0.20 * math.sin(t * 6.0 + i * 1.4))
                h_factor = min(1.0, max(0.12, base_motion + voice_boost))
                bar_h = max(5.0, h_factor * (height - 4.0))
            elif self.mode == "TRANSCRIBING":
                wave = math.sin(t * 8.0 - i * 0.9)
                bar_h = 5.0 + 8.0 * (0.5 + 0.5 * wave)
            else:
                bar_h = 5.0

            r, g, b = self.bar_colors[i % len(self.bar_colors)]
            cr.set_source_rgba(r, g, b, 0.95)

            radius = bar_width / 2.0
            y1 = center_y - (bar_h / 2.0)
            y2 = center_y + (bar_h / 2.0)

            cr.new_sub_path()
            cr.arc(x + radius, y1 + radius, radius, math.pi, 0)
            cr.arc(x + radius, y2 - radius, radius, 0, math.pi)
            cr.close_path()
            cr.fill()

        return False

class WhisperOverlay:
    def __init__(self, theme_data, config_data):
        self.theme = theme_data
        self.cfg = config_data
        self.window = Gtk.Window()
        self.window.set_title("Whisper Dictation")
        self.window.set_app_paintable(True)

        screen = Gdk.Screen.get_default()
        visual = screen.get_rgba_visual()
        if visual:
            self.window.set_visual(visual)

        GtkLayerShell.init_for_window(self.window)
        GtkLayerShell.set_namespace(self.window, "whisper-overlay")
        GtkLayerShell.set_layer(self.window, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_keyboard_mode(self.window, GtkLayerShell.KeyboardMode.NONE)

        pos = self.cfg["ui"].get("position", "bottom").lower()
        margin = self.cfg["ui"].get("margin", 50)
        if pos == "top":
            GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.TOP, True)
            GtkLayerShell.set_margin(self.window, GtkLayerShell.Edge.TOP, margin)
        else:
            GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.BOTTOM, True)
            GtkLayerShell.set_margin(self.window, GtkLayerShell.Edge.BOTTOM, margin)

        self.window.connect("draw", self.on_window_draw)

        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.event_box = Gtk.EventBox()
        self.event_box.set_visible_window(False)
        self.event_box.connect("button-press-event", self.on_pill_clicked)

        self.box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        self.box.set_name("pill")

        self.visualizer = VoiceVisualizer(self.theme)
        self.visualizer.set_valign(Gtk.Align.CENTER)

        self.text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.text_box.set_valign(Gtk.Align.CENTER)
        
        self.title_label = Gtk.Label()
        self.title_label.set_name("title")
        self.title_label.set_xalign(0.0)
        self.title_label.set_text("Listening...")

        self.sub_label = Gtk.Label()
        self.sub_label.set_name("subtitle")
        self.sub_label.set_xalign(0.0)
        self.sub_label.set_text("Speak now • Press Super+H to finish")

        self.text_box.pack_start(self.title_label, False, False, 0)
        self.text_box.pack_start(self.sub_label, False, False, 0)

        # Distinguishable Dictionary Button
        self.dict_btn = Gtk.Button(label="✎ Dict")
        self.dict_btn.set_name("dict_btn")
        self.dict_btn.set_tooltip_text("Open Vocabulary & Technical Dictionary Manager")
        self.dict_btn.set_valign(Gtk.Align.CENTER)
        self.dict_btn.connect("clicked", self.on_open_dict_editor)

        self.box.pack_start(self.visualizer, False, False, 0)
        self.box.pack_start(self.text_box, True, True, 0)
        self.box.pack_start(self.dict_btn, False, False, 0)

        self.event_box.add(self.box)
        self.window.add(self.event_box)
        self.window.connect("destroy", Gtk.main_quit)

        self.anim_timer = GLib.timeout_add(25, self.refresh_animation)
        self.mic_thread_running = False

        self.base_noise_gate = float(self.cfg["audio"].get("noise_gate", 0.18))
        self.sensitivity = float(self.cfg["audio"].get("mic_sensitivity", 3.0))
        self.adaptive_floor = self.base_noise_gate

        if self.cfg["audio"].get("reactive_audio", True):
            self.start_mic_listener()

    def on_pill_clicked(self, widget, event):
        if event.button == 3:
            self.on_open_dict_editor(None)
            return True
        return False

    def on_open_dict_editor(self, widget):
        self.stop_mic_listener()

        # Cancel active recording process and remove audio to prevent any transcription
        pid_file = "/tmp/whisper_dictate.pid"
        audio_file = "/tmp/whisper_dictate.wav"
        if os.path.exists(pid_file):
            try:
                with open(pid_file, "r") as f:
                    rec_pid = int(f.read().strip())
                os.kill(rec_pid, 9)
            except Exception:
                pass
            try:
                os.remove(pid_file)
            except OSError:
                pass

        if os.path.exists(audio_file):
            try:
                os.remove(audio_file)
            except OSError:
                pass

        # Launch Dictionary Editor GUI
        dict_script = Path(__file__).resolve().parent / "dict_editor.py"
        venv_python = Path(__file__).resolve().parent / "venv" / "bin" / "python"
        py_bin = str(venv_python) if venv_python.exists() else "python3"
        subprocess.Popen([py_bin, str(dict_script)])
        self.close_overlay()

    def start_mic_listener(self):
        self.mic_thread_running = True
        t = threading.Thread(target=self._mic_worker, daemon=True)
        t.start()

    def _mic_worker(self):
        try:
            import numpy as np
            import sounddevice as sd

            def audio_cb(indata, frames, time_info, status):
                if not self.mic_thread_running:
                    return
                rms = float(np.sqrt(np.mean(indata**2)))
                if rms < self.adaptive_floor:
                    self.adaptive_floor = 0.85 * self.adaptive_floor + 0.15 * rms
                else:
                    self.adaptive_floor = 0.998 * self.adaptive_floor + 0.002 * rms

                effective_floor = max(self.base_noise_gate, self.adaptive_floor * 1.15)
                diff = max(0.0, rms - effective_floor)
                norm_level = min(1.0, diff * self.sensitivity)
                GLib.idle_add(self.visualizer.set_volume_level, norm_level)

            with sd.InputStream(callback=audio_cb, channels=1, samplerate=16000, blocksize=512):
                while self.mic_thread_running:
                    time.sleep(0.05)
        except Exception:
            pass

    def stop_mic_listener(self):
        self.mic_thread_running = False
        GLib.idle_add(self.visualizer.set_volume_level, 0.0)

    def on_window_draw(self, widget, cr):
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()
        return False

    def refresh_animation(self):
        self.visualizer.queue_draw()
        return True

    def set_recording(self):
        self.visualizer.mode = "RECORDING"
        self.title_label.set_text("Listening...")
        self.sub_label.set_text("Speak now • Press Super+H to finish")
        self.sub_label.set_visible(True)
        self.dict_btn.set_visible(True)

    def set_transcribing(self):
        self.stop_mic_listener()
        self.visualizer.mode = "TRANSCRIBING"
        self.title_label.set_text("Transcribing...")
        self.sub_label.set_visible(False)
        self.dict_btn.set_visible(False)

    def set_done(self, text=""):
        self.stop_mic_listener()
        self.visualizer.mode = "DONE"
        self.title_label.set_text("Dictated")
        self.dict_btn.set_visible(False)
        display_text = text if len(text) <= 55 else text[:52] + "..."
        if display_text:
            self.sub_label.set_text(f'"{display_text}"')
            self.sub_label.set_visible(True)
        else:
            self.sub_label.set_visible(False)
        GLib.timeout_add(1300, self.close_overlay)

    def close_overlay(self):
        self.stop_mic_listener()
        Gtk.main_quit()
        return False

    def show(self):
        self.window.show_all()

def socket_listener(overlay):
    if os.path.exists(SOCKET_PATH):
        try:
            os.remove(SOCKET_PATH)
        except OSError:
            pass

    server = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    server.bind(SOCKET_PATH)

    while True:
        try:
            data, _ = server.recvfrom(1024)
            msg = data.decode("utf-8").strip()
            if msg == "TRANSCRIBING":
                GLib.idle_add(overlay.set_transcribing)
            elif msg.startswith("DONE:"):
                text = msg[5:]
                GLib.idle_add(overlay.set_done, text)
            elif msg == "QUIT":
                GLib.idle_add(overlay.close_overlay)
                break
        except Exception:
            break

def main():
    current_theme = load_quickshell_theme()
    overlay = WhisperOverlay(current_theme, user_cfg)
    if len(sys.argv) > 1 and sys.argv[1] == "--transcribing":
        overlay.set_transcribing()
    else:
        overlay.set_recording()

    overlay.show()

    t = threading.Thread(target=socket_listener, args=(overlay,), daemon=True)
    t.start()

    Gtk.main()

    if os.path.exists(SOCKET_PATH):
        try:
            os.remove(SOCKET_PATH)
        except OSError:
            pass

if __name__ == "__main__":
    main()
