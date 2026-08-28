#!/usr/bin/env python3
import sys
import os
import threading
import socket
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gtk, Gdk, GLib, GtkLayerShell

SOCKET_PATH = "/tmp/whisper_overlay.sock"

CSS = b"""
window {
    background: transparent;
}

#pill {
    background-color: rgba(18, 20, 29, 0.92);
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 28px;
    padding: 10px 24px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.45);
}

#icon {
    font-size: 20px;
    margin-right: 12px;
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
    color: #9094a6;
    margin-top: 2px;
}

#status_dot {
    background-color: #ff5555;
    border-radius: 5px;
    min-width: 10px;
    min-height: 10px;
    margin-right: 10px;
}

.transcribing {
    color: #b3c5ff;
}

.done {
    color: #50fa7b;
}
"""

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
        GtkLayerShell.set_margin(self.window, GtkLayerShell.Edge.BOTTOM, 60)

        # Apply CSS
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # Layout Container
        self.box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.box.set_name("pill")

        self.icon_label = Gtk.Label()
        self.icon_label.set_name("icon")
        self.icon_label.set_text("🎙️")

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

        self.box.pack_start(self.icon_label, False, False, 0)
        self.box.pack_start(text_box, True, True, 0)

        self.window.add(self.box)
        self.window.connect("destroy", Gtk.main_quit)

        self.pulse_state = 0
        self.timer_id = GLib.timeout_add(400, self.pulse_animation)

    def pulse_animation(self):
        self.pulse_state = (self.pulse_state + 1) % 2
        if hasattr(self, 'current_mode') and self.current_mode == "RECORDING":
            dots = "." * ((self.pulse_state % 3) + 1)
            # Subtle pulse
            self.icon_label.set_text("🔴" if self.pulse_state else "🎙️")
        return True

    def set_recording(self):
        self.current_mode = "RECORDING"
        self.icon_label.set_text("🎙️")
        self.title_label.set_text("Listening...")
        self.sub_label.set_text("Speak now • Press Super+H to finish")

    def set_transcribing(self):
        self.current_mode = "TRANSCRIBING"
        self.icon_label.set_text("⚡")
        self.title_label.set_text("Transcribing...")
        self.sub_label.set_text("Processing on RTX 4050 CUDA...")

    def set_done(self, text=""):
        self.current_mode = "DONE"
        self.icon_label.set_text("✅")
        self.title_label.set_text("Dictated")
        display_text = text if len(text) <= 50 else text[:47] + "..."
        self.sub_label.set_text(display_text if display_text else "Done")
        GLib.timeout_add(1200, self.close_overlay)

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

    # Start socket listener thread
    t = threading.Thread(target=socket_listener, args=(overlay,), daemon=True)
    t.start()

    Gtk.main()

    # Cleanup socket
    if os.path.exists(SOCKET_PATH):
        try:
            os.remove(SOCKET_PATH)
        except OSError:
            pass

if __name__ == "__main__":
    main()
