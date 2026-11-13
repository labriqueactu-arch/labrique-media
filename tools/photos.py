#!/usr/bin/env python3
"""La Brique : une photo ne sert qu'une seule fois.

Le registre banque/utilisees.json garde chaque photo déjà publiée : page source, auteur, joueur,
empreinte visuelle (dHash) et le post qui l'a utilisée. render_ds.py et reel.py appellent
verifier() avant de rendre et refusent une photo déjà vue, même recadrée ou détourée autrement.

Usage :
  python3 tools/photos.py verifier image.png [--source URL]   dit si la photo est libre
  python3 tools/photos.py liste [joueur]                      photos déjà utilisées
Dans une fiche : "source_photo": {"url": "https://commons.wikimedia.org/wiki/File:...", "auteur": "...", "joueur": "..."}
"""
import datetime, json, sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
REGISTRE = RACINE / "banque" / "utilisees.json"
SEUIL = 10  # distance de Hamming maximale entre deux dHash 64 bits pour « même photo »


def charger():
    if REGISTRE.exists():
        return json.loads(REGISTRE.read_text(encoding="utf-8"))
    return []


def dhash(chemin):
    """Empreinte de la photo, sur fond gris neutre pour qu'un détourage ne change rien."""
    from PIL import Image
    im = Image.open(chemin).convert("RGBA")
    fond = Image.new("RGBA", im.size, (128, 128, 128, 255))
    fond.alpha_composite(im)
    bbox = im.getchannel("A").point(lambda v: 255 if v > 20 else 0).getbbox()
    g = fond.crop(bbox or (0, 0, *im.size)).convert("L").resize((9, 8))
    px = list(g.getdata())
    bits = 0
    for y in range(8):
        for x in range(8):
            bits = (bits << 1) | (px[y * 9 + x] > px[y * 9 + x + 1])
    return f"{bits:016x}"


def distance(a, b):
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def norme(u):
    """Adresse de page Commons comparable, quel que soit l'encodage."""
    import urllib.parse
    return urllib.parse.unquote(u or "").replace(" ", "_").split("?")[0] or None


def conflit(chemin=None, source=None, post=None):
    """Renvoie l'entrée du registre qui bloque cette photo, ou None."""
    h = dhash(chemin) if chemin else None
    url = norme((source or {}).get("url"))
    for e in charger():
        if post and e.get("post") == post:
            continue  # nouveau rendu du même post
        if url and norme(e.get("url")) == url:
            return e
        if h and e.get("dhash") and distance(h, e["dhash"]) <= SEUIL:
            return e
        if source and not e.get("url") and e.get("joueur") == source.get("joueur") and e.get("auteur") == source.get("auteur"):
            return e  # photo ancienne sans adresse connue : même joueur et même auteur, on ne prend pas le risque
    return None


def marquer(chemin, source, post):
    reg = charger()
    h = dhash(chemin)
    if any(e.get("post") == post and e.get("dhash") == h for e in reg):
        return
    reg.append({"joueur": source.get("joueur"), "auteur": source.get("auteur"), "url": source.get("url"),
                "dhash": h, "post": post, "date": datetime.date.today().isoformat()})
    REGISTRE.parent.mkdir(exist_ok=True)
    REGISTRE.write_text(json.dumps(reg, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def message(e):
    return (f"photo déjà utilisée le {e.get('date')} pour « {e.get('post')} » "
            f"({e.get('joueur')}, {e.get('auteur')}). Une photo ne sert qu'une fois : trouve une autre photo.")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["verifier"] and len(a) >= 2:
        src = {"url": a[a.index("--source") + 1]} if "--source" in a else None
        e = conflit(a[1], src)
        print("libre" if not e else "REFUSÉE : " + message(e))
        sys.exit(1 if e else 0)
    if a[:1] == ["liste"]:
        for e in charger():
            if len(a) < 2 or a[1].lower() in (e.get("joueur") or "").lower():
                print(f"{e.get('date')}  {e.get('joueur')}  {e.get('auteur')}  {e.get('post')}  {e.get('url') or ''}")
        sys.exit(0)
    sys.exit(__doc__)
