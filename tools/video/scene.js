/* La Brique · scène Reel « recap » (1080 × 1920), pilotée par window.seek(t).
   Tout est déterministe : chaque image ne dépend que de t. Données : window.FICHE. */
(function () {
  var F = window.FICHE, L = window.LaBrique, h = React.createElement;
  var D = F.duree;

  // ---------- outils d'animation ----------
  function clamp(x, a, b) { return Math.max(a, Math.min(b, x)); }
  var E = {
    lin: function (x) { return x; },
    out: function (x) { return 1 - Math.pow(1 - x, 3); },
    in: function (x) { return x * x * x; },
    io: function (x) { return x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; },
    back: function (x) { var c = 1.9; return 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2); },
    slam: function (x) { return x < .7 ? Math.pow(x / .7, 2) * 1.0 : 1 + Math.sin((x - .7) / .3 * Math.PI) * .06 * (1 - x); }
  };
  // k : liste [t, valeur, easing vers la valeur suivante]
  function k(t, cles) {
    if (t <= cles[0][0]) return cles[0][1];
    for (var i = 0; i < cles.length - 1; i++) {
      var a = cles[i], b = cles[i + 1];
      if (t <= b[0]) { var p = (t - a[0]) / Math.max(1e-6, b[0] - a[0]); return a[1] + (b[1] - a[1]) * (E[a[2] || 'io'])(p); }
    }
    return cles[cles.length - 1][1];
  }
  function pose(id, o) {
    var el = document.getElementById(id); if (!el) return;
    var tr = 'translate(' + (o.x || 0) + 'px,' + (o.y || 0) + 'px) scale(' + (o.s == null ? 1 : o.s) + ') rotate(' + (o.r || 0) + 'deg)';
    el.style.transform = tr;
    el.style.opacity = o.o == null ? 1 : o.o;
    el.style.filter = o.b ? 'blur(' + o.b + 'px)' : 'none';
    if (o.clip != null) el.style.clipPath = 'inset(0 ' + (100 - o.clip) + '% 0 0)';
  }

  // ---------- composition ----------
  var md = function (s) { // *mot* -> accent
    return String(s).split(/(\*[^*]+\*)/).map(function (p, i) {
      return /^\*.*\*$/.test(p) ? h('span', { key: i, className: 'lb-accent' }, p.slice(1, -1)) : p;
    });
  };
  var C = F.cadre;
  var enfants = [
    // fantôme tramé et halo derrière le joueur
    h('div', { id: 'halo', key: 'halo', className: 'lb-abs', style: { left: C.x - 160, top: C.y - 40, width: C.l + 320, height: C.l * 1.6, borderRadius: '50%', background: 'radial-gradient(closest-side, rgba(246,160,77,.85), rgba(246,160,77,0))' } }),
    h('img', { id: 'fantome', key: 'fantome', className: 'lb-abs', src: F.fantome, style: { left: C.x - 70, top: C.y - 30, width: C.l, opacity: .5 } }),
    // le chiffre héros, derrière le joueur
    h('div', { id: 'chiffre', key: 'chiffre', className: 'lb-abs', style: { left: 0, top: 470, width: 1080, height: 900, transformOrigin: '30% 55%' } },
      h(L.MotHeros, { texte: String(F.chiffre), taille: F.tailleChiffre || 860, relief: true, echo: true, position: { left: F.chiffreX == null ? 30 : F.chiffreX, top: 0 } })),
    h('img', { id: 'joueur', key: 'joueur', className: 'lb-abs lb-photo lb-photo-lumiere', src: F.photo, style: { left: C.x, top: C.y, width: C.l, transformOrigin: '50% 30%', WebkitMaskImage: 'linear-gradient(to bottom, #000 62%, transparent 88%)', maskImage: 'linear-gradient(to bottom, #000 62%, transparent 88%)' } }),
    h('div', { id: 'voile', key: 'voile', className: 'lb-abs', style: { left: 0, top: 1000, width: 1080, height: 920, background: 'linear-gradient(rgba(26,13,8,0), rgba(26,13,8,.88) 50%)' } }),
    h('div', { id: 'logo', key: 'logo', className: 'lb-abs', style: { left: 60, top: 262 } }, h(L.Logo, { taille: 64 })),
    h('div', { id: 'surtitre', key: 'surtitre', className: 'lb-abs', style: { left: 60, top: 372, fontSize: 44 } },
      h('div', { className: 'lb-surtitre', style: { fontSize: 44 } }, h('span', { className: 'lb-surtitre-filet' }), h('span', null, md(F.surtitre)))),
    h('div', { id: 'nom', key: 'nom', className: 'lb-abs', style: { left: 90, top: 1130 } }, h(L.NomJoueur, { prenom: F.prenom, nom: F.nom, taille: 118 })),
    h('div', { id: 'stats', key: 'stats', className: 'lb-abs lb-pastilles', style: { left: 60, top: 1290 } },
      F.stats.map(function (s, i) {
        return h('span', { key: i, id: 'stat' + i, className: 'lb-pastille ' + (i ? 'lb-pastille-contour' : 'lb-pastille-pleine'), style: { fontSize: 52, display: 'inline-block' } },
          h('span', { id: 'val' + i }, s.a), s.suffixe || '');
      })),
    h('div', { id: 'punch', key: 'punch', className: 'lb-abs lb-serif', style: { left: 60, top: 1300, width: 900, fontSize: 82, lineHeight: 1.02 } }, F.punchline),
    F.verdict ? h('div', { id: 'sceau', key: 'sceau', className: 'lb-abs', style: { left: 640, top: 1120 } }, h(L.SceauVerdict, { verdict: F.verdict, taille: 300, rotation: -8, libre: true })) : null,
    h('div', { id: 'fin', key: 'fin', className: 'lb-abs', style: { left: 60, top: 1110, width: 860, textAlign: 'center' } },
      h('div', { className: 'lb-cond', style: { fontSize: 136, lineHeight: .9 } }, md(F.fin)),
      h('div', { className: 'lb-serif', style: { fontSize: 56, marginTop: 26 } }, '@labrique.hoops'))
  ].filter(Boolean);

  ReactDOM.createRoot(document.getElementById('root')).render(
    h(L.Post, { theme: F.theme, hauteur: 1920, grain: true, reperes: false, motif: true }, enfants));

  // ---------- timeline ----------
  var T = F.temps; // repères calculés par reel.py
  window.seek = function (t) {
    var fin0 = T.fin, boucle = D - 0.55;
    // le chiffre : déjà là à t = 0, coup de tampon à l'ouverture, revient seul à la fin
    var cs = k(t, [[0, 1.0], [0.18, 1.07, 'out'], [0.42, 1.0, 'io'], [fin0, 1.0], [fin0 + .5, 0.92, 'io'], [boucle, 0.92, 'io'], [D, 1.0]]);
    pose('chiffre', { s: cs, y: k(t, [[fin0, 0], [fin0 + .5, -40, 'io'], [boucle, -40, 'io'], [D, 0]]) });
    // joueur : léger push continu, entrée depuis la droite au début
    var jx = k(t, [[0, 60], [0.9, 0, 'out']]);
    var js = k(t, [[0, 1.05], [0.9, 1.0, 'out'], [fin0, 1.03, 'lin'], [fin0 + .6, 1.08, 'io'], [boucle, 1.08], [D, 1.05, 'io']]);
    pose('joueur', { x: jx, s: js });
    pose('halo', { o: 0.55 + 0.25 * Math.sin(t * 2 * Math.PI / 1.6), s: 1 + 0.04 * Math.sin(t * 2 * Math.PI / 1.6) });
    pose('fantome', { x: k(t, [[0, 120], [1.6, -30, 'out'], [D, -90, 'lin']]), o: .45 });
    pose('voile', { o: k(t, [[0, .6], [T.joueur, 1, 'io']]) });
    pose('logo', { o: k(t, [[fin0, 1], [fin0 + .3, 0], [boucle, 0], [D, 1]]) });
    // surtitre : présent dès la première image, sort quand le nom arrive, revient pour la boucle
    pose('surtitre', { o: k(t, [[T.joueur - .3, 1], [T.joueur, 0], [boucle, 0], [D, 1]]), x: k(t, [[T.joueur - .3, 0], [T.joueur, -40]]) });
    // nom et stats
    var nIn = T.joueur, nOut = T.punch - 0.1;
    pose('nom', { o: k(t, [[nIn, 0], [nIn + .35, 1], [nOut - .25, 1], [nOut, 0]]), x: k(t, [[nIn, -40], [nIn + .45, 0, 'out'], [nOut - .25, 0], [nOut, -30, 'in']]) });
    F.stats.forEach(function (s, i) {
      var t0 = T.stats[i];
      pose('stat' + i, { o: k(t, [[t0, 0], [t0 + .12, 1], [nOut - .25, 1], [nOut, 0]]), s: k(t, [[t0, .6], [t0 + .3, 1, 'back']]) });
      var v = Math.round(k(t, [[t0, s.de || 0], [t0 + .6, s.a, 'out']]));
      var el = document.getElementById('val' + i); if (el) el.textContent = v;
    });
    // punchline : apparaît mot à mot (fondu masqué)
    pose('punch', { o: k(t, [[T.punch, 0], [T.punch + .15, 1], [fin0 - .2, 1], [fin0, 0]]), clip: k(t, [[T.punch, 0], [T.punch + .9, 100, 'out']]), y: k(t, [[T.punch, 24], [T.punch + .5, 0, 'out']]) });
    if (F.verdict) pose('sceau', { o: k(t, [[T.sceau, 0], [T.sceau + .05, 1], [fin0 - .2, 1], [fin0, 0]]), s: k(t, [[T.sceau, 2.4], [T.sceau + .22, 1, 'slam']]), r: k(t, [[T.sceau, -20], [T.sceau + .22, 0, 'out']]) });
    // carte de fin
    pose('fin', { o: k(t, [[fin0, 0], [fin0 + .25, 1], [boucle - .1, 1], [boucle + .2, 0]]), s: k(t, [[fin0, .85], [fin0 + .35, 1, 'back']]) });
    return true;
  };

  // ---------- contrôles : rectangles des textes visibles ----------
  window.controles = function () {
    var post = document.querySelector('.lb-post').getBoundingClientRect(), res = [];
    var w = document.createTreeWalker(document.querySelector('.lb-post'), NodeFilter.SHOW_TEXT);
    while (w.nextNode()) {
      var n = w.currentNode; if (!n.textContent.trim()) continue;
      var el = n.parentElement, op = 1, e = el;
      while (e && e !== document.body) { op *= parseFloat(getComputedStyle(e).opacity); e = e.parentElement; }
      if (op < 0.5 || el.closest('[aria-hidden="true"]') || el.closest('svg')) continue;
      var heros = !!el.closest('#chiffre'), fin = !!el.closest('#fin'), logo = !!el.closest('#logo');
      var rg = document.createRange(); rg.selectNodeContents(n);
      var r = rg.getBoundingClientRect();
      res.push({ texte: n.textContent.trim().slice(0, 30), taille: parseFloat(getComputedStyle(el).fontSize), heros: heros, fin: fin, logo: logo,
        x0: r.left - post.left, y0: r.top - post.top, x1: r.right - post.left, y1: r.bottom - post.top });
    }
    var modules = Array.from(document.querySelectorAll('.lb-pastille, .lb-sceau-verdict')).filter(function (m) {
      var op = 1, e = m; while (e && e !== document.body) { op *= parseFloat(getComputedStyle(e).opacity); e = e.parentElement; } return op >= .5;
    }).map(function (m) { var r = m.getBoundingClientRect(); return { x0: r.left - post.left, y0: r.top - post.top, x1: r.right - post.left, y1: r.bottom - post.top }; });
    var j = document.getElementById('joueur').getBoundingClientRect();
    return { textes: res, modules: modules, joueur: { x: j.left - post.left, y: j.top - post.top, w: j.width, h: j.height },
      polices: [document.fonts.check('900 100px "Archivo Extra Condensed"'), document.fonts.check('800 30px Archivo'), document.fonts.check('italic 400 60px "Instrument Serif"')] };
  };
})();
