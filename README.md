<div align="center">

# 🎙️ HyprVox

### Ultra-fast, GPU-accelerated AI Voice Dictation with Dynamic Power Profiles, System Game Mode Sync & Audio-Reactive Waveforms for Hyprland & Wayland.

[![Arch Linux](https://img.shields.io/badge/Arch_Linux-1793D1?logo=arch-linux&logoColor=white&style=flat-square)](https://archlinux.org/)
[![Wayland](https://img.shields.io/badge/Wayland-Native-brightgreen?style=flat-square)](https://wayland.freedesktop.org/)
[![Hyprland](https://img.shields.io/badge/Hyprland-Optimized-00c0b3?style=flat-square)](https://hyprland.org/)
[![NVIDIA CUDA](https://img.shields.io/badge/NVIDIA_CUDA-12.x-76B900?logo=nvidia&logoColor=white&style=flat-square)](https://developer.nvidia.com/cuda-toolkit)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)

</div>

---

## ✨ Features

- **⚡ Lightning-Fast Inference**: Powered by [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper) (CTranslate2) running in `float16` on **NVIDIA CUDA**. Typical transcription latency is only **~100–150 ms** (or **~50 ms** in warm daemon mode).
- **🔋 Dynamic Power & Gaming Profiles**:
  - **🔌 Charger / AC Power**: Automatically switches to the highest-accuracy model (`distil-large-v3`) with optional pre-warmed resident daemon for instant transcription.
  - **🔋 Battery Power**: Automatically switches to a balanced, power-efficient model (`small.en`) running in on-demand cold mode (0 MB VRAM when idle).
  - **🎮 Game Mode**: Paired with your system's Game Mode toggle (`animations:enabled: 0` / `gamemoded`) to run an ultra-light model (`base.en`) with zero GPU overhead to preserve gaming FPS.
- **🎤 Real-Time Audio-Reactive Visualizer**: Multi-color Cairo waveform bars bounce dynamically in response to your microphone's live speech amplitude (RMS) with adaptive ambient noise filtering.
- **🧠 Tech Glossary & Smart Formatting**:
  - Automatically primes Whisper with technical developer vocabulary (`Hyprland, Wayland, Pacman, Neovim, CachyOS, Python, Rust, zsh...`) to eliminate phonetic misspellings.
  - Spoken punctuation support: say *"new line"*, *"period"*, *"comma"*, *"colon"*, or *"question mark"* and it inserts the proper symbols with smart capitalization.
- **🎨 Dynamic Material You & Quickshell Theming**: The floating pill automatically synchronizes colors (`primary`, `tertiary`, `surface`, `outline`), background transparency (`0.65`), and typography (`Google Sans Flex` / `Inter`) from your active Quickshell / Matugen desktop palette in real time.
- **📖 Built-in Dictionary & Vocabulary Manager**:
  - Click the **✎ Dict** button on the pill (or right-click the pill / run `hyprvox --dict`) to open a modern tag-based vocabulary editor.
  - Instantly add, remove, and manage custom coding and technical terms without touching configuration files.
- **🪟 True Wayland LayerShell Overlay**: Uses `gtk-layer-shell` on the `OVERLAY` layer with `KeyboardMode.NONE` — **never steals cursor or keyboard focus from your active text input**.
- **🌫️ Hyprland Glassmorphism Blur**: Fully supports Hyprland `layerrule` blur for a frosted glass look over active windows.
- **⌨️ Direct Typing & Clipboard Sync**: Injects text directly into the focused window with `wtype` and saves a copy to your clipboard with `wl-copy`.

---

## 🚀 Quick 1-Command Installation

```bash
git clone https://github.com/MedhanshOO7/HyprVox.git ~/.local/share/whisper-dictate
cd ~/.local/share/whisper-dictate
./install.sh
```

---

## ⚙️ Hyprland Configuration Setup

To ensure seamless integration with your desktop, add the following configuration blocks:

### 1. Keybindings

#### For Lua Configs (`~/.config/hypr/custom/keybinds.lua`):
```lua
-- Toggle AI Voice Dictation (Super + H)
hl.bind("SUPER + H", hl.dsp.exec_cmd("~/.local/bin/hyprvox"), { description = "Voice: Toggle AI voice dictation" })

-- Open Vocabulary & Dictionary Manager (Super + Shift + H)
hl.bind("SUPER + SHIFT + H", hl.dsp.exec_cmd("~/.local/bin/hyprvox --dict"), { description = "Voice: Edit technical vocabulary" })
```

#### For Standard `hyprland.conf`:
```ini
# Toggle AI Voice Dictation
bind = SUPER, H, exec, ~/.local/bin/hyprvox

# Open Vocabulary & Dictionary Manager
bind = SUPER SHIFT, H, exec, ~/.local/bin/hyprvox --dict
```

---

### 2. Layer & Window Rules

#### For Lua Configs (`~/.config/hypr/custom/rules.lua`):
```lua
-- Floating pill overlay blur and slide animation
hl.layer_rule({
    match = { namespace = "whisper-overlay" },
    blur = true,
    ignore_alpha = 0.1,
    animation = "slide bottom",
})

-- Centered floating Dictionary Manager window
hl.window_rule({
    match = { class = "^(hyprvox-dictionary)$" },
    float = true,
    center = true,
    size = { "monitor_w*0.42", "monitor_h*0.48" },
    no_blur = false,
})
hl.window_rule({
    match = { title = "^(HyprVox Dictionary)$" },
    float = true,
    center = true,
    size = { "monitor_w*0.42", "monitor_h*0.48" },
})
```

#### For Standard `hyprland.conf`:
```ini
# Floating overlay layer rules (blur & glassmorphism)
layerrule = blur, whisper-overlay
layerrule = ignorealpha 0.1, whisper-overlay
layerrule = animation slide bottom, whisper-overlay

# Dictionary Manager window rules (float & center)
windowrulev2 = float, class:^(hyprvox-dictionary)$
windowrulev2 = center, class:^(hyprvox-dictionary)$
windowrulev2 = size 42% 48%, class:^(hyprvox-dictionary)$
windowrulev2 = float, title:^(HyprVox Dictionary)$
windowrulev2 = center, title:^(HyprVox Dictionary)$
```

---

## ⚙️ User Configuration (`~/.config/hyprvox/config.toml`)

Customize your settings and profiles in `~/.config/hyprvox/config.toml`:

```toml
[general]
auto_profiles = true     # Dynamically select model based on power & game mode

[profiles.ac]
# When connected to charger / AC power
model = "distil-large-v3" # Best state-of-the-art accuracy model
compute_type = "float16"  # CUDA float16
mode = "warm"             # "warm" for instant pre-warmed daemon, "cold" for on-demand

[profiles.battery]
# When running on battery power (saves battery and GPU power)
model = "small.en"        # Balanced, efficient model
compute_type = "float16"  # CUDA float16
mode = "cold"             # "cold" uses 0 MB VRAM when idle

[profiles.game_mode]
# When System Game Mode is active (minimizes GPU usage for maximum gaming FPS)
model = "base.en"         # Ultra-light model
compute_type = "int8"     # CPU int8 / minimal GPU impact
mode = "cold"

[audio]
sample_rate = 16000
play_sounds = true
reactive_audio = true    # Live microphone amplitude waveform
noise_gate = 0.18        # Ambient room noise filtering threshold
mic_sensitivity = 3.0    # Equalizer bounce sensitivity

[formatting]
smart_punctuation = true # Converts spoken commands ("new line", "period", "comma", etc.)
custom_prompt = "Hyprland, Wayland, Arch Linux, CachyOS, Neovim, Pacman, Yay, GitHub, Python, Rust, Zsh, Quickshell, Matugen, NVIDIA, CUDA, PipeWire, PyGObject, GTK"

[ui]
font_family = "Google Sans Flex"
font_size = 16
transparency = 0.65
position = "bottom"      # "bottom" or "top"
margin = 50
```

---

## 📂 Project Structure

```
HyprVox/
├── install.sh            # Automated installer script
├── whisper-dictate       # Main toggle & PipeWire recorder
├── overlay.py            # GTK LayerShell floating visualizer & live audio-reactive waveform
├── transcribe.py         # Dynamic profile engine with CUDA faster-whisper & smart formatting
├── daemon.py             # Pre-warmed background resident daemon for warm AC mode
├── dict_editor.py        # Tag-based Vocabulary & Technical Glossary GUI
├── config.example.toml   # Default configuration template
├── README.md             # Project documentation
├── LICENSE               # MIT License
└── .gitignore            # Git exclusion rules
```

---

## 📜 License

Distributed under the [MIT License](LICENSE).
