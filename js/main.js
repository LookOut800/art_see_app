(function () {
  'use strict';

  // Mobile menu
  var toggle = document.querySelector('.nav-toggle');
  var nav = document.getElementById('site-nav');
  if (toggle && nav) {
    toggle.addEventListener('click', function () {
      var open = nav.classList.toggle('open');
      toggle.setAttribute('aria-expanded', String(open));
    });
  }

  // Piece pages: arrows, counter and previews for the row of photos
  Array.prototype.forEach.call(document.querySelectorAll('.slider'), function (sl) {
    var row = sl.querySelector('.gallery-slider');
    var figs = row.querySelectorAll('figure');
    var count = sl.querySelector('.sl-count');
    var prev = sl.querySelector('.sl-prev');
    var next = sl.querySelector('.sl-next');
    var thumbs = sl.querySelectorAll('.slider-thumbs button');
    function at() { return Math.round(row.scrollLeft / Math.max(1, figs[0].offsetWidth + 16)); }
    function go(i) {
      i = Math.max(0, Math.min(figs.length - 1, i));
      row.scrollTo({ left: figs[i].offsetLeft - row.offsetLeft, behavior: 'smooth' });
    }
    function update() {
      var i = at();
      count.textContent = (i + 1) + ' / ' + figs.length;
      prev.disabled = i === 0;
      next.disabled = i === figs.length - 1;
      Array.prototype.forEach.call(thumbs, function (t, k) { t.setAttribute('aria-current', String(k === i)); });
    }
    prev.addEventListener('click', function () { go(at() - 1); });
    next.addEventListener('click', function () { go(at() + 1); });
    Array.prototype.forEach.call(thumbs, function (t) {
      t.addEventListener('click', function () { go(Number(t.getAttribute('data-i'))); });
    });
    row.addEventListener('keydown', function (ev) {
      if (ev.key === 'ArrowLeft') { ev.preventDefault(); go(at() - 1); }
      else if (ev.key === 'ArrowRight') { ev.preventDefault(); go(at() + 1); }
    });
    row.addEventListener('scroll', function () { window.requestAnimationFrame(update); }, { passive: true });
    update();
  });

  // Lightbox for project galleries
  var links = Array.prototype.slice.call(document.querySelectorAll('.gallery .zoom'));
  if (!links.length) { return; }

  var box = document.createElement('div');
  box.className = 'lightbox';
  box.setAttribute('role', 'dialog');
  box.setAttribute('aria-modal', 'true');
  box.setAttribute('aria-label', 'Image viewer');
  box.innerHTML =
    '<button class="lb-close" aria-label="Close">×</button>' +
    '<button class="lb-prev" aria-label="Previous image">‹</button>' +
    '<img alt="">' +
    '<button class="lb-next" aria-label="Next image">›</button>';
  document.body.appendChild(box);

  var img = box.querySelector('img');
  var current = 0;
  var opener = null;

  function show(i) {
    current = (i + links.length) % links.length;
    var src = links[current].querySelector('img');
    img.src = links[current].getAttribute('href');
    img.alt = src ? src.alt : '';
  }
  function open(i) {
    opener = document.activeElement;
    show(i);
    box.classList.add('open');
    document.body.classList.add('lb-open');
    box.querySelector('.lb-close').focus();
  }
  function close() {
    box.classList.remove('open');
    document.body.classList.remove('lb-open');
    if (opener) { opener.focus(); }
  }

  links.forEach(function (a, i) {
    a.addEventListener('click', function (ev) { ev.preventDefault(); open(i); });
  });
  box.querySelector('.lb-close').addEventListener('click', close);
  box.querySelector('.lb-prev').addEventListener('click', function () { show(current - 1); });
  box.querySelector('.lb-next').addEventListener('click', function () { show(current + 1); });
  box.addEventListener('click', function (ev) { if (ev.target === box) { close(); } });
  document.addEventListener('keydown', function (ev) {
    if (!box.classList.contains('open')) { return; }
    if (ev.key === 'Escape') { close(); }
    else if (ev.key === 'ArrowLeft') { show(current - 1); }
    else if (ev.key === 'ArrowRight') { show(current + 1); }
  });
})();
