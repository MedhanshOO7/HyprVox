#!/usr/bin/env python3
import sys
import os
import json
import math
import time
import threading
import socket
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gtk, Gdk, GLib, GtkLayerShell
import cairo

SOCKET_PATH = "/tmp/whisper_overlay.sock"
COLORS_JSON_PATH = os.path.expanduser("~/.local/state/quickshell/user/generated/colors.json")

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

# Translucent CSS with true alpha matching top bar (0.65 background, 0.40 border)
CSS = f"""
window {{
    background-color: transparent;
    background: transparent;
}}

#pill {{
    background-color: {hex_to_rgba_css(theme["bg"], 0.65)};
    border: 1px solid {hex_to_rgba_css(theme["outline_variant"], 0.40)};
    border-radius: 28px;
    padding: 10px 24px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35);
}}

#title {{
    font-family: 'Google Sans Flex', 'Inter', 'Segoe UI', sans-serif;
    font-size: 13px;
    font-weight: 600;
    color: {theme["on_surface"]};
}}

#subtitle {{
    font-family: 'Google Sans Flex', 'Inter', 'Segoe UI', sans-serif;
    font-size: 11px;
    color: {theme["on_surface_variant"]};
    margin-top: 1px;
}}
""".encode('utf-8')

class VoiceVisualizer(Gtk.DrawingArea):
    def __init__(self, theme_data):
        super().__init__()
        self.set_size_request(34, 24)
        self.connect("draw", self.on_draw)
        self.num_bars = 5
        self.mode = "RECORDING"
        self.start_time = time.time()
        
        self.bar_colors = [
            hex_to_rgb(theme_data["primary"]),
            hex_to_rgb(theme_data["tertiary"]),
            hex_to_rgb(theme_data["secondary"]),
            hex_to_rgb(theme_data["primary"]),
            hex_to_rgb(theme_data["tertiary"]),
        ]

    def on_draw(self, widget, cr):
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()
        t = time.time() - self.start_time

        bar_width = 3.0
        spacing = 3.5
        total_bars_width = (self.num_bars * bar_width) + ((self.num_bars - 1) * spacing)
        start_x = (width - total_bars_width) / 2.0
        center_y = height / 2.0

        for i in range(self.num_bars):
            x = start_x + i * (bar_width + spacing)

            if self.mode == "RECORDING":
                freq1 = 4.5 + (i * 0.8)
                freq2 = 2.2 - (i * 0.3)
                h_factor = 0.35 + 0.35 * math.sin(t * freq1 + i * 1.2) + 0.25 * math.cos(t * freq2 + i * 0.9)
                bar_h = max(5.0, h_factor * (height - 4.0))
            elif self.mode == "TRANSCRIBING":
                wave = math.sin(t * 8.0 - i * 0.9)
                bar_h = 5.0 + 7.0 * (0.5 + 0.5 * wave)
            else:
                bar_h = 4.0

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
    def __init__(self, theme_data):
        self.theme = theme_data
        self.window = Gtk.Window()
        self.window.set_title("Whisper Dictation")
        self.window.set_app_paintable(True)

        # Set RGBA Visual for true Wayland alpha transparency
        screen = Gdk.Screen.get_default()
        visual = screen.get_rgba_visual()
        if visual:
            self.window.set_visual(visual)

        # Init LayerShell with custom namespace for Hyprland blur
        GtkLayerShell.init_for_window(self.window)
        GtkLayerShell.set_namespace(self.window, "whisper-overlay")
        GtkLayerShell.set_layer(self.window, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_keyboard_mode(self.window, GtkLayerShell.KeyboardMode.NONE)
        GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.BOTTOM, True)
        GtkLayerShell.set_margin(self.window, GtkLayerShell.Edge.BOTTOM, 50)

        # Connect draw signal to ensure window surface is cleared transparently
        self.window.connect("draw", self.on_window_draw)

        # Apply CSS
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # Layout Container
        self.box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.box.set_name("pill")

        self.visualizer = VoiceVisualizer(self.theme)

        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        
        self.title_label = Gtk.Label()
        self.title_label.set_name("title")
        self.title_label.set_xalign(0.0)
        self.title_label.set_text("Listening...")

        self.sub_label = Gtk.Label()
        self.sub_label.set_name("subtitle")
        self.sub_label.set_xalign(0.0)
        self.sub_label.set_text("Speak now • Press Super+H to finish")

        text_box.pack_start(self.title_label, False, False, 0)
        text_box.pack_start(self.sub_label, False, False, 0)

        self.box.pack_start(self.visualizer, False, False, 0)
        self.box.pack_start(text_box, True, True, 0)

        self.window.add(self.box)
        self.window.connect("destroy", Gtk.main_quit)

        self.anim_timer = GLib.timeout_add(25, self.refresh_animation)

    def on_window_draw(self, widget, cr):
        # Clear window surface to fully transparent
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

    def set_transcribing(self):
        self.visualizer.mode = "TRANSCRIBING"
        self.title_label.set_text("Transcribing...")
        self.sub_label.set_text("Processing on RTX 4050 CUDA...")

    def set_done(self, text=""):
        self.visualizer.mode = "DONE"
        self.title_label.set_text("Dictated")
        display_text = text if len(text) <= 55 else text[:52] + "..."
        self.sub_label.set_text(f'"{display_text}"' if display_text else "Done")
        GLib.timeout_add(1300, self.close_overlay)

    def close_overlay(self):
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
    overlay = WhisperOverlay(current_theme)
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
