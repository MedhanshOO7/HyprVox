#!/usr/bin/env python3
import sys
import os
import argparse
from pathlib import Path

# Add nvidia cuda/cudnn libraries from venv to LD_LIBRARY_PATH if present
venv_dir = Path(__file__).resolve().parent / "venv"
cudnn_lib = venv_dir / "lib" / "python3.12" / "site-packages" / "nvidia" / "cudnn" / "lib"
cublas_lib = venv_dir / "lib" / "python3.12" / "site-packages" / "nvidia" / "cublas" / "lib"

extra_paths = []
if cudnn_lib.exists():
    extra_paths.append(str(cudnn_lib))
if cublas_lib.exists():
    extra_paths.append(str(cublas_lib))

if extra_paths:
    current_ld = os.environ.get("LD_LIBRARY_PATH", "")
    os.environ["LD_LIBRARY_PATH"] = ":".join(extra_paths + ([current_ld] if current_ld else []))

try:
    from faster_whisper import WhisperModel
except ImportError:
    print("Error: faster-whisper is not installed in the virtual environment.", file=sys.stderr)
    sys.exit(1)

def transcribe(audio_path, model_name="small.en", language="en"):
    if not os.path.exists(audio_path) or os.path.getsize(audio_path) < 1000:
        return ""

    try:
        # Try CUDA first
        model = WhisperModel(model_name, device="cuda", compute_type="float16")
    except Exception as e:
        print(f"Notice: CUDA initialization failed ({e}), falling back to CPU...", file=sys.stderr)
        model = WhisperModel(model_name, device="cpu", compute_type="int8")

    segments, info = model.transcribe(
        audio_path,
        beam_size=5,
        language=language if language != "auto" else None,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
    )

    text_segments = [segment.text.strip() for segment in segments if segment.text.strip()]
    full_text = " ".join(text_segments).strip()
    return full_text

def main():
    parser = argparse.ArgumentParser(description="Transcribe audio file with faster-whisper.")
    parser.add_argument("audio_file", help="Path to input audio file (WAV format)")
    parser.add_argument("--model", default="small.en", help="Whisper model (e.g., base.en, small.en, distil-large-v3)")
    parser.add_argument("--language", default="en", help="Language code or auto")
    args = parser.parse_args()

    result = transcribe(args.audio_file, model_name=args.model, language=args.language)
    if result:
        print(result)

if __name__ == "__main__":
    main()
