#!/usr/bin/env python3
import sys
import os
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

CSS = b"""
window {
    background: transparent;
}

#pill {
    background-color: rgba(16, 18, 26, 0.94);
    border: 1.5px solid rgba(255, 255, 255, 0.16);
    border-radius: 32px;
    padding: 12px 28px;
    box-shadow: 0 10px 36px rgba(0, 0, 0, 0.6);
}

#title {
    font-family: 'Google Sans Flex', 'Inter', 'Segoe UI', sans-serif;
    font-size: 14px;
    font-weight: 600;
    color: #e3e2e9;
}

#subtitle {
    font-family: 'Google Sans Flex', 'Inter', 'Segoe UI', sans-serif;
    font-size: 12px;
    color: #9398aa;
    margin-top: 2px;
}
"""

class VoiceVisualizer(Gtk.DrawingArea):
    def __init__(self):
        super().__init__()
        self.set_size_request(38, 28)
        self.connect("draw", self.on_draw)
        self.num_bars = 5
        self.mode = "RECORDING"  # RECORDING, TRANSCRIBING, DONE
        self.start_time = time.time()
        self.bar_colors = [
            (0.38, 0.69, 0.98),  # Cyan-blue
            (0.53, 0.44, 0.96),  # Purple
            (0.95, 0.40, 0.55),  # Coral-pink
            (0.98, 0.68, 0.35),  # Amber
            (0.30, 0.85, 0.60),  # Emerald green
        ]

    def on_draw(self, widget, cr):
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()
        t = time.time() - self.start_time

        bar_width = 3.5
        spacing = 4.0
        total_bars_width = (self.num_bars * bar_width) + ((self.num_bars - 1) * spacing)
        start_x = (width - total_bars_width) / 2.0
        center_y = height / 2.0

        for i in range(self.num_bars):
            x = start_x + i * (bar_width + spacing)

            if self.mode == "RECORDING":
                # Multi-harmonic organic voice bounce
                freq1 = 4.5 + (i * 0.8)
                freq2 = 2.2 - (i * 0.3)
                h_factor = 0.35 + 0.35 * math.sin(t * freq1 + i * 1.2) + 0.25 * math.cos(t * freq2 + i * 0.9)
                bar_h = max(6.0, h_factor * (height - 6.0))
            elif self.mode == "TRANSCRIBING":
                # Smooth traveling sine wave shimmer
                wave = math.sin(t * 8.0 - i * 0.9)
                bar_h = 6.0 + 8.0 * (0.5 + 0.5 * wave)
            else:  # DONE
                bar_h = 5.0

            r, g, b = self.bar_colors[i % len(self.bar_colors)]
            cr.set_source_rgba(r, g, b, 0.95)

            # Draw smooth rounded pill bar
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
    def __init__(self):
        self.window = Gtk.Window()
        self.window.set_title("Whisper Dictation")
        self.window.set_app_paintable(True)

        # Init LayerShell
        GtkLayerShell.init_for_window(self.window)
        GtkLayerShell.set_layer(self.window, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_keyboard_mode(self.window, GtkLayerShell.KeyboardMode.NONE)
        GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.BOTTOM, True)
        GtkLayerShell.set_margin(self.window, GtkLayerShell.Edge.BOTTOM, 55)

        # Apply CSS
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # Layout Container
        self.box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        self.box.set_name("pill")

        # Animated Voice Waveform Bars
        self.visualizer = VoiceVisualizer()

        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        
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

        # 40 FPS animation refresh
        self.anim_timer = GLib.timeout_add(25, self.refresh_animation)

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
    overlay = WhisperOverlay()
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
