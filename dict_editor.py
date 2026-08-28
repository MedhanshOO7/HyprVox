#!/usr/bin/env python3
import sys
import os
import re
import json
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
import cairo

CONFIG_PATH = os.path.expanduser("~/.config/hyprvox/config.toml")
COLORS_JSON_PATH = os.path.expanduser("~/.local/state/quickshell/user/generated/colors.json")

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

CSS = f"""
window {{
    background-color: transparent;
    background: transparent;
}}

#dialog_box {{
    background-color: {hex_to_rgba_css(theme["bg"], 0.88)};
    border: 1px solid {hex_to_rgba_css(theme["outline_variant"], 0.50)};
    border-radius: 24px;
    padding: 24px;
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.45);
}}

#header_title {{
    font-family: 'Google Sans Flex', 'Inter', sans-serif;
    font-size: 18px;
    font-weight: bold;
    color: {theme["on_surface"]};
}}

#header_subtitle {{
    font-family: 'Google Sans Flex', 'Inter', sans-serif;
    font-size: 12px;
    color: {theme["on_surface_variant"]};
    margin-top: 2px;
}}

#tag_pill {{
    background-color: {hex_to_rgba_css(theme["surface"], 0.85)};
    border: 1px solid {hex_to_rgba_css(theme["outline_variant"], 0.35)};
    border-radius: 14px;
    padding: 5px 12px;
}}

#tag_text {{
    font-family: 'Google Sans Flex', 'Inter', sans-serif;
    font-size: 12px;
    font-weight: 500;
    color: {theme["primary"]};
}}

#remove_btn {{
    font-size: 11px;
    color: {theme["on_surface_variant"]};
    background: transparent;
    border: none;
    padding: 0 2px;
}}

#remove_btn:hover {{
    color: {theme["tertiary"]};
}}

#add_entry {{
    font-family: 'Google Sans Flex', 'Inter', sans-serif;
    font-size: 13px;
    background-color: {hex_to_rgba_css(theme["surface"], 0.70)};
    border: 1px solid {hex_to_rgba_css(theme["outline_variant"], 0.40)};
    border-radius: 14px;
    color: {theme["on_surface"]};
    padding: 10px 16px;
}}

#add_entry:focus {{
    border: 1px solid {theme["primary"]};
}}

#action_btn {{
    font-family: 'Google Sans Flex', 'Inter', sans-serif;
    font-size: 13px;
    font-weight: 600;
    background-color: {theme["primary"]};
    color: #121318;
    border-radius: 14px;
    border: none;
    padding: 10px 20px;
}}

#action_btn:hover {{
    background-color: {theme["secondary"]};
}}

#sec_btn {{
    font-family: 'Google Sans Flex', 'Inter', sans-serif;
    font-size: 12px;
    background-color: transparent;
    color: {theme["on_surface_variant"]};
    border: 1px solid {hex_to_rgba_css(theme["outline_variant"], 0.40)};
    border-radius: 12px;
    padding: 7px 16px;
}}

#sec_btn:hover {{
    background-color: {hex_to_rgba_css(theme["surface"], 0.60)};
    color: {theme["on_surface"]};
}}
""".encode('utf-8')

class DictionaryEditor(Gtk.Window):
    def __init__(self):
        super().__init__(title="HyprVox Dictionary")
        self.set_wmclass("hyprvox-dictionary", "hyprvox-dictionary")
        self.set_role("hyprvox-dictionary")
        self.set_default_size(560, 420)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_app_paintable(True)

        screen = Gdk.Screen.get_default()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)

        self.connect("draw", self.on_window_draw)
        self.connect("key-press-event", self.on_key_press)

        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            screen,
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.words = self.read_words()

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        main_box.set_name("dialog_box")

        # Header
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title_label = Gtk.Label(label="HyprVox Vocabulary & Technical Glossary")
        title_label.set_name("header_title")
        title_label.set_xalign(0.0)

        sub_label = Gtk.Label(label="Custom terms primed in Whisper to guarantee 100% spelling accuracy.")
        sub_label.set_name("header_subtitle")
        sub_label.set_xalign(0.0)

        header_box.pack_start(title_label, False, False, 0)
        header_box.pack_start(sub_label, False, False, 0)
        main_box.pack_start(header_box, False, False, 0)

        # Tags Cloud in Scrolled Window
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_height(180)

        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_valign(Gtk.Align.START)
        self.flowbox.set_max_children_per_line(30)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flowbox.set_row_spacing(8)
        self.flowbox.set_column_spacing(8)

        scrolled.add(self.flowbox)
        main_box.pack_start(scrolled, True, True, 0)

        self.populate_tags()

        # Add Word Input Row
        input_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        self.entry = Gtk.Entry()
        self.entry.set_name("add_entry")
        self.entry.set_placeholder_text("Add word (e.g. Kubernetes, Ollama, Docker)...")
        self.entry.connect("activate", self.on_add_word)

        add_btn = Gtk.Button(label="Add Word")
        add_btn.set_name("action_btn")
        add_btn.connect("clicked", self.on_add_word)

        input_row.pack_start(self.entry, True, True, 0)
        input_row.pack_start(add_btn, False, False, 0)
        main_box.pack_start(input_row, False, False, 0)

        # Footer Row (Open in Editor & Close)
        footer_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        edit_file_btn = Gtk.Button(label="Open Config File")
        edit_file_btn.set_name("sec_btn")
        edit_file_btn.connect("clicked", self.on_open_config)

        close_btn = Gtk.Button(label="Done")
        close_btn.set_name("sec_btn")
        close_btn.connect("clicked", lambda b: self.destroy())

        footer_row.pack_start(edit_file_btn, False, False, 0)
        footer_row.pack_end(close_btn, False, False, 0)
        main_box.pack_start(footer_row, False, False, 0)

        self.add(main_box)

    def on_window_draw(self, widget, cr):
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()
        return False

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.destroy()
            return True
        return False

    def read_words(self):
        if not os.path.exists(CONFIG_PATH):
            return []
        try:
            with open(CONFIG_PATH, "r") as f:
                content = f.read()
            m = re.search(r'custom_prompt\s*=\s*\"([^\"]*)\"', content)
            if m:
                return [w.strip() for w in m.group(1).split(",") if w.strip()]
        except Exception:
            pass
        return []

    def save_words(self):
        if not os.path.exists(CONFIG_PATH):
            return
        try:
            joined = ", ".join(self.words)
            with open(CONFIG_PATH, "r") as f:
                content = f.read()
            new_content = re.sub(r'custom_prompt\s*=\s*\"[^\"]*\"', f'custom_prompt = "{joined}"', content)
            with open(CONFIG_PATH, "w") as f:
                f.write(new_content)
        except Exception as e:
            print(f"Error saving words: {e}", file=sys.stderr)

    def populate_tags(self):
        for child in self.flowbox.get_children():
            self.flowbox.remove(child)

        for word in self.words:
            chip_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            chip_box.set_name("tag_pill")

            lbl = Gtk.Label(label=word)
            lbl.set_name("tag_text")

            del_btn = Gtk.Button(label="✕")
            del_btn.set_name("remove_btn")
            del_btn.connect("clicked", self.create_delete_handler(word))

            chip_box.pack_start(lbl, False, False, 0)
            chip_box.pack_start(del_btn, False, False, 0)

            self.flowbox.add(chip_box)

        self.flowbox.show_all()

    def create_delete_handler(self, word):
        def handler(widget):
            if word in self.words:
                self.words.remove(word)
                self.save_words()
                self.populate_tags()
        return handler

    def on_add_word(self, widget):
        text = self.entry.get_text().strip()
        if text:
            new_items = [w.strip() for w in text.split(",") if w.strip()]
            for item in new_items:
                if item not in self.words:
                    self.words.append(item)
            self.save_words()
            self.populate_tags()
            self.entry.set_text("")

    def on_open_config(self, widget):
        editor = os.environ.get("EDITOR", "xdg-open")
        os.system(f"{editor} '{CONFIG_PATH}' &")

def main():
    win = DictionaryEditor()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()
