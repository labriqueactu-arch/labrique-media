#!/usr/bin/env python3
"""La Brique : posts version 2 (DA « brute », alignée sur les Reels dynamiques). Appelé par render_ds.py
quand la fiche porte "version": 2. Scène : tools/post2.js. Rendu 2160 × 2700, réduit en 1080 × 1350, accentué, JPEG 92.

Fiche :
  {"version": 2, "composant": "PostVerdict" | "PostChiffre" | "PostAffiche" | "PostFaceAFace",
   "props": {
     "verdict": "SWISH" | "REBOND" | "BRIQUE" (obligatoire pour PostVerdict, facultatif ailleurs),
     "chiffre": "40" (PostChiffre), "mot": "MVP" (PostAffiche, un mot géant),
     "photo": "joueur_detoure.png", "cadre": {"visage": 380, "cx": 560, "top": 150} (facultatif),
     "titre": "40 points et *rien* au bout" (la phrase du bandeau noir, un seul *mot* en serif),
     "bandeau": "13.11 · NBA · CLIPPERS 113-112 OKC · SOURCES ESPN, AP",
     "format": "LE VERDICT" (facultatif),
     PostFaceAFace : "haut" et "bas" : {"photo", "nom", "stat", "cadre"}
   }}
Fond : SWISH Os, REBOND Parquet, BRIQUE Encre ; sans verdict, Le Chiffre sur Os, L'Affiche sur Parquet.

Contrôles en plus de ceux de render_ds.py (refus avec _refuse.png) :
  3 niveaux de texte au plus et rapport d'au moins 5 entre le titre et l'info ; 2 signes forts au plus ;
  héros (joueur et mot géant) sur au moins 60 % de la surface ; marges de 64 px ; contraste des infos d'au moins 4,5 ;
  photo nette (Laplacien du visage) et visage jamais agrandi plus de 2 fois.
"""
import json, sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
DS = TOOLS / "ds"
W, H = 1080, 1350
FORMATS = {"PostVerdict": "LE VERDICT", "PostChiffre": "LE CHIFFRE", "PostAffiche": "L'AFFICHE", "PostFaceAFace": "FACE À FACE"}
THEMES = {"SWISH": "os", "REBOND": "parquet", "BRIQUE": "encre"}

# seuils calibrés le 14/11/2026 (design/diagnostic) : les anciens rendus échouent, la piste B passe
NIVEAUX_MAX = 3
RAPPORT_MIN = 5.0
HEROS_MIN = 0.60
MARGE = 64
CONTRASTE_MIN = 4.5
SIGNES_MAX = 2
NETTETE_MIN = 120.0        # variance du Laplacien du visage ramené à 256 px ; banque du 14/11 : 189 à 1220
AGRANDISSEMENT_MAX = 2.0   # hauteur du visage affiché / hauteur dans la source

CONTROLES2_JS = r"""
(args) => {
  const [W, H, MARGE] = args;
  const post = document.querySelector('.lb-post'); const P = post.getBoundingClientRect();
  const opac = e => { let o = 1; while (e && e !== document.body) { o *= parseFloat(getComputedStyle(e).opacity); e = e.parentElement; } return o; };
  const lum = c => { const m = c.match(/[\d.]+/g).map(Number); const f = v => { v /= 255; return v <= .03928 ? v / 12.92 : Math.pow((v + .055) / 1.055, 2.4); }; return .2126 * f(m[0]) + .7152 * f(m[1]) + .0722 * f(m[2]); };
  const fondDe = e => { while (e && e !== document.documentElement) { const b = getComputedStyle(e).backgroundColor; if (b && !/rgba\(.*,\s*0\)$/.test(b) && b !== 'transparent') return b; e = e.parentElement; } return 'rgb(255,255,255)'; };
  const textes = [];
  const w = document.createTreeWalker(post, NodeFilter.SHOW_TEXT);
  while (w.nextNode()) {
    const n = w.currentNode; if (!n.textContent.trim()) continue;
    const el = n.parentElement;
    if (el.closest('svg') || el.closest('[aria-hidden="true"]') || opac(el) < .5) continue;
    if (el.closest('.marque, .lb-logo, [class*="logo"]')) continue;
    const rg = document.createRange(); rg.selectNodeContents(n); const r = rg.getBoundingClientRect();
    if (r.width < 1 || r.right < P.left || r.left > P.right || r.bottom < P.top || r.top > P.bottom) continue;
    textes.push({ t: n.textContent.trim().slice(0, 30), fs: parseFloat(getComputedStyle(el).fontSize), el,
      heros: !!el.closest('.mot-geant, .lb-heros, .lb-mot-heros'), bandeau: !!el.closest('.bandeau'),
      x0: r.left - P.left, x1: r.right - P.left, y0: r.top - P.top, y1: r.bottom - P.top });
  }
  const issues = [];
  // niveaux de texte : tailles regroupées à 25 % près
  const tailles = Array.from(new Set(textes.map(t => Math.round(t.fs)))).sort((a, b) => b - a);
  const niveaux = [];
  tailles.forEach(s => { if (!niveaux.length || niveaux[niveaux.length - 1] / s > 1.25) niveaux.push(s); });
  // héros : rectangle qui englobe les joueurs et le mot géant (le joueur ou le chiffre, avec sa profondeur)
  let aire = 0; const rects = [];
  document.querySelectorAll('.mot-geant').forEach(e => { if (opac(e) >= .5) { const r = e.getBoundingClientRect(); rects.push([Math.max(r.left, P.left), Math.max(r.top, P.top), Math.min(r.right, P.right), Math.min(r.bottom, P.bottom)]); } });
  document.querySelectorAll('img.lb-photo').forEach(img => {
    if (img.classList.contains('lb-fantome') || img.classList.contains('lb-photo-fond') || opac(img) < .5) return;
    let r = img.getBoundingClientRect(), x0 = Math.max(r.left, P.left), y0 = Math.max(r.top, P.top), x1 = Math.min(r.right, P.right), y1 = Math.min(r.bottom, P.bottom);
    let e = img.parentElement;
    while (e && e !== post) { if (getComputedStyle(e).overflow === 'hidden') { const q = e.getBoundingClientRect(); x0 = Math.max(x0, q.left); y0 = Math.max(y0, q.top); x1 = Math.min(x1, q.right); y1 = Math.min(y1, q.bottom); } e = e.parentElement; }
    if (x1 > x0 && y1 > y0) rects.push([x0, y0, x1, y1]);
  });
  // par zone (face à face : chaque moitié a son héros), sinon l'union de tout
  const zones = Array.from(document.querySelectorAll('.lb-post > div')).filter(z => getComputedStyle(z).overflow === 'hidden' && z.querySelector('img.lb-photo'));
  const groupes = zones.length ? zones.map(z => { const q = z.getBoundingClientRect(); return rects.filter(r => r[0] >= q.left - 1 && r[2] <= q.right + 1 && r[1] >= q.top - 1 && r[3] <= q.bottom + 1); }) : [rects];
  groupes.forEach(g => { if (!g.length) return; const u = [Math.min(...g.map(r => r[0])), Math.min(...g.map(r => r[1])), Math.max(...g.map(r => r[2])), Math.max(...g.map(r => r[3]))]; aire += (u[2] - u[0]) * (u[3] - u[1]); });
  // marges
  const hors = textes.filter(t => !t.heros && !t.bandeau && (t.x0 < MARGE - 2 || t.x1 > W - MARGE + 2)).map(t => t.t);
  // contraste des infos (tout texte hors mot géant)
  const faibles = [];
  textes.filter(t => !t.heros).forEach(t => { const a = lum(getComputedStyle(t.el).color), b = lum(fondDe(t.el)); const c = (Math.max(a, b) + .05) / (Math.min(a, b) + .05); if (c < 4.5) faibles.push(t.t + ' (' + c.toFixed(1) + ')'); });
  const signes = document.querySelectorAll('.signe').length;
  return { niveaux, aire: aire / (W * H), hors: Array.from(new Set(hors)), faibles: Array.from(new Set(faibles)), signes, n: textes.length };
}
"""


def verifier2(res, v2=True):
    """Problèmes des contrôles du brief design, à partir du résultat de CONTROLES2_JS."""
    p = []
    nv = res["niveaux"]
    if len(nv) > NIVEAUX_MAX:
        p.append(f"{len(nv)} niveaux de texte ({', '.join(str(x) for x in nv)} px), {NIVEAUX_MAX} au plus")
    if len(nv) >= 2 and nv[0] / nv[1] < RAPPORT_MIN:
        p.append(f"rapport titre / info de {nv[0] / nv[1]:.1f} (au moins {RAPPORT_MIN})")
    if res["aire"] < HEROS_MIN:
        p.append(f"héros (joueur et mot géant) sur {res['aire'] * 100:.0f} % de la surface (au moins {HEROS_MIN * 100:.0f} %)")
    if res["hors"]:
        p.append("texte hors des marges de 64 px : " + " ; ".join(res["hors"][:4]))
    if res["faibles"]:
        p.append("contraste sous 4,5 : " + " ; ".join(res["faibles"][:4]))
    if v2 and res["signes"] > SIGNES_MAX:
        p.append(f"{res['signes']} signes graphiques forts ({SIGNES_MAX} au plus)")
    return p


def nettete(chemin, boite):
    import cv2
    im = cv2.imread(str(chemin), cv2.IMREAD_UNCHANGED)
    h, w = im.shape[:2]
    x0, y0, x1, y1 = int(boite[0] * w), int(boite[1] * h), int(boite[2] * w), int(boite[3] * h)
    g = cv2.cvtColor(im[y0:y1, x0:x1, :3], cv2.COLOR_BGR2GRAY)
    g = cv2.resize(g, (max(1, int(g.shape[1] * 256 / g.shape[0])), 256), interpolation=cv2.INTER_AREA)
    return float(cv2.Laplacian(g, cv2.CV_64F).var()), y1 - y0


def page(P):
    css = (DS / "tokens.css").read_text(encoding="utf-8").replace('url("fonts/', f'url("{(DS / "fonts").as_uri()}/')
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><style>{css} html,body{{margin:0;background:#000}}</style></head>
<body><div id="root"></div><script>window.P={json.dumps(P, ensure_ascii=False)};</script>
<script>document.fonts.ready.then(function(){{var s=document.createElement('script');s.src='{(TOOLS / "post2.js").as_uri()}';document.body.appendChild(s);}});</script></body></html>"""


def main(fiche, out, essai):
    import render_ds as R
    import photos as registre
    from faces import detect
    from PIL import Image, ImageFilter
    d = json.loads(fiche.read_text(encoding="utf-8"))
    comp, props = d.get("composant"), dict(d.get("props") or {})
    if comp not in FORMATS:
        sys.exit(f"ERREUR : composant {comp} absent de la version 2 ({', '.join(FORMATS)}). Classement et Échange restent en version 1.")
    verdict = (props.get("verdict") or "").upper() or None
    if comp == "PostVerdict" and verdict not in THEMES:
        sys.exit("ERREUR : PostVerdict demande un verdict SWISH, REBOND ou BRIQUE")
    for champ in ("titre", "bandeau"):
        if comp != "PostFaceAFace" and not props.get(champ):
            sys.exit(f"ERREUR : il manque \"{champ}\"")
    texte_total = " ".join(str(props.get(k, "")) for k in ("titre", "bandeau", "mot"))
    if any(t in texte_total for t in (" - ", " – ", " — ", "–", "—")):
        sys.exit("ERREUR : tiret interdit dans les textes")
    if texte_total.count("*") > 2:
        sys.exit("ERREUR : un seul mot en serif (*mot*) par post")
    base = fiche.parent
    chemins = []
    props = R.resoudre(props, base, chemins)
    if not chemins:
        sys.exit("ERREUR : aucune photo dans la fiche.")
    uniques = list(dict.fromkeys(chemins))
    sources = d.get("source_photo") or []
    sources = [sources] if isinstance(sources, dict) else sources
    if not sources and not essai:
        sys.exit("ERREUR : la fiche doit déclarer \"source_photo\": {\"url\", \"auteur\", \"joueur\"} pour chaque photo.")
    for i, p in enumerate(uniques):
        e = registre.conflit(p, sources[min(i, len(sources) - 1)] if sources else None, post=out.stem)
        if e:
            sys.exit(f"ERREUR : {p.name} : {registre.message(e)}")
    # photos : visages, taille, netteté
    infos, visages, probs = {}, {}, []
    for p in uniques:
        r = detect(p)
        if not r["boites"]:
            sys.exit(f"ERREUR : aucun visage détecté sur {p.name} : le contrôle visage est impossible")
        visages[str(p)] = r["boites"]
        im = Image.open(p)
        infos[p.as_uri()] = {"p": p.as_uri(), "w": im.size[0], "h": im.size[1], "v": r["boites"]}
    def ph(u):
        return infos[u] if isinstance(u, str) and u in infos else u
    for k in ("photo",):
        if k in props:
            props[k] = ph(props[k])
    for k in ("haut", "bas"):
        if isinstance(props.get(k), dict):
            props[k] = dict(props[k], photo=ph(props[k].get("photo")))
    P = dict(props, composant=comp, verdict=verdict, format=props.get("format") or FORMATS[comp],
             theme=THEMES.get(verdict) or {"PostChiffre": "os", "PostAffiche": "parquet"}.get(comp, "encre"))
    # netteté et agrandissement : le visage affiché ne dépasse pas 2 fois sa taille dans la source
    def regarde(phi, cadre, defaut):
        b = max(phi["v"], key=lambda q: q[3] - q[1])
        lap, hv = nettete(uri_chemin(phi["p"]), b)
        affiche = (cadre or {}).get("visage", defaut)
        if lap < NETTETE_MIN:
            probs.append(f"photo trop molle (netteté {lap:.0f}, minimum {NETTETE_MIN:.0f}) : prends une meilleure photo")
        if affiche / max(1, hv) > AGRANDISSEMENT_MAX:
            probs.append(f"visage agrandi {affiche / hv:.1f} fois (source {hv} px pour {affiche} px affichés, {AGRANDISSEMENT_MAX} au plus) : baisse \"cadre.visage\" ou change de photo")
    if comp == "PostFaceAFace":
        regarde(P["haut"]["photo"], P["haut"].get("cadre"), 230); regarde(P["bas"]["photo"], P["bas"].get("cadre"), 230)
    else:
        regarde(P["photo"], P.get("cadre"), 380)

    html_path = out.with_suffix(".html")
    html_path.write_text(page(P), encoding="utf-8")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch(args=["--allow-file-access-from-files"])
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=2)
        erreurs = []
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        pg.goto(html_path.as_uri())
        pg.wait_for_function("window.pret === true", timeout=20000)
        pg.wait_for_timeout(300)
        res = pg.evaluate(R.CONTROLES_JS, visages)
        res2 = pg.evaluate(CONTROLES2_JS, [W, H, MARGE])
        if erreurs:
            probs.append("erreur JavaScript : " + erreurs[0])
        if not all(res["polices"]):
            probs.append("polices non chargées")
        if res["petits"]:
            probs.append("textes sous 28 px : " + " ; ".join(res["petits"][:5]))
        probs += res["issues"] + verifier2(res2)
        grand = out.with_name(out.stem + "@2x.png")
        pg.locator(".lb-post").screenshot(path=str(grand))
        b.close()
    im = Image.open(grand).convert("RGB").resize((W, H), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2))
    grand.unlink()
    html_path.unlink()
    if probs:
        im.save(out.with_name(out.stem + "_refuse.png"))
        sys.exit("ERREUR : " + " | ".join(dict.fromkeys(probs)) + ". Corrige la fiche (cadre, photo, textes) puis relance. Ne publie pas.")
    im.save(out, "JPEG", quality=92, optimize=True, progressive=True)
    if not essai:
        for i, p in enumerate(uniques):
            registre.marquer(p, sources[min(i, len(sources) - 1)], out.stem)
    print(json.dumps({"ok": True, "sortie": str(out), "composant": comp, "version": 2, "niveaux": res2["niveaux"], "heros": round(res2["aire"], 2)}, ensure_ascii=False))


def uri_chemin(u):
    from urllib.parse import unquote, urlparse
    return Path(unquote(urlparse(u).path))
