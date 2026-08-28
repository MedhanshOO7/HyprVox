# HyprVox 🎙️

Ultra-fast, native local AI voice dictation with a dynamic Material You floating overlay for Hyprland and Wayland, powered by `faster-whisper` running on NVIDIA GPU CUDA (`float16`).

---

## ✨ Features

- **⚡ GPU Accelerated**: Local `faster-whisper` inference on NVIDIA CUDA in ~100–150 ms.
- **🎨 Dynamic Material You Theming**: Floating pill overlay that automatically matches your Quickshell top bar colors, transparency, and fonts.
- **🌊 Animated Waveform Visualizer**: Smooth Cairo multi-color voice equalizers while listening and transcribing.
- **🪟 True Wayland LayerShell Overlay**: Anchored above windows without stealing cursor focus (`KeyboardMode.NONE`).
- **⌨️ Direct Typing & Clipboard Sync**: Injects text into active windows with `wtype` and simultaneously synchronizes to `wl-copy`.
- **🔊 PipeWire Audio & Sound Cues**: Low-latency audio recording via `pw-record` with subtle non-intrusive chimes.

---

## 🚀 Quick Setup & Keybind

### 1. Hyprland Configuration (`~/.config/hypr/custom/keybinds.lua`)
```lua
hl.bind("SUPER + H", hl.dsp.exec_cmd("~/.local/bin/whisper-dictate"), { description = "Voice: Toggle AI voice dictation" })
```

### 2. Usage
- Press <kbd>Super</kbd> + <kbd>H</kbd> anywhere &rarr; start speaking.
- Press <kbd>Super</kbd> + <kbd>H</kbd> again &rarr; transcribes and types into the focused application.

---

## 🛠️ Requirements

- **OS**: Arch Linux / Linux with Wayland
- **Compositor**: Hyprland (or any wlroots/LayerShell compositor)
- **GPU**: NVIDIA GPU with CUDA support
- **Packages**: `wtype`, `wl-clipboard`, `pipewire` (`pw-record`, `pw-play`), `libnotify`, `gtk3`, `gtk-layer-shell`, `python-gobject`
