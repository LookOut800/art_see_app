// The shop's script: the bag, which pieces are held or sold, and the sale countdowns.
// The bag is kept in this browser only (localStorage); nothing is held until checkout starts.
(function () {
  'use strict';
  var root = document.body.getAttribute('data-root') || '';
  var KEY = 'ct-shop-bag';

  function readBag() {
    try { return JSON.parse(localStorage.getItem(KEY)) || []; } catch (err) { return []; }
  }
  function writeBag(skus) {
    try { localStorage.setItem(KEY, JSON.stringify(skus)); } catch (err) { /* private mode: bag lasts this page only */ }
    memo = skus;
    refresh();
  }
  var memo = readBag();
  function bag() { return memo; }

  var stock = {};  // sku -> "held" | "sold"; missing means available

  // ---------- Sale times ----------
  function state(opens, closes) {
    var t = Date.now();
    if (t < Date.parse(opens)) { return 'soon'; }
    if (t >= Date.parse(closes)) { return 'ended'; }
    return 'open';
  }
  function span(ms) {
    var m = Math.max(0, Math.round(ms / 60000));
    var d = Math.floor(m / 1440), h = Math.floor((m % 1440) / 60), min = m % 60;
    if (d) { return d + (d === 1 ? ' day ' : ' days ') + h + (h === 1 ? ' hour' : ' hours'); }
    if (h) { return h + (h === 1 ? ' hour ' : ' hours ') + min + ' min'; }
    return min + ' min';
  }
  function local(iso) {
    try {
      return new Date(iso).toLocaleString(undefined, { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
    } catch (err) { return iso; }
  }
  function saleText(opens, closes) {
    var s = state(opens, closes);
    if (s === 'soon') { return 'Opens ' + local(opens) + ' · in ' + span(Date.parse(opens) - Date.now()); }
    if (s === 'open') { return 'Open now · closes ' + local(closes) + ' (in ' + span(Date.parse(closes) - Date.now()) + ')'; }
    return 'This sale has ended';
  }

  // ---------- Pages ----------
  function refresh() {
    var n = bag().length;
    Array.prototype.forEach.call(document.querySelectorAll('.bag-count'), function (el) {
      el.textContent = n;
      el.parentNode.classList.toggle('has-items', n > 0);
    });
    Array.prototype.forEach.call(document.querySelectorAll('.sale-when'), function (el) {
      var o = el.getAttribute('data-opens'), c = el.getAttribute('data-closes');
      el.querySelector('.sale-state').textContent = saleText(o, c);
      el.setAttribute('data-state', state(o, c));
    });
    Array.prototype.forEach.call(document.querySelectorAll('button.add'), function (b) {
      var sku = b.getAttribute('data-sku');
      var s = state(b.getAttribute('data-opens'), b.getAttribute('data-closes'));
      var inBag = bag().indexOf(sku) !== -1;
      var st = stock[sku];
      var card = b.closest('.card, .item');
      if (card) {
        card.classList.toggle('is-sold', st === 'sold');
        card.classList.toggle('is-held', st === 'held');
        var badge = card.querySelector('.badge');
        if (badge) { badge.textContent = st === 'sold' ? 'Sold' : st === 'held' ? 'In someone’s checkout' : ''; }
      }
      b.classList.remove('in-bag');
      if (st === 'sold') { b.textContent = 'Sold'; b.disabled = true; }
      else if (s === 'soon') { b.textContent = 'Opens soon'; b.disabled = true; }
      else if (s === 'ended') { b.textContent = 'Sale ended'; b.disabled = true; }
      else if (inBag) { b.textContent = 'In your bag ✓'; b.disabled = false; b.classList.add('in-bag'); }
      else if (st === 'held') { b.textContent = 'On hold'; b.disabled = true; }
      else { b.textContent = 'Add to bag'; b.disabled = false; }
    });
    renderBag();
  }

  document.addEventListener('click', function (ev) {
    var b = ev.target.closest('button.add');
    if (b && !b.disabled) {
      var sku = b.getAttribute('data-sku');
      var skus = bag().slice();
      if (skus.indexOf(sku) === -1) { skus.push(sku); writeBag(skus); }
      else { window.location.href = root + 'bag/'; }
      return;
    }
    var r = ev.target.closest('button.remove');
    if (r) { writeBag(bag().filter(function (s) { return s !== r.getAttribute('data-sku'); })); }
    var t = ev.target.closest('.photo-thumbs button');
    if (t) {
      var list = document.getElementById('photo-list').content.querySelectorAll('img');
      var main = document.querySelector('.photo-main img');
      main.replaceWith(list[Number(t.getAttribute('data-i'))].cloneNode(true));
    }
  });

  // ---------- Bag page ----------
  var bagEl = document.getElementById('bag');
  var catalog = {};
  try { catalog = JSON.parse((document.getElementById('catalog') || {}).textContent || '{}'); } catch (err) { catalog = {}; }
  var message = '';

  function money(v) { return '$' + (Number.isInteger(v) ? v.toLocaleString() : v.toFixed(2)); }
  function esc(s) { var d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

  function renderBag() {
    if (!bagEl) { return; }
    var skus = bag().filter(function (s) { return catalog[s]; });
    if (!skus.length) {
      bagEl.innerHTML = (message ? '<p class="note">' + esc(message) + '</p>' : '') +
        '<p class="lede">Your bag is empty.</p><p><a href="' + root + '">See the sales</a></p>';
      return;
    }
    var total = 0, ok = true;
    var rows = skus.map(function (sku) {
      var it = catalog[sku], st = stock[sku], s = state(it.opens, it.closes);
      var problem = st === 'sold' ? 'Sold' : st === 'held' ? 'In someone else’s checkout right now'
        : s === 'soon' ? 'The sale has not opened yet' : s === 'ended' ? 'The sale has ended' : '';
      if (problem) { ok = false; } else { total += it.price; }
      return '<li class="bag-row' + (problem ? ' is-problem' : '') + '">' +
        '<a href="' + root + it.url + '"><img src="' + root + it.image + '" alt=""></a>' +
        '<div><a href="' + root + it.url + '">' + esc(it.title) + '</a><small>' + esc(sku) + '</small>' +
        (problem ? '<em>' + problem + '</em>' : '') + '</div>' +
        '<span class="price">' + money(it.price) + '</span>' +
        '<button type="button" class="remove" data-sku="' + esc(sku) + '" aria-label="Remove ' + esc(it.title) + '">Remove</button></li>';
    });
    bagEl.innerHTML = (message ? '<p class="note">' + esc(message) + '</p>' : '') +
      '<ul class="bag-list">' + rows.join('') + '</ul>' +
      '<div class="bag-total"><span>Subtotal</span><span class="price">' + money(total) + '</span></div>' +
      '<p class="small">Shipping (one insured rate for the whole order) or free local pickup is chosen at checkout. ' +
      'Your pieces are held for you for 30 minutes once you start checking out.</p>' +
      '<button type="button" class="checkout"' + (ok ? '' : ' disabled') + '>' +
      (ok ? 'Check out' : 'Remove the pieces marked above to check out') + '</button>';
    var btn = bagEl.querySelector('.checkout');
    btn.addEventListener('click', function () { checkout(skus, btn); });
  }

  function checkout(skus, btn) {
    btn.disabled = true;
    btn.textContent = 'Holding your pieces…';
    fetch('/api/checkout', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ skus: skus }) })
      .then(function (res) { return res.json().then(function (data) { return { status: res.status, data: data }; }); })
      .then(function (r) {
        if (r.data.url) { window.location.href = r.data.url; return; }
        if (r.status === 409) {
          message = r.data.reason === 'taken'
            ? 'Sorry, someone else got to a piece first. It is marked below; remove it to check out the rest.'
            : 'A piece in your bag is no longer on sale. It is marked below.';
          return loadStock();
        }
        message = r.data.error || 'Checkout is not available right now. Please try again.';
        refresh();
      })
      .catch(function () { message = 'Could not reach the shop. Please check your connection and try again.'; refresh(); });
  }

  // ---------- Coming back from Stripe ----------
  var params = new URLSearchParams(window.location.search);
  if (params.get('released')) {  // backed out of checkout: let the pieces go right away
    fetch('/api/release', { method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ hold: params.get('released') }) }).then(loadStock);
    history.replaceState(null, '', window.location.pathname);
  }
  if (document.body.classList.contains('thanks-page') && params.get('session_id')) { writeBag([]); }

  function loadStock() {
    return fetch('/api/stock', { cache: 'no-store' })
      .then(function (res) { return res.ok ? res.json() : {}; })
      .then(function (data) { stock = data || {}; refresh(); })
      .catch(function () { refresh(); });
  }

  refresh();
  loadStock();
  setInterval(refresh, 30000);  // countdowns, and buttons that open or close on time
  setInterval(loadStock, 60000);
})();
