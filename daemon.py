#!/usr/bin/env python3
import sys
import os
import re
import time
import socket
import threading
from pathlib import Path

DAEMON_SOCK = "/tmp/hyprvox_daemon.sock"
PID_FILE = "/tmp/hyprvox_daemon.pid"
CONFIG_PATH = os.path.expanduser("~/.config/hyprvox/config.toml")

# Ensure CUDA paths
venv_dir = Path(__file__).resolve().parent / "venv"
for lib_name in ("cudnn", "cublas"):
    lib_path = venv_dir / "lib" / "python3.12" / "site-packages" / "nvidia" / lib_name / "lib"
    if lib_path.exists():
        current_ld = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = f"{lib_path}:{current_ld}" if current_ld else str(lib_path)

from faster_whisper import WhisperModel

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

class WhisperDaemon:
    def __init__(self, model_name="small.en", compute_type="float16"):
        self.config = load_config()
        self.model_name = model_name
        self.compute_type = compute_type
        self.load_model(model_name, compute_type)

    def load_model(self, model_name, compute_type):
        self.model_name = model_name
        self.compute_type = compute_type
        print(f"[Daemon] Loading model '{model_name}' on CUDA ({compute_type})...")
        try:
            self.model = WhisperModel(model_name, device="cuda", compute_type=compute_type)
        except Exception as e:
            print(f"[Daemon] CUDA initialization failed ({e}), falling back to CPU int8...")
            self.model = WhisperModel(model_name, device="cpu", compute_type="int8")
        print("[Daemon] Model ready.")

    def transcribe(self, audio_path, language="en"):
        if not os.path.exists(audio_path) or os.path.getsize(audio_path) < 1000:
            return ""
        self.config = load_config()
        custom_prompt = self.config["formatting"].get("custom_prompt", "")
        enable_smart_punct = self.config["formatting"].get("smart_punctuation", True)

        segments, _ = self.model.transcribe(
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

def run_server():
    cfg = load_config()
    m_name = cfg["model"].get("name", "small.en")
    c_type = cfg["model"].get("compute_type", "float16")
    
    daemon = WhisperDaemon(m_name, c_type)

    if os.path.exists(DAEMON_SOCK):
        try:
            os.remove(DAEMON_SOCK)
        except OSError:
            pass

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(DAEMON_SOCK)
    server.listen(5)

    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    print(f"[Daemon] Listening on {DAEMON_SOCK}")

    while True:
        try:
            conn, _ = server.accept()
            data = conn.recv(4096).decode("utf-8").strip()
            if not data:
                conn.close()
                continue
            
            if data.startswith("TRANSCRIBE:"):
                audio_file = data[11:]
                result = daemon.transcribe(audio_file)
                conn.sendall(result.encode("utf-8"))
            elif data.startswith("LOAD:"):
                # Dynamically switch model
                new_model = data[5:]
                if new_model != daemon.model_name:
                    daemon.load_model(new_model, daemon.compute_type)
                conn.sendall(b"OK")
            elif data == "PING":
                conn.sendall(b"PONG")
            elif data == "QUIT":
                conn.sendall(b"BYE")
                conn.close()
                break
            conn.close()
        except Exception as e:
            print(f"[Daemon] Error handling request: {e}", file=sys.stderr)

    if os.path.exists(DAEMON_SOCK):
        try:
            os.remove(DAEMON_SOCK)
        except OSError:
            pass
    if os.path.exists(PID_FILE):
        try:
            os.remove(PID_FILE)
        except OSError:
            pass

if __name__ == "__main__":
    run_server()
