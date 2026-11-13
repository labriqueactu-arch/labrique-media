#!/usr/bin/env python3
"""La Brique : moteur de Reels. Une fiche JSON devient un MP4 1080 × 1920 en motion design, avec voix off.

Usage :
  python3 tools/video/reel.py fiche.json sortie.mp4                 MP4 + sortie-cover.jpg + rapport
  python3 tools/video/reel.py fiche.json sortie.mp4 --frames 0.5,2,6 images de contrôle seulement (rapide)
  python3 tools/video/reel.py fiche.json sortie.mp4 --sans-son      vidéo sans piste voix ni sons
  --essai : le registre des photos n'est pas mis à jour (rendu de travail)

Rendu : scène HTML (tools/video/scene.js) avec les tokens, polices et composants du design system,
animée par window.seek(t), capturée image par image par Playwright (30 i/s) et encodée par ffmpeg.
Voix : Piper, modèle local tools/video/voix/<modele>.onnx (aucun appel réseau). Sons : tools/video/sons/.
Aucune image ni voix générée ne représente un joueur : le joueur est la photo libre détourée,
la voix est celle d'un narrateur.

Contrôles (refus avec sortie_refuse.jpg) : polices ; texte sous 40 px ; texte hors zone sûre
(250 px en haut, 420 px en bas, 140 px à droite) ; plus de 8 mots à l'écran hors carte de fin ;
texte ou pastille sur le visage ; visage coupé ; photo déjà utilisée ; durée hors 9 à 13 s ;
ffprobe (h264, yuv420p, 1080 × 1920, 30 i/s, audio) ; niveau sonore hors −14 LUFS ± 1,5.
"""
import json, re, subprocess, sys, tempfile, wave
from pathlib import Path

VIDEO = Path(__file__).resolve().parent
TOOLS = VIDEO.parent
DS = TOOLS / "ds"
sys.path.insert(0, str(TOOLS))
W, H, FPS = 1080, 1920, 30
ZONE = {"haut": 250, "bas": H - 420, "droite": W - 140, "gauche": 40}
THEMES = {"SWISH": "os", "REBOND": "affiche", "BRIQUE": "sombre", None: "affiche"}


def erreur(msg):
    sys.exit("ERREUR : " + msg)


def voix(fiche, dossier):
    """Synthétise chaque réplique ; renvoie [(t, chemin, durée)]."""
    v = fiche.get("voix") or {}
    if not v.get("repliques"):
        return []
    modele = VIDEO / "voix" / f"{v.get('modele', 'fr_FR-tom-medium')}.onnx"
    if not modele.exists():
        erreur(f"voix absente : {modele}. Lis tools/video/VIDEO.md (section Voix).")
    sortie = []
    for i, r in enumerate(v["repliques"]):
        p = dossier / f"voix{i}.wav"
        res = subprocess.run([sys.executable, "-m", "piper", "-m", str(modele), "-f", str(p),
                              "--length-scale", str(v.get("vitesse", 0.92)), "--sentence-silence", "0.05"],
                             input=r["texte"], text=True, capture_output=True)
        if res.returncode or not p.exists():
            erreur("Piper : " + res.stderr[-300:])
        d = rogner(p)
        t0 = float(r["t"]) if r.get("t") is not None else (sortie[-1][0] + sortie[-1][2] + v.get("ecart", 0.22) if sortie else 0.15)
        sortie.append((round(t0, 2), p, d))
    for (t0, _, d0), (t1, _, _) in zip(sortie, sortie[1:]):
        if t0 + d0 > t1 - 0.05:
            erreur(f"la réplique de {t0} s dure {d0:.2f} s et chevauche la suivante ({t1} s) : raccourcis le texte ou décale")
    t_last, _, d_last = sortie[-1]
    if t_last + d_last > fiche["duree"] - 0.2:
        erreur(f"la voix finit à {t_last + d_last:.2f} s, après la fin de la vidéo ({fiche['duree']} s)")
    return sortie


def rogner(p, seuil=0.012):
    """Coupe le silence en fin de réplique ; renvoie la durée."""
    import numpy as np
    with wave.open(str(p)) as w:
        sr, n, ch, sw = w.getframerate(), w.getnframes(), w.getnchannels(), w.getsampwidth()
        x = np.frombuffer(w.readframes(n), dtype="<i2")
    a = np.abs(x.astype(float)) / 32768
    fort = np.nonzero(a > seuil)[0]
    fin = min(len(x), (fort[-1] if len(fort) else len(x)) + int(0.06 * sr))
    with wave.open(str(p), "wb") as w:
        w.setnchannels(ch); w.setsampwidth(sw); w.setframerate(sr); w.writeframes(x[:fin].tobytes())
    return fin / sr


def temps(fiche, repl):
    """Repères de la timeline, calés sur la voix quand elle existe."""
    t = {"joueur": 2.4, "punch": 5.6, "fin": 8.3}
    if len(repl) >= 4:
        t = {"joueur": repl[1][0], "punch": repl[2][0], "fin": repl[3][0]}
    t.update(fiche.get("temps") or {})
    t["stats"] = [t["joueur"] + 0.45 + 0.65 * i for i in range(len(fiche["stats"]))]
    t["sceau"] = t["punch"] + 1.0
    return t


def page_html(fiche, f_js):
    css = (DS / "tokens.css").read_text(encoding="utf-8").replace('url("fonts/', f'url("{(DS / "fonts").as_uri()}/')
    css += (DS / "bundle.css").read_text(encoding="utf-8")
    js = lambda p: f'<script src="{p.as_uri()}"></script>'
    return f"""<!doctype html><html lang="fr" data-theme="affiche"><head><meta charset="utf-8">
<style>{css} html,body{{margin:0;background:#000;width:{W}px;height:{H}px;overflow:hidden}}</style>
{js(DS / 'lib/react.production.min.js')}{js(DS / 'lib/react-dom.production.min.js')}{js(DS / 'bundle.js')}
</head><body><div id="root"></div>
<script>window.FICHE = {json.dumps(f_js, ensure_ascii=False)};</script>{js(VIDEO / 'scene.js')}</body></html>"""


def controler(c, visages, t):
    probs = []
    if not all(c["polices"]):
        probs.append("polices non chargées")
    j = c["joueur"]
    faces = [(j["x"] + b[0] * j["w"], j["y"] + b[1] * j["h"], j["x"] + b[2] * j["w"], j["y"] + b[3] * j["h"]) for b in visages]
    coupe = lambda a, b, m: a[0] < b[2] + m and a[2] > b[0] - m and a[1] < b[3] + m and a[3] > b[1] - m
    mots = 0
    for x in c["textes"]:
        r = (x["x0"], x["y0"], x["x1"], x["y1"])
        if x["taille"] < 39.5:
            probs.append(f"texte sous 40 px : « {x['texte']} » ({x['taille']} px)")
        if not x["heros"] and (r[1] < ZONE["haut"] or r[3] > ZONE["bas"] or r[2] > ZONE["droite"] or r[0] < ZONE["gauche"] - 1):
            probs.append(f"texte hors zone sûre : « {x['texte']} » ({int(r[0])},{int(r[1])} → {int(r[2])},{int(r[3])})")
        if not x["heros"] and any(coupe(r, f, 6) for f in faces):
            probs.append(f"texte sur le visage : « {x['texte']} »")
        if not (x["fin"] or x["logo"]):
            mots += 1 if x["heros"] else len(x["texte"].split())
    for m in c["modules"]:
        if any(coupe((m["x0"], m["y0"], m["x1"], m["y1"]), f, 4) for f in faces):
            probs.append("pastille ou sceau sur le visage")
    for f in faces:
        if f[0] < -4 or f[1] < -4 or f[2] > W + 4 or f[3] > H + 4:
            probs.append("visage coupé par le bord")
    if mots > 8:
        probs.append(f"{mots} mots à l'écran (8 au plus hors carte de fin)")
    return [f"{t:.1f} s : {p}" for p in dict.fromkeys(probs)]


def audio(fiche, repl, T, dossier, sortie):
    S = VIDEO / "sons"
    ev = [(0.18, "impact", -4), (0.0, "whoosh", -10), (T["joueur"], "whoosh", -12), (T["fin"], "swish", -6)]
    for t0 in T["stats"]:
        ev += [(t0 + i * 0.07, "tick", -14) for i in range(9)]
    if fiche.get("verdict"):
        son = {"SWISH": "swish", "REBOND": "rebond", "BRIQUE": "impact"}[fiche["verdict"]]
        ev += [(T["sceau"] + 0.18, "tampon", -4), (T["sceau"] + 0.25, son, -6)]
    entrees, filtres = [], []
    for i, (t0, nom, db) in enumerate(ev):
        entrees += ["-i", str(S / f"{nom}.wav")]
        filtres.append(f"[{i}:a]aresample=48000,volume={db}dB,adelay={int(t0 * 1000)}|{int(t0 * 1000)}[s{i}]")
    n = len(ev)
    for j, (t0, p, _) in enumerate(repl):
        entrees += ["-i", str(p)]
        filtres.append(f"[{n + j}:a]aresample=48000,pan=stereo|c0=c0|c1=c0,highpass=f=90,acompressor=threshold=-18dB:ratio=3,volume=3dB,adelay={int(t0 * 1000)}|{int(t0 * 1000)}[v{j}]")
    labels = "".join(f"[s{i}]" for i in range(n)) + "".join(f"[v{j}]" for j in range(len(repl)))
    filtres.append(f"{labels}amix=inputs={n + len(repl)}:normalize=0,apad,atrim=0:{fiche['duree']},loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[out]")
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", *entrees, "-filter_complex", ";".join(filtres), "-map", "[out]", "-ac", "2", str(sortie)], capture_output=True, text=True)
    if r.returncode:
        erreur("mixage : " + r.stderr[-400:])


def main():
    a = sys.argv[1:]
    essai, sans_son = "--essai" in a, "--sans-son" in a
    frames = None
    if "--frames" in a:
        frames = [float(x) for x in a[a.index("--frames") + 1].split(",")]
        a = a[:a.index("--frames")] + a[a.index("--frames") + 2:]
    a = [x for x in a if not x.startswith("--")]
    if len(a) != 2:
        sys.exit(__doc__)
    fiche_p, out = Path(a[0]).resolve(), Path(a[1]).resolve()
    F = json.loads(fiche_p.read_text(encoding="utf-8"))
    base = fiche_p.parent
    if F.get("format") != "recap":
        erreur("format inconnu (seul « recap » existe pour l'instant)")
    if not 9 <= F["duree"] <= 13:
        erreur(f"durée {F['duree']} s hors de la plage 9 à 13 s")
    photo = (base / F["photo"]).resolve()
    if not photo.exists():
        erreur(f"photo introuvable : {photo}")
    import photos as registre
    src = F.get("source_photo")
    if not src and not essai:
        erreur("la fiche doit déclarer \"source_photo\": {\"url\", \"auteur\", \"joueur\"}")
    e = registre.conflit(photo, src, post=out.stem)
    if e:
        erreur(registre.message(e))
    from faces import detect
    vis = detect(photo)["boites"]
    if not vis:
        erreur("aucun visage détecté sur la photo : le contrôle visage est impossible, choisis une photo où le visage est net")
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="reel-"))
    from trame import trame
    fantome = tmp / "fantome.png"
    trame(photo, fantome)
    repl = [] if (sans_son or frames) else voix(F, tmp)
    if frames and (F.get("voix") or {}).get("repliques"):
        repl = voix(F, tmp)  # la voix fixe les temps, même pour les images de contrôle
    T = temps(F, repl)
    fj = dict(F, photo=photo.as_uri(), fantome=fantome.as_uri(), theme=THEMES[F.get("verdict")], temps=T,
              cadre=F.get("cadre") or {"x": 330, "y": 430, "l": 760})
    html = tmp / "scene.html"
    html.write_text(page_html(F, fj), encoding="utf-8")

    from playwright.sync_api import sync_playwright
    n = round(F["duree"] * FPS)
    problemes = []
    with sync_playwright() as pw:
        b = pw.chromium.launch(args=["--allow-file-access-from-files"])
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(html.as_uri())
        pg.wait_for_selector(".lb-post", timeout=15000)
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(500)
        if errs:
            erreur("JavaScript : " + errs[0])
        if frames:
            for t in frames:
                pg.evaluate(f"seek({t})")
                p = out.with_name(f"{out.stem}_{t:05.2f}s.jpg")
                pg.screenshot(path=str(p), type="jpeg", quality=90)
                pr = controler(pg.evaluate("controles()"), vis, t)
                print(p.name, "OK" if not pr else " | ".join(pr))
            b.close()
            return
        silencieux = tmp / "video.mp4"
        enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
                                "-vf", "scale=out_range=tv,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-color_range", "tv", "-r", str(FPS), str(silencieux)],
                               stdin=subprocess.PIPE)
        for i in range(n):
            t = i / FPS
            pg.evaluate(f"seek({t})")
            img = pg.screenshot(type="jpeg", quality=95)
            if i % (FPS // 2) == 0:
                pr = controler(pg.evaluate("controles()"), vis, t)
                if pr:
                    out.with_name(out.stem + "_refuse.jpg").write_bytes(img)
                    problemes += pr
            if i == round(1.0 * FPS):
                out.with_name(out.stem + "-cover.jpg").write_bytes(img)
            enc.stdin.write(img)
        enc.stdin.close()
        enc.wait()
        b.close()
    if problemes:
        out.with_name(out.stem + "-cover.jpg").unlink(missing_ok=True)
        erreur(" ; ".join(problemes[:6]) + ". Corrige la fiche (cadre, textes, temps) puis relance. Ne publie pas.")
    if sans_son:
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(silencieux), "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-shortest",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(out)], check=True)
    else:
        son = tmp / "audio.wav"
        audio(F, repl, T, tmp, son)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(silencieux), "-i", str(son), "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
                        "-ar", "48000", "-ac", "2", "-shortest", "-movflags", "+faststart", str(out)], check=True)
    rapport = verifier(out, sans_son)
    if not essai:
        registre.marquer(photo, src, out.stem)
    print(json.dumps(dict(rapport, ok=True, sortie=str(out), couverture=str(out.with_name(out.stem + "-cover.jpg"))), ensure_ascii=False))


def verifier(out, sans_son):
    p = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(out)], capture_output=True, text=True).stdout)
    v = next(s for s in p["streams"] if s["codec_type"] == "video")
    au = [s for s in p["streams"] if s["codec_type"] == "audio"]
    probs = []
    if v["codec_name"] != "h264" or v["pix_fmt"] != "yuv420p" or (v["width"], v["height"]) != (W, H) or v["r_frame_rate"] != f"{FPS}/1":
        probs.append(f"vidéo non conforme ({v['codec_name']}, {v['pix_fmt']}, {v['width']}×{v['height']}, {v['r_frame_rate']})")
    if not au:
        probs.append("piste audio absente")
    lufs = None
    if not sans_son:
        m = subprocess.run(["ffmpeg", "-v", "info", "-i", str(out), "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
        lufs = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", m)[-1])
        if abs(lufs + 14) > 1.5:
            probs.append(f"niveau sonore {lufs} LUFS (cible −14)")
    if probs:
        erreur(" ; ".join(probs))
    return {"duree": float(p["format"]["duration"]), "taille_mo": round(int(p["format"]["size"]) / 1e6, 2), "lufs": lufs}


if __name__ == "__main__":
    main()
