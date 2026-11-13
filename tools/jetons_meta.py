#!/usr/bin/env python3
"""La Brique : range les jetons Meta dans les secrets GitHub du dépôt, sans jamais les afficher.

À lancer par Anto dans un terminal (gh doit être connecté) :
  python3 tools/jetons_meta.py meta      # Instagram et Facebook
  python3 tools/jetons_meta.py threads   # Threads

meta : demande l'identifiant de l'app, sa clé secrète et un jeton utilisateur de courte durée
(Graph API Explorer). Échange le jeton contre un jeton longue durée, en tire le jeton de la page
« La Brique - Hoops » (sans expiration) et l'identifiant du compte Instagram lié, puis écrit
META_PAGE_TOKEN, FB_PAGE_ID et IG_USER_ID dans les secrets.
threads : demande le jeton longue durée du générateur de jetons Threads, le vérifie et écrit THREADS_TOKEN.
Les saisies sont masquées. Rien n'est écrit sur le disque.
"""
import getpass, json, os, subprocess, sys, urllib.error, urllib.parse, urllib.request

DEPOT = "Mokamo2023/labrique-media"
V = os.environ.get("GRAPH_VERSION", "v27.0")
FB = f"https://graph.facebook.com/{V}"
PAGE = "La Brique - Hoops"


def get(url, **p):
    try:
        with urllib.request.urlopen(url + "?" + urllib.parse.urlencode(p), timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            m = json.loads(e.read()).get("error", {}).get("message")
        except Exception:
            m = ""
        sys.exit(f"Refusé par Meta ({e.code}) : {m}")


def secret(nom, valeur):
    r = subprocess.run(["gh", "secret", "set", nom, "--repo", DEPOT], input=valeur, text=True, capture_output=True)
    if r.returncode:
        sys.exit(f"gh n'a pas pu écrire {nom} : {r.stderr.strip()}")
    print(f"  secret {nom} enregistré")


def meta():
    app = input("Identifiant de l'app (29731724096420501 par défaut) : ").strip() or "29731724096420501"
    cle = getpass.getpass("Clé secrète de l'app (masquée) : ").strip()
    court = getpass.getpass("Jeton utilisateur du Graph API Explorer (masqué) : ").strip()
    long = get(f"{FB}/oauth/access_token", grant_type="fb_exchange_token", client_id=app, client_secret=cle, fb_exchange_token=court)["access_token"]
    pages = get(f"{FB}/me/accounts", fields="name,id,access_token,instagram_business_account", access_token=long).get("data", [])
    p = next((x for x in pages if x.get("name") == PAGE), None)
    if not p:
        sys.exit(f"Page « {PAGE} » absente du jeton. Pages vues : {', '.join(x.get('name', '?') for x in pages) or 'aucune'}. "
                 "Regénère le jeton en cochant la page et le compte Instagram.")
    ig = (p.get("instagram_business_account") or {}).get("id")
    if not ig:
        sys.exit("Aucun compte Instagram professionnel lié à la page. Relie @labrique.hoops à la page puis recommence.")
    info = get(f"{FB}/debug_token", input_token=p["access_token"], access_token=f"{app}|{cle}").get("data", {})
    exp = info.get("expires_at", 0)
    u = get(f"{FB}/{ig}", fields="username", access_token=p["access_token"]).get("username")
    print(f"Page {p['name']} ({p['id']}), Instagram @{u} ({ig}), jeton de page {'sans expiration' if not exp else 'qui EXPIRE : recommence avec un jeton longue durée'}.")
    secret("META_PAGE_TOKEN", p["access_token"])
    secret("FB_PAGE_ID", p["id"])
    secret("IG_USER_ID", ig)


def threads():
    jeton = getpass.getpass("Jeton Threads du générateur (masqué) : ").strip()
    u = get("https://graph.threads.net/v1.0/me", fields="username", access_token=jeton).get("username")
    print(f"Threads : @{u}")
    if u != "labrique.hoops":
        sys.exit("Ce jeton n'est pas celui de @labrique.hoops, rien n'est enregistré.")
    secret("THREADS_TOKEN", jeton)


if __name__ == "__main__":
    {"meta": meta, "threads": threads}.get((sys.argv[1:] or [""])[0], lambda: sys.exit(__doc__))()
    print("Terminé. Vérifie avec : gh workflow run publier.yml -f action=verifier --repo " + DEPOT)
