#!/usr/bin/env python3
"""DERUSH -> assets/<slug>_cut.mp4 + work/<slug>_map.json

Seul endroit ou l'on touche a ffmpeg pour de la video : la coupe brute.
Tout l'habillage qui suit est fait par HyperFrames.

  python3 tools/build_cut.py <slug> [--fade 0.04] [--crf 18]
"""
import argparse, json, subprocess, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work"; ASSETS = ROOT / "assets"; ASSETS.mkdir(exist_ok=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug"); ap.add_argument("--fade", type=float, default=0.04)
    ap.add_argument("--crf", type=int, default=18); ap.add_argument("--preset", default="medium")
    a = ap.parse_args()

    pj = WORK / f"{a.slug}_plan.json"
    if not pj.exists(): raise SystemExit(json.dumps({"error": f"{pj} absent"}))
    plan = json.loads(pj.read_text()); src = Path(plan["source"])
    keep = [i for i in plan["islands"] if i.get("keep")]
    if not keep: raise SystemExit(json.dumps({"error": "aucun ilot garde"}))

    segs = []
    for i in keep:
        s, e = float(i["cut_start"]), float(i["cut_end"])
        if segs and abs(s - segs[-1][1]) < 1e-3: segs[-1][1] = e
        else: segs.append([s, e])
    segs = [(s, e) for s, e in segs if e - s > 0.05]

    parts, f = [], a.fade
    for n, (s, e) in enumerate(segs):
        d = e - s
        af = f"atrim=start={s}:end={e},asetpts=PTS-STARTPTS"
        if d > 2 * f + 0.05:
            af += f",afade=t=in:st=0:d={f},afade=t=out:st={d - f:.3f}:d={f}"
        parts.append(f"[0:v]trim=start={s}:end={e},setpts=PTS-STARTPTS[v{n}];[0:a]{af}[a{n}]")
    fc = ";".join(parts) + ";" + "".join(f"[v{n}][a{n}]" for n in range(len(segs))) \
         + f"concat=n={len(segs)}:v=1:a=1[v][a]"

    out = ASSETS / f"{a.slug}_cut.mp4"
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as t:
        t.write(fc); script = t.name
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
                        "-filter_complex_script", script, "-map", "[v]", "-map", "[a]",
                        "-c:v", "libx264", "-crf", str(a.crf), "-preset", a.preset,
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                        "-movflags", "+faststart", str(out)], capture_output=True, text=True)
    Path(script).unlink(missing_ok=True)
    if r.returncode != 0:
        raise SystemExit(json.dumps({"error": "ffmpeg a echoue", "stderr": r.stderr[-1200:]}))

    mapping, cur = [], 0.0
    for s, e in segs:
        mapping.append({"src_start": round(s, 3), "src_end": round(e, 3),
                        "out_start": round(cur, 3), "out_end": round(cur + (e - s), 3)})
        cur += e - s
    (WORK / f"{a.slug}_map.json").write_text(json.dumps(
        {"slug": a.slug, "cut": str(out), "segments": mapping,
         "out_duration": round(cur, 3)}, ensure_ascii=False, indent=1))
    print(json.dumps({"ok": True, "segments": len(segs), "avant": round(plan["duration"], 1),
                      "apres": round(cur, 1),
                      "gain_pct": round(100 * (1 - cur / plan["duration"])),
                      "cut": str(out)}, ensure_ascii=False))

if __name__ == "__main__": main()
