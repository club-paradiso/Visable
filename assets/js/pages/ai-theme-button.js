// Moved verbatim from the inline <script> block of ai.html (lines 77-87 before the move; Phase 5 of the frontend rebuild, 2026-11-04).
// Classic script loaded at the same document position, so it still runs synchronously at parse time in the same order.
    (function(){
      var btn = document.getElementById('aiThemeBtn');
      if (!btn) return;
      btn.addEventListener('click', function(){
        var next = document.body.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
        document.body.setAttribute('data-theme', next);
        try { localStorage.setItem('paradiso:brightness', next); } catch (e) {}
      });
    })();
