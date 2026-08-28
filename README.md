<div align="center">

# 🎙️ HyprVox

### Ultra-fast, GPU-accelerated AI Voice Dictation with Dynamic Material You Theming & Audio-Reactive Waveforms for Hyprland & Wayland.

[![Arch Linux](https://img.shields.io/badge/Arch_Linux-1793D1?logo=arch-linux&logoColor=white&style=flat-square)](https://archlinux.org/)
[![Wayland](https://img.shields.io/badge/Wayland-Native-brightgreen?style=flat-square)](https://wayland.freedesktop.org/)
[![Hyprland](https://img.shields.io/badge/Hyprland-Optimized-00c0b3?style=flat-square)](https://hyprland.org/)
[![NVIDIA CUDA](https://img.shields.io/badge/NVIDIA_CUDA-12.x-76B900?logo=nvidia&logoColor=white&style=flat-square)](https://developer.nvidia.com/cuda-toolkit)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)

</div>

---

## ✨ Features

- **⚡ Lightning-Fast Inference**: Powered by [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper) (CTranslate2) running in `float16` on **NVIDIA CUDA**. Latency is typically **~100–150 ms**.
- **🎤 Real-Time Audio-Reactive Visualizer**: Multi-color Cairo waveform bars bounce dynamically in response to your microphone's live speech amplitude (RMS) with adaptive ambient noise filtering.
- **🧠 Tech Glossary & Smart Formatting**:
  - Automatically primes Whisper with technical developer vocabulary (`Hyprland, Wayland, Pacman, Neovim, CachyOS, Python, Rust, zsh...`) to eliminate phonetic misspellings.
  - Spoken punctuation support: say *"new line"*, *"period"*, *"comma"*, *"colon"*, or *"question mark"* and it inserts the proper symbols with smart capitalization.
- **🎨 Dynamic Material You & Quickshell Theming**: The floating pill automatically synchronizes colors (`primary`, `tertiary`, `surface`, `outline`), background transparency (`0.65`), and typography (`Google Sans Flex` / `Inter`) from your active Quickshell / Matugen desktop palette in real time.
- **🪟 True Wayland LayerShell Overlay**: Uses `gtk-layer-shell` on the `OVERLAY` layer with `KeyboardMode.NONE` — **never steals cursor or keyboard focus from your active text input**.
- **🌫️ Hyprland Glassmorphism Blur**: Fully supports Hyprland `layerrule` blur for a frosted glass look over active windows.
- **⌨️ Direct Typing & Clipboard Sync**: Injects text directly into the focused window with `wtype` and saves a copy to your clipboard with `wl-copy`.
- **⚙️ User Configuration**: Customize models, glossary, UI position, fonts, noise gate, and sound effects via `~/.config/hyprvox/config.toml`.

---

## 🚀 Quick 1-Command Installation

Clone the repository and run the automated installer:

```bash
git clone https://github.com/MedhanshOO7/HyprVox.git ~/.local/share/whisper-dictate
cd ~/.local/share/whisper-dictate
./install.sh
```

The installer will:
1. Detect and verify all system dependencies (`pipewire`, `wtype`, `wl-clipboard`, `gtk-layer-shell`, etc.).
2. Set up the Python virtual environment with NVIDIA CUDA libraries.
3. Pre-download the default `small.en` model for zero-wait first run.
4. Symlink `whisper-dictate` and `hyprvox` into `~/.local/bin/`.
5. Create your configuration template at `~/.config/hyprvox/config.toml`.

---

## ⌨️ Hyprland Keybind & Blur Rules

### 1. Add Keybind (`~/.config/hypr/custom/keybinds.lua` or `hyprland.conf`)

```lua
-- Voice Dictation Toggle (Super + H)
hl.bind("SUPER + H", hl.dsp.exec_cmd("~/.local/bin/whisper-dictate"), { description = "Voice: Toggle AI voice dictation" })
```

*Or in standard `hyprland.conf`:*
```ini
bind = SUPER, H, exec, ~/.local/bin/whisper-dictate
```

### 2. Add Layer Rule for Blur (`~/.config/hypr/custom/rules.lua` or `hyprland.conf`)

```lua
-- Translucent floating pill with background blur
hl.layer_rule({
    match = { namespace = "whisper-overlay" },
    blur = true,
    ignore_alpha = 0.1,
    animation = "slide bottom",
})
```

*Or in standard `hyprland.conf`:*
```ini
layerrule = blur, whisper-overlay
layerrule = ignorealpha 0.1, whisper-overlay
layerrule = animation slide bottom, whisper-overlay
```

---

## ⚙️ Configuration (`~/.config/hyprvox/config.toml`)

Customize your settings in `~/.config/hyprvox/config.toml`:

```toml
[model]
name = "small.en"        # Options: base.en (fastest), small.en (balanced), distil-large-v3 (highest accuracy)
compute_type = "float16" # float16 for NVIDIA CUDA GPUs, int8 for CPU fallback
language = "en"          # "en" for English, "auto" for auto-detect multi-language

[audio]
sample_rate = 16000
play_sounds = true
reactive_audio = true    # Live microphone amplitude waveform
noise_gate = 0.18        # Ambient room noise filtering threshold
mic_sensitivity = 3.0    # Equalizer bounce sensitivity

[formatting]
smart_punctuation = true # Converts spoken commands ("new line", "period", "comma", etc.)
# Custom vocabulary glossary to prime Whisper for technical terms
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
├── transcribe.py         # CUDA faster-whisper worker with VAD silence trimming & smart formatting
├── config.example.toml   # Default configuration template
├── README.md             # Project documentation
├── LICENSE               # MIT License
└── .gitignore            # Git exclusion rules
```

---

## 📜 License

Distributed under the [MIT License](LICENSE).
