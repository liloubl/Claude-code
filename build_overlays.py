#!/usr/bin/env python3
"""OVERLAYS : propose des candidats de sous-titres mot-a-mot -> work/<slug>_overlays.json

Doctrine de reference : skill `video-editing-word-subtitles` (Thomas, valide aout 2026).
Ce ne sont PAS des sous-titres de couverture. Ce sont des overlays RARES qui amplifient.

Ce script ne DECIDE rien : il recale les mots sur le derush, decoupe en phrases verbatim,
les score, et propose une selection. L'agent tranche en editant "keep", "punch" et "reason".
Cible : ~5 overlays par minute (15 sur 3 minutes). Le script pre-coche a cette densite.

  python3 tools/build_overlays.py <slug> [--per-minute 5]
"""
import argparse, json, re, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work"
STRONG = re.compile(r"[.!?…]+$")
STRIP_END = re.compile(r"[.,;:!?…]+$")
NUM = re.compile(r"\d")

FILLER = {"alors", "donc", "voila", "en", "fait", "du", "coup", "genre", "bah", "ben",
          "euh", "hein", "quoi", "et", "mais", "enfin", "tu", "vois", "je", "veux", "dire"}

def deac(s):
    return "".join(c for c in unicodedata.normalize("NFD", s.lower())
                   if unicodedata.category(c) != "Mn")

def remap(words, segments):
    out = []
    for w in words:
        for s in segments:
            if w["start"] >= s["src_start"] - 1e-3 and w["end"] <= s["src_end"] + 1e-3:
                d = s["out_start"] - s["src_start"]
                out.append({"w": w["w"], "start": round(w["start"] + d, 3),
                            "end": round(w["end"] + d, 3)})
                break
    return out

def score(phrase_words, text):
    """Heuristique de puissance. L'agent la corrige, elle ne fait qu'ordonner."""
    n = len(phrase_words)
    s = 0.0
    if NUM.search(text): s += 3.0                      # un chiffre porte toujours
    if 3 <= n <= 8: s += 2.0                           # longueur lisible d'un coup
    elif n <= 2: s += 0.5
    else: s -= (n - 8) * 0.4                           # trop long = on lit au lieu d'ecouter
    toks = [deac(STRIP_END.sub("", w["w"])) for w in phrase_words]
    ratio = sum(1 for t in toks if t in FILLER) / max(n, 1)
    s -= ratio * 4.0                                   # connectif = zero valeur
    if any(t in ("jamais", "personne", "rien", "aucun", "gratuit", "gratuitement",
                 "secret", "enfin", "impossible") for t in toks): s += 1.5
    caps = sum(1 for w in phrase_words if w["w"][:1].isupper() and not w["w"].isupper())
    if caps and n <= 6: s += 0.8                       # nom propre / nom de produit
    return round(s, 2)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--per-minute", type=float, default=5.0)
    ap.add_argument("--gap", type=float, default=0.45, help="trou qui ferme une phrase (s)")
    ap.add_argument("--max-words", type=int, default=8)
    a = ap.parse_args()

    wj, mj = WORK / f"{a.slug}_words.json", WORK / f"{a.slug}_map.json"
    for p in (wj, mj):
        if not p.exists(): raise SystemExit(json.dumps({"error": f"{p} absent"}))
    words = json.loads(wj.read_text())["words"]
    m = json.loads(mj.read_text())
    ws = remap(words, m["segments"])
    if not ws: raise SystemExit(json.dumps({"error": "aucun mot apres recalage"}))
    dur = float(m["out_duration"])

    # decoupage en phrases verbatim : ponctuation forte, trou long, ou longueur max
    phrases, cur = [], []
    for w in ws:
        if cur and (w["start"] - cur[-1]["end"] > a.gap or len(cur) >= a.max_words):
            phrases.append(cur); cur = []
        cur.append(w)
        if STRONG.search(w["w"]): phrases.append(cur); cur = []
    if cur: phrases.append(cur)

    cands = []
    for i, ph in enumerate(phrases):
        text = " ".join(STRIP_END.sub("", x["w"]) for x in ph).strip()
        text = re.sub(r"\s{2,}", " ", text)
        if not text: continue
        cands.append({"id": len(cands), "text": text,
                      "start": round(ph[0]["start"], 3), "end": round(ph[-1]["end"], 3),
                      "score": score(ph, text),
                      "words": [{"w": STRIP_END.sub("", x["w"]), "start": x["start"]} for x in ph],
                      "keep": False, "punch": False, "reason": ""})

    target = max(1, round(dur / 60.0 * a.per_minute))
    for c in sorted(cands, key=lambda x: -x["score"])[:target]:
        c["keep"] = True
    # les 2 meilleures gardees deviennent des candidats punch (max ~2/minute)
    kept = sorted([c for c in cands if c["keep"]], key=lambda x: -x["score"])
    for c in kept[:max(1, round(dur / 60.0 * 2))]:
        c["punch"] = True

    dst = WORK / f"{a.slug}_overlays.json"
    dst.write_text(json.dumps({"slug": a.slug, "out_duration": dur,
                               "doctrine": "video-editing-word-subtitles",
                               "cible_overlays": target, "n_candidats": len(cands),
                               "overlays": cands}, ensure_ascii=False, indent=1))
    print(json.dumps({"ok": True, "candidats": len(cands), "pre_selectionnes": target,
                      "punchs_proposes": sum(1 for c in cands if c["punch"]),
                      "mots_perdus_dans_les_coupes": len(words) - len(ws),
                      "out": str(dst),
                      "note": "edite keep/punch/reason avant build_composition.py"},
                     ensure_ascii=False))

if __name__ == "__main__": main()
