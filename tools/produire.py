#!/usr/bin/env python3
"""La Brique : d'une commande éditoriale à deux publications prêtes (post image + Reel voix off).

Tourne dans GitHub Actions (.github/workflows/produire.yml), déclenché par un push dans a_produire/.
  python3 tools/produire.py a_produire/2026-11-14-1-sujet.json

La commande (écrite par la tâche du matin ou de midi, voir automatisation/COMMANDE.md) :
  {
    "id": "2026-11-14-1-wembanyama-40",            unique, sert de nom de fichier
    "heure": "2026-11-14T08:00:00+01:00",          Reel en ligne ; le post sort 10 min avant
    "photos": {
      "post":  {"fichier": "File:Nom.jpg", "joueur": "Prénom Nom", "recadrage": [0.4, 0.0, 1.0, 1.0]},
      "video": {"fichier": "File:Autre.jpg", "joueur": "Prénom Nom"}
    },
    "post":  {"composant": "PostChiffre", "props": {... "photo": "@post" ...}, "rupture": "..."},
    "video": {"format": "recap", "duree": 12, ... "photo": "@video", "voix": {...}},
    "legende": "...", "threads": "...", "alt": "...",
    "legende_reel": "...", "threads_reel": "..."
  }
« @post » et « @video » désignent les photos de la commande. Chaque photo est vérifiée sur Commons
(licence libre, prise de vue de moins de 4 ans), téléchargée une fois, détourée et inscrite au registre :
une photo ne sert qu'une fois. Les crédits sont ajoutés à la fin des légendes.

Sorties : posts/<id>.jpg, posts/videos/<id>.mp4 et -cover.jpg, a_publier/<id>-post.json et -reel.json,
produit/<id>.json (rapport, avec les erreurs à corriger dans la commande si le rendu est refusé).
"""
import datetime, json, re, subprocess, sys, time, urllib.parse, urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
TOOLS = RACINE / "tools"
UA = "LaBriqueBot/1.0 (https://www.instagram.com/labrique.hoops)"
LICENCES = ("CC0", "PUBLIC DOMAIN", "PD", "CC BY 2.0", "CC BY 2.5", "CC BY 3.0", "CC BY 4.0", "CC BY-SA 2.0", "CC BY-SA 2.5", "CC BY-SA 3.0", "CC BY-SA 4.0")
sys.path.insert(0, str(TOOLS))


class Refus(Exception):
    pass


def commons(fichier):
    titre = fichier if fichier.startswith("File:") else "File:" + fichier
    q = urllib.parse.urlencode({"action": "query", "format": "json", "titles": titre, "prop": "imageinfo",
                                "iiprop": "url|extmetadata|size", "iiurlwidth": 2560})
    req = urllib.request.Request("https://commons.wikimedia.org/w/api.php?" + q, headers={"User-Agent": UA})
    p = list(json.loads(urllib.request.urlopen(req, timeout=60).read())["query"]["pages"].values())[0]
    if "imageinfo" not in p:
        raise Refus(f"photo introuvable sur Commons : {titre}")
    ii = p["imageinfo"][0]
    m = ii["extmetadata"]
    g = lambda k: re.sub(r"<[^>]+>", "", m.get(k, {}).get("value", "")).strip()
    lic = g("LicenseShortName").upper().replace("PUBLIC DOMAIN MARK", "PUBLIC DOMAIN")
    if "NC" in lic or "ND" in lic or not any(lic.startswith(x) for x in LICENCES):
        raise Refus(f"{titre} : licence refusée ({g('LicenseShortName')}). Libres seulement : CC0, domaine public, CC BY, CC BY-SA.")
    date = g("DateTimeOriginal")[:10]
    try:
        d = datetime.date.fromisoformat(date)
        if (datetime.date.today() - d).days > 1461:
            raise Refus(f"{titre} : photo de {date}, plus de 4 ans.")
    except ValueError:
        date = None
    return {"titre": titre, "page": "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(titre.replace(" ", "_")),
            "image": ii.get("thumburl") or ii["url"], "auteur": g("Artist") or "auteur inconnu", "licence": g("LicenseShortName"),
            "licence_url": g("LicenseUrl"), "date": date}


def preparer_photo(cle, spec, id_):
    """Télécharge, recadre, détoure ; renvoie (chemin du détourage, source, crédit)."""
    info = commons(spec["fichier"])
    import photos as registre
    source = {"url": info["page"], "auteur": info["auteur"], "joueur": spec.get("joueur")}
    e = registre.conflit(None, source, post=id_)  # un nouveau rendu du même post reprend ses photos
    if e:
        raise Refus(f"photo « {cle} » : {registre.message(e)}")
    dossier = RACINE / "banque" / "photos" / re.sub(r"[^a-z0-9]+", "-", info["titre"][5:].lower()).strip("-")[:80]
    dossier.mkdir(parents=True, exist_ok=True)
    orig = dossier / "original.jpg"
    if not orig.exists():
        req = urllib.request.Request(info["image"], headers={"User-Agent": UA})
        orig.write_bytes(urllib.request.urlopen(req, timeout=120).read())
        time.sleep(2)
    from PIL import Image
    im = Image.open(orig).convert("RGB")
    if spec.get("recadrage"):
        x0, y0, x1, y1 = spec["recadrage"]
        im = im.crop((int(x0 * im.width), int(y0 * im.height), int(x1 * im.width), int(y1 * im.height)))
    src_cut = dossier / f"source-{cle}.jpg"
    im.save(src_cut, quality=95)
    brut = dossier / f"brut-{cle}.png"
    subprocess.run(["node", str(TOOLS / "cutout.mjs"), str(src_cut), str(brut)], check=True, capture_output=True, timeout=600)
    a = Image.open(brut).convert("RGBA").getchannel("A")
    rgba = Image.open(src_cut).convert("RGBA")
    rgba.putalpha(a)
    bbox = a.point(lambda v: 255 if v > 20 else 0).getbbox()
    if not bbox:
        raise Refus(f"photo « {cle} » : détourage vide")
    det = dossier / f"detoure-{cle}.png"
    rgba.crop(bbox).save(det)
    brut.unlink()
    auteur = re.sub(r"\s+", " ", info["auteur"])
    credit = f"{auteur} / Wikimedia Commons, {info['licence']}"
    (dossier / "CREDIT.txt").write_text(f"{info['titre']}\n{info['page']}\nAuteur : {info['auteur']}\nLicence : {info['licence']} {info['licence_url']}\nPrise de vue : {info['date']}\n", encoding="utf-8")
    return det, source, credit, info["licence"]


def remplacer(v, photos):
    if isinstance(v, dict):
        return {k: remplacer(x, photos) for k, x in v.items()}
    if isinstance(v, list):
        return [remplacer(x, photos) for x in v]
    if isinstance(v, str) and v.startswith("@") and v[1:] in photos:
        return str(photos[v[1:]][0])
    return v


def credits(legende, cr):
    lignes = [f"📸 {cr[0]}, photo détourée."]
    if "SA" in cr[1].upper():
        lignes.append("Visuel sous CC BY-SA 4.0.")
    return legende.rstrip() + "\n\n" + " ".join(lignes) if "📸" not in legende else legende


def apercu(id_, photos, img, cover):
    """Planche de contrôle : post, couverture du Reel et détourages sur fond Parquet."""
    from PIL import Image
    H = 900
    tuiles = [Image.open(img).convert("RGB"), Image.open(cover).convert("RGB")]
    for cle in ("post", "video"):
        d = Image.open(photos[cle][0]).convert("RGBA")
        f = Image.new("RGBA", d.size, (224, 78, 34, 255)); f.alpha_composite(d)
        tuiles.append(f.convert("RGB"))
    tuiles = [t.resize((int(t.width * H / t.height), H)) for t in tuiles]
    planche = Image.new("RGB", (sum(t.width for t in tuiles) + 20 * (len(tuiles) - 1), H), "white")
    x = 0
    for t in tuiles:
        planche.paste(t, (x, 0)); x += t.width + 20
    planche.save(RACINE / "produit" / f"{id_}-apercu.jpg", quality=85)


def ecrire(p, d):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def produire(chemin):
    chemin = Path(chemin).resolve()
    C = json.loads(chemin.read_text(encoding="utf-8"))
    id_ = C["id"]
    rapport_p = RACINE / "produit" / f"{id_}.json"
    if rapport_p.exists() and json.loads(rapport_p.read_text()).get("ok"):
        print(f"{id_} : déjà produit.")
        return True
    rap = {"id": id_, "commande": str(chemin.relative_to(RACINE)), "date": datetime.datetime.now().isoformat(timespec="seconds"), "ok": False, "erreurs": []}
    try:
        heure = datetime.datetime.fromisoformat(C["heure"])
        if not {"post", "video"} <= set(C["photos"]):
            raise Refus("la commande doit déclarer deux photos différentes : « post » et « video »")
        if C["photos"]["post"]["fichier"] == C["photos"]["video"]["fichier"]:
            raise Refus("le post et la vidéo utilisent la même photo : une photo ne sert qu'une fois")
        print(f"[{id_}] photos", flush=True)
        photos = {k: preparer_photo(k, s, id_) for k, s in C["photos"].items()}
        travail = RACINE / "produit" / "travail" / id_
        travail.mkdir(parents=True, exist_ok=True)
        # 1. post image
        fp = dict(C["post"], props=remplacer(C["post"]["props"], photos), source_photo=photos["post"][1])
        ecrire(travail / "post.json", fp)
        out_img = RACINE / "posts" / f"{id_}.jpg"
        print(f"[{id_}] post", flush=True)
        r = subprocess.run([sys.executable, str(TOOLS / "render_ds.py"), str(travail / "post.json"), str(out_img)] + (["--essai"] if C.get("essai") else []), capture_output=True, text=True, timeout=600)
        if r.returncode:
            raise Refus("post : " + (r.stderr or r.stdout).strip()[-600:])
        # 2. Reel
        fv = dict(remplacer(C["video"], photos), source_photo=photos["video"][1])
        ecrire(travail / "video.json", fv)
        out_vid = RACINE / "posts" / "videos" / f"{id_}.mp4"
        print(f"[{id_}] reel", flush=True)
        r = subprocess.run([sys.executable, str(TOOLS / "video" / "reel.py"), str(travail / "video.json"), str(out_vid)] + (["--essai"] if C.get("essai") else []), capture_output=True, text=True, timeout=600)
        if r.returncode:
            raise Refus("vidéo : " + (r.stderr or r.stdout).strip()[-600:])
        info_v = json.loads(r.stdout.strip().splitlines()[-1])
        # 3. fiches de publication (une commande « essai » ne publie rien : ses fiches restent dans produit/essais)
        h_post = heure - datetime.timedelta(minutes=10)
        dest = RACINE / ("produit/essais" if C.get("essai") else "a_publier")
        ecrire(dest / f"{id_}-1-post.json", {
            "heure": h_post.isoformat(), "type": "image", "medias": [f"posts/{id_}.jpg"],
            "legende": credits(C["legende"], photos["post"][2:]), "threads": credits(C["threads"], photos["post"][2:]),
            "alt": C.get("alt"), "reseaux": ["instagram", "facebook", "threads"]})
        ecrire(dest / f"{id_}-2-reel.json", {
            "heure": heure.isoformat(), "type": "reel", "medias": [f"posts/videos/{id_}.mp4"], "couverture": f"posts/videos/{id_}-cover.jpg",
            "legende": credits(C["legende_reel"], photos["video"][2:]), "threads": credits(C["threads_reel"], photos["video"][2:]),
            "alt": C.get("alt"), "reseaux": ["instagram", "facebook", "threads"]})
        apercu(id_, photos, out_img, out_vid.with_name(f"{id_}-cover.jpg"))
        rap.update(ok=True, apercu=f"produit/{id_}-apercu.jpg", post=f"posts/{id_}.jpg", reel=f"posts/videos/{id_}.mp4", couverture=f"posts/videos/{id_}-cover.jpg",
                   reel_info=info_v, publication={"post": h_post.isoformat(), "reel": heure.isoformat()})
    except Refus as e:
        rap["erreurs"].append(str(e))
    except subprocess.TimeoutExpired as e:
        rap["erreurs"].append(f"outil bloqué plus de {int(e.timeout)} s : {' '.join(map(str, e.cmd[1:3]))}. Repousse la commande telle quelle pour relancer.")
    except subprocess.CalledProcessError as e:
        rap["erreurs"].append(f"outil en échec : {e.cmd[:2]} {(e.stderr or b'')[-300:]!r}")
    except Exception as e:
        rap["erreurs"].append(f"{type(e).__name__} : {e}")
    # aperçus des refus pour que la tâche puisse les regarder
    rap["refus"] = [str(p.relative_to(RACINE)) for p in (RACINE / "posts").rglob(f"{id_}*_refuse.*")]
    ecrire(rapport_p, rap)
    print(json.dumps(rap, ensure_ascii=False, indent=1))
    return rap["ok"]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    ok = all([produire(p) for p in sys.argv[1:]])
    sys.exit(0 if ok else 1)
