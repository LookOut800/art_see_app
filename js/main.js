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
