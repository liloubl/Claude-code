#!/usr/bin/env python3
"""PLAN DE COUPE deterministe -> work/<slug>_plan.json

Un LLM ne donne JAMAIS un timestamp. Le OU couper vient d'ici
(ffmpeg silencedetect + timestamps mot a mot). Le QUOI garder vient de l'agent,
qui n'ecrit que "keep" et "reason".

  python3 tools/cut_plan.py <slug> [--min-silence 0.45] [--noise -32]
"""
import argparse, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work"

def silences(src, noise, mind):
    log = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(src),
                          "-af", f"silencedetect=noise={noise}dB:d={mind}", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    st = [float(x) for x in re.findall(r"silence_start:\s*(-?[\d.]+)", log)]
    en = [float(x) for x in re.findall(r"silence_end:\s*([\d.]+)", log)]
    out = []
    for i, s in enumerate(st):
        out.append((max(0.0, s), en[i] if i < len(en) else None))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--min-silence", type=float, default=None)
    ap.add_argument("--noise", type=float, default=None)
    a = ap.parse_args()
    c = {}
    f = ROOT / "config.json"
    if f.exists(): c = json.loads(f.read_text()).get("derush", {})
    mind = a.min_silence if a.min_silence is not None else c.get("minSilence", 0.45)
    noise = a.noise if a.noise is not None else c.get("noiseDb", -32)

    wj = WORK / f"{a.slug}_words.json"
    if not wj.exists(): raise SystemExit(json.dumps({"error": f"{wj} absent, lance transcribe.py"}))
    d = json.loads(wj.read_text())
    words, src, total = d["words"], Path(d["source"]), float(d["duration"])

    cuts = [{"start": s, "end": (total if e is None else e), "mid": (s + (total if e is None else e)) / 2}
            for s, e in silences(src, noise, mind)]
    cuts = [c2 for c2 in cuts if c2["end"] - c2["start"] >= mind]

    islands, cur = [], []
    for w in words:
        if cur:
            gap = w["start"] - cur[-1]["end"]
            crosses = any(x["start"] <= cur[-1]["end"] + 1e-3 and x["end"] >= w["start"] - 1e-3 for x in cuts)
            if gap >= mind or crosses: islands.append(cur); cur = []
        cur.append(w)
    if cur: islands.append(cur)

    def before(t):
        p = [x for x in cuts if x["end"] <= t + 1e-3]; return round(p[-1]["mid"], 3) if p else 0.0
    def after(t):
        n = [x for x in cuts if x["start"] >= t - 1e-3]; return round(n[0]["mid"], 3) if n else round(total, 3)

    plan = [{"id": i, "text": " ".join(w["w"] for w in isl).strip(),
             "speech_start": round(isl[0]["start"], 3), "speech_end": round(isl[-1]["end"], 3),
             "cut_start": before(isl[0]["start"]), "cut_end": after(isl[-1]["end"]),
             "n_words": len(isl), "keep": True, "reason": ""}
            for i, isl in enumerate(islands)]
    for i in range(len(plan) - 1):
        if plan[i]["cut_end"] > plan[i + 1]["cut_start"]:
            m = round((plan[i]["speech_end"] + plan[i + 1]["speech_start"]) / 2, 3)
            plan[i]["cut_end"] = m; plan[i + 1]["cut_start"] = m

    out = {"slug": a.slug, "source": str(src), "duration": round(total, 3),
           "min_silence": mind, "noise_db": noise,
           "n_islands": len(plan), "n_silences": len(cuts), "islands": plan}
    (WORK / f"{a.slug}_plan.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps({"ok": True, "islands": len(plan), "silences": len(cuts),
                      "duration": round(total, 1),
                      "out": str(WORK / f"{a.slug}_plan.json")}, ensure_ascii=False))

if __name__ == "__main__": main()
