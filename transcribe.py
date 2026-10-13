#!/usr/bin/env python3
"""Transcription MOT A MOT en LOCAL (whisper.cpp) -> work/<slug>_words.json

Rien ne quitte la machine. Aucune cle API.

  python3 tools/transcribe.py rushes/ma_video.mp4 [--lang fr] [--slug nom]

Sortie : {"language","duration","text","words":[{"w","start","end"}]}  (secondes absolues)
"""
import argparse, json, os, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work"; WORK.mkdir(exist_ok=True)
CACHE = Path.home() / ".cache" / "reel-cut"

def cfg():
    f = ROOT / "config.json"
    return json.loads(f.read_text()) if f.exists() else {}

def sh(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(json.dumps({"error": f"{Path(cmd[0]).name} a echoue",
                                     "stderr": r.stderr[-1500:]}, ensure_ascii=False))
    return r.stdout

def resolve_whisper(c):
    p = (c.get("whisperCli") or "").strip()
    cands = ([Path(p).expanduser()] if p else []) + [
        Path("whisper-cli"), CACHE / "whisper" / "whisper-cli",
        CACHE / "whisper-src" / "build" / "bin" / "whisper-cli"]
    import shutil
    for x in cands:
        if x.name == str(x) :
            w = shutil.which(str(x))
            if w: return w
        elif x.is_file() and os.access(x, os.X_OK):
            return str(x)
    raise SystemExit(json.dumps({"error": "whisper-cli introuvable, lance INSTALL.md"}))

def resolve_model(c):
    m = (c.get("whisperModel") or "").strip()
    if m:
        mp = Path(m).expanduser()
        if mp.exists(): return str(mp)
    found = sorted((CACHE / "whisper").glob("ggml-*.bin")) if (CACHE / "whisper").exists() else []
    if found: return str(found[0])
    raise SystemExit(json.dumps({"error": "aucun modele ggml-*.bin, lance INSTALL.md"}))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source"); ap.add_argument("--lang", default=None); ap.add_argument("--slug", default=None)
    a = ap.parse_args()
    c = cfg()
    src = Path(a.source).resolve()
    if not src.exists(): raise SystemExit(json.dumps({"error": f"introuvable: {src}"}))
    slug = a.slug or src.stem
    lang = a.lang or c.get("language", "fr")
    cli, model = resolve_whisper(c), resolve_model(c)

    wav = WORK / f"{slug}.wav"
    sh(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-vn",
        "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(wav)])
    dur = float(sh(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=nw=1:nk=1", str(src)]).strip())

    t0 = time.time()
    out = WORK / f"{slug}_whisper"
    # -ml 1 : un segment par mot.  -sow : coupe sur les mots, pas au milieu.
    sh([cli, "-m", model, "-f", str(wav), "-l", lang, "-oj", "-ml", "1", "-sow",
        "-of", str(out), "-t", str(max(1, (os.cpu_count() or 2)))])
    data = json.loads(out.with_suffix(".json").read_text())

    words = []
    for s in data.get("transcription", []):
        w = (s.get("text") or "").strip()
        if not w: continue
        o = s.get("offsets") or {}
        st, en = o.get("from", 0) / 1000.0, o.get("to", 0) / 1000.0
        if en <= st: en = st + 0.08
        words.append({"w": w, "start": round(st, 3), "end": round(en, 3)})
    if not words: raise SystemExit(json.dumps({"error": "aucun mot transcrit"}))

    res = {"language": lang, "source": str(src), "duration": round(dur, 3),
           "elapsed": round(time.time() - t0, 1),
           "text": " ".join(w["w"] for w in words), "words": words}
    dst = WORK / f"{slug}_words.json"
    dst.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    wav.unlink(missing_ok=True); out.with_suffix(".json").unlink(missing_ok=True)
    print(json.dumps({"ok": True, "words": len(words), "duration": round(dur, 1),
                      "elapsed": res["elapsed"],
                      "vitesse": f"x{round(dur / max(res['elapsed'], .01), 2)} temps reel",
                      "out": str(dst)}, ensure_ascii=False))

if __name__ == "__main__": main()
