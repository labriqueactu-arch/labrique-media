/* La Brique · boîte à outils motion, réutilisable par toutes les scènes Reel (window.M).
   Tout est déterministe : une valeur ne dépend que de t (et d'une graine). Aucune animation CSS, aucun hasard. */
(function () {
  var FPS = 30;
  function clamp(x, a, b) { return Math.max(a, Math.min(b, x)); }
  function mix(a, b, p) { return a + (b - a) * p; }
  // courbes : jamais de linéaire hors compteurs
  var E = {
    lin: function (x) { return x; },
    out: function (x) { return 1 - Math.pow(1 - x, 3); },
    in: function (x) { return x * x * x; },
    io: function (x) { return x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; },
    expoOut: function (x) { return x >= 1 ? 1 : 1 - Math.pow(2, -10 * x); },
    expoIn: function (x) { return x <= 0 ? 0 : Math.pow(2, 10 * x - 10); },
    expoIo: function (x) { return x <= 0 ? 0 : x >= 1 ? 1 : x < .5 ? Math.pow(2, 20 * x - 10) / 2 : (2 - Math.pow(2, -20 * x + 10)) / 2; },
    back: function (x) { var c = 2.2; return 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2); },
    elastic: function (x) { return x <= 0 ? 0 : x >= 1 ? 1 : Math.pow(2, -10 * x) * Math.sin((x * 10 - .75) * (2 * Math.PI / 3)) + 1; },
    slam: function (x) { return x < .55 ? Math.pow(x / .55, 3) : 1 + Math.sin((x - .55) / .45 * Math.PI) * .08 * (1 - x); }
  };
  // clés : [[t, valeur, courbe vers la suivante], ...]
  function k(t, cles) {
    if (t <= cles[0][0]) return cles[0][1];
    for (var i = 0; i < cles.length - 1; i++) {
      var a = cles[i], b = cles[i + 1];
      if (t <= b[0]) { var p = (t - a[0]) / Math.max(1e-6, b[0] - a[0]); return a[1] + (b[1] - a[1]) * E[a[2] || 'io'](p); }
    }
    return cles[cles.length - 1][1];
  }
  // progression 0 → 1 entre t0 et t0 + d
  function p(t, t0, d, courbe) { return E[courbe || 'out'](clamp((t - t0) / d, 0, 1)); }
  // impulsion : monte en a secondes, redescend en r secondes (punch in, flash)
  function impulsion(t, t0, a, r) {
    if (t < t0) return 0;
    if (t < t0 + a) return E.out((t - t0) / a);
    return 1 - E.out(clamp((t - t0 - a) / r, 0, 1));
  }
  // bruit déterministe par image
  function bruit(i, graine) { var x = Math.sin((i + 1) * 12.9898 + (graine || 0) * 78.233) * 43758.5453; return x - Math.floor(x); }
  // tremblement court : n images, amplitude décroissante
  function tremble(t, t0, images, amp, graine) {
    var i = Math.floor((t - t0) * FPS + 1e-6);
    if (t < t0 || i >= images) return { x: 0, y: 0, r: 0 };
    var f = amp * (1 - i / images);
    return { x: (bruit(i, graine) * 2 - 1) * f, y: (bruit(i, (graine || 0) + 7) * 2 - 1) * f, r: (bruit(i, (graine || 0) + 13) * 2 - 1) * f * .05 };
  }
  // flash de n images (opacité)
  function flash(t, t0, images, force) {
    var i = Math.floor((t - t0) * FPS + 1e-6);
    return (t >= t0 && i < images) ? (force == null ? 1 : force) * (1 - i / (images + 1)) : 0;
  }
  // compteur qui accélère puis freine
  function compteur(t, t0, d, de, a) { return Math.round(mix(de, a, E.expoIo(clamp((t - t0) / d, 0, 1)))); }

  // flou directionnel horizontal (whip pan) : un filtre SVG par élément
  var defs = null;
  function flouX(id, px) {
    if (!defs) {
      var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svg.setAttribute('width', 0); svg.setAttribute('height', 0); svg.style.position = 'absolute';
      defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs'); svg.appendChild(defs); document.body.appendChild(svg);
    }
    var fid = 'flou-' + id, f = document.getElementById(fid);
    if (!f) {
      f = document.createElementNS('http://www.w3.org/2000/svg', 'filter'); f.id = fid;
      f.setAttribute('x', '-20%'); f.setAttribute('width', '140%');
      var g = document.createElementNS('http://www.w3.org/2000/svg', 'feGaussianBlur'); f.appendChild(g); defs.appendChild(f);
    }
    f.firstChild.setAttribute('stdDeviation', px.toFixed(1) + ' 0');
    return 'url(#' + fid + ')';
  }

  // pose : transform, opacité, flou, masque
  function pose(id, o) {
    var el = typeof id === 'string' ? document.getElementById(id) : id; if (!el) return;
    el.style.transform = 'translate(' + (o.x || 0).toFixed(2) + 'px,' + (o.y || 0).toFixed(2) + 'px) scale(' + (o.s == null ? 1 : o.s).toFixed(4) + ')' + (o.sx != null ? ' scaleX(' + o.sx + ')' : '') + ' rotate(' + (o.r || 0).toFixed(3) + 'deg)';
    el.style.opacity = o.o == null ? 1 : clamp(o.o, 0, 1);
    var f = [];
    if (o.bx > 0.5) f.push(flouX(el.id || 'x', o.bx));
    if (o.b > 0.3) f.push('blur(' + o.b.toFixed(1) + 'px)');
    if (o.f) f.push(o.f);
    el.style.filter = f.length ? f.join(' ') : 'none';
    // masque horizontal : marges négatives en haut et en bas pour ne jamais rogner les accents (Č, É)
    if (o.clip != null) el.style.clipPath = 'inset(-40% ' + (100 - o.clip).toFixed(2) + '% -40% -4%)';
    if (o.clipY != null) el.style.clipPath = 'inset(' + (100 - o.clipY).toFixed(2) + '% 0 0 0)';
  }

  // volet en briques : polygone en escalier, rangées décalées (p de 0 à 1)
  function voletBriques(p, rangees, depuisGauche) {
    var h = 1920 / rangees, pts = [];
    var largeurs = [];
    for (var r = 0; r < rangees; r++) {
      var q = clamp((p - r * 0.06) / (1 - (rangees - 1) * 0.06), 0, 1);
      var w = E.expoOut(q) * 1180 + (r % 2 ? -50 : 0);
      largeurs.push(clamp(w, 0, 1080));
    }
    if (depuisGauche) {
      pts.push('0px 0px');
      for (r = 0; r < rangees; r++) { pts.push(largeurs[r] + 'px ' + (r * h) + 'px'); pts.push(largeurs[r] + 'px ' + ((r + 1) * h) + 'px'); }
      pts.push('0px 1920px');
    } else {
      pts.push('1080px 0px');
      for (r = 0; r < rangees; r++) { pts.push((1080 - largeurs[r]) + 'px ' + (r * h) + 'px'); pts.push((1080 - largeurs[r]) + 'px ' + ((r + 1) * h) + 'px'); }
      pts.push('1080px 1920px');
    }
    return 'polygon(' + pts.join(',') + ')';
  }

  // découpe d'un texte « *mot* clé » en mots, avec l'accent
  function mots(s) {
    var res = [];
    String(s || '').split(/(\*[^*]+\*)/).forEach(function (part) {
      var acc = /^\*.*\*$/.test(part);
      (acc ? part.slice(1, -1) : part).split(/\s+/).forEach(function (w) { if (w) res.push({ m: w, accent: acc }); });
    });
    return res;
  }
  // répartit n mots affichés sur les mots parlés d'une phrase : temps d'apparition de chacun
  function caler(n, parles, d, f) {
    var out = [];
    for (var i = 0; i < n; i++) {
      if (parles && parles.length) {
        var j = Math.min(parles.length - 1, Math.floor(i * parles.length / n));
        out.push(parles[j].d);
      } else out.push(d + (f - d) * i / Math.max(1, n));
    }
    return out;
  }

  window.M = { FPS: FPS, clamp: clamp, mix: mix, E: E, k: k, p: p, impulsion: impulsion, bruit: bruit, tremble: tremble,
    flash: flash, compteur: compteur, flouX: flouX, pose: pose, voletBriques: voletBriques, mots: mots, caler: caler };
})();
