#!/usr/bin/env python3
"""Diagnostic machine. Premier script lance par l'agent. Ne modifie RIEN."""
import json, os, platform, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOME = Path.home(); CACHE = HOME / ".cache" / "reel-cut"

def run(c):
    try: return subprocess.run(c, capture_output=True, text=True, timeout=25).stdout.strip()
    except Exception: return ""

def has(b):
    p = shutil.which(b); return {"present": bool(p), "path": p}

def ram_gb():
    s = platform.system()
    try:
        if s == "Linux":
            kb = int(next(l for l in open("/proc/meminfo") if "MemTotal" in l).split()[1])
            return round(kb / 1e6, 1)
        if s == "Darwin":
            o = run(["sysctl", "-n", "hw.memsize"]); return round(int(o) / 1e9, 1) if o.isdigit() else None
    except Exception: pass
    return None

def main():
    cfg = {}
    f = ROOT / "config.json"
    if f.exists():
        try: cfg = json.loads(f.read_text())
        except Exception: pass

    wcli = has("whisper-cli")
    if not wcli["present"]:
        cands = [CACHE / "whisper" / "whisper-cli",
                 CACHE / "whisper-src" / "build" / "bin" / "whisper-cli"]
        cc = (cfg.get("whisperCli") or "").strip()
        if cc: cands.append(Path(cc).expanduser())
        for c in cands:
            if c.is_file() and os.access(c, os.X_OK):
                wcli = {"present": True, "path": str(c)}; break

    models = sorted(str(p) for p in (CACHE / "whisper").glob("ggml-*.bin")) if (CACHE / "whisper").exists() else []
    node = run(["node", "-v"]) or None
    try:
        import PIL  # noqa
        pil = True
    except Exception:
        pil = False

    r = {"os": platform.system(), "arch": platform.machine(),
         "python": platform.python_version(), "cpu_count": os.cpu_count(), "ram_gb": ram_gb(),
         "ffmpeg": has("ffmpeg"), "ffprobe": has("ffprobe"),
         "whisper_cli": wcli, "whisper_models": models,
         "node": node, "pillow": pil,
         "hyperframes_installed": (ROOT / "node_modules" / "hyperframes").exists(),
         "config_present": f.exists()}

    blk, warn = [], []
    if not r["ffmpeg"]["present"]: blk.append("ffmpeg absent")
    if not r["ffprobe"]["present"]: blk.append("ffprobe absent")
    if not wcli["present"]: blk.append("whisper-cli absent")
    if not models: blk.append("aucun modele whisper (ggml-*.bin) telecharge")
    if not node: blk.append("Node.js absent (requis par HyperFrames)")
    if not pil: blk.append("Pillow absent (mesure de la largeur des sous-titres)")
    if not r["hyperframes_installed"]: blk.append("HyperFrames pas installe (npm install)")

    cpu = os.cpu_count() or 0; ram = r["ram_gb"]
    if cpu < 4: warn.append(f"{cpu} coeurs CPU : la transcription locale sera lente")
    if ram and ram < 8: warn.append(f"RAM {ram} Go : le rendu HyperFrames peut saturer")
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        warn.append("Mac Apple Silicon detecte : configuration optimale")

    r["blocking"] = blk; r["warnings"] = warn; r["ready"] = not blk
    print(json.dumps(r, indent=2, ensure_ascii=False))
    return 0 if not blk else 1

if __name__ == "__main__": sys.exit(main())
