#!/usr/bin/env python3
"""COMPOSITION HyperFrames -> index.html

Doctrines de reference (font foi) :
  - camera  : skill `video-editing-camera-moves`   (drift + punch, chainage, bornes)
  - overlays: skill `video-editing-word-subtitles` (rarete, mot a mot, lead 0.12s, placements)

  python3 tools/build_composition.py <slug> [--width 1080] [--height 1920]
"""
import argparse, html, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work"

# Doctrine camera : bornes de travail
S_MIN, S_MAX = 1.02, 1.13
PUNCH_JUMP, PUNCH_SETTLE, PUNCH_DUR = 0.075, 0.055, 3.0   # +7.5%, retombee ~2%, 3s
DRIFT_SPREAD = 0.03                                        # 3% (doctrine : 2-4%)
DRIFT_TARGET = 10.0                                        # doctrine : 5-15 s

def esc(s): return html.escape(s, quote=True)
def clamp(v): return round(max(S_MIN, min(S_MAX, v)), 4)

def build_cam(dur, punches):
    """CAM = [t, from, to, duration, ease]. Les drifts CHAINENT (from == to precedent).
       Un punch saute de +7.5% au-dessus du to precedent, puis retombe."""
    cam, cur, up = [], 1.04, True
    bounds = sorted({0.0, *[p for p in punches if 0 < p < dur], dur})
    for i in range(len(bounds) - 1):
        t0, t1 = bounds[i], bounds[i + 1]
        span = t1 - t0
        if span <= 0.05: continue
        if i > 0 and abs(t0 - min(punches, key=lambda p: abs(p - t0), default=-99)) < 1e-6:
            pd = min(PUNCH_DUR, span)
            a, b = clamp(cur + PUNCH_JUMP), clamp(cur + PUNCH_SETTLE)
            cam.append([round(t0, 3), a, b, round(pd, 3), "power2.out"])
            cur = b
            t0, span = t0 + pd, span - pd
            if span <= 0.05: continue
        n = max(1, round(span / DRIFT_TARGET))
        seg = span / n
        for k in range(n):
            nxt = clamp(cur + (DRIFT_SPREAD if up else -DRIFT_SPREAD))
            cam.append([round(t0 + k * seg, 3), clamp(cur), nxt, round(seg, 3), "power1.inOut"])
            cur, up = nxt, not up
    return cam

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--width", type=int, default=None); ap.add_argument("--height", type=int, default=None)
    ap.add_argument("--no-cam", action="store_true")
    ap.add_argument("--no-sfx", action="store_true")
    a = ap.parse_args()

    c = {}
    f = ROOT / "config.json"
    if f.exists(): c = json.loads(f.read_text())
    vis = c.get("visual", {})
    W = a.width or vis.get("width", 1080); H = a.height or vis.get("height", 1920)
    family = vis.get("fontFamily", "Inter")
    color = vis.get("textColor", "#ffffff")
    # Doctrine : 80-96 / 94-100 / 96-124 px sur 1920 de LARGE (VSL paysage).
    # En vertical le cadre est bien plus etroit : le ratio pur donne un texte minuscule.
    # Defaut : x1.5 en portrait. Surchargeable par visual.sizeScale.
    scale_ui = float(vis.get("sizeScale", 1.5 if H > W else 1.0))
    r = W / 1920.0
    SZ = {"side": round(88 * r * scale_ui), "center": round(97 * r * scale_ui),
          "topline": round(110 * r * scale_ui)}
    SHADOW = ("0 2px 5px rgba(0,0,0,0.9), 0 6px 18px rgba(0,0,0,0.75), "
              "0 14px 40px rgba(0,0,0,0.55)")   # doctrine : 3 couches, aucune plaque

    sfxc = c.get("sfx", {})
    sfx_on = (not a.no_sfx) and sfxc.get("enabled", True)
    SFXDIR = ROOT / "assets" / "sfx"

    mj, oj = WORK / f"{a.slug}_map.json", WORK / f"{a.slug}_overlays.json"
    for p in (mj, oj):
        if not p.exists(): raise SystemExit(json.dumps({"error": f"{p} absent"}))
    m = json.loads(mj.read_text()); ov = json.loads(oj.read_text())
    dur = float(m["out_duration"]); cut = Path(m["cut"]).name
    kept = [o for o in ov["overlays"] if o.get("keep") and o["start"] < dur]
    kept.sort(key=lambda o: o["start"])

    # Doctrine placements : alterner gauche/droite, promouvoir les plus forts au centre
    ROT = ["nL", "nR", "nL", "nR"]
    nodes, tw, i_alt = [], [], 0
    for o in kept:
        if o.get("punch"):
            place = "topline" if (i_alt % 2 == 0) else "nC"
        else:
            place = ROT[i_alt % len(ROT)]
        i_alt += 1
        st = round(max(0.0, o["start"] - 0.12), 3)          # le clip ouvre AVANT le lead
        en = min(float(o["end"]) + 0.45, dur)
        d = round(en - st, 3)
        if d <= 0.1: continue
        oid = f"ov-{o['id']}"
        spans = " ".join(f'<span class="w">{esc(w["w"])}</span>' for w in o["words"])
        nodes.append(f'      <div class="clip note {place}" id="{oid}" data-start="{st}" '
                     f'data-duration="{d}" data-track-index="5">{spans}</div>')
        # doctrine : ne jamais declencher avant le data-start du clip (clamp).
        # Le clamp peut coller deux mots sur le meme instant -> on garde un ecart
        # minimal strictement croissant, sinon les tweens se chevauchent.
        times, prev = [], None
        for w in o["words"]:
            t = max(st, float(w["start"]))
            if prev is not None and t < prev + 0.02: t = prev + 0.02
            times.append(round(t, 3)); prev = t
        tw.append(f'  wIn("#{oid}", {json.dumps(times)});')
        tw.append(f'  noteOut("#{oid}", {round(min(en - 0.3, dur), 3)});')
        tw.append(f'  tl.set("#{oid}", {{ opacity: 0 }}, {round(en, 3)});')  # hard-kill

    punches = [float(o["start"]) for o in kept if o.get("punch")]
    cam = [] if a.no_cam else build_cam(dur, punches)

    # SFX : un whoosh legerement AVANT chaque punch, un tick sur chaque jointure de derush.
    # Sons synthetises localement (make_sfx.py), libres de droits.
    sfx_nodes, n_whoosh, n_tick = [], 0, 0
    if sfx_on and SFXDIR.exists():
        vw = float(sfxc.get("whooshVolume", 0.7))
        vt = float(sfxc.get("tickVolume", 0.35))
        lead = float(sfxc.get("leadSeconds", 0.06))
        if (SFXDIR / "whoosh.wav").exists():
            for k, p in enumerate(sorted(punches)):
                t = round(max(0.0, p - lead), 3)
                if t >= dur: continue
                sfx_nodes.append(
                    f'      <audio id="sfx-w{k}" src="assets/sfx/whoosh.wav" data-start="{t}" '
                    f'data-duration="0.42" data-track-index="11" data-volume="{vw}"></audio>')
                n_whoosh += 1
        if (SFXDIR / "tick.wav").exists():
            joints = [round(float(sg["out_start"]), 3) for sg in m["segments"][1:]]
            for k, t in enumerate(joints):
                if t <= 0.05 or t >= dur: continue
                sfx_nodes.append(
                    f'      <audio id="sfx-t{k}" src="assets/sfx/tick.wav" data-start="{t}" '
                    f'data-duration="0.09" data-track-index="12" data-volume="{vt}"></audio>')
                n_tick += 1

    doc = f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width={W}, height={H}" />
<title>{esc(a.slug)}</title>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
  html, body {{ margin: 0; padding: 0; background: #000; }}
  #root {{ position: relative; width: {W}px; height: {H}px; overflow: hidden; }}
  #bg {{ position: absolute; inset: 0; background: #000; }}
  .zw {{ position: absolute; inset: 0; overflow: hidden; }}
  #cam {{ position: absolute; inset: 0; transform-origin: 50% 42%; will-change: transform; }}
  #a-roll {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
  .note {{
    position: absolute; font-family: {family}; font-weight: 800; color: {color};
    line-height: 1.1; letter-spacing: -0.01em; text-shadow: {SHADOW}; text-wrap: balance;
  }}
  .note .w {{ display: inline-block; }}
  .nL {{ left: {round(90 * r)}px; width: {round(W * 0.58)}px; text-align: left;  top: {round(H * 0.52)}px; font-size: {SZ['side']}px; }}
  .nR {{ right: {round(90 * r)}px; width: {round(W * 0.58)}px; text-align: right; top: {round(H * 0.58)}px; font-size: {SZ['side']}px; }}
  .nC {{ left: {round(70 * r)}px; right: {round(70 * r)}px; text-align: center; top: {round(H * 0.72)}px; font-size: {SZ['center']}px; }}
  .topline {{ left: {round(70 * r)}px; right: {round(70 * r)}px; text-align: center; top: {round(H * 0.16)}px;
              font-size: {SZ['topline']}px; text-transform: uppercase; }}
</style>
</head>
<body>
  <div id="root" data-composition-id="reel" data-start="0"
       data-width="{W}" data-height="{H}" data-duration="{dur}">
    <div id="bg"></div>
    <div class="zw">
      <div id="cam">
        <video id="a-roll" class="clip" src="assets/{esc(cut)}"
               data-start="0" data-duration="{dur}" data-track-index="0" muted playsinline></video>
      </div>
    </div>
    <audio id="a-roll-audio" src="assets/{esc(cut)}"
           data-start="0" data-duration="{dur}" data-track-index="10" data-volume="1"></audio>

{chr(10).join(sfx_nodes)}
{chr(10).join(nodes)}
  </div>
<script>
  window.__timelines = window.__timelines || {{}};
  const tl = gsap.timeline({{ paused: true }});

  /* doctrine word-subtitles : lead de 0.12s pour que la revelation tombe SUR le mot */
  function wIn(sel, times) {{
    const spans = document.querySelectorAll(sel + " .w");
    times.forEach(function (t, i) {{
      if (spans[i]) tl.fromTo(spans[i], {{ opacity: 0, y: 16 }},
        {{ opacity: 1, y: 0, duration: 0.24, ease: "power2.out", immediateRender: false }},
        Math.max(0, t - 0.12));
    }});
  }}
  function noteOut(sel, t) {{
    tl.to(sel, {{ opacity: 0, y: -14, duration: 0.3, ease: "power2.in" }}, t);
  }}

  /* doctrine camera-moves : [t, from, to, duration, ease] — drifts chaines, punchs rares */
  var CAM = {json.dumps(cam)};
  CAM.forEach(function (c) {{
    tl.fromTo("#cam", {{ scale: c[1] }},
      {{ scale: c[2], duration: c[3], ease: c[4], immediateRender: false }}, c[0]);
  }});

{chr(10).join(tw)}

  window.__timelines["reel"] = tl;
}}
</script>
</body>
</html>
"""
    doc = doc.replace("\n}\n</script>", "\n</script>")
    (ROOT / "index.html").write_text(doc, encoding="utf-8")
    drifts = sum(1 for x in cam if x[4] == "power1.inOut")
    print(json.dumps({"ok": True, "format": f"{W}x{H}", "duree": dur,
                      "overlays": len(nodes), "cam_entries": len(cam),
                      "drifts": drifts, "punchs": len(cam) - drifts,
                      "sfx_whoosh": n_whoosh, "sfx_tick": n_tick,
                      "tailles_px": SZ,
                      "suite": "npx hyperframes lint  puis  npx hyperframes preview"},
                     ensure_ascii=False))

if __name__ == "__main__": main()
