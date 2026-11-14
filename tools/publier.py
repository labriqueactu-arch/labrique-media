#!/usr/bin/env python3
"""La Brique : publication directe sur Instagram, Facebook et Threads par les API officielles de Meta.

Remplace Metricool. Tourne dans GitHub Actions (.github/workflows/publier.yml) avec les secrets
du dépôt. Aucun jeton n'est écrit dans le dépôt ni affiché dans les journaux.

Usage :
  python3 tools/publier.py verifier                  # comptes joignables et quota Instagram, sans rien publier
  python3 tools/publier.py publier a_publier/X.json  # attend l'heure prévue puis publie
  python3 tools/publier.py echeances                 # publie toutes les fiches arrivées à échéance
  python3 tools/publier.py rafraichir-threads        # prolonge le jeton Threads (60 jours), écrit le nouveau dans $GITHUB_OUTPUT
  python3 tools/publier.py supprimer publie/X.json   # supprime définitivement les publications de ce résultat (les 3 réseaux)

Variables d'environnement (secrets GitHub) :
  META_PAGE_TOKEN   jeton de page longue durée (Instagram et Facebook)
  IG_USER_ID        identifiant du compte Instagram professionnel
  FB_PAGE_ID        identifiant de la page Facebook
  THREADS_TOKEN     jeton Threads longue durée
  GRAPH_VERSION     facultatif, v27.0 par défaut

Fiche a_publier/AAAA-MM-JJ-sujet.json :
  {
    "heure": "2026-11-14T07:30:00+01:00",
    "type": "image" | "carrousel" | "reel",
    "medias": ["posts/2026-11-14-sujet.jpg"],      chemins du dépôt (ou URL https)
    "couverture": "posts/videos/...-cover.jpg",      reel seulement
    "legende": "Légende Instagram et Facebook",
    "threads": "Texte Threads (450 caractères au plus)",
    "alt": "Texte alternatif",
    "reseaux": ["instagram", "facebook", "threads"]
  }
Résultat : publie/<même nom>.json avec, par réseau, l'identifiant, le lien et le statut.
Une fiche dont le résultat existe déjà n'est jamais republiée. Une fiche en retard de plus
de RETARD_MAX minutes n'est pas publiée : le résultat note « abandonné (retard) ».
"""
import datetime, json, os, subprocess, sys, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

RACINE = Path(__file__).resolve().parent.parent
DEPOT = os.environ.get("GITHUB_REPOSITORY", "labriqueactu-arch/labrique-media")
BRANCHE = os.environ.get("BRANCHE", "main")
RAW = f"https://raw.githubusercontent.com/{DEPOT}/{BRANCHE}/"
V = os.environ.get("GRAPH_VERSION", "v27.0")
FB = f"https://graph.facebook.com/{V}"
TH = "https://graph.threads.net/v1.0"
BXL = ZoneInfo("Europe/Brussels")
RETARD_MAX = int(os.environ.get("RETARD_MAX", "45"))
ATTENTE_MAX = 5.5 * 3600  # un job GitHub dure 6 h au plus


class ErreurAPI(Exception):
    pass


def env(nom):
    v = os.environ.get(nom, "").strip()
    if not v:
        raise ErreurAPI(f"secret {nom} absent")
    return v


def appel(methode, url, params=None, entetes=None):
    """Appel HTTP ; le jeton passe dans les paramètres et n'est jamais affiché."""
    params = {k: v for k, v in (params or {}).items() if v is not None}
    data = None
    if methode == "GET":
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    else:
        data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method=methode, headers=entetes or {})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        corps = e.read().decode(errors="replace")
        try:
            err = json.loads(corps).get("error", {})
            msg = f"{err.get('message')} (code {err.get('code')}, sous-code {err.get('error_subcode')})"
        except Exception:
            msg = corps[:300]
        raise ErreurAPI(f"HTTP {e.code} sur {url.split('?')[0]} : {msg}") from None


def url_media(m):
    if m.startswith("https://"):
        return m
    if not (RACINE / m).exists():
        raise ErreurAPI(f"média introuvable dans le dépôt : {m}")
    return RAW + urllib.parse.quote(m)


def attendre_media(url):
    """raw.githubusercontent.com met parfois une minute à servir un fichier tout juste poussé."""
    for _ in range(20):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=30) as r:
                if r.status == 200:
                    return
        except Exception:
            pass
        time.sleep(15)
    raise ErreurAPI(f"média non servi : {url}")


# ---------- Instagram (API Graph, connexion Facebook) ----------

def ig_attendre(cid, tok, limite=600):
    t0 = time.time()
    while time.time() - t0 < limite:
        s = appel("GET", f"{FB}/{cid}", {"fields": "status_code,status", "access_token": tok})
        code = s.get("status_code")
        if code == "FINISHED":
            return
        if code in ("ERROR", "EXPIRED"):
            raise ErreurAPI(f"conteneur Instagram {code} : {s.get('status')}")
        time.sleep(10)
    raise ErreurAPI("conteneur Instagram pas prêt après 10 minutes")


def instagram(f):
    tok, ig = env("META_PAGE_TOKEN"), env("IG_USER_ID")
    medias = [url_media(m) for m in f["medias"]]
    if f["type"] == "image":
        c = appel("POST", f"{FB}/{ig}/media", {"image_url": medias[0], "caption": f["legende"], "alt_text": f.get("alt"), "access_token": tok})["id"]
    elif f["type"] == "carrousel":
        enfants = [appel("POST", f"{FB}/{ig}/media", {"image_url": u, "is_carousel_item": "true", "access_token": tok})["id"] for u in medias]
        for e in enfants:
            ig_attendre(e, tok)
        c = appel("POST", f"{FB}/{ig}/media", {"media_type": "CAROUSEL", "children": ",".join(enfants), "caption": f["legende"], "access_token": tok})["id"]
    elif f["type"] == "reel":
        p = {"media_type": "REELS", "video_url": medias[0], "caption": f["legende"], "share_to_feed": "true", "access_token": tok}
        if f.get("couverture"):
            p["cover_url"] = url_media(f["couverture"])
        elif f.get("couverture_ms") is not None:
            p["thumb_offset"] = str(f["couverture_ms"])
        c = appel("POST", f"{FB}/{ig}/media", p)["id"]
    else:
        raise ErreurAPI(f"type inconnu : {f['type']}")
    ig_attendre(c, tok)
    mid = appel("POST", f"{FB}/{ig}/media_publish", {"creation_id": c, "access_token": tok})["id"]
    lien = appel("GET", f"{FB}/{mid}", {"fields": "permalink", "access_token": tok}).get("permalink")
    return {"id": mid, "lien": lien}


# ---------- Facebook (page) ----------

def facebook(f):
    tok, page = env("META_PAGE_TOKEN"), env("FB_PAGE_ID")
    medias = [url_media(m) for m in f["medias"]]
    if f["type"] == "image":
        r = appel("POST", f"{FB}/{page}/photos", {"url": medias[0], "message": f["legende"], "alt_text_custom": f.get("alt"), "access_token": tok})
        pid = r.get("post_id") or r["id"]
    elif f["type"] == "carrousel":
        ids = [appel("POST", f"{FB}/{page}/photos", {"url": u, "published": "false", "access_token": tok})["id"] for u in medias]
        p = {"message": f["legende"], "access_token": tok}
        for i, x in enumerate(ids):
            p[f"attached_media[{i}]"] = json.dumps({"media_fbid": x})
        pid = appel("POST", f"{FB}/{page}/feed", p)["id"]
    elif f["type"] == "reel":
        d = appel("POST", f"{FB}/{page}/video_reels", {"upload_phase": "start", "access_token": tok})
        vid = d["video_id"]
        req = urllib.request.Request(f"https://rupload.facebook.com/video-upload/{V}/{vid}", method="POST",
                                     headers={"Authorization": f"OAuth {tok}", "file_url": medias[0]})
        try:
            urllib.request.urlopen(req, timeout=300).read()
        except urllib.error.HTTPError as e:
            raise ErreurAPI(f"envoi du Reel Facebook refusé : HTTP {e.code} {e.read()[:300]!r}") from None
        appel("POST", f"{FB}/{page}/video_reels", {"upload_phase": "finish", "video_id": vid, "video_state": "PUBLISHED", "description": f["legende"], "access_token": tok})
        pid = vid
    else:
        raise ErreurAPI(f"type inconnu : {f['type']}")
    lien = appel("GET", f"{FB}/{pid}", {"fields": "permalink_url", "access_token": tok}).get("permalink_url")
    if lien and lien.startswith("/"):
        lien = "https://www.facebook.com" + lien
    return {"id": pid, "lien": lien}


# ---------- Threads ----------

def th_attendre(cid, tok, limite=600):
    t0 = time.time()
    while time.time() - t0 < limite:
        s = appel("GET", f"{TH}/{cid}", {"fields": "status,error_message", "access_token": tok})
        if s.get("status") == "FINISHED":
            return
        if s.get("status") in ("ERROR", "EXPIRED"):
            raise ErreurAPI(f"conteneur Threads {s.get('status')} : {s.get('error_message')}")
        time.sleep(10)
    raise ErreurAPI("conteneur Threads pas prêt après 10 minutes")


def threads(f):
    tok = env("THREADS_TOKEN")
    texte = f.get("threads") or f["legende"]
    if len(texte) > 500:
        raise ErreurAPI("texte Threads au delà de 500 caractères")
    medias = [url_media(m) for m in f["medias"]]
    if f["type"] == "image":
        c = appel("POST", f"{TH}/me/threads", {"media_type": "IMAGE", "image_url": medias[0], "text": texte, "alt_text": f.get("alt"), "access_token": tok})["id"]
    elif f["type"] == "carrousel":
        enfants = [appel("POST", f"{TH}/me/threads", {"media_type": "IMAGE", "image_url": u, "is_carousel_item": "true", "access_token": tok})["id"] for u in medias]
        for e in enfants:
            th_attendre(e, tok)
        c = appel("POST", f"{TH}/me/threads", {"media_type": "CAROUSEL", "children": ",".join(enfants), "text": texte, "access_token": tok})["id"]
    elif f["type"] == "reel":
        c = appel("POST", f"{TH}/me/threads", {"media_type": "VIDEO", "video_url": medias[0], "text": texte, "access_token": tok})["id"]
    else:
        raise ErreurAPI(f"type inconnu : {f['type']}")
    th_attendre(c, tok)
    mid = appel("POST", f"{TH}/me/threads_publish", {"creation_id": c, "access_token": tok})["id"]
    lien = appel("GET", f"{TH}/{mid}", {"fields": "permalink", "access_token": tok}).get("permalink")
    return {"id": mid, "lien": lien}


RESEAUX = {"instagram": instagram, "facebook": facebook, "threads": threads}


# ---------- Orchestration ----------

def chemin_resultat(fiche):
    return RACINE / "publie" / Path(fiche).name


def heure(f):
    return datetime.datetime.fromisoformat(f["heure"]).astimezone(BXL)


def publier(fiche, attendre=True):
    fiche = Path(fiche)
    res_path = chemin_resultat(fiche)
    if res_path.exists():
        print(f"{fiche.name} : déjà traité, rien à faire.")
        return True
    f = json.loads(fiche.read_text(encoding="utf-8"))
    h, now = heure(f), datetime.datetime.now(BXL)
    delai = (h - now).total_seconds()
    if delai > 0:
        if not attendre or delai > ATTENTE_MAX:
            print(f"{fiche.name} : prévu à {h:%d/%m %H:%M}, pas encore l'heure.")
            return True
        print(f"{fiche.name} : attente jusqu'à {h:%H:%M} ({int(delai)} s).")
        for m in f["medias"] + ([f["couverture"]] if f.get("couverture") else []):
            attendre_media(url_media(m))
        time.sleep(max(0, (h - datetime.datetime.now(BXL)).total_seconds()))
    elif -delai > RETARD_MAX * 60:
        res = {"fiche": fiche.name, "heure_prevue": f["heure"], "statut": f"abandonné (retard de {int(-delai // 60)} min)"}
        ecrire(res_path, res)
        print(json.dumps(res, ensure_ascii=False))
        return True
    if os.environ.get("GITHUB_ACTIONS"):
        # dernière lecture du dépôt : la tâche a pu retirer ou corriger la fiche pendant l'attente
        subprocess.run(["git", "pull", "-q", "--rebase"], cwd=RACINE)
        if chemin_resultat(fiche).exists():
            print(f"{fiche.name} : déjà traité par un autre passage.")
            return True
        if not fiche.exists():
            print(f"{fiche.name} : retirée avant l'heure, rien n'est publié.")
            return True
        f = json.loads(fiche.read_text(encoding="utf-8"))
    for m in f["medias"] + ([f["couverture"]] if f.get("couverture") else []):
        attendre_media(url_media(m))
    res = {"fiche": fiche.name, "heure_prevue": f["heure"], "reseaux": {}}
    ok = True
    for r in f.get("reseaux", ["instagram", "facebook", "threads"]):
        try:
            res["reseaux"][r] = dict(RESEAUX[r](f), statut="publié", heure=datetime.datetime.now(BXL).strftime("%H:%M"))
        except Exception as e:
            ok = False
            res["reseaux"][r] = {"statut": "échec", "erreur": str(e)}
    res["statut"] = "publié" if ok else "échec partiel"
    ecrire(res_path, res)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return ok


def ecrire(p, d):
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def supprimer(resultat):
    """Supprime définitivement chaque publication d'un résultat publie/X.json et note la suppression."""
    p = RACINE / resultat
    r = json.loads(p.read_text(encoding="utf-8"))
    ok = True
    for res, info in r.get("reseaux", {}).items():
        if info.get("statut") != "publié" or not info.get("id"):
            continue
        try:
            if res in ("instagram", "facebook"):
                rep = appel("DELETE", f"{FB}/{info['id']}", {"access_token": env("META_PAGE_TOKEN")})
            elif res == "threads":
                rep = appel("DELETE", f"{TH}/{info['id']}", {"access_token": env("THREADS_TOKEN")})
            else:
                continue
            if rep.get("success") is False:
                raise ErreurAPI(f"refus : {rep}")
            info["statut"] = "supprimé"
            info["supprime_le"] = datetime.datetime.now(BXL).strftime("%Y-%m-%d %H:%M")
            print(f"{p.name} {res} : supprimé")
        except ErreurAPI as e:
            info["erreur_suppression"] = str(e)
            print(f"{p.name} {res} : ÉCHEC {e}")
            ok = False
    if all(i.get("statut") != "publié" for i in r.get("reseaux", {}).values()):
        r["statut"] = "supprimé"
    ecrire(p, r)
    return ok


def echeances():
    ok = True
    for fiche in sorted((RACINE / "a_publier").glob("*.json")):
        ok &= publier(fiche, attendre=False)
    return ok


def verifier():
    ok = True
    try:
        tok, page, ig = env("META_PAGE_TOKEN"), env("FB_PAGE_ID"), env("IG_USER_ID")
        p = appel("GET", f"{FB}/{page}", {"fields": "name,instagram_business_account", "access_token": tok})
        print(f"Facebook : page « {p.get('name')} » joignable.")
        lie = (p.get("instagram_business_account") or {}).get("id")
        print(f"Instagram : compte lié {lie} ({'conforme' if lie == ig else 'DIFFÉRENT de IG_USER_ID'}).")
        u = appel("GET", f"{FB}/{ig}", {"fields": "username", "access_token": tok})
        q = appel("GET", f"{FB}/{ig}/content_publishing_limit", {"fields": "quota_usage,config", "access_token": tok})
        d = (q.get("data") or [{}])[0]
        print(f"Instagram : @{u.get('username')}, quota {d.get('quota_usage')} sur {(d.get('config') or {}).get('quota_total')} par 24 h.")
    except Exception as e:
        ok = False
        print(f"Instagram et Facebook : {e}")
    try:
        t = appel("GET", f"{TH}/me", {"fields": "username", "access_token": env("THREADS_TOKEN")})
        print(f"Threads : @{t.get('username')} joignable.")
    except Exception as e:
        ok = False
        print(f"Threads : {e}")
    return ok


def tester_reel(chemin):
    """Crée les conteneurs Reel Instagram et vidéo Threads sans rien publier, pour valider l'hébergement."""
    url = url_media(chemin)
    attendre_media(url)
    tok, ig = env("META_PAGE_TOKEN"), env("IG_USER_ID")
    c = appel("POST", f"{FB}/{ig}/media", {"media_type": "REELS", "video_url": url, "caption": "test", "access_token": tok})["id"]
    ig_attendre(c, tok)
    print(f"Instagram : conteneur Reel {c} prêt (non publié, il expire seul en 24 h).")
    th = env("THREADS_TOKEN")
    c2 = appel("POST", f"{TH}/me/threads", {"media_type": "VIDEO", "video_url": url, "text": "test", "access_token": th})["id"]
    th_attendre(c2, th)
    print(f"Threads : conteneur vidéo {c2} prêt (non publié).")
    return True


def rafraichir_threads():
    r = appel("GET", f"{TH}/refresh_access_token", {"grant_type": "th_refresh_token", "access_token": env("THREADS_TOKEN")})
    jours = int(r.get("expires_in", 0)) // 86400
    sortie = os.environ.get("GITHUB_OUTPUT")
    if not sortie:
        raise ErreurAPI("GITHUB_OUTPUT absent : ce rafraîchissement ne tourne que dans GitHub Actions")
    print(f"::add-mask::{r['access_token']}")
    with open(sortie, "a") as fh:
        fh.write(f"jeton={r['access_token']}\n")
    print(f"Jeton Threads prolongé de {jours} jours.")
    return True


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    try:
        if a[0] == "verifier":
            ok = verifier()
        elif a[0] == "publier" and len(a) >= 2:
            ok = all([publier(f) for f in sorted(a[1:])])
        elif a[0] == "echeances":
            ok = echeances()
        elif a[0] == "tester-reel" and len(a) == 2:
            ok = tester_reel(a[1])
        elif a[0] == "supprimer" and len(a) >= 2:
            ok = all([supprimer(f) for f in a[1:]])
        elif a[0] == "rafraichir-threads":
            ok = rafraichir_threads()
        else:
            sys.exit(__doc__)
    except ErreurAPI as e:
        sys.exit(f"ERREUR : {e}")
    sys.exit(0 if ok else 1)
