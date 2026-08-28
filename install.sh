#!/usr/bin/env bash
set -e

# HyprVox Automated Installer for Arch Linux / Wayland
BOLD="\033[1m"
GREEN="\033[1;32m"
BLUE="\033[1;34m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
RESET="\033[0m"

echo -e "${BLUE}${BOLD}=== HyprVox Automated Installer ===${RESET}\n"

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
CONFIG_DIR="$HOME/.config/hyprvox"
VENV_DIR="$APP_DIR/venv"

# 1. Check System Dependencies
echo -e "${YELLOW}--> Checking system dependencies...${RESET}"
REQUIRED_PKGS=("pipewire" "wtype" "wl-copy" "notify-send" "python3")
MISSING_PKGS=()

for pkg in "${REQUIRED_PKGS[@]}"; do
    if ! command -v "$pkg" >/dev/null 2>&1; then
        MISSING_PKGS+=("$pkg")
    fi
done

if [ ${#MISSING_PKGS[@]} -gt 0 ]; then
    echo -e "${RED}Warning: Missing required packages: ${MISSING_PKGS[*]}${RESET}"
    if command -v pacman >/dev/null 2>&1; then
        read -rp "Would you like to install missing dependencies via pacman? [Y/n] " answer
        if [[ ! "$answer" =~ ^[Nn] ]]; then
            sudo pacman -S --needed pipewire pipewire-audio wtype wl-clipboard libnotify gtk3 gtk-layer-shell python-gobject python-cairo uv
        fi
    fi
else
    echo -e "${GREEN}✓ All core system dependencies found.${RESET}"
fi

# 2. Check NVIDIA GPU
echo -e "\n${YELLOW}--> Checking GPU acceleration...${RESET}"
if command -v nvidia-smi >/dev/null 2>&1; then
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -n1 || echo "NVIDIA GPU")
    echo -e "${GREEN}✓ Detected GPU: ${GPU_NAME} (CUDA enabled)${RESET}"
else
    echo -e "${YELLOW}Notice: nvidia-smi not found. CUDA libraries will fall back to CPU int8 if unavailable.${RESET}"
fi

# 3. Setup Python Virtual Environment
echo -e "\n${YELLOW}--> Setting up Python virtual environment...${RESET}"
if command -v uv >/dev/null 2>&1; then
    if [ ! -d "$VENV_DIR" ]; then
        uv venv "$VENV_DIR" --python 3.12 2>/dev/null || uv venv "$VENV_DIR"
    fi
    echo -e "${YELLOW}--> Installing Python CUDA and UI dependencies via uv...${RESET}"
    uv pip install --python "$VENV_DIR/bin/python" \
        faster-whisper \
        nvidia-cublas-cu12 \
        nvidia-cudnn-cu12 \
        sounddevice \
        numpy \
        PyGObject \
        pycairo
else
    echo -e "${YELLOW}--> Installing via standard python3 venv & pip...${RESET}"
    if [ ! -d "$VENV_DIR" ]; then
        python3 -m venv "$VENV_DIR"
    fi
    "$VENV_DIR/bin/pip" install --upgrade pip
    "$VENV_DIR/bin/pip" install \
        faster-whisper \
        nvidia-cublas-cu12 \
        nvidia-cudnn-cu12 \
        sounddevice \
        numpy \
        PyGObject \
        pycairo
fi

echo -e "${GREEN}✓ Python virtual environment ready.${RESET}"

# 4. Pre-download Default Models for Profiles
echo -e "\n${YELLOW}--> Verifying pre-cached models (small.en & distil-large-v3)...${RESET}"
"$VENV_DIR/bin/python" -c "
from faster_whisper import WhisperModel
for m in ('small.en', 'base.en'):
    print(f'Checking {m}...')
    WhisperModel(m, device='cpu', compute_type='int8')
print('Models ready!')
" || echo -e "${YELLOW}Notice: Models will download on first dictation trigger.${RESET}"

# 5. Create Config & Symlinks
echo -e "\n${YELLOW}--> Installing binary launcher and configuration...${RESET}"
mkdir -p "$BIN_DIR" "$CONFIG_DIR"

if [ ! -f "$CONFIG_DIR/config.toml" ]; then
    cp "$APP_DIR/config.example.toml" "$CONFIG_DIR/config.toml"
    echo -e "${GREEN}✓ Created default configuration at ~/.config/hyprvox/config.toml${RESET}"
else
    echo -e "${BLUE}✓ Configuration already exists at ~/.config/hyprvox/config.toml${RESET}"
fi

ln -sf "$APP_DIR/whisper-dictate" "$BIN_DIR/whisper-dictate"
ln -sf "$APP_DIR/whisper-dictate" "$BIN_DIR/hyprvox"
chmod +x "$APP_DIR/whisper-dictate" "$APP_DIR/overlay.py" "$APP_DIR/transcribe.py" "$APP_DIR/daemon.py"

echo -e "${GREEN}✓ Symlinked launcher to ~/.local/bin/whisper-dictate and ~/.local/bin/hyprvox${RESET}"

# 6. Success Output & Configuration Help
echo -e "\n${GREEN}${BOLD}=== Installation Complete! ===${RESET}\n"
echo -e "To finish setup, add the following to your Hyprland configuration:\n"

echo -e "${BOLD}1. Keybind (~/.config/hypr/custom/keybinds.lua or hyprland.conf):${RESET}"
echo -e "${BLUE}hl.bind(\"SUPER + H\", hl.dsp.exec_cmd(\"~/.local/bin/whisper-dictate\"), { description = \"Voice: Toggle AI voice dictation\" })${RESET}\n"

echo -e "${BOLD}2. Layer Blur Rule (~/.config/hypr/custom/rules.lua or hyprland.conf):${RESET}"
echo -e "${BLUE}hl.layer_rule({ match = { namespace = \"whisper-overlay\" }, blur = true, ignore_alpha = 0.1, animation = \"slide bottom\" })${RESET}\n"

echo -e "Press ${BOLD}Super + H${RESET} to start dictating!\n"
