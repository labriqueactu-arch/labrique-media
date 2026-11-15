#!/usr/bin/env python3
"""La Brique : banque de photos libres, triées par qualité, pour ne plus chercher sous pression.

  python3 tools/banque.py construire [Nom1 "Nom 2" ...]   tous les joueurs de JOUEURS si aucun nom
  python3 tools/banque.py chercher <nom>                   meilleures photos libres encore jamais utilisées

Pour chaque joueur : catégorie Commons et sous-catégories (profondeur 2), licence libre, moins de 4 ans.
Chaque photo est notée sur une vignette de 1280 px : visages (OpenCV), netteté du plus grand visage
(variance du Laplacien), taille du visage, résolution d'origine. Une photo est « bonne » si le visage
est net, assez grand, et l'original fait au moins 1200 px de petit côté.
Sorties : banque/registre.json (une entrée par photo, avec note et statut) et banque/planches/<joueur>.jpg
(les 12 meilleures, numérotées, avec quadrillage 10 % pour choisir un recadrage).
Les vignettes restent dans ~/.cache/labrique-banque (hors du dépôt).
"""
import concurrent.futures as cf, datetime, json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "tools"))
from reperer import api, libre, UA  # noqa: E402

REGISTRE = RACINE / "banque" / "registre.json"
PLANCHES = RACINE / "banque" / "planches"
CACHE = Path.home() / ".cache" / "labrique-banque"

JOUEURS = [
    # stars NBA 2026-27
    "Victor Wembanyama", "Shai Gilgeous-Alexander", "Nikola Jokić", "Luka Dončić", "Giannis Antetokounmpo",
    "Jayson Tatum", "Jaylen Brown", "Anthony Edwards", "Stephen Curry", "LeBron James", "Kevin Durant",
    "Donovan Mitchell", "Jalen Brunson", "Karl-Anthony Towns", "Tyrese Haliburton", "Tyrese Maxey",
    "Joel Embiid", "Paul George", "Cade Cunningham", "Ja Morant", "Devin Booker", "Anthony Davis",
    "Kawhi Leonard", "James Harden", "Jimmy Butler", "Bam Adebayo", "De'Aaron Fox", "Domantas Sabonis",
    "Alperen Şengün", "Paolo Banchero", "Franz Wagner", "Trae Young", "Jalen Williams", "Chet Holmgren",
    "Zion Williamson", "LaMelo Ball", "Evan Mobley", "Darius Garland", "Cooper Flagg", "Stephon Castle",
    "Austin Reaves", "Jamal Murray", "Kristaps Porziņģis", "Lauri Markkanen", "Scottie Barnes",
    # Français et Belges
    "Rudy Gobert", "Bilal Coulibaly", "Alexandre Sarr", "Zaccharie Risacher", "Tidjane Salaün",
    "Guerschon Yabusele", "Nicolas Batum", "Moussa Diabaté", "Ousmane Dieng", "Sidy Cissoko",
    "Toumani Camara", "Ajay Mitchell", "Nolan Traoré", "Maxime Raynaud", "Noah Penda", "Joan Beringer",
    # Europe
    "Nadir Hifi", "Kendrick Nunn", "Sasha Vezenkov", "Facundo Campazzo", "Mike James", "Théo Maledon",
    "Elie Okobo", "Mathias Lessort", "Edgar Sneed", "TJ Shorts",
]


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower().encode("ascii", "ignore").decode()).strip("-")


def categorie(joueur):
    """Titres de fichiers de la catégorie du joueur et de ses sous-catégories (profondeur 2)."""
    titres, a_voir, vues = [], [f"Category:{joueur}"], set()
    for prof in range(3):
        suivantes = []
        for cat in a_voir:
            if cat in vues:
                continue
            vues.add(cat)
            try:
                r = api(list="categorymembers", cmtitle=cat, cmlimit=500, cmtype="file|subcat")
            except Exception:
                continue
            for m in r.get("query", {}).get("categorymembers", []):
                if m["ns"] == 14 and prof < 2:
                    suivantes.append(m["title"])
                elif m["title"].lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                    titres.append(m["title"])
        a_voir = suivantes
    return list(dict.fromkeys(titres))


def infos(titres):
    out = []
    for i in range(0, len(titres), 40):
        d = api(titles="|".join(titres[i:i + 40]), prop="imageinfo", iiprop="url|extmetadata|size", iiurlwidth=1280)
        for p in d.get("query", {}).get("pages", {}).values():
            if "imageinfo" not in p:
                continue
            ii = p["imageinfo"][0]; m = ii["extmetadata"]
            g = lambda k: re.sub(r"<[^>]+>", "", m.get(k, {}).get("value", "")).strip()
            out.append({"fichier": p["title"], "licence": g("LicenseShortName"), "auteur": re.sub(r"\s+", " ", g("Artist")),
                        "date": g("DateTimeOriginal")[:10], "largeur": ii["width"], "hauteur": ii["height"],
                        "vignette": ii.get("thumburl"),
                        "page": "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(p["title"].replace(" ", "_"), safe=":/()")})
    return out


def telecharger(c, dossier):
    p = dossier / (slug(c["fichier"][5:])[:90] + ".jpg")
    if not p.exists():
        req = urllib.request.Request(c["vignette"], headers={"User-Agent": UA})
        p.write_bytes(urllib.request.urlopen(req, timeout=60).read())
        time.sleep(0.5)
    return p


def noter(p):
    """Visages, netteté du plus grand visage, part du visage dans l'image."""
    import cv2
    im = cv2.imread(str(p))
    if im is None:
        return {"visages": 0, "nettete": 0, "visage_part": 0}
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    casc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = casc.detectMultiScale(g, 1.1, 6, minSize=(max(24, g.shape[1] // 40),) * 2)
    if len(faces) == 0:
        prof = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml")
        faces = prof.detectMultiScale(g, 1.1, 6, minSize=(max(24, g.shape[1] // 40),) * 2)
    if len(faces) == 0:
        return {"visages": 0, "nettete": 0, "visage_part": 0}
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    crop = cv2.resize(g[y:y + h, x:x + w], (200, 200))
    return {"visages": int(len(faces)), "nettete": round(float(cv2.Laplacian(crop, cv2.CV_64F).var()), 1),
            "visage_part": round(w / g.shape[1], 3)}


def statut(c):
    if c["visages"] == 0:
        return "sans visage"
    if min(c["largeur"], c["hauteur"]) < 1200:
        return "trop petite"
    if c["nettete"] < 100:
        return "molle"
    if c["visage_part"] < 0.035:
        return "joueur trop loin"
    return "bonne"


def note(c):
    return round(min(c["nettete"], 600) / 6 + min(c["visage_part"], 0.25) * 200 + (10 if c["visages"] == 1 else 0)
                 + min(min(c["largeur"], c["hauteur"]), 3000) / 300, 1)


def planche(joueur, cands):
    from PIL import Image, ImageDraw, ImageFont
    T = 420
    tuiles = []
    for c in cands[:12]:
        im = Image.open(c["_vignette"]).convert("RGB"); im.thumbnail((T, T))
        t = Image.new("RGB", (T, T + 44), "white"); ox = (T - im.width) // 2; t.paste(im, (ox, 0))
        d = ImageDraw.Draw(t)
        for k in range(1, 10):
            d.line([(ox + im.width * k / 10, 0), (ox + im.width * k / 10, im.height)], fill=(255, 255, 255))
            d.line([(ox, im.height * k / 10), (ox + im.width, im.height * k / 10)], fill=(255, 255, 255))
        d.text((8, T + 8), f"{c['rang']}  {c['date']}  net {int(c['nettete'])}", fill=(0, 0, 0), font=ImageFont.load_default(size=24))
        tuiles.append(t)
    if not tuiles:
        return
    cols = 4; rows = (len(tuiles) + cols - 1) // cols
    pl = Image.new("RGB", (cols * (T + 10), rows * (T + 54)), (230, 230, 230))
    for i, t in enumerate(tuiles):
        pl.paste(t, ((i % cols) * (T + 10), (i // cols) * (T + 54)))
    PLANCHES.mkdir(parents=True, exist_ok=True)
    pl.save(PLANCHES / f"{slug(joueur)}.jpg", quality=80)


def construire(joueurs):
    reg = json.loads(REGISTRE.read_text()) if REGISTRE.exists() else {}
    import photos as registre_utilisees
    for j in joueurs:
        t0 = time.time()
        titres = categorie(j) + categorie(j + " (basketball)")
        nom = j.split()[-1]
        for q in (j, f"{j} 2025", f"{j} 2026", f"{j} basketball"):
            try:
                r = api(list="search", srnamespace=6, srlimit=50, srsearch=q)
                titres += [x["title"] for x in r.get("query", {}).get("search", [])
                           if x["title"].lower().endswith((".jpg", ".jpeg", ".png")) and all(m in slug(x["title"]) for m in slug(j).split("-"))]
            except Exception:
                pass
        cands = [c for c in infos(list(dict.fromkeys(titres))) if libre(c)]
        dossier = CACHE / slug(j); dossier.mkdir(parents=True, exist_ok=True)
        with cf.ThreadPoolExecutor(3) as ex:
            chemins = list(ex.map(lambda c: (c, telecharger(c, dossier)), cands))
        for c, p in chemins:
            c.update(noter(p)); c["_vignette"] = str(p)
            c["statut"] = statut(c); c["note"] = note(c)
            c["deja_utilisee"] = bool(registre_utilisees.conflit(None, {"url": c["page"], "auteur": c["auteur"], "joueur": j}))
        cands.sort(key=lambda c: (c["statut"] != "bonne", -c["note"]))
        for i, c in enumerate(cands, 1):
            c["rang"] = i
        planche(j, cands)
        reg[j] = {"mis_a_jour": datetime.date.today().isoformat(),
                  "photos": [{k: v for k, v in c.items() if not k.startswith("_") and k != "vignette"} for c in cands]}
        REGISTRE.write_text(json.dumps(reg, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        bonnes = sum(c["statut"] == "bonne" and not c["deja_utilisee"] for c in cands)
        print(f"{j} : {len(cands)} libres, {bonnes} bonnes et neuves ({int(time.time() - t0)} s)", flush=True)


def chercher(nom):
    reg = json.loads(REGISTRE.read_text())
    cle = next((k for k in reg if slug(nom) in slug(k)), None)
    if not cle:
        sys.exit(f"{nom} absent de la banque : python3 tools/banque.py construire \"{nom}\"")
    import photos as registre_utilisees
    for c in reg[cle]["photos"]:
        if c["statut"] == "bonne" and not registre_utilisees.conflit(None, {"url": c["page"], "auteur": c["auteur"], "joueur": cle}):
            print(f"{c['rang']:>3}  note {c['note']:>5}  net {int(c['nettete']):>4}  {c['date']}  {c['licence']:12}  {c['fichier']}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["construire"]:
        construire(a[1:] or JOUEURS)
    elif a[:1] == ["chercher"] and len(a) == 2:
        chercher(a[1])
    else:
        sys.exit(__doc__)
