#!/usr/bin/env python3
"""La Brique : Reels version 2, « dynamiques ». reel.py passe la main ici quand la fiche porte "version": 2.

Voix : tout le script part en une seule requête ElevenLabs (eleven_v4, voix Max) avec une balise de ton par phrase,
ce qui garde une intonation continue. La réponse porte l'horodatage de chaque caractère : on en tire les mots,
on resserre les blancs (silence voulu avant le verdict compris), on ajuste le débit, et toute la timeline
(coupes, mots à l'écran, sous-titres, compteurs, tampon, sons) suit ces temps.

Image : scène recap2.js + boîte à outils motion.js (caméra 2.5D, punch in, whip pan, flash, tremblement,
typo cinétique, compteurs, éclats, volet brique, grain animé).

Contrôles en plus de ceux de reel.py : dynamisme (aucune fenêtre de 0,7 s molle), accroche (texte et mouvement
dès l'image 1, voix avant 0,25 s), voix (débit, variation de hauteur, blancs), sous-titres (décalage sous 80 ms),
durée selon le format.
"""
import base64, hashlib, json, os, re, subprocess, sys, tempfile, urllib.error, urllib.request, wave
from pathlib import Path

import numpy as np

import reel as R
import analyse as A

W, H, FPS = R.W, R.H, R.FPS
VIDEO, DS = R.VIDEO, R.DS
SR = 48000

# ---------- seuils (calibrés le 14/11/2026 : les 4 anciens Reels échouent, voir video/diagnostic) ----------
SEUIL_DYNAMISME = 1.6      # différence moyenne entre images (sur 255, 270 × 480) sur toute fenêtre de 0,7 s
SEUIL_ACCROCHE = 1.6       # mouvement moyen des 3 premières transitions d'images
VOIX_DEBUT_MAX = 0.25      # premier mot avant 0,25 s
DEBIT = (3.2, 4.1)         # mots par seconde de parole
DEBIT_CIBLE = 3.6
VARIATION_F0_MIN = 5.0     # demi-tons ; ancienne voix : 3,9 à 4,0 sur la piste entière, 4,6 au plus sur une réplique
BLANC_MAX = 0.6            # hors silence voulu
DECALAGE_ST_MAX = 0.08     # sous-titres
DUREES = {"recap": (8.0, 11.5)}
FIN_APRES_VOIX = 0.75      # carte de fin tenue après le dernier mot

# balises de ton par rôle : retenues au casting du 14/11/2026 (variation de hauteur 5,3 demi-tons contre 3,3 à 3,9
# pour excited/confident/curious/serious/playful, mesure analyse.variation_f0 sur le script SGA)
TONS = {"accroche": "shouting", "joueur": "fast", "contexte": "sarcastic", "verdict": "dramatic",
        "punch": "laughs", "question": "mischievously"}
TONS_ALT = {"accroche": "excited", "joueur": "sarcastic", "contexte": "curious", "verdict": "dramatic",
            "punch": "laughs", "question": "shouting"}  # deuxième direction (5,1 demi-tons au casting), alternée avec la première
PRISES = 4                 # prises de voix au plus (graines différentes) avant refus
ECARTS = {"mot": 0.12, "phrase": 0.16}  # blancs maximum gardés entre mots d'une phrase, entre phrases

MOT = re.compile(r"[\wÀ-ÿ'’]+")


def erreur(m):
    R.erreur(m)


# ---------- voix ----------
def texte_complet(v, tons=None):
    morceaux = []
    for p in v["phrases"]:
        ton = p.get("ton", (tons or TONS).get(p.get("role"), ""))
        morceaux.append((f"[{ton}] " if ton else "") + p["texte"].strip())
    return " ".join(morceaux)


def tts_horodate(v, dossier, graine=None, tons=None):
    texte = texte_complet(v, tons)
    corps = {"seed": graine} if graine is not None else {}
    corps.update({"text": texte, "model_id": v.get("modele", "eleven_v4"), "language_code": "fr",
             "voice_settings": {"stability": v.get("stabilite", 0.0), "similarity_boost": 0.8, "style": v.get("style", 0.6), "use_speaker_boost": True}})
    cache = Path(os.environ.get("LB_CACHE_VOIX", Path.home() / ".cache" / "labrique-voix"))
    cache.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha256(json.dumps(["ts", v["id"], corps], sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:20]
    mp3, js = cache / f"{h}.mp3", cache / f"{h}.json"
    if not (mp3.exists() and js.exists()):
        req = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{v['id']}/with-timestamps?output_format=mp3_44100_128",
                                     data=json.dumps(corps).encode(), method="POST",
                                     headers={"xi-api-key": R.cle_elevenlabs(), "Content-Type": "application/json", "User-Agent": "LaBrique/1.0"})
        try:
            d = json.loads(urllib.request.urlopen(req, timeout=180).read())
        except urllib.error.HTTPError as e:
            erreur(f"ElevenLabs {e.code} : {e.read()[:300]!r}")
        mp3.write_bytes(base64.b64decode(d["audio_base64"]))
        js.write_text(json.dumps(d.get("alignment") or d.get("normalized_alignment"), ensure_ascii=False), encoding="utf-8")
    al = json.loads(js.read_text(encoding="utf-8"))
    wav = dossier / f"voix_brute_{h}.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(mp3), "-ar", str(SR), "-ac", "1", "-c:a", "pcm_s16le", str(wav)], check=True)
    return wav, mots_alignes(al, v)


def mots_alignes(al, v):
    """Mots parlés (balises retirées) avec début, fin et numéro de phrase."""
    ch, d0, d1 = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
    mots, cur, s, e, tag = [], "", 0, 0, False
    for c, a, b in zip(ch, d0, d1):
        if c == "[":
            tag = True
        if tag:
            if c == "]":
                tag = False
            continue
        if MOT.fullmatch(c):
            if not cur:
                s = a
            cur += c
            e = b
        elif cur:
            mots.append([cur, s, e]); cur = ""
    if cur:
        mots.append([cur, s, e])
    attendus = [len(MOT.findall(p["texte"])) for p in v["phrases"]]
    if sum(attendus) != len(mots):
        erreur(f"voix : {len(mots)} mots horodatés pour {sum(attendus)} mots écrits ; simplifie la ponctuation du script")
    i = 0
    for n, k in enumerate(attendus):
        for _ in range(k):
            mots[i].append(n); i += 1
    return mots


def lire_wav(p):
    with wave.open(str(p)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float64) / 32768


def ecrire_wav(p, x):
    with wave.open(str(p), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())


def resserrer(wav, mots, v, dossier):
    """Débit ajusté (atempo, hauteur conservée), blancs resserrés, silence voulu avant les phrases qui le demandent."""
    # débit estimé une fois les blancs resserrés : durée de chaque phrase, blancs internes ramenés à l'écart gardé
    parole = 0.0
    for n in sorted({m[3] for m in mots}):
        ms = [m for m in mots if m[3] == n]
        parole += sum(m[2] - m[1] for m in ms) + sum(min(ECARTS["mot"], b[1] - a[2]) for a, b in zip(ms, ms[1:]) if b[1] > a[2])
    debit = len(mots) / parole
    facteur = min(1.22, max(1.0, DEBIT_CIBLE / debit))
    if facteur > 1.001:
        rapide = dossier / "voix_rapide.wav"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(wav), "-af", f"atempo={facteur:.4f}", "-ar", str(SR), "-ac", "1", str(rapide)], check=True)
        wav = rapide
        mots = [[m, s / facteur, e / facteur, n] for m, s, e, n in mots]
    x = lire_wav(wav)
    silences = {i: float(p.get("silence_avant", 0)) for i, p in enumerate(v["phrases"])}
    morceaux, t_out = [], 0.0
    fondu = int(0.006 * SR)

    def ajoute(seg):
        nonlocal t_out
        seg = seg.copy()
        if len(seg) > 2 * fondu:
            seg[:fondu] *= np.linspace(0, 1, fondu); seg[-fondu:] *= np.linspace(1, 0, fondu)
        morceaux.append(seg); t_out += len(seg) / SR

    debut = max(0.0, mots[0][1] - 0.035)
    curseur = debut
    for i, (m, s, e, n) in enumerate(mots):
        if i == 0:
            garde = 0.035
        elif n != mots[i - 1][3] and silences.get(n):
            garde = silences[n]
        else:
            garde = ECARTS["phrase"] if n != mots[i - 1][3] else ECARTS["mot"]
        if i > 0:
            fin_prec = mots[i - 1][2]
            g = s - fin_prec
            if g > garde + 0.02:
                # on garde la queue du mot précédent et l'attaque de celui-ci, on retire le milieu
                q = min(0.06, garde * 0.5)
                ajoute(x[int(curseur * SR):int((fin_prec + q) * SR)])
                a = garde - q
                attaque = min(a, 0.04)
                pause = a - attaque
                if pause > 0:
                    ajoute(np.zeros(int(pause * SR)))
                curseur = s - attaque
    ajoute(x[int(curseur * SR):min(len(x), int((mots[-1][2] + 0.25) * SR))])
    y = np.concatenate(morceaux)
    # recalcul des temps : on rejoue le même découpage pour savoir où chaque mot a atterri
    temps, pos, curseur = [], 0.0, debut
    for i, (m, s, e, n) in enumerate(mots):
        if i == 0:
            garde = 0.035
        elif n != mots[i - 1][3] and silences.get(n):
            garde = silences[n]
        else:
            garde = ECARTS["phrase"] if n != mots[i - 1][3] else ECARTS["mot"]
        if i > 0:
            fin_prec = mots[i - 1][2]
            if s - fin_prec > garde + 0.02:
                q = min(0.06, garde * 0.5)
                pos += (fin_prec + q) - curseur
                a = garde - q
                attaque = min(a, 0.04)
                pos += max(0, a - attaque)
                curseur = s - attaque
        d = pos + (s - curseur)
        temps.append([m, round(d, 3), round(d + (e - s), 3), n])
    sortie_p = dossier / "voix.wav"
    ecrire_wav(sortie_p, y)
    return sortie_p, temps, facteur


def phrases_temps(v, mots):
    res = []
    for i, p in enumerate(v["phrases"]):
        ms = [m for m in mots if m[3] == i]
        res.append({"role": p.get("role"), "d": ms[0][1], "f": ms[-1][2], "ecran": p.get("ecran"), "sous_titres": p.get("sous_titres"),
                    "silence": float(p.get("silence_avant", 0)), "mots": [{"m": m[0], "d": m[1], "f": m[2]} for m in ms]})
    return res


def timeline(F, ph):
    roles = {p["role"]: p for p in ph}
    D = round((ph[-1]["f"] + FIN_APRES_VOIX) * FPS) / FPS
    T = {"D": D, "phrases": ph, "stats": [], "sceau": None, "fin": roles.get("question", ph[-1])["d"]}
    j = roles.get("joueur") or ph[min(1, len(ph) - 1)]
    for i, s in enumerate(F["stats"]):
        t = None
        if s.get("mot"):
            t = next((m["d"] for m in j["mots"] if m["m"].lower() == s["mot"].lower()), None)
        if t is None:
            t = j["d"] + (j["f"] - j["d"]) * (0.35 + 0.3 * i)
        T["stats"].append(round(t, 3))
    if F.get("verdict") and "verdict" in roles:
        T["sceau"] = roles["verdict"]["mots"][-1]["d"]
    return T


# ---------- son ----------
def mixer(F, voix_wav, T, sortie):
    S = VIDEO / "sons"
    ph = T["phrases"]
    ev = [(0.0, "impact", -3), (0.0, "whoosh", -12)]
    for p in ph[1:]:
        ev.append((max(0, p["d"] - 0.22), "whoosh", -9))  # transition entre phrases, avant le mot
    for t0 in T["stats"]:
        ev += [(t0 + 0.5 * (1 - (1 - i / 9) ** 2), "tick", -12) for i in range(9)]  # ticks qui accélèrent puis freinent
        ev.append((t0 + 0.55, "impact", -8))
    if T["sceau"] is not None:
        son = {"SWISH": "swish", "REBOND": "rebond", "BRIQUE": "impact"}[F["verdict"]]
        ev += [(T["sceau"] - 0.02, "tampon", -2), (T["sceau"] + 0.08, son, -5)]
    ev.append((T["fin"], "swish", -8))
    ev.append((T["D"] - 0.2, "impact", -10))  # coupe sèche de la boucle
    entrees, f = [], []
    for i, (t0, nom, db) in enumerate(ev):
        entrees += ["-i", str(S / f"{nom}.wav")]
        ms = int(t0 * 1000)
        f.append(f"[{i}:a]aresample={SR},aformat=channel_layouts=stereo,volume={db}dB,adelay={ms}|{ms}[s{i}]")
    n = len(ev)
    entrees += ["-i", str(voix_wav)]
    f.append("".join(f"[s{i}]" for i in range(n)) + f"amix=inputs={n}:normalize=0,apad,atrim=0:{T['D']}[sfx]")
    # voix : passe-haut, présence 2 à 4 kHz, de-esser, compression légère
    f.append(f"[{n}:a]aresample={SR},highpass=f=90,equalizer=f=3000:t=q:w=1.1:g=3,deesser=i=0.35:f=0.5,"
             f"acompressor=threshold=-20dB:ratio=3:attack=5:release=90:makeup=2,pan=stereo|c0=c0|c1=c0,apad,atrim=0:{T['D']},asplit=2[v][vsc]")
    # ducking : les sons baissent d'environ 6 dB quand la voix parle
    f.append("[sfx][vsc]sidechaincompress=threshold=0.02:ratio=6:attack=8:release=160:knee=4[sfxd]")
    f.append("[v][sfxd]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[out]")
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", *entrees, "-filter_complex", ";".join(f), "-map", "[out]", "-ac", "2", str(sortie)], capture_output=True, text=True)
    if r.returncode:
        erreur("mixage : " + r.stderr[-500:])


# ---------- contrôles v2 ----------
def controles_voix(mots, ph, voix_wav):
    probs, mesures = [], {}
    parole = sum(p["f"] - p["d"] for p in ph)
    debit = len(mots) / parole if parole else 0
    mesures["debit_mots_s"] = round(debit, 2)
    if not DEBIT[0] <= debit <= DEBIT[1]:
        probs.append(f"débit de la voix {debit:.2f} mots/s (plage {DEBIT[0]} à {DEBIT[1]})")
    mesures["premier_mot_s"] = mots[0][1]
    if mots[0][1] > VOIX_DEBUT_MAX:
        probs.append(f"la voix démarre à {mots[0][1]:.2f} s (avant {VOIX_DEBUT_MAX} s exigé)")
    var = A.variation_f0(A.lire_audio(voix_wav))
    mesures["variation_f0_demi_tons"] = round(var, 2)
    if var < VARIATION_F0_MIN:
        probs.append(f"voix trop plate : variation de hauteur {var:.2f} demi-tons (minimum {VARIATION_F0_MIN})")
    voulus = [p["d"] for p in ph if p["silence"] > 0]
    trous = [(t, g, m) for t, g, m in A.blancs([(m[0], m[1], m[2]) for m in mots], voulus) if g > BLANC_MAX]
    if trous:
        probs.append("blanc dans la voix : " + ", ".join(f"{g:.2f} s après « {m} » ({t} s)" for t, g, m in trous[:3]))
    return probs, mesures


def controle_sous_titres(ph):
    pire = 0.0
    for p in ph:
        for m in p["mots"]:
            image = np.ceil(m["d"] * FPS - 1e-6) / FPS  # première image où le mot est affiché
            pire = max(pire, image - m["d"])
    return ([f"sous-titres décalés de {pire * 1000:.0f} ms"] if pire > DECALAGE_ST_MAX else []), round(pire * 1000)


def controles_image(out):
    d = A.dynamisme(out)
    probs = []
    molles = A.fenetres_molles(d, SEUIL_DYNAMISME)
    if molles:
        probs.append("vidéo molle : " + ", ".join(f"{t} s (moyenne {m})" for t, m in molles[:4]) + f" sous le seuil {SEUIL_DYNAMISME}")
    acc = float(d[:3].mean())
    if acc < SEUIL_ACCROCHE:
        probs.append(f"accroche immobile : mouvement {acc:.2f} sur les premières images (minimum {SEUIL_ACCROCHE})")
    return probs, {"dynamisme_moyen": round(float(d.mean()), 2), "fenetre_min": round(float(np.convolve(d, np.ones(21) / 21, mode='valid').min()), 2), "accroche": round(acc, 2)}


# ---------- rendu ----------
def page(fj):
    css = (DS / "tokens.css").read_text(encoding="utf-8").replace('url("fonts/', f'url("{(DS / "fonts").as_uri()}/')
    css += (DS / "bundle.css").read_text(encoding="utf-8")
    js = lambda p: f'<script src="{p.as_uri()}"></script>'
    return f"""<!doctype html><html lang="fr" data-theme="affiche"><head><meta charset="utf-8">
<style>{css} html,body{{margin:0;background:#000;width:{W}px;height:{H}px;overflow:hidden}}</style>
{js(DS / 'lib/react.production.min.js')}{js(DS / 'lib/react-dom.production.min.js')}{js(DS / 'bundle.js')}{js(VIDEO / 'motion.js')}
</head><body><div id="root"></div>
<script>window.FICHE = {json.dumps(fj, ensure_ascii=False)};</script>{js(VIDEO / 'recap2.js')}</body></html>"""


def main(a):
    essai, sans_son = "--essai" in a, "--sans-son" in a
    frames = None
    if "--frames" in a:
        frames = [float(x) for x in a[a.index("--frames") + 1].split(",")]
        a = a[:a.index("--frames")] + a[a.index("--frames") + 2:]
    a = [x for x in a if not x.startswith("--")]
    fiche_p, out = Path(a[0]).resolve(), Path(a[1]).resolve()
    F = json.loads(fiche_p.read_text(encoding="utf-8"))
    base = fiche_p.parent
    if F.get("format") not in DUREES:
        erreur("format inconnu en version 2 (seul « recap » existe pour l'instant)")
    photo = (base / F["photo"]).resolve()
    if not photo.exists():
        erreur(f"photo introuvable : {photo}")
    sys.path.insert(0, str(R.TOOLS))
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
        erreur("aucun visage détecté sur la photo : le contrôle visage est impossible")
    v = F.get("voix") or {}
    if not v.get("phrases") or not v.get("id"):
        erreur("voix : il faut \"id\" et \"phrases\" (version 2)")
    for p in v["phrases"]:
        if re.search(r"\s[-–—]\s|[–—]", p["texte"] + " " + (p.get("ecran") or "")):
            erreur(f"tiret interdit dans « {p['texte']} »")
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="reel2-"))
    sys.path.insert(0, str(R.TOOLS))
    from trame import trame
    fantome = tmp / "fantome.png"
    trame(photo, fantome)

    # plusieurs prises si la voix sort plate : on garde la plus expressive
    meilleure = None
    for k in range(PRISES):
        graine = int(v.get("graine", 7)) + k // 2
        brute, mots0 = tts_horodate(v, tmp, graine, TONS if k % 2 == 0 else TONS_ALT)
        prise = tmp / f"prise{k}"
        prise.mkdir(exist_ok=True)
        vw, ms, fa = resserrer(brute, mots0, v, prise)
        var = A.variation_f0(A.lire_audio(vw))
        print(f"prise {k + 1} (graine {graine}) : variation de hauteur {var:.2f} demi-tons", file=sys.stderr)
        if meilleure is None or var > meilleure[0]:
            meilleure = (var, vw, ms, fa)
        if var >= VARIATION_F0_MIN:
            break
    _, voix_wav, mots, facteur = meilleure
    ph = phrases_temps(v, mots)
    T = timeline(F, ph)
    dmin, dmax = DUREES[F["format"]]
    problemes, mesures = [], {"tempo": round(facteur, 3), "duree": T["D"]}
    if not dmin <= T["D"] <= dmax:
        problemes.append(f"durée {T['D']:.2f} s hors de la plage {dmin} à {dmax} s : raccourcis le script")
    pv, mv = controles_voix(mots, ph, voix_wav)
    problemes += pv; mesures.update(mv)
    pst, dec = controle_sous_titres(ph)
    problemes += pst; mesures["decalage_sous_titres_ms"] = dec
    if problemes and not frames:
        erreur(" ; ".join(problemes) + ". Corrige la fiche puis relance. Ne publie pas.")

    fj = dict(F, photo=photo.as_uri(), fantome=fantome.as_uri(), visages=vis, temps=T,
              theme_verdict=R.THEMES[F.get("verdict")], cadre=F.get("cadre") or {"x": 330, "y": 430, "l": 760})
    html = tmp / "scene.html"
    html.write_text(page(fj), encoding="utf-8")

    from playwright.sync_api import sync_playwright
    n = round(T["D"] * FPS)
    import time
    t_debut = time.time()
    with sync_playwright() as pw:
        b = pw.chromium.launch(args=["--allow-file-access-from-files"])
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(html.as_uri())
        pg.wait_for_selector(".lb-post", timeout=15000)
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(500)
        pg.evaluate("window.preparer && window.preparer()")
        if errs:
            erreur("JavaScript : " + errs[0])
        if frames:
            for t in frames:
                pg.evaluate(f"seek({t})")
                p = out.with_name(f"{out.stem}_{t:05.2f}s.jpg")
                pg.screenshot(path=str(p), type="jpeg", quality=90)
                c = pg.evaluate("controles()")
                pr = R.controler(c, vis, t)
                print(p.name, "OK" if not pr else " | ".join(pr))
                if os.environ.get("LB_DEBUG"):  # rectangles du joueur, des visages et des textes
                    j = c["joueur"]
                    print("  joueur", {k: round(v) for k, v in j.items()}, "visages", [[round(j["x"] + b[0] * j["w"]), round(j["y"] + b[1] * j["h"]), round(j["x"] + b[2] * j["w"]), round(j["y"] + b[3] * j["h"])] for b in vis])
                    print("  textes", [(x["texte"], round(x["x0"]), round(x["y0"]), round(x["x1"]), round(x["y1"])) for x in c["textes"]])
            if errs:
                print("JavaScript :", errs[0])
            print(json.dumps(dict(mesures, problemes=problemes), ensure_ascii=False))
            b.close()
            return
        silencieux = tmp / "video.mp4"
        enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
                                "-vf", "scale=out_range=tv,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
                                "-color_range", "tv", "-r", str(FPS), str(silencieux)], stdin=subprocess.PIPE)
        for i in range(n):
            t = i / FPS
            pg.evaluate(f"seek({t})")
            img = pg.screenshot(type="jpeg", quality=95)
            if i % (FPS // 6) == 0:
                pr = R.controler(pg.evaluate("controles()"), vis, t)
                if t == 0 and not [x for x in pg.evaluate("controles()")["textes"] if not x["logo"]]:
                    pr.append("0.0 s : aucun texte lisible sur la première image")
                if pr:
                    out.with_name(out.stem + "_refuse.jpg").write_bytes(img)
                    problemes += pr
            if i == round(1.0 * FPS):
                out.with_name(out.stem + "-cover.jpg").write_bytes(img)
            enc.stdin.write(img)
        enc.stdin.close(); enc.wait(); b.close()
    if errs:
        problemes.append("JavaScript : " + errs[0])
    mesures["rendu_s"] = round(time.time() - t_debut, 1)
    if sans_son:
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(silencieux), "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-shortest",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(out)], check=True)
    else:
        son = tmp / "audio.wav"
        mixer(F, voix_wav, T, son)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(silencieux), "-i", str(son), "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
                        "-ar", "48000", "-ac", "2", "-shortest", "-movflags", "+faststart", str(out)], check=True)
    pi, mi = controles_image(out)
    problemes += pi; mesures.update(mi)
    json.dump({"mots": mots, "phrases": ph, "mesures": mesures}, open(out.with_suffix(".timeline.json"), "w"), ensure_ascii=False, indent=1)
    if problemes:
        out.with_name(out.stem + "-cover.jpg").unlink(missing_ok=True)
        erreur(" ; ".join(dict.fromkeys(problemes[:8])) + ". Corrige la fiche puis relance. Ne publie pas.")
    rapport = R.verifier(out, sans_son)
    if not essai:
        registre.marquer(photo, src, out.stem)
    print(json.dumps(dict(rapport, **mesures, ok=True, sortie=str(out)), ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1:])
