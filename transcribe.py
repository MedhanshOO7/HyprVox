#!/usr/bin/env python3
import sys
import os
import re
import argparse
from pathlib import Path

# Load TOML config
CONFIG_PATH = os.path.expanduser("~/.config/hyprvox/config.toml")

def load_config():
    defaults = {
        "model": {"name": "small.en", "compute_type": "float16", "language": "en"},
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
                defaults["model"].update(cfg.get("model", {}))
                defaults["formatting"].update(cfg.get("formatting", {}))
        except Exception:
            pass
    return defaults

config = load_config()

# Dynamic CUDA library paths
venv_dir = Path(__file__).resolve().parent / "venv"
for lib_name in ("cudnn", "cublas"):
    lib_path = venv_dir / "lib" / "python3.12" / "site-packages" / "nvidia" / lib_name / "lib"
    if lib_path.exists():
        current_ld = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = f"{lib_path}:{current_ld}" if current_ld else str(lib_path)

try:
    from faster_whisper import WhisperModel
except ImportError:
    print("Error: faster-whisper is not installed in the virtual environment.", file=sys.stderr)
    sys.exit(1)

def format_smart_punctuation(text):
    if not text:
        return text

    # Replacements for spoken punctuation commands
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

    # Clean up accidental spaces before punctuation: "hello , world ." -> "hello, world."
    text = re.sub(r'\s+([.,!?:;])', r'\1', text)
    # Clean up spacing after newlines
    text = re.sub(r'\n\s+', '\n', text)
    
    # Capitalize after newlines or sentence endings
    def capitalize_match(match):
        return match.group(1) + match.group(2).upper()

    text = re.sub(r'([.!?\n]\s*)([a-z])', capitalize_match, text)

    return text.strip()

def transcribe(audio_path, model_name=None, language=None):
    if not os.path.exists(audio_path) or os.path.getsize(audio_path) < 1000:
        return ""

    m_name = model_name or config["model"].get("name", "small.en")
    c_type = config["model"].get("compute_type", "float16")
    lang = language or config["model"].get("language", "en")
    custom_prompt = config["formatting"].get("custom_prompt", "")
    enable_smart_punct = config["formatting"].get("smart_punctuation", True)

    try:
        model = WhisperModel(m_name, device="cuda", compute_type=c_type)
    except Exception as e:
        print(f"Notice: CUDA initialization failed ({e}), falling back to CPU...", file=sys.stderr)
        model = WhisperModel(m_name, device="cpu", compute_type="int8")

    segments, info = model.transcribe(
        audio_path,
        beam_size=5,
        language=lang if lang != "auto" else None,
        initial_prompt=custom_prompt if custom_prompt else None,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
    )

    text_segments = [segment.text.strip() for segment in segments if segment.text.strip()]
    raw_text = " ".join(text_segments).strip()

    if enable_smart_punct:
        return format_smart_punctuation(raw_text)
    return raw_text

def main():
    parser = argparse.ArgumentParser(description="Transcribe audio file with faster-whisper.")
    parser.add_argument("audio_file", help="Path to input audio file (WAV format)")
    parser.add_argument("--model", default=None, help="Whisper model (overrides config.toml)")
    parser.add_argument("--language", default=None, help="Language code (overrides config.toml)")
    args = parser.parse_args()

    result = transcribe(args.audio_file, model_name=args.model, language=args.language)
    if result:
        print(result)

if __name__ == "__main__":
    main()
