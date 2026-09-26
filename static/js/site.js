// seanredenbaugh.com — small progressive enhancements. Everything works without JS except the lightbox and video loading.
(function () {
  // mobile menu
  var toggle = document.querySelector('.nav-toggle');
  var nav = document.getElementById('site-nav');
  if (toggle && nav) {
    toggle.addEventListener('click', function () {
      var open = nav.classList.toggle('open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      document.body.classList.toggle('nav-open', open);
    });
  }

  // YouTube: show a thumbnail, load the player only when clicked
  document.querySelectorAll('.yt[data-id]').forEach(function (el) {
    var id = el.getAttribute('data-id');
    el.style.backgroundImage = 'url(https://i.ytimg.com/vi/' + id + '/hqdefault.jpg)';
    var b = document.createElement('button');
    b.type = 'button';
    b.setAttribute('aria-label', 'Play video');
    b.addEventListener('click', function () {
      var f = document.createElement('iframe');
      f.src = 'https://www.youtube-nocookie.com/embed/' + id + '?autoplay=1&rel=0';
      f.allow = 'autoplay; encrypted-media; picture-in-picture; fullscreen';
      f.allowFullscreen = true;
      f.title = 'YouTube video';
      el.innerHTML = '';
      el.appendChild(f);
    });
    el.appendChild(b);
  });

  // home page: poem carousel with arrows, keyboard and swipe
  var rot = document.querySelector('.poem-rotator');
  var pnav = document.querySelector('.poem-nav');
  if (rot && pnav) {
    var cards = rot.querySelectorAll('.poem-card');
    var countEl = pnav.querySelector('.poem-count');
    var cur = Math.floor(Math.random() * cards.length);
    var show = function (i, focus) {
      cur = (i + cards.length) % cards.length;
      cards.forEach(function (c, j) { c.hidden = j !== cur; });
      countEl.textContent = (cur + 1) + ' of ' + cards.length;
      if (focus) {
        var top = rot.getBoundingClientRect().top;
        if (top < 70) window.scrollBy({ top: top - 90, behavior: 'smooth' });
      }
    };
    pnav.hidden = false;
    show(cur);
    pnav.querySelector('[data-poem-prev]').addEventListener('click', function () { show(cur - 1, true); });
    pnav.querySelector('[data-poem-next]').addEventListener('click', function () { show(cur + 1, true); });
    rot.tabIndex = 0;
    rot.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowLeft') { show(cur - 1); e.preventDefault(); }
      if (e.key === 'ArrowRight') { show(cur + 1); e.preventDefault(); }
    });
    var sx = null, sy = null;
    rot.addEventListener('touchstart', function (e) { sx = e.touches[0].clientX; sy = e.touches[0].clientY; }, { passive: true });
    rot.addEventListener('touchend', function (e) {
      if (sx === null) return;
      var dx = e.changedTouches[0].clientX - sx, dy = e.changedTouches[0].clientY - sy;
      if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.5) show(cur + (dx < 0 ? 1 : -1), true);
      sx = null;
    });
  }

  // lightbox for galleries
  var links = Array.prototype.slice.call(document.querySelectorAll('a[data-lightbox]'));
  var box = document.querySelector('.lightbox');
  if (links.length && box && box.showModal) {
    var img = box.querySelector('img'), cap = box.querySelector('figcaption'), idx = 0;
    var open = function (i) {
      idx = (i + links.length) % links.length;
      var a = links[idx];
      img.src = a.href;
      img.alt = (a.querySelector('img') || {}).alt || '';
      cap.textContent = a.getAttribute('data-caption') || '';
      if (!box.open) box.showModal();
    };
    links.forEach(function (a, i) { a.addEventListener('click', function (e) { e.preventDefault(); open(i); }); });
    box.querySelector('.lb-prev').addEventListener('click', function () { open(idx - 1); });
    box.querySelector('.lb-next').addEventListener('click', function () { open(idx + 1); });
    box.querySelector('.lb-close').addEventListener('click', function () { box.close(); });
    box.addEventListener('click', function (e) { if (e.target === box) box.close(); });
    document.addEventListener('keydown', function (e) {
      if (!box.open) return;
      if (e.key === 'ArrowLeft') open(idx - 1);
      if (e.key === 'ArrowRight') open(idx + 1);
    });
    box.addEventListener('close', function () { img.removeAttribute('src'); });
  }

  // contact form: prefill subject, show result, anti-spam timer
  var form = document.querySelector('.contact-form');
  if (form) {
    var params = new URLSearchParams(location.search);
    var status = form.querySelector('.form-status');
    if (params.get('subject')) form.subject.value = params.get('subject');
    form.t.value = String(Date.now());
    var sent = params.get('sent');
    if (sent) {
      status.hidden = false;
      if (sent === '1') { status.textContent = 'Thanks — your message was sent. I’ll get back to you soon.'; status.classList.add('ok'); }
      else { status.textContent = 'Your message couldn’t be sent. Please check the form and try again, or email seanredenbaugh@yahoo.com directly.'; }
    }
  }
})();
