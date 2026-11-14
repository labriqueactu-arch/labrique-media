/* La Brique · posts version 2 (DA « brute », alignée sur les Reels dynamiques). 1080 × 1350, rendu × 2.
   Données : window.P (fiche + photos mesurées par render_ds.py). Système :
   logo en haut à gauche, tampon du verdict en haut à droite, mot géant devant le corps sous le visage,
   bandeau noir qui porte la phrase, bandeau télé en bas. Trois niveaux de texte, deux signes forts. */
(function () {
  var P = window.P;
  var FOND = { os: '#f2ede4', parquet: '#e04e22', encre: '#121110' };
  var TEXTE = { os: '#121110', parquet: '#f2ede4', encre: '#f2ede4' };
  var ACCENT = { os: '#e04e22', parquet: '#121110', encre: '#f6a04d' };
  var W = 1080, H = 1350, M = 64, BANDEAU = 64;
  var th = P.theme, fond = FOND[th], texte = TEXTE[th], accent = ACCENT[th];
  var root = document.getElementById('root');
  root.className = 'lb-post';
  root.style.cssText = 'position:relative;width:1080px;height:1350px;overflow:hidden;background:' + fond;
  function el(tag, css, html, cls) { var e = document.createElement(tag); e.style.cssText = 'position:absolute;' + (css || ''); if (html != null) e.innerHTML = html; if (cls) e.className = cls; root.appendChild(e); return e; }
  function cond(px) { return "font-family:'Archivo Extra Condensed';font-weight:900;text-transform:uppercase;font-size:" + px + 'px;line-height:.86;letter-spacing:-.01em;'; }
  var sans = "font-family:Archivo;font-weight:800;text-transform:uppercase;letter-spacing:.06em;";
  var serif = "font-family:'Instrument Serif';font-style:italic;font-weight:400;text-transform:none;letter-spacing:0;";
  function md(s) { return String(s || '').replace(/\*([^*]+)\*/g, '<span style="' + serif + 'font-size:1.08em">$1</span>'); }
  function ajuste(e, max, min, largeur, lignes) {
    var fs = max; e.style.fontSize = fs + 'px';
    while (fs > min && (e.scrollWidth > largeur + 1 || e.offsetHeight > fs * .95 * lignes + 4)) { fs -= 2; e.style.fontSize = fs + 'px'; }
    return fs;
  }

  // ---------- joueur : cadrage par le visage, étalonnage, lumière de contour, ombre ----------
  function joueur(ph, o) {
    var v = ph.v.reduce(function (a, b) { return (b[3] - b[1]) > (a[3] - a[1]) ? b : a; });
    var k = o.visage / ((v[3] - v[1]) * ph.h);
    if (ph.h * k * (1 - v[1]) < o.bas - o.top) k = (o.bas - o.top) / ((1 - v[1]) * ph.h);
    var w = ph.w * k, h = ph.h * k, x = o.cx - ((v[0] + v[2]) / 2) * w, y = o.top - v[1] * h;
    // le visage ne sort jamais du cadre
    var fx0 = x + v[0] * w, fx1 = x + v[2] * w;
    if (fx0 < 16) x += 16 - fx0; if (fx1 > W - 16) x -= fx1 - (W - 16);
    var i = document.createElement('img'); i.src = ph.p; i.className = 'lb-photo';
    i.style.cssText = 'position:absolute;left:' + x + 'px;top:' + y + 'px;width:' + w + 'px;height:' + h + 'px;z-index:5;' +
      'filter:contrast(1.14) saturate(1.1) brightness(1.02) drop-shadow(0 0 1.5px rgba(255,248,236,.9)) drop-shadow(' + (o.ombre || '22px 28px 34px') + ' rgba(18,17,16,.38));';
    (o.parent || root).appendChild(i);
    return { x: x, y: y, w: w, h: h, faceBas: y + v[3] * h };
  }

  // ---------- habillage constant ----------
  function logo(c) { el('div', 'left:' + M + 'px;top:48px;z-index:20;color:' + (c || texte), '<span style="' + serif + 'font-size:46px">la</span><span style="' + cond(54) + 'line-height:1"> BRIQUE</span>', 'marque logo'); }
  function tampon() {
    if (!P.verdict) return;
    var c = { SWISH: ['#f2ede4', '#121110'], REBOND: ['#ffd08a', '#121110'], BRIQUE: ['#e04e22', '#f2ede4'] }[P.verdict];
    el('div', 'right:' + M + 'px;top:40px;width:176px;height:176px;border-radius:50%;z-index:20;transform:rotate(-8deg);display:flex;align-items:center;justify-content:center;' +
      'background:' + c[0] + ';box-shadow:0 0 0 5px ' + c[1] + ' inset, 0 0 0 11px ' + c[0] + ' inset, 0 0 0 14px ' + c[1] + ' inset, 6px 8px 0 rgba(18,17,16,.35);color:' + c[1],
      '<svg width="0" height="0"></svg><div style="text-align:center" aria-hidden="true"><div style="' + sans + 'font-size:15px;letter-spacing:.2em">LE VERDICT</div><div style="' + cond(64) + 'line-height:.95">' + P.verdict + '</div><div style="' + sans + 'font-size:13px;letter-spacing:.2em">LA BRIQUE</div></div>',
      'lb-sceau-verdict signe marque');
  }
  function bandeau() {
    var b = el('div', 'left:0;bottom:0;width:1080px;height:' + BANDEAU + 'px;z-index:30;display:flex;align-items:center;background:#121110;color:#f2ede4;' + sans + 'font-size:28px;letter-spacing:.06em', null, 'bandeau');
    b.innerHTML = '<div style="height:100%;display:flex;align-items:center;padding:0 22px 0 ' + M + 'px;background:#e04e22;color:#121110;white-space:nowrap;flex:none">' + P.format + '</div>' +
      '<div class="defile" style="padding-left:22px;white-space:nowrap;overflow:hidden;text-overflow:clip;flex:1;padding-right:' + M + 'px">' + (P.bandeau || '') + '</div>';
  }

  // ---------- formats ----------
  function rectTexte(e) { var rg = document.createRange(); rg.selectNodeContents(e); return rg.getBoundingClientRect(); }
  function standard() {
    var mot = P.composant === 'PostChiffre' ? String(P.chiffre) : P.composant === 'PostAffiche' ? P.mot : P.verdict;
    var C = P.cadre || {}, visage = C.visage || 380, top = C.top || 150, cmax = 70, essais = 0, LARGE = W - 40;
    for (;;) {
      root.innerHTML = '';
      var post = root.getBoundingClientRect();
      var cap = el('div', 'left:0;bottom:' + BANDEAU + 'px;width:1080px;z-index:9;background:' + (th === 'encre' ? '#f2ede4' : '#121110') + ';padding:24px ' + M + 'px 28px;box-sizing:border-box;color:' + (th === 'encre' ? '#121110' : '#f2ede4'), null, 'legende');
      var ct = document.createElement('div'); ct.style.cssText = cond(cmax) + 'line-height:.92'; ct.innerHTML = md(P.titre); cap.appendChild(ct);
      var cfs = ajuste(ct, cmax, 40, W - 2 * M, 2);
      var bandTop = H - BANDEAU - cap.offsetHeight;
      // le bas du joueur se cache derrière le bandeau noir : il peut rapetisser sans flotter
      var pj = joueur(P.photo, { visage: visage, cx: C.cx || 560, top: top, bas: bandTop + 12 });
      var lignes = P.composant === 'PostAffiche' && String(mot).indexOf(' ') > 0 ? 2 : 1;
      var m = el('div', cond(520) + 'left:0;z-index:7;white-space:' + (lignes > 1 ? 'normal' : 'nowrap') + ';text-align:center;display:inline-block;max-width:' + LARGE + 'px;color:' + (P.composant === 'PostVerdict' ? accent : texte) + ';line-height:.8;' +
        'text-shadow:10px 12px 0 rgba(18,17,16,.28);-webkit-text-stroke:' + Math.round(8) + 'px ' + fond + ';paint-order:stroke fill', mot, 'mot-geant signe');
      var fs = ajuste(m, P.composant === 'PostChiffre' ? 760 : 600, 160, LARGE, lignes);
      var large = fs;
      // pied des lettres sur le bandeau noir ; le haut des glyphes reste sous le visage
      var place = function () { m.style.top = (bandTop + fs * .06 - m.offsetHeight) + 'px'; m.style.left = ((W - m.offsetWidth) / 2) + 'px'; return rectTexte(m).top - post.top; };
      var haut = place();
      while (fs > 160 && haut < pj.faceBas + 14) { fs -= 4; m.style.fontSize = fs + 'px'; haut = place(); }
      // le mot reste au moins 5 fois plus grand que la phrase (serif compris) :
      // la phrase s'adapte au mot ; si c'est le visage qui bride le mot, le joueur remonte et rapetisse
      var phrase = cfs * (String(P.titre).indexOf('*') >= 0 ? 1.08 : 1);
      if (fs >= 5.2 * phrase || essais++ > 10) break;
      if (cfs > 40 && large <= fs + 4) { cmax = Math.max(40, Math.floor(fs / 5.3 / (phrase / cfs))); continue; }
      visage *= .9; top = Math.max(110, top - 12);
    }
    logo(); tampon(); bandeau();
  }
  function face() {
    var hh = (H - BANDEAU) / 2, LARGE = W - 40;
    var mesure = document.createElement('div'); mesure.style.cssText = 'position:absolute;visibility:hidden;white-space:nowrap;display:inline-block;line-height:.8;' + cond(220); root.appendChild(mesure);
    var fsNom = Math.min.apply(null, [P.haut, P.bas].map(function (q) { mesure.textContent = q.nom; return ajuste(mesure, 220, 140, LARGE, 1); }));
    mesure.remove();
    [[P.haut, 0, '#e04e22', '#121110'], [P.bas, hh, '#121110', '#f2ede4']].forEach(function (q) {
      var C = q[0].cadre || {}, visage = C.visage || 300, essais = 0;
      for (;;) {
        var zone = el('div', 'left:0;top:' + q[1] + 'px;width:1080px;height:' + hh + 'px;overflow:hidden;background:' + q[2] + ';z-index:2');
        var pj = joueur(q[0].photo, { visage: visage, cx: C.cx || 640, top: C.top || 90, bas: hh + 40, parent: zone, ombre: '0 0 0' });
        var nom = document.createElement('div'); nom.className = 'mot-geant'; nom.style.cssText = 'position:absolute;' + cond(fsNom) + 'z-index:8;color:' + q[3] + ';line-height:.8;white-space:nowrap;display:inline-block;text-shadow:8px 10px 0 rgba(18,17,16,.25);-webkit-text-stroke:8px ' + q[2] + ';paint-order:stroke fill'; nom.textContent = q[0].nom; zone.appendChild(nom);
        nom.style.top = (hh - 18 - nom.offsetHeight) + 'px'; nom.style.left = ((W - nom.offsetWidth) / 2) + 'px';
        var st = document.createElement('div'); st.className = 'info'; st.style.cssText = 'position:absolute;' + sans + 'left:' + M + 'px;top:' + (hh - 18 - nom.offsetHeight - 46) + 'px;z-index:8;font-size:28px;padding:6px 12px;background:' + q[2] + ';color:' + q[3]; st.textContent = q[0].stat; zone.appendChild(st);
        var hautNom = rectTexte(nom).top - zone.getBoundingClientRect().top;
        if (pj.faceBas - q[1] + 14 <= Math.min(hautNom, parseFloat(st.style.top)) || essais++ > 8) break;
        zone.remove(); visage *= .9;
      }
    });
    el('div', 'right:' + M + 'px;top:' + (hh - 55) + 'px;z-index:9;width:110px;height:110px;border-radius:50%;background:#f2ede4;color:#121110;display:flex;align-items:center;justify-content:center;' + cond(64) + 'box-shadow:0 0 0 6px #121110', '<span aria-hidden="true">OU</span>', 'signe');
    logo('#121110'); bandeau();
  }

  (P.composant === 'PostFaceAFace' ? face : standard)();
  window.pret = true;
})();
