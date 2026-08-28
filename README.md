# Whisper-Dictate (CUDA + Wayland / Hyprland)

Ultra-fast, native local AI voice dictation with floating Wayland LayerShell overlay, powered by `faster-whisper` running on NVIDIA GPU CUDA (`float16`).

## Features
- **GPU Accelerated**: Faster-Whisper inference on CUDA (NVIDIA RTX 4050) in ~100-150ms.
- **Wayland Native**: Types directly into active windows with `wtype` and synchronizes to `wl-copy`.
- **Modern Floating Overlay**: Pill-shaped translucent UI using GTK LayerShell (anchored above active windows without stealing input focus).
- **PipeWire Audio**: Low-latency 16kHz mono audio recording via `pw-record`.
- **Toggle Recording**: Press <kbd>Super</kbd> + <kbd>H</kbd> to start speaking, press again to transcribe and type.

## Keybind (Hyprland)
```lua
-- ~/.config/hypr/custom/keybinds.lua
hl.bind("SUPER + H", hl.dsp.exec_cmd("~/.local/bin/whisper-dictate"), { description = "Voice: Toggle AI voice dictation" })
```

## Structure
- `whisper-dictate` (Launcher script in `~/.local/bin/whisper-dictate`)
- `transcribe.py` (CUDA transcription worker with VAD silence filtering)
- `overlay.py` (GTK LayerShell floating visualizer)
- `venv/` (Python 3.12 virtualenv with faster-whisper, nvidia-cudnn, nvidia-cublas)
