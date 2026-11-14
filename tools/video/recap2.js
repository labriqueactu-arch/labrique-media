/* La Brique · scène Reel « recap » version 2 (1080 × 1920), pilotée par window.seek(t).
   Plans calés sur les phrases de la voix : accroche, joueur, contexte, verdict, punch, question.
   Données : window.FICHE (fiche + temps calculés par dynamique.py). Outils : window.M (motion.js). */
(function () {
  var F = window.FICHE, L = window.LaBrique, h = React.createElement, M = window.M;
  var T = F.temps, D = T.D, C = F.cadre, PH = T.phrases;
  var V = F.verdict ? F.theme_verdict : null;

  // ---------- plans ----------
  var ROLE_PLAN = { accroche: 'A', joueur: 'B', contexte: 'C', verdict: 'D', punch: 'E', question: 'F' };
  var ENTREE = { B: 'whip', C: 'zoom', D: 'volet', E: 'coupe', F: 'voletD' };
  var plans = PH.map(function (p, i) {
    return { id: ROLE_PLAN[p.role] || 'C', ph: p, t0: i === 0 ? 0 : Math.max(0, p.d - (p.silence || 0) - 0.06) };
  });
  plans.forEach(function (pl, i) { pl.t1 = i + 1 < plans.length ? plans[i + 1].t0 : D; pl.entree = i === 0 ? null : ENTREE[pl.id]; });
  var THEME = { A: 'affiche', B: 'sombre', C: V === 'os' ? 'affiche' : 'os', D: V || 'affiche', E: V || 'sombre', F: V === 'affiche' ? 'sombre' : 'affiche' };
  var FOND = { affiche: '#e04e22', sombre: '#121110', os: '#f2ede4' };
  function planA(t) { for (var i = plans.length - 1; i >= 0; i--) if (t >= plans[i].t0) return i; return 0; }

  // ---------- textes ----------
  function jetons(s) { // mots affichés, la ponctuation seule rejoint le mot précédent
    var out = [];
    String(s).split(/\s+/).forEach(function (w) { if (!w) return; if (!/[\wÀ-ÿ]/.test(w) && out.length) out[out.length - 1] += ' ' + w; else out.push(w); });
    return out;
  }
  // sous-titres : groupes de 3 mots au plus, coupés à la ponctuation
  var ST = [];
  PH.forEach(function (p, i) {
    var role = p.role;
    var montre = p.sous_titres !== false && (role === 'contexte' || role === 'verdict' || role === 'punch' || (typeof p.sous_titres === 'string'));
    if (!montre) return;
    var aff = jetons(typeof p.sous_titres === 'string' ? p.sous_titres : F.voix.phrases[i].texte);
    var parles = p.mots;
    if (aff.length !== parles.length) aff = parles.map(function (m) { return m.m; });
    var n = aff.length;
    if (role === 'verdict' && F.verdict) n -= 1; // le dernier mot, c'est le tampon
    var g = [];
    for (var j = 0; j < n; j++) {
      g.push({ m: aff[j], d: parles[j].d });
      if (g.length === 3 || /[.,?!…:]$/.test(aff[j]) || j === n - 1) { ST.push({ role: role, mots: g, d: g[0].d }); g = []; }
    }
  });
  ST.forEach(function (s, i) { var fin = PH.filter(function (p) { return p.role === s.role; })[0].f + 0.25; s.f = i + 1 < ST.length ? Math.min(ST[i + 1].d, Math.max(fin, ST[i + 1].d)) : fin; if (i + 1 < ST.length && ST[i + 1].role !== s.role) s.f = Math.min(fin, ST[i + 1].d); });

  var acc = PH.filter(function (p) { return p.role === 'accroche'; })[0];
  var ACC = M.mots(acc && acc.ecran || '');
  var accT = acc ? M.caler(ACC.length, acc.mots, acc.d, acc.f) : [];
  if (accT.length) accT[0] = 0; // le premier mot est là dès l'image 1
  var qu = PH.filter(function (p) { return p.role === 'question'; })[0];
  var FIN = M.mots(F.fin);
  var finT = qu ? M.caler(FIN.length, qu.mots, qu.d, qu.f) : [];

  // ---------- composition ----------
  var grainURI = 'data:image/svg+xml;utf8,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="300" height="300"><filter id="n"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" stitchTiles="stitch"/><feColorMatrix values="0 0 0 0 .5 0 0 0 0 .5 0 0 0 0 .5 0 0 0 1.4 -.2"/></filter><rect width="300" height="300" filter="url(#n)"/></svg>');
  var abs = function (id, style, enfant, cls) { return h('div', { id: id, key: id, className: 'lb-abs ' + (cls || ''), style: style }, enfant); };
  var ECLATS = 16;
  var enfants = [
    abs('fondNeuf', { left: 0, top: 0, width: 1080, height: 1920, background: '#000' }),
    abs('monde', { left: 0, top: 0, width: 1080, height: 1920, transformOrigin: '540px 960px' }, [
      h('div', { id: 'halo', key: 'halo', className: 'lb-abs', style: { left: C.x - 160, top: C.y - 40, width: C.l + 320, height: C.l * 1.6, borderRadius: '50%', background: 'radial-gradient(closest-side, rgba(246,160,77,.8), rgba(246,160,77,0))' } }),
      h('img', { id: 'fantome', key: 'fantome', className: 'lb-abs', src: F.fantome, style: { left: C.x - 70, top: C.y - 30, width: C.l, opacity: .5 } }),
      h('div', { id: 'chiffre', key: 'chiffre', className: 'lb-abs heros', style: { left: 0, top: 470, width: 1080, height: 900, transformOrigin: '30px 55%' } },
        h(L.MotHeros, { texte: String(F.chiffre), taille: F.tailleChiffre || 860, relief: true, echo: true, position: { left: 30, top: 0 } })),
      h('img', { id: 'joueur', key: 'joueur', className: 'lb-abs lb-photo lb-photo-lumiere', src: F.photo, style: { left: C.x, top: C.y, width: C.l, transformOrigin: '50% 30%', WebkitMaskImage: 'linear-gradient(to bottom, #000 64%, transparent 90%)', maskImage: 'linear-gradient(to bottom, #000 64%, transparent 90%)' } })
    ]),
    abs('voile', { left: 0, top: 960, width: 1080, height: 960, background: 'linear-gradient(to bottom, transparent, var(--fond) 62%)' }),
    abs('lignes', { left: 0, top: 0, width: 1080, height: 1920 }, h('svg', { width: 1080, height: 1920, viewBox: '0 0 1080 1920' },
      Array.from({ length: 16 }, function (_, i) { return h('rect', { key: i, id: 'ligne' + i, x: 0, y: 120 + M.bruit(i, 3) * 1680, width: 160 + M.bruit(i, 5) * 520, height: 3 + M.bruit(i, 9) * 7, rx: 4, fill: 'var(--texte)', opacity: .55 }); }))),
    abs('ondes', { left: 0, top: 0, width: 1080, height: 1920 }, [0, 1, 2].map(function (i) {
      return h('div', { key: i, id: 'onde' + i, className: 'lb-abs', style: { left: -200, top: -200, width: 400, height: 400, borderRadius: '50%', border: '10px solid var(--texte)', boxSizing: 'border-box', opacity: 0 } });
    })),
    abs('titres', { left: 60, top: 1180, width: 880, display: 'flex', flexWrap: 'wrap', alignItems: 'baseline', columnGap: '0.22em', rowGap: 0, fontSize: 150, lineHeight: .92 },
      ACC.map(function (w, i) { return h('span', { key: i, id: 'acc' + i, className: 'lb-cond' + (w.accent ? ' lb-accent' : ''), style: { display: 'inline-block', textTransform: 'uppercase', transformOrigin: '0% 80%' } }, w.m); })),
    abs('nom', { left: 60, top: 1170 }, h(L.NomJoueur, { prenom: F.prenom, nom: F.nom, taille: F.tailleNom || (String(F.nom).length > 11 ? 84 : 118) })),
    abs('stats', { left: 60, top: 1330 }, h('div', { className: 'lb-pastilles' }, F.stats.map(function (s, i) {
      return h('span', { key: i, id: 'stat' + i, className: 'lb-pastille ' + (i ? 'lb-pastille-contour' : 'lb-pastille-pleine'), style: { fontSize: 56, display: 'inline-block' } },
        s.texte ? s.texte : [h('span', { key: 'v', id: 'val' + i }, s.a), s.suffixe || '']);
    }))),
    abs('st', { left: 60, top: 1230, width: 880, height: 240, display: 'flex', flexWrap: 'wrap', alignContent: 'flex-end', columnGap: '0.24em' }),
    abs('eclats', { left: 0, top: 0, width: 1080, height: 1920 }, Array.from({ length: ECLATS }, function (_, i) {
      return h('div', { key: i, id: 'eclat' + i, className: 'lb-abs', style: { left: -30, top: -16, width: 44 + M.bruit(i, 2) * 40, height: 24 + M.bruit(i, 4) * 14, background: i % 3 ? '#e04e22' : '#7e200e', boxShadow: 'inset 0 0 0 3px #121110', opacity: 0 } });
    })),
    F.verdict ? abs('sceau', { left: 620, top: 1080 }, h(L.SceauVerdict, { verdict: F.verdict, taille: 320, rotation: 0, libre: true })) : null,
    abs('fin', { left: 60, top: 1060, width: 880, textAlign: 'center' }, [
      h('div', { key: 'q', className: 'lb-cond', style: { fontSize: 140, lineHeight: .9, display: 'flex', flexWrap: 'wrap', justifyContent: 'center', columnGap: '0.2em' } },
        FIN.map(function (w, i) { return h('span', { key: i, id: 'fin' + i, className: w.accent ? 'lb-accent' : '', style: { display: 'inline-block', textTransform: 'uppercase' } }, w.m); })),
      h('div', { key: 'c', id: 'compte', className: 'lb-serif', style: { fontSize: 58, marginTop: 30 } }, '@labrique.hoops')
    ]),
    abs('logo', { left: 60, top: 262 }, h(L.Logo, { taille: 64 })),
    abs('balayage', { left: -700, top: -200, width: 520, height: 2320, background: 'linear-gradient(90deg, rgba(255,240,220,0), rgba(255,240,220,.55) 50%, rgba(255,240,220,0))', mixBlendMode: 'soft-light', transform: 'rotate(14deg)', pointerEvents: 'none' }),
    abs('grain2', { left: 0, top: 0, width: 1080, height: 1920, backgroundImage: 'url("' + grainURI + '")', backgroundSize: '300px 300px', mixBlendMode: 'overlay', opacity: .16, pointerEvents: 'none' }),
    abs('flash', { left: 0, top: 0, width: 1080, height: 1920, background: '#fff', opacity: 0 })
  ].filter(Boolean);

  ReactDOM.createRoot(document.getElementById('root')).render(
    h(L.Post, { theme: 'affiche', hauteur: 1920, grain: false, reperes: false, motif: true }, enfants));

  // ---------- mesures (après chargement des polices) ----------
  var G = { pret: false };
  function rectTextes(el) {
    var r = { l: 1e9, r: -1e9, t: 1e9, b: -1e9 }, w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    while (w.nextNode()) { if (!w.currentNode.textContent.trim()) continue; var rg = document.createRange(); rg.selectNodeContents(w.currentNode); var q = rg.getBoundingClientRect(); r.l = Math.min(r.l, q.left); r.r = Math.max(r.r, q.right); r.t = Math.min(r.t, q.top); r.b = Math.max(r.b, q.bottom); }
    return r;
  }
  window.preparer = function () {
    ['monde', 'chiffre', 'joueur'].forEach(function (id) { M.pose(id, {}); });
    var img = document.getElementById('joueur'), lh = C.l * img.naturalHeight / img.naturalWidth;
    G.jh = lh;
    var v = (F.visages || [[0.35, 0.05, 0.65, 0.3]]).reduce(function (a, b) { return (b[3] - b[1]) * (b[2] - b[0]) > (a[3] - a[1]) * (a[2] - a[0]) ? b : a; });
    G.face = { l: C.x + v[0] * C.l, r: C.x + v[2] * C.l, t: C.y + v[1] * lh, b: C.y + v[3] * lh };
    G.face.cx = (G.face.l + G.face.r) / 2; G.face.cy = (G.face.t + G.face.b) / 2; G.face.h = G.face.b - G.face.t;
    G.basVisages = Math.max.apply(null, (F.visages || []).map(function (b) { return C.y + b[3] * lh; }).concat([G.face.b]));
    var num = rectTextes(document.getElementById('chiffre'));
    // plan A : le chiffre doit rester lisible en entier, le joueur se décale à droite sans couper le visage
    // zoom maximal du plan A : arrivée 1,1, poussée 0,08/s, punch 4 %
    var dA = plans.length > 1 ? plans[1].t0 : D, zA = 1.1 * (1 + 0.08 * dA) * 1.04;
    var bl0 = Math.min.apply(null, (F.visages || []).map(function (b) { return C.x + b[0] * C.l; }).concat([G.face.l]));
    var br0 = Math.max.apply(null, (F.visages || []).map(function (b) { return C.x + b[2] * C.l; }).concat([G.face.r]));
    var besoin = Math.max(0, num.r - 50 - G.face.l), marge = (FX + (1064 - FX) / zA) - br0 - 24, mini = (FX - (FX - 16) / zA) - bl0 + 24;
    G.dxA = M.clamp(besoin, mini, Math.max(mini, marge));
    G.sA = besoin > marge ? Math.max(.6, (G.face.l + G.dxA + 50 - 30) / (num.r - 30)) : 1;
    // gros plan : visage à 400 px de haut, centré en (540, 720)
    var limite = function (ey) { return (1200 - ey) / Math.max(1, G.basVisages - G.face.cy); };
    var largeur = 960 / Math.max(1, G.face.r - G.face.l) / 1.3; // marge pour l'entrée, le recadrage et les punch in
    G.exE = (G.face.r - G.face.l) * Math.min(G.zC || 9, largeur) / 2 < 380 ? 420 : 540;
    G.zC = Math.min(M.clamp(420 / G.face.h, 1.35, 2.4), limite(700), largeur);
    G.zE = Math.min(1 + (G.zC - 1) * 0.5, limite(680), largeur);
    // titres de l'accroche : tenir en 2 lignes de 880 px
    var ti = document.getElementById('titres'), fs = 150;
    while (fs > 80 && (ti.scrollHeight > fs * .95 * 2 + 4 || ti.scrollWidth > 884)) { fs -= 6; ti.style.fontSize = fs + 'px'; }
    ti.style.top = (1490 - ti.scrollHeight) + 'px';
    // décalage du joueur pour que toutes les boîtes visage tiennent à l'écran au zoom zmax (zoom centré)
    var ox = C.x + C.l / 2;
    var bl = Math.min.apply(null, (F.visages || []).map(function (b) { return C.x + b[0] * C.l; }).concat([G.face.l]));
    var br = Math.max.apply(null, (F.visages || []).map(function (b) { return C.x + b[2] * C.l; }).concat([G.face.r]));
    G.cale = function (xv, js, zmax) {
      var lo = 540 - 528 / zmax, hi = 540 + 528 / zmax;
      var L0 = ox + (bl - ox) * js, R0 = ox + (br - ox) * js;
      return M.clamp(xv, lo - L0, Math.max(lo - L0, hi - R0));
    };
    G.xB = G.cale(40, 1.09, 1.2); G.xD = G.cale(40, 1.07, 1.35); G.xF = G.cale(0, 1.03, 1.12);
    G.boites = (F.visages || []).map(function (b) { return [C.x + b[0] * C.l, C.y + b[1] * lh, C.x + b[2] * C.l, C.y + b[3] * lh]; });
    G.pret = true;
  };
  var FX = 540, FY = 1000; // point fixe de la poussée de l'accroche
  function zoomAutour(z) { return { s: z, x: (FX - 540) * (1 - z), y: (FY - 960) * (1 - z) }; }
  function camVers(cx, cy, z, ex, ey) { return { s: z, x: ex - ((cx - 540) * z + 540), y: ey - ((cy - 960) * z + 960) }; }

  // ---------- timeline ----------
  var themeActuel = null;
  function theme(nom) { if (nom !== themeActuel) { document.querySelector('.lb-post').setAttribute('data-theme', nom); themeActuel = nom; } }

  window.seek = function (t) {
    if (!G.pret) window.preparer();
    var boucle = t >= D - 0.2;            // coupe sèche finale : retour sur l'accroche pour la boucle
    var tt = boucle ? t - (D - 0.2) + 0.12 : t;
    var i = boucle ? 0 : planA(tt), pl = plans[i], u = tt - pl.t0, id = pl.id;
    var suiv = plans[i + 1];
    var S = {
      cam: { s: 1, x: 0, y: 0, r: 0 }, pan: 0, bx: 0,
      joueur: { x: 0, y: 0, s: 1, o: 1 }, chiffre: { x: 0, y: 0, s: 1, o: 1 }, fantome: { o: .45 }, halo: .6,
      titres: false, nom: false, stats: false, sceau: 0, fin: false, logo: 0, lignes: 0, flash: 0, voile: .9
    };
    var respire = 1 + 0.015 * (1 + Math.sin(tt * 2 * Math.PI / 2.4));

    // ----- plan par plan -----
    if (id === 'A') {
      var arr = M.k(u, [[0, 1.1], [0.3, 1.0, 'back']]);
      var za = zoomAutour(arr * (1 + 0.08 * u));
      S.cam = { s: za.s, x: za.x, y: za.y, r: 0 };
      S.joueur = { x: G.dxA + M.k(u, [[0, -70], [0.5, 0, 'expoOut']]), y: 0, s: respire, o: 1 };
      S.chiffre = { x: -40 * u, y: 0, s: G.sA * M.k(u, [[0, 1.12], [0.28, 1, 'back']]) * (1 + 0.04 * u), o: 1 };
      S.titres = true; S.lignes = 1 - M.p(u, 0, .45, 'out'); S.voile = .95;
      S.flash = M.flash(tt, 1 / 30, 2, .55);
    } else if (id === 'B') {
      S.cam.s = 1.02 + 0.12 * u; S.cam.x = -30 * u;
      S.joueur = { x: G.xB, y: -20, s: 1.06 * respire, o: 1 };
      S.chiffre = { x: 120, y: -140, s: 1.3, o: .16 };
      S.nom = true; S.stats = true; S.halo = .45;
    } else if (id === 'C') {
      var c = camVers(G.face.cx, G.face.cy, G.zC * (1 + 0.1 * u), 540, 720);
      S.cam = { s: c.s, x: c.x, y: c.y, r: 0 };
      S.joueur = { x: 0, y: 0, s: respire, o: 1 };
      S.chiffre = { x: -60, y: -260, s: 1.1, o: .12 }; S.fantome = { o: .7 }; S.halo = .3; S.voile = 1;
    } else if (id === 'D') {
      var pd = M.p(u, 0, .6, 'expoOut');
      S.cam.s = M.mix(1.25, 1.0, pd) * (1 + 0.12 * u);
      S.joueur = { x: G.xD, y: 0, s: 1.04 * respire, o: 1 };
      S.chiffre = { x: 0, y: -80, s: 1.15, o: .14 }; S.halo = .35;
      S.sceau = 1;
    } else if (id === 'E') {
      var e = camVers(G.face.cx, G.face.cy, G.zE * (1 + 0.1 * u), G.exE, 700);
      S.cam = { s: e.s, x: e.x, y: e.y, r: 0 };
      S.joueur = { x: 0, y: 0, s: respire, o: 1 };
      S.chiffre = { x: 260, y: -120, s: 1.2, o: .14 }; S.fantome = { o: .6 };
      S.sceau = F.verdict ? 1 : 0; S.sceauHaut = M.p(u, 0, .3, 'expoOut');
    } else if (id === 'F') {
      S.cam.s = 1.04 + 0.12 * u;
      S.joueur = { x: G.xF, y: -60 - 30 * u, s: respire, o: .55 };
      S.chiffre = { x: 0, y: -180 - 90 * u, s: 1 + .05 * u, o: .2 }; S.fin = true; S.voile = 1;
      S.joueur.x -= 40 * u;
    }

    // ----- entrées de plan -----
    var vol = null;
    if (pl.entree === 'whip' || (suiv && suiv.entree === 'whip' && tt > suiv.t0 - 0.12)) {
      if (pl.entree === 'whip' && u < 0.16) { var q = M.p(u, 0, .16, 'expoOut'); S.pan = M.mix(560, 0, q); S.bx = M.mix(70, 0, q); S.lignes = 1 - q; }
      if (suiv && suiv.entree === 'whip' && tt > suiv.t0 - 0.12) { var q2 = M.p(tt, suiv.t0 - 0.12, .12, 'expoIn'); S.pan = -560 * q2; S.bx = 70 * q2; S.lignes = q2; }
    }
    if (suiv && suiv.entree === 'zoom' && tt > suiv.t0 - 0.16) {
      var z = M.p(tt, suiv.t0 - 0.16, .16, 'expoIn');
      S.cam.s *= M.mix(1, 1.12, z); S.flash = Math.max(S.flash, z * .5);
    }
    if (pl.entree === 'zoom') { S.flash = Math.max(S.flash, M.flash(tt, pl.t0, 2, .8)); S.cam.s *= M.k(u, [[0, 1.12], [.3, 1, 'expoOut']]); }
    if (pl.entree === 'coupe') { S.cam.s *= 1 + 0.1 * M.impulsion(u, 0, .03, .3); }
    if (pl.entree === 'volet' || pl.entree === 'voletD') {
      var pv = M.p(u, 0, .34, 'lin');
      if (pv < 1) vol = { p: pv, theme: THEME[id], gauche: pl.entree === 'volet' };
    }

    // ----- punch in sur les temps forts -----
    var punch = 0;
    if (id === 'A') accT.forEach(function (a) { punch += 0.035 * M.impulsion(tt, a, .04, .25); });
    if (id === 'B') T.stats.forEach(function (a) { punch += 0.06 * M.impulsion(tt, a, .04, .3); });
    if (id === 'F') finT.forEach(function (a) { punch += 0.05 * M.impulsion(tt, a, .04, .25); });
    if (id !== 'A' && id !== 'F') pl.ph.mots.forEach(function (m) { punch += 0.035 * M.impulsion(tt, m.d, .03, .22); });
    var onsets = [];
    PH.forEach(function (q) { q.mots.forEach(function (m) { onsets.push(m.d); }); });
    for (var bt0 = 0.5; bt0 < D - 0.3; bt0 += 0.5) {
      if (onsets.some(function (o) { return Math.abs(o - bt0) < .17; })) continue;
      punch += 0.045 * M.impulsion(tt, bt0, .04, .26);
    }
    // silence de tension avant le verdict : pulsation sur la grille de tempo (120 BPM, un temps toutes les 0,5 s)
    if (id === 'D' && T.sceau != null) for (var bt = pl.t0 + .25; bt < T.sceau - .1; bt += .5) punch += 0.035 * M.impulsion(tt, bt, .04, .3);
    var gi = -1;
    for (var q3 = 0; q3 < ST.length; q3++) if (tt >= ST[q3].d && ST[q3].role === pl.ph.role) gi = q3;
    if (gi >= 0 && (id === 'C' || id === 'E') && ST[gi].d > pl.t0 + .3) {
      var sens = gi % 2 ? 1 : -1;
      S.cam.x += sens * 34 * S.cam.s; S.cam.s *= 1.05;
      punch += 0.04 * M.impulsion(tt, ST[gi].d, .03, .22);
    }
    S.cam.s *= 1 + punch;

    S.cam.x += 20 * Math.sin(tt * 2 * Math.PI / 1.9); S.cam.y += 14 * Math.sin(tt * 2 * Math.PI / 2.5 + 1);
    // ----- tremblements -----
    var tr = M.tremble(tt, 0, 4, 16, 1);
    if (T.sceau != null) { var t2 = M.tremble(tt, T.sceau, 5, 26, 2); tr.x += t2.x; tr.y += t2.y; tr.r += t2.r; }
    T.stats.forEach(function (a, n) { var t3 = M.tremble(tt, a + .5, 3, 8, 5 + n); tr.x += t3.x; tr.y += t3.y; });
    var salve = null;
    if (F.verdict === 'BRIQUE' && T.sceau != null && tt >= T.sceau && tt < T.sceau + 1.1 && id === 'D') salve = { t: T.sceau, x: 780, y: 1240, v: 1 };
    var iBr = FIN.map(function (w) { return w.accent; }).indexOf(true);
    if (iBr >= 0 && id === 'F' && tt >= finT[iBr] + .12) salve = { t: finT[iBr] + .12, x: 640, y: 1250, v: .75 };
    if (salve) { var t4 = M.tremble(tt, salve.t, 4, 14, 9); tr.x += t4.x; tr.y += t4.y; }

    // ----- thème et fond -----
    var themeCible = THEME[id];
    if (vol) { theme(THEME[plans[i - 1].id]); var fn = document.getElementById('fondNeuf'); fn.style.background = FOND[vol.theme]; fn.style.clipPath = M.voletBriques(vol.p, 7, vol.gauche); fn.style.opacity = 1; }
    else { theme(themeCible); document.getElementById('fondNeuf').style.opacity = 0; }

    // ----- garde de caméra : les boîtes visage restent dans le cadre (règle « visage jamais coupé ») -----
    var derive = Math.sin(tt * 2 * Math.PI / 5) * 8;
    if (G.boites) {
      var ox2 = C.x + C.l / 2, oy2 = C.y + .3 * G.jh, jx = S.joueur.x + S.pan + derive, jy = S.joueur.y, js2 = S.joueur.s;
      var sc = S.cam.s, ex0 = 1e9, ex1 = -1e9, ey0 = 1e9, ey1 = -1e9;
      G.boites.forEach(function (b) {
        var X0 = ox2 + (b[0] - ox2) * js2 + jx, X1 = ox2 + (b[2] - ox2) * js2 + jx, Y0 = oy2 + (b[1] - oy2) * js2 + jy, Y1 = oy2 + (b[3] - oy2) * js2 + jy;
        ex0 = Math.min(ex0, X0); ex1 = Math.max(ex1, X1); ey0 = Math.min(ey0, Y0); ey1 = Math.max(ey1, Y1);
      });
      if (S.joueur.o >= .5 && ex1 > ex0) {
        var lim = Math.min(1056 / (ex1 - ex0), 1896 / (ey1 - ey0));
        if (sc > lim) { var r0 = lim / sc; S.cam.x *= r0; S.cam.y *= r0; sc = lim; S.cam.s = sc; }
        var dx = S.cam.x + tr.x, dy = S.cam.y + tr.y;
        var a0 = 540 + (ex0 - 540) * sc + dx, a1 = 540 + (ex1 - 540) * sc + dx, b0 = 960 + (ey0 - 960) * sc + dy, b1 = 960 + (ey1 - 960) * sc + dy;
        if (a0 < 12) S.cam.x += 12 - a0; else if (a1 > 1068) S.cam.x -= a1 - 1068;
        if (b0 < 12) S.cam.y += 12 - b0; else if (b1 > 1908) S.cam.y -= b1 - 1908;
      }
    }
    // ----- application -----
    M.pose('monde', { s: S.cam.s, x: S.cam.x + tr.x, y: S.cam.y + tr.y, r: tr.r, bx: S.bx });
    M.pose('balayage', { x: ((tt % 1.3) / 1.3) * 2300, r: 14 });
    M.pose('joueur', { x: S.joueur.x + S.pan + derive, y: S.joueur.y, s: S.joueur.s, o: S.joueur.o,
      f: 'drop-shadow(0 0 ' + (22 + 12 * Math.sin(tt * 2 * Math.PI / 1.3)).toFixed(1) + 'px rgba(246,160,77,.75)) drop-shadow(' + (14 + derive).toFixed(1) + 'px 18px 0 rgba(18,17,16,.35))' });
    M.pose('chiffre', { x: S.chiffre.x + S.pan * .8, y: S.chiffre.y, s: S.chiffre.s, o: S.chiffre.o });
    M.pose('fantome', { x: S.pan * .55 - 40 - 60 * Math.sin(tt / 1.1), y: 18 * Math.cos(tt / 0.9), o: S.fantome.o });
    M.pose('halo', { x: S.pan * .4, o: S.halo * (0.75 + 0.25 * Math.sin(tt * 2 * Math.PI / 1.6)), s: 1 + .05 * Math.sin(tt * 2 * Math.PI / 1.6) });
    M.pose('voile', { o: S.voile });
    // lignes de vitesse
    for (var l = 0; l < 16; l++) {
      var el = document.getElementById('ligne' + l);
      var vit = 2400 + M.bruit(l, 11) * 2600;
      el.setAttribute('x', (((M.bruit(l, 13) * 1500 - tt * vit) % 1500) + 1500) % 1500 - 300);
      el.setAttribute('opacity', (S.lignes * .6).toFixed(2));
    }
    // accroche, mot par mot sur la voix
    ACC.forEach(function (w, n) {
      var a = accT[n], on = S.titres && tt >= a - 1e-6;
      var pa = M.p(tt, a, .2, 'back');
      M.pose('acc' + n, { o: on ? 1 : 0, s: on ? (a === 0 ? M.mix(1.06, 1, M.p(tt, 0, .2, 'out')) : M.mix(.55, 1, pa)) : 1, y: on ? M.mix(30, 0, M.p(tt, a, .18, 'expoOut')) : 0,
        f: on && tt - a < .1 ? 'drop-shadow(5px 0 0 rgba(255,0,60,.55)) drop-shadow(-5px 0 0 rgba(0,220,255,.55))' : null });
    });
    var ot = M.clamp(1 - Math.abs(S.pan) / 160, 0, 1);
    M.pose('titres', { o: S.titres ? ot : 0, x: S.pan * 1.1, bx: S.bx });
    // nom et stats
    var tB = id === 'B' ? pl.t0 : -9;
    M.pose('nom', { o: S.nom ? ot : 0, clip: S.nom ? M.p(tt, tB + .02, .3, 'expoOut') * 100 : 100, x: S.nom ? M.mix(-50, 0, M.p(tt, tB, .4, 'expoOut')) + S.pan * 1.1 : 0, bx: S.bx });
    M.pose('stats', { o: S.stats ? ot : 0, x: S.pan * 1.1, bx: S.bx });
    F.stats.forEach(function (s, n) {
      var a = T.stats[n], on = S.stats && tt >= a;
      M.pose('stat' + n, { o: on ? 1 : 0, s: on ? M.mix(1.6, 1, M.p(tt, a, .26, 'back')) : 1, r: on ? M.mix(-6, 0, M.p(tt, a, .3, 'elastic')) : 0 });
      var v = document.getElementById('val' + n);
      if (v) { var fin = M.compteur(tt, a, .55, s.de || 0, s.a); v.textContent = fin; v.parentNode.style.transform += ' scale(' + (1 + .3 * M.impulsion(tt, a + .55, .02, .18)).toFixed(3) + ')'; }
    });
    // sous-titres
    var st = document.getElementById('st'), g = null;
    for (var s2 = 0; s2 < ST.length; s2++) if (tt >= ST[s2].d && tt < ST[s2].f) g = ST[s2];
    if (boucle || id === 'F' || id === 'A' || id === 'B') g = null;
    var cle = g ? ST.indexOf(g) : -1;
    if (st.dataset.g !== String(cle)) {
      st.dataset.g = String(cle);
      st.innerHTML = '';
      if (g) {
        var serif = g.role === 'punch';
        st.style.fontSize = (serif ? 112 : 104) + 'px';
        g.mots.forEach(function (m, n) { var sp = document.createElement('span'); sp.id = 'stm' + n; sp.textContent = m.m; sp.className = serif ? 'lb-serif' : 'lb-cond'; sp.style.display = 'inline-block'; sp.style.textTransform = serif ? 'none' : 'uppercase'; sp.style.lineHeight = '1'; sp.style.transformOrigin = '50% 85%'; st.appendChild(sp); });
        var fs = serif ? 112 : 104;
        var haut = function () { var sp = st.children, a = 1e9, b = -1e9, r = 0; for (var q = 0; q < sp.length; q++) { a = Math.min(a, sp[q].offsetTop); b = Math.max(b, sp[q].offsetTop + sp[q].offsetHeight); r = Math.max(r, sp[q].offsetLeft + sp[q].offsetWidth); } return { h: b - a, w: r }; };
        var mz = haut();
        while (fs > 64 && (mz.w > 880 || mz.h > fs * 2.15)) { fs -= 6; st.style.fontSize = fs + 'px'; mz = haut(); }
      }
    }
    if (g) g.mots.forEach(function (m, n) {
      var on = tt >= m.d - 1e-6, cour = on && (n === g.mots.length - 1 || tt < g.mots[n + 1].d);
      var el = document.getElementById('stm' + n);
      M.pose(el, { o: on ? 1 : 0, s: on ? M.mix(.6, 1, M.p(tt, m.d, .18, 'back')) : 1, y: on ? M.mix(18, 0, M.p(tt, m.d, .14, 'expoOut')) : 0 });
      el.style.color = cour ? (themeActuel === 'affiche' ? '#121110' : 'var(--texte-accent)') : 'var(--texte)';
    });
    // tampon du verdict
    if (F.verdict) {
      var ts = T.sceau, ds = tt - ts, on2 = S.sceau > 0 && tt >= ts;
      var rot = -8 + (on2 ? M.mix(-24, 0, M.p(tt, ts, .22, 'out')) : 0);
      if (on2 && F.verdict === 'REBOND') rot += Math.sin(ds * 2 * Math.PI * 9) * 7 * Math.exp(-ds * 3.5);
      var sh = S.sceauHaut || 0;
      M.pose('sceau', { o: on2 ? S.sceau : 0, s: on2 ? M.mix(3, 1, M.p(tt, ts, .2, 'slam')) * M.mix(1, .55, sh) : 1, r: rot,
        x: M.mix(0, 120, sh), y: M.mix(0, -800, sh),
        f: on2 && ds < .14 ? 'drop-shadow(8px 0 0 rgba(255,0,60,.6)) drop-shadow(-8px 0 0 rgba(0,220,255,.6))' : null });
      if (on2 && ds < 2 / 30) S.flash = Math.max(S.flash, .7);
      var cx = 620 + 160, cy = 1080 + 160;
      for (var o = 0; o < 3; o++) {
        var od = ds - o * .12, po = M.clamp(od / .7, 0, 1);
        var ok = (F.verdict === 'SWISH' || F.verdict === 'REBOND') && on2 && od > 0 && po < 1;
        var sc = F.verdict === 'SWISH' ? M.mix(.6, 2.6, M.E.expoOut(po)) : (1.05 + o * .22) * (1 + .05 * Math.sin(od * 2 * Math.PI * 12) * (1 - po));
        M.pose('onde' + o, { x: cx, y: cy, s: sc, o: ok ? (1 - po) * .8 : 0 });
      }
    }
    for (var e2 = 0; e2 < ECLATS; e2++) {
      var de = salve ? tt - salve.t : -1, vis = salve && de >= 0 && de < 1.1;
      var ang = (M.bruit(e2, 21) * 1.6 - 1.3) * Math.PI, vit2 = (900 + M.bruit(e2, 23) * 1300) * (salve ? salve.v : 1);
      M.pose('eclat' + e2, vis ? { x: salve.x + Math.cos(ang) * vit2 * de, y: salve.y + Math.sin(ang) * vit2 * de + 2600 * de * de, r: de * (M.bruit(e2, 25) * 1400 - 700), o: 1 - de / 1.1 } : { o: 0 });
    }
    // carte de fin, mot par mot
    FIN.forEach(function (w, n) {
      var a = finT[n], on = S.fin && tt >= a - 1e-6;
      M.pose('fin' + n, { o: on ? 1 : 0, s: on ? M.mix(.5, 1, M.p(tt, a, .22, 'back')) : 1, y: on ? M.mix(-40, 0, M.p(tt, a, .2, 'expoOut')) : 0 });
    });
    M.pose('compte', { o: S.fin ? M.p(tt, (finT[FIN.length - 1] || 0) + .2, .2) : 0 });
    M.pose('fin', { o: S.fin ? 1 : 0 });
    M.pose('logo', { o: S.logo });
    // grain animé et flash
    var gr = document.getElementById('grain2'), fi = Math.floor(t * 30);
    gr.style.backgroundPosition = Math.floor(M.bruit(fi, 31) * 300) + 'px ' + Math.floor(M.bruit(fi, 37) * 300) + 'px';
    M.pose('flash', { o: S.flash });
    return true;
  };

  // ---------- contrôles : rectangles des textes visibles ----------
  window.controles = function () {
    var post = document.querySelector('.lb-post').getBoundingClientRect(), res = [];
    function opacite(e) { var op = 1; while (e && e !== document.body) { op *= parseFloat(getComputedStyle(e).opacity); e = e.parentElement; } return op; }
    var w = document.createTreeWalker(document.querySelector('.lb-post'), NodeFilter.SHOW_TEXT);
    while (w.nextNode()) {
      var n = w.currentNode; if (!n.textContent.trim()) continue;
      var el = n.parentElement;
      if (opacite(el) < 0.5 || el.closest('[aria-hidden="true"]') || el.closest('svg')) continue;
      var rg = document.createRange(); rg.selectNodeContents(n);
      var r = rg.getBoundingClientRect();
      res.push({ texte: n.textContent.trim().slice(0, 30), taille: parseFloat(getComputedStyle(el).fontSize) * (el.closest('#monde') ? 1 : 1),
        heros: !!el.closest('.heros'), fin: !!el.closest('#fin'), logo: !!el.closest('#logo'),
        x0: r.left - post.left, y0: r.top - post.top, x1: r.right - post.left, y1: r.bottom - post.top });
    }
    var modules = Array.from(document.querySelectorAll('.lb-pastille, .lb-sceau-verdict')).filter(function (m) { return opacite(m) >= .5; })
      .map(function (m) { var r = m.getBoundingClientRect(); return { x0: r.left - post.left, y0: r.top - post.top, x1: r.right - post.left, y1: r.bottom - post.top }; });
    var j = document.getElementById('joueur').getBoundingClientRect();
    return { textes: res, modules: modules, joueur: { x: j.left - post.left, y: j.top - post.top, w: j.width, h: j.height },
      polices: [document.fonts.check('900 100px "Archivo Extra Condensed"'), document.fonts.check('800 30px Archivo'), document.fonts.check('italic 400 60px "Instrument Serif"')] };
  };
})();
