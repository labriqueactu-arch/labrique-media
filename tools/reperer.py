#!/usr/bin/env python3
"""La Brique : repérage de photos libres sur Wikimedia Commons, avec planche contact.

Tourne dans GitHub Actions (.github/workflows/reperer.yml), déclenché par un push dans a_reperer/.
  python3 tools/reperer.py a_reperer/wembanyama.json

Demande : {"joueur": "Victor Wembanyama", "recherches": ["Wembanyama Spurs", "Wembanyama 2025"], "fichiers": ["File:..."], "max": 16}
Sortie : reperage/<nom>.jpg (planche numérotée, quadrillage tous les 10 % pour choisir un recadrage)
         reperage/<nom>.json (pour chaque numéro : fichier, licence, auteur, date, taille, déjà utilisée ou non).
Seules les photos sous licence libre et de moins de 2 ans sont gardées.
"""
import datetime, json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "tools"))
UA = "LaBriqueBot/1.0 (https://www.instagram.com/labrique.hoops)"
API = "https://commons.wikimedia.org/w/api.php?"
LIBRES = ("CC0", "PUBLIC DOMAIN", "CC BY 2", "CC BY 3", "CC BY 4", "CC BY-SA 2", "CC BY-SA 3", "CC BY-SA 4")


def api(**p):
    p.update(format="json", action="query")
    req = urllib.request.Request(API + urllib.parse.urlencode(p), headers={"User-Agent": UA})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())


def infos(titres):
    d = api(titles="|".join(titres), prop="imageinfo", iiprop="url|extmetadata|size", iiurlwidth=640)
    out = []
    for p in d.get("query", {}).get("pages", {}).values():
        if "imageinfo" not in p:
            continue
        ii = p["imageinfo"][0]; m = ii["extmetadata"]
        g = lambda k: re.sub(r"<[^>]+>", "", m.get(k, {}).get("value", "")).strip()
        out.append({"fichier": p["title"], "licence": g("LicenseShortName"), "auteur": re.sub(r"\s+", " ", g("Artist")),
                    "date": g("DateTimeOriginal")[:10], "taille": f"{ii['width']}x{ii['height']}", "vignette": ii.get("thumburl"),
                    "page": "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(p["title"].replace(" ", "_"))})
    return out


def libre(c):
    lic = c["licence"].upper()
    if "NC" in lic or "ND" in lic or not any(lic.startswith(x) for x in LIBRES):
        return False
    try:
        return (datetime.date.today() - datetime.date.fromisoformat(c["date"])).days <= 730
    except ValueError:
        return False


def reperer(chemin):
    chemin = Path(chemin).resolve()
    D = json.loads(chemin.read_text(encoding="utf-8"))
    nom = chemin.stem
    titres = list(D.get("fichiers", []))
    for q in D.get("recherches", []):
        r = api(list="search", srnamespace=6, srlimit=40, srsearch=q)
        titres += [x["title"] for x in r.get("query", {}).get("search", []) if x["title"].lower().endswith((".jpg", ".jpeg", ".png"))]
    titres = list(dict.fromkeys(titres))
    cands = []
    for i in range(0, len(titres), 40):
        cands += infos(titres[i:i + 40])
    cands = [c for c in cands if libre(c)][: D.get("max", 16)]
    import photos as registre
    for c in cands:
        e = registre.conflit(None, {"url": c["page"], "auteur": c["auteur"], "joueur": D.get("joueur")})
        c["deja_utilisee"] = bool(e)
    from PIL import Image, ImageDraw, ImageFont
    T = 420
    tuiles = []
    for n, c in enumerate(cands, 1):
        c["numero"] = n
        req = urllib.request.Request(c["vignette"], headers={"User-Agent": UA})
        p = RACINE / "reperage" / "tmp.jpg"; p.parent.mkdir(exist_ok=True)
        p.write_bytes(urllib.request.urlopen(req, timeout=60).read()); time.sleep(1)
        im = Image.open(p).convert("RGB"); im.thumbnail((T, T))
        tuile = Image.new("RGB", (T, T + 40), "white"); tuile.paste(im, ((T - im.width) // 2, 0))
        d = ImageDraw.Draw(tuile)
        ox, oy = (T - im.width) // 2, 0
        for k in range(1, 10):  # quadrillage tous les 10 %
            d.line([(ox + im.width * k / 10, oy), (ox + im.width * k / 10, oy + im.height)], fill=(255, 255, 255), width=1)
            d.line([(ox, oy + im.height * k / 10), (ox + im.width, oy + im.height * k / 10)], fill=(255, 255, 255), width=1)
        f = ImageFont.load_default(size=26)
        etiq = f"{n}  {c['date']}  {'DEJA UTILISEE' if c['deja_utilisee'] else ''}"
        d.text((8, T + 6), etiq, fill=(200, 0, 0) if c["deja_utilisee"] else (0, 0, 0), font=f)
        tuiles.append(tuile)
    (RACINE / "reperage" / "tmp.jpg").unlink(missing_ok=True)
    if tuiles:
        cols = 4
        rows = (len(tuiles) + cols - 1) // cols
        planche = Image.new("RGB", (cols * (T + 10), rows * (T + 50)), (230, 230, 230))
        for i, t in enumerate(tuiles):
            planche.paste(t, ((i % cols) * (T + 10), (i // cols) * (T + 50)))
        planche.save(RACINE / "reperage" / f"{nom}.jpg", quality=82)
    for c in cands:
        c.pop("vignette", None)
    (RACINE / "reperage" / f"{nom}.json").write_text(json.dumps(cands, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{nom} : {len(cands)} photo(s) libres et récentes")


if __name__ == "__main__":
    for a in sys.argv[1:] or sys.exit(__doc__):
        reperer(a)
