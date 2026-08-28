<div align="center">

# 🎙️ HyprVox

### Ultra-fast, GPU-accelerated AI Voice Dictation with a Dynamic Material You Floating Overlay for Hyprland & Wayland.

[![Arch Linux](https://img.shields.io/badge/Arch_Linux-1793D1?logo=arch-linux&logoColor=white&style=flat-square)](https://archlinux.org/)
[![Wayland](https://img.shields.io/badge/Wayland-Native-brightgreen?style=flat-square)](https://wayland.freedesktop.org/)
[![Hyprland](https://img.shields.io/badge/Hyprland-Optimized-00c0b3?style=flat-square)](https://hyprland.org/)
[![NVIDIA CUDA](https://img.shields.io/badge/NVIDIA_CUDA-12.x-76B900?logo=nvidia&logoColor=white&style=flat-square)](https://developer.nvidia.com/cuda-toolkit)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)

</div>

---

## ✨ Features

- **⚡ Lightning-Fast Inference**: Powered by [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper) (CTranslate2) running in `float16` on **NVIDIA CUDA**. Typical transcription latency is only **~100–150 ms**.
- **🎨 Dynamic Material You & Quickshell Theming**: The floating pill automatically pulls and synchronizes colors (`primary`, `tertiary`, `surface`, `outline`), background transparency (`0.65`), and typography (`Google Sans Flex` / `Inter`) from your active Quickshell / Matugen desktop palette in real time.
- **🌊 Animated Waveform Visualizer**: Smooth 40 FPS multi-color animated voice equalizers built with Cairo:
  - **Listening**: Multi-harmonic organic voice bounce across dynamic accent colors.
  - **Transcribing**: Fluid traveling sine wave shimmer.
  - **Done**: Quick text preview before auto-dismissing.
- **🪟 True Wayland LayerShell Overlay**: Uses `gtk-layer-shell` on the `OVERLAY` layer with `KeyboardMode.NONE` — **never steals cursor or keyboard focus from your active text input**.
- **🌫️ Hyprland Glassmorphism Blur**: Fully supports Hyprland `layerrule` blur for a frosted glass look over active windows.
- **⌨️ Direct Typing & Clipboard Sync**: Injects transcribed text directly into the focused window using `wtype` and saves a copy to your clipboard with `wl-copy`.
- **🔊 PipeWire Audio & Sound Cues**: Low-latency 16 kHz mono capture via `pw-record` with subtle audio feedback.

---

## 📸 Workflow

```text
[ Super + H ]
     │
     ▼
🎙️ Floating Pill Appears (Waveform Animating + PipeWire Recording)
     │
 (Speak your text)
     │
     ▼
[ Super + H ]
     │
     ▼
⚡ GPU Transcription (~100ms via RTX / NVIDIA CUDA)
     │
     ├─► Types directly into active application (wtype)
     ├─► Copies to Wayland clipboard (wl-copy)
     └─► Shows brief preview on pill, then smoothly closes
```

---

## 📦 Dependencies

Ensure the following packages are installed on your system:

### Arch Linux (`pacman` / `yay`)
```bash
sudo pacman -S --needed \
    pipewire \
    pipewire-audio \
    wtype \
    wl-clipboard \
    libnotify \
    gtk3 \
    gtk-layer-shell \
    python-gobject \
    cairo \
    uv
```

---

## 🚀 Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/MedhanshOO7/HyprVox.git ~/.local/share/whisper-dictate
cd ~/.local/share/whisper-dictate
```

### 2. Create the Python Environment & Install CUDA Whisper
Using [`uv`](https://github.com/astral-sh/uv) (recommended) or standard `venv`:
```bash
uv venv venv --python 3.12
uv pip install --python venv/bin/python \
    faster-whisper \
    nvidia-cublas-cu12 \
    nvidia-cudnn-cu12
```

### 3. Install the Launcher Script
```bash
mkdir -p ~/.local/bin
ln -sf ~/.local/share/whisper-dictate/whisper-dictate ~/.local/bin/whisper-dictate
chmod +x ~/.local/bin/whisper-dictate
```
*(Ensure `~/.local/bin` is in your `$PATH`)*

---

## ⚙️ Hyprland Configuration

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

## 🛠️ Configuration & Models

You can customize the Whisper model by setting `WHISPER_MODEL` in your environment or editing `~/.local/bin/whisper-dictate`:

| Model | Size | VRAM Usage | Latency (RTX 4050) | Recommended For |
| :--- | :--- | :--- | :--- | :--- |
| `base.en` | ~140 MB | ~400 MB | ~50 ms | Ultra-fast casual dictation |
| `small.en` *(default)* | ~460 MB | ~900 MB | ~120 ms | High accuracy & everyday use |
| `distil-large-v3` | ~1.5 GB | ~2.0 GB | ~200 ms | Complex technical / coding terms |

Example:
```bash
export WHISPER_MODEL="small.en"
```

---

## 📂 Project Structure

```
HyprVox/
├── whisper-dictate       # Main bash toggle & PipeWire recorder
├── overlay.py            # GTK LayerShell floating visualizer & Cairo waveform
├── transcribe.py         # CUDA faster-whisper worker with VAD silence trimming
├── README.md             # Project documentation
└── .gitignore            # Git exclusion rules
```

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/MedhanshOO7/HyprVox/issues).

---

## 📜 License

Distributed under the [MIT License](LICENSE).
