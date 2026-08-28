#!/usr/bin/env python3
import sys
import os
import re
import socket
import subprocess
import argparse
from pathlib import Path

DAEMON_SOCK = "/tmp/hyprvox_daemon.sock"
CONFIG_PATH = os.path.expanduser("~/.config/hyprvox/config.toml")

def load_config():
    defaults = {
        "general": {"auto_profiles": True},
        "profiles": {
            "ac": {"model": "distil-large-v3", "compute_type": "float16", "mode": "warm"},
            "battery": {"model": "small.en", "compute_type": "float16", "mode": "cold"},
            "game_mode": {"model": "base.en", "compute_type": "int8", "mode": "cold"},
        },
        "formatting": {
            "smart_punctuation": True,
            "custom_prompt": "Hyprland, Wayland, Arch Linux, CachyOS, Neovim, Pacman, Yay, GitHub, Python, Rust, Zsh, Quickshell, Matugen, NVIDIA, CUDA, PipeWire, PyGObject, GTK"
        }
    }
    if os.path.exists(CONFIG_PATH):
        try:
            import tomllib
            with open(CONFIG_PATH, "rb") as f:
                cfg = tomllib.load(f)
                defaults["general"].update(cfg.get("general", {}))
                if "profiles" in cfg:
                    defaults["profiles"]["ac"].update(cfg["profiles"].get("ac", {}))
                    defaults["profiles"]["battery"].update(cfg["profiles"].get("battery", {}))
                    defaults["profiles"]["game_mode"].update(cfg["profiles"].get("game_mode", {}))
                defaults["formatting"].update(cfg.get("formatting", {}))
        except Exception:
            pass
    return defaults

config = load_config()

def detect_system_profile():
    # 1. Game Mode Check (Hyprland animations:enabled == 0 or gamemoded running)
    try:
        hypr_check = subprocess.run(["hyprctl", "getoption", "animations:enabled"], capture_output=True, text=True, timeout=0.4)
        if "int: 0" in hypr_check.stdout:
            return "game_mode"
    except Exception:
        pass

    # 2. AC / Charger Power Check
    try:
        for p in Path("/sys/class/power_supply").glob("*"):
            online_f = p / "online"
            status_f = p / "status"
            if online_f.exists() and online_f.read_text().strip() == "1":
                return "ac"
            if status_f.exists() and status_f.read_text().strip() in ("Charging", "Full"):
                return "ac"
    except Exception:
        pass

    # 3. Default Battery
    return "battery"

def format_smart_punctuation(text):
    if not text:
        return text

    replacements = [
        (r'\bnew paragraph\b', '\n\n'),
        (r'\bnew line\b|\bnewline\b', '\n'),
        (r'\bperiod\b|\bfull stop\b', '.'),
        (r'\bcomma\b', ','),
        (r'\bquestion mark\b', '?'),
        (r'\bexclamation (mark|point)\b', '!'),
        (r'\bcolon\b', ':'),
        (r'\bsemicolon\b', ';'),
        (r'\bopen quote\b|\bclose quote\b', '"'),
        (r'\bhyphen\b|\bdash\b', '-'),
    ]

    for pattern, repl in replacements:
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)

    text = re.sub(r'\s+([.,!?:;])', r'\1', text)
    text = re.sub(r'\n\s+', '\n', text)
    text = re.sub(r'([.!?\n]\s*)([a-z])', lambda m: m.group(1) + m.group(2).upper(), text)

    return text.strip()

def transcribe_via_daemon(audio_path):
    if not os.path.exists(DAEMON_SOCK):
        return None
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(15.0)
        s.connect(DAEMON_SOCK)
        s.sendall(f"TRANSCRIBE:{audio_path}".encode("utf-8"))
        result = s.recv(8192).decode("utf-8")
        s.close()
        return result
    except Exception:
        return None

def transcribe_cold(audio_path, model_name, compute_type, language="en"):
    # Ensure CUDA library paths
    venv_dir = Path(__file__).resolve().parent / "venv"
    for lib_name in ("cudnn", "cublas"):
        lib_path = venv_dir / "lib" / "python3.12" / "site-packages" / "nvidia" / lib_name / "lib"
        if lib_path.exists():
            current_ld = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = f"{lib_path}:{current_ld}" if current_ld else str(lib_path)

    from faster_whisper import WhisperModel

    custom_prompt = config["formatting"].get("custom_prompt", "")
    enable_smart_punct = config["formatting"].get("smart_punctuation", True)

    device = "cuda" if compute_type != "int8" else "cpu"
    try:
        model = WhisperModel(model_name, device=device, compute_type=compute_type)
    except Exception:
        model = WhisperModel(model_name, device="cpu", compute_type="int8")

    segments, _ = model.transcribe(
        audio_path,
        beam_size=5,
        language=language if language != "auto" else None,
        initial_prompt=custom_prompt if custom_prompt else None,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
    )

    text_segments = [seg.text.strip() for seg in segments if seg.text.strip()]
    raw_text = " ".join(text_segments).strip()

    if enable_smart_punct:
        return format_smart_punctuation(raw_text)
    return raw_text

def transcribe(audio_path, model_override=None, language="en"):
    if not os.path.exists(audio_path) or os.path.getsize(audio_path) < 1000:
        return ""

    if model_override:
        return transcribe_cold(audio_path, model_override, "float16", language)

    # Resolve active dynamic profile
    profile_name = detect_system_profile() if config["general"].get("auto_profiles", True) else "battery"
    prof = config["profiles"].get(profile_name, config["profiles"]["battery"])

    model_name = prof.get("model", "small.en")
    compute_type = prof.get("compute_type", "float16")
    mode = prof.get("mode", "cold")

    # If warm mode, try daemon first
    if mode == "warm":
        daemon_res = transcribe_via_daemon(audio_path)
        if daemon_res is not None:
            return daemon_res
        
        # Daemon not running, spawn it in background for next time and transcribe cold now
        venv_python = Path(__file__).resolve().parent / "venv" / "bin" / "python"
        daemon_script = Path(__file__).resolve().parent / "daemon.py"
        if venv_python.exists() and daemon_script.exists():
            subprocess.Popen([str(venv_python), str(daemon_script)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return transcribe_cold(audio_path, model_name, compute_type, language)

def main():
    parser = argparse.ArgumentParser(description="Transcribe audio with dynamic power & gaming profiles.")
    parser.add_argument("audio_file", help="Path to input audio file")
    parser.add_argument("--model", default=None, help="Whisper model override")
    parser.add_argument("--language", default="en", help="Language code")
    args = parser.parse_args()

    result = transcribe(args.audio_file, model_override=args.model, language=args.language)
    if result:
        print(result)

if __name__ == "__main__":
    main()
