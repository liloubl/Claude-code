#!/usr/bin/env python3
"""Synthetise la banque de SFX -> assets/sfx/*.wav  (une fois, a l'installation)

Sons generes par ffmpeg, donc LIBRES DE DROITS et redistribuables avec le package.
Aucun telechargement, aucune banque tierce, aucune licence a verifier.

  python3 tools/make_sfx.py [--force]
"""
import argparse, json, subprocess
from pathlib import Path

SFX = Path(__file__).resolve().parent.parent / "assets" / "sfx"

# name -> (duree, chaine de filtres ffmpeg)
RECIPES = {
    # souffle montant court : accompagne un punch-in
    "whoosh": (0.42,
        "anoisesrc=d=0.42:c=pink:a=0.5,"
        "highpass=f=300,lowpass=f=6000,"
        "afade=t=in:st=0:d=0.22:curve=exp,afade=t=out:st=0.24:d=0.18,"
        "volume=0.55"),
    # impact sourd tres court : marque une coupe franche
    "thump": (0.26,
        "sine=frequency=92:duration=0.26,"
        "afade=t=out:st=0.02:d=0.24:curve=exp,volume=0.42"),
    # clic doux : jointure de derush, presque subliminal
    "tick": (0.09,
        "anoisesrc=d=0.09:c=white:a=0.3,"
        "highpass=f=1800,afade=t=out:st=0:d=0.09,volume=0.20"),
    # montee courte : avant une revelation
    "riser": (0.9,
        "anoisesrc=d=0.9:c=pink:a=0.35,"
        "highpass=f=200,"
        "afade=t=in:st=0:d=0.85:curve=exp,afade=t=out:st=0.85:d=0.05,"
        "volume=0.4"),
}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    SFX.mkdir(parents=True, exist_ok=True)
    made, skipped = [], []
    for name, (d, filt) in RECIPES.items():
        out = SFX / f"{name}.wav"
        if out.exists() and not a.force: skipped.append(name); continue
        r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                            "-i", f"anullsrc=r=48000:cl=stereo:d={d}",
                            "-filter_complex", f"{filt},aformat=channel_layouts=stereo[a]",
                            "-map", "[a]", "-ar", "48000", str(out)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(json.dumps({"error": f"generation {name} echouee",
                                         "stderr": r.stderr[-800:]}, ensure_ascii=False))
        made.append(name)
    print(json.dumps({"ok": True, "generes": made, "deja_presents": skipped,
                      "dossier": str(SFX)}, ensure_ascii=False))

if __name__ == "__main__": main()
