// Linien "stechen", sobald sie ins Bild scrollen.
(function () {
  // pathLength=1 normiert jede Linie, damit dasharray 1 für alle Formen passt.
  document.querySelectorAll('.ink path, .ink circle, .ink line, .ink polyline, .ink rect, .ink ellipse')
    .forEach(function (el) { el.setAttribute('pathLength', '1'); });

  var targets = document.querySelectorAll('.ink, .fade');
  if (!('IntersectionObserver' in window)) {
    targets.forEach(function (t) { t.classList.add('drawn'); });
    return;
  }
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) { e.target.classList.add('drawn'); io.unobserve(e.target); }
    });
  }, { threshold: 0.25 });
  targets.forEach(function (t) { io.observe(t); });
})();

// Sternenhimmel: wenige, langsam atmende Punkte. Bei reduzierter Bewegung statisch.
(function () {
  var canvas = document.getElementById('sky');
  var ctx = canvas.getContext('2d');
  var still = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var stars = [];
  var dpr = Math.min(window.devicePixelRatio || 1, 2);
  var color = '';

  function readColor() {
    color = getComputedStyle(document.documentElement).getPropertyValue('--star').trim();
  }

  function resize() {
    canvas.width = innerWidth * dpr;
    canvas.height = innerHeight * dpr;
    var count = Math.round((innerWidth * innerHeight) / 9000);
    stars = [];
    for (var i = 0; i < count; i++) {
      stars.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        r: (Math.random() * 0.9 + 0.3) * dpr,
        p: Math.random() * Math.PI * 2,
        s: 0.0004 + Math.random() * 0.0008
      });
    }
  }

  function draw(t) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = color;
    for (var i = 0; i < stars.length; i++) {
      var s = stars[i];
      ctx.globalAlpha = still ? 0.6 : 0.25 + 0.75 * (0.5 + 0.5 * Math.sin(s.p + t * s.s));
      ctx.beginPath();
      ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
      ctx.fill();
    }
    if (!still) requestAnimationFrame(draw);
  }

  readColor();
  resize();
  addEventListener('resize', function () { resize(); if (still) draw(0); });
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', readColor);
  requestAnimationFrame(draw);
})();

// Bilder-Lanes: liest media/media.json (erzeugt die GitHub Action aus dem Ordner media/)
// und hängt die Bilder jeder App direkt unter ihre Beschreibung.
// Alles wird als Text bzw. per Attribut gesetzt, nie als HTML.
(function () {
  var APPS = {
    'mood-checker': 'Mood Checker',
    'juntos': 'JuntOS',
    'waldlaeufer': 'Waldläufer',
    'farbdorf': 'Farbdorf',
    'lesespiel': 'Lesespiel',
    'aemtli': 'Ämtli',
    'allgemein': 'Allgemein'
  };
  var box = document.getElementById('lightbox');
  var inner = document.getElementById('lightboxInner');

  function el(tag, attrs, text) {
    var e = document.createElement(tag);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    if (text) e.textContent = text;
    return e;
  }

  // Nur einfache Dateinamen direkt in media/ erlauben, keine fremden Pfade oder URLs.
  function safeSrc(name) {
    return /^[a-z0-9][a-z0-9._-]*\.(jpe?g|png|webp|gif|mp4|webm)$/i.test(name) ? 'media/' + name : null;
  }

  function media(item, big) {
    var src = safeSrc(item.file);
    if (!src) return null;
    if (item.type === 'video') {
      var v = el('video', { src: src, muted: '', playsinline: '', loop: '', preload: big ? 'auto' : 'metadata' });
      v.muted = true;
      if (big) { v.controls = true; v.autoplay = true; }
      var poster = item.poster && safeSrc(item.poster);
      if (poster) v.setAttribute('poster', poster);
      return v;
    }
    return el('img', { src: src, alt: item.caption || APPS[item.app] || '', loading: big ? 'eager' : 'lazy', decoding: 'async' });
  }

  function open(item) {
    inner.textContent = '';
    var m = media(item, true);
    if (!m) return;
    inner.appendChild(m);
    var cap = el('p', {});
    cap.appendChild(el('span', { class: 'mono' }, APPS[item.app] || ''));
    if (item.caption) { cap.appendChild(document.createElement('br')); cap.appendChild(el('em', {}, item.caption)); }
    cap.style.textAlign = 'center';
    inner.appendChild(cap);
    if (box.showModal) box.showModal(); else box.setAttribute('open', '');
  }

  function close() {
    inner.querySelectorAll('video').forEach(function (v) { v.pause(); });
    inner.textContent = '';
    if (box.close) box.close(); else box.removeAttribute('open');
  }

  // Rand nur dort ausblenden, wo es tatsächlich weitergeht.
  function edges(lane) {
    var max = lane.scrollWidth - lane.clientWidth;
    lane.classList.toggle('more-l', lane.scrollLeft > 2);
    lane.classList.toggle('more-r', max - lane.scrollLeft > 2);
  }

  // Videos nur abspielen, solange sie sichtbar sind (spart Akku).
  var videoIo = 'IntersectionObserver' in window ? new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) { var p = e.target.play(); if (p && p.catch) p.catch(function () {}); }
      else e.target.pause();
    });
  }, { threshold: 0.6 }) : null;

  function fill(lane, list) {
    list.forEach(function (it) {
      var m = media(it, false);
      if (!m) return;
      var btn = el('button', { type: 'button', class: 'shot', 'aria-label': 'Gross ansehen: ' + (it.caption || APPS[it.app] || 'Bild') });
      if (it.caption) btn.title = it.caption;
      btn.appendChild(m);
      btn.addEventListener('click', function () { open(it); });
      lane.appendChild(btn);
      if (videoIo && m.tagName === 'VIDEO') videoIo.observe(m);
    });
    if (!lane.children.length) return;
    lane.hidden = false;
    lane.addEventListener('scroll', function () { edges(lane); }, { passive: true });
    edges(lane);
  }

  document.getElementById('lightboxClose').addEventListener('click', close);
  box.addEventListener('click', function (e) { if (e.target === box || e.target === inner) close(); });
  box.addEventListener('cancel', function (e) { e.preventDefault(); close(); });

  fetch('media/media.json', { cache: 'no-cache' })
    .then(function (r) { return r.ok ? r.json() : []; })
    .catch(function () { return []; })
    .then(function (data) {
      var items = Array.isArray(data) ? data.filter(function (it) { return it && typeof it.file === 'string'; }) : [];
      var lanes = document.querySelectorAll('.app[data-app] .lane');
      lanes.forEach(function (lane) {
        var app = lane.parentNode.getAttribute('data-app');
        fill(lane, items.filter(function (it) { return it.app === app; }));
      });
      addEventListener('resize', function () { lanes.forEach(edges); });
    });
})();
