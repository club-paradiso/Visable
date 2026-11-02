/* The saved reminder form lives once, in a native dialog outside the home renderer. */
(function () {
  'use strict';
  var dialog = document.getElementById('reminderDialog');
  if (!dialog) return;
  var state = null;
  var restoreFrame = 0, pendingRestore = null;
  function finish() {
    if (!state) return;
    var previous = state;
    state = null;
    // Native dialog closing restores focus itself. Finish after that browser
    // step, before the next paint, so it cannot scroll the underlying page.
    pendingRestore = function () {
      restoreFrame = 0;
      pendingRestore = null;
      if (!previous.locked) document.documentElement.classList.remove('vs-reminder-open');
      var opener = previous.opener && previous.opener.isConnected ? previous.opener : document.querySelector('.cs-tools-core [data-cs-tool="reminders"]');
      if (opener) {
        opener.setAttribute('aria-expanded', 'false');
        opener.focus({ preventScroll: true });
      }
      window.scrollTo({ left: previous.x, top: previous.y, behavior: 'instant' });
      document.documentElement.style.scrollBehavior = previous.scrollBehavior;
    };
    restoreFrame = requestAnimationFrame(pendingRestore);
  }
  function open(trigger) {
    if (dialog.open) return;
    if (pendingRestore) { cancelAnimationFrame(restoreFrame); pendingRestore(); }
    state = {
      opener: trigger || document.activeElement,
      x: window.scrollX, y: window.scrollY,
      locked: document.documentElement.classList.contains('vs-reminder-open'),
      scrollBehavior: document.documentElement.style.scrollBehavior
    };
    document.documentElement.style.scrollBehavior = 'auto';
    window.scrollTo({ left: state.x, top: state.y, behavior: 'instant' });
    document.documentElement.classList.add('vs-reminder-open');
    dialog.showModal();
    if (state.opener && state.opener.setAttribute) state.opener.setAttribute('aria-expanded', 'true');
    dialog.querySelector('[data-vs-reminder-close]').focus({ preventScroll: true });
    if (dialog.querySelector('.vs-reminder-content')) dialog.querySelector('.vs-reminder-content').scrollTop = 0;
  }
  function close() {
    if (dialog.open) dialog.close();
    finish();
  }
  dialog.querySelector('[data-vs-reminder-close]').addEventListener('click', close);
  document.addEventListener('click', function (event) {
    var trigger = event.target.closest && event.target.closest('[data-action="reveal-home-section"][data-target="reminderSection"]');
    if (!trigger) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    open(trigger);
  }, true);
  dialog.addEventListener('cancel', function (event) { event.preventDefault(); close(); });
  dialog.addEventListener('close', function () { if (!dialog.open) finish(); });
  dialog.addEventListener('click', function (event) {
    if (event.target !== dialog) return;
    var rect = dialog.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) close();
  });
  document.addEventListener('keydown', function (event) {
    if (dialog.open && event.key === 'Tab') {
      var controls = Array.from(dialog.querySelectorAll('a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])'))
        .filter(function (el) { return !el.hidden && el.getClientRects().length > 0; });
      var first = controls[0], last = controls[controls.length - 1];
      if (first && (!dialog.contains(document.activeElement) || (event.shiftKey && document.activeElement === first) || (!event.shiftKey && document.activeElement === last))) {
        event.preventDefault();
        (event.shiftKey ? last : first).focus({ preventScroll: true });
      }
    }
    if (dialog.open && event.key === 'Escape') {
      event.preventDefault(); event.stopPropagation(); close();
    }
  }, true);
  window.addEventListener('pagehide', function () {
    close();
    if (pendingRestore) { cancelAnimationFrame(restoreFrame); pendingRestore(); }
  });
  function openHash() { if (location.hash === '#reminderSection') open(); }
  window.addEventListener('hashchange', openHash);
  openHash();
  window.VisableReminderDialog = { open: open, close: close };
})();
