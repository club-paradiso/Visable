// @ts-nocheck
/**
 * Landing animations (Phase 3, moved verbatim from index.html lines 25169-25190 and 25193-25295):
 * the scroll-reveal IntersectionObserver IIFE and the legacy-hero anagram builder. They used to run
 * at parse time; as a module they run after parsing, before `load` (the anagram waits for `load`
 * anyway). The legacy hero is hidden behind the civic shell on the current landing.
 */

(function() {
    const revealElements = document.querySelectorAll('[data-reveal]');
    const staggerParents = document.querySelectorAll('[data-stagger]');
    if (!revealElements.length && !staggerParents.length) return;
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('revealed');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });
    revealElements.forEach(el => observer.observe(el));
    staggerParents.forEach(parent => {
        const children = parent.children;
        const delay = parseInt(parent.dataset.staggerDelay) || 80;
        Array.from(children).forEach((child, i) => {
            child.style.transitionDelay = `${i * delay}ms`;
        });
        observer.observe(parent);
    });
})();

(function initFigmaAnagram() {
    const wrap   = document.getElementById('anagram');
    const topRow = document.getElementById('anagram-top');
    const botRow = document.getElementById('anagram-bot');
    const svg    = document.getElementById('anagram-svg');
    if (!wrap || !topRow || !botRow || !svg) return;

    const MAP = [4, 5, 1, 6, 0, 7, 2, 3]; // DIASPORA[i] → PARADISO position
    const topWord = ['D','I','A','S','P','O','R','A'];
    const botWord = ['P','A','R','A','D','I','S','O'];

    topWord.forEach((ch, i) => {
        const s = document.createElement('span');
        s.className = 'anagram-letter anagram-top';
        s.id = `at-${i}`;
        s.textContent = ch;
        topRow.appendChild(s);
    });
    botWord.forEach((ch, i) => {
        const s = document.createElement('span');
        s.className = 'anagram-letter anagram-bot';
        s.id = `ab-${i}`;
        s.textContent = ch;
        botRow.appendChild(s);
    });

    function buildLines() {
        const wRect = wrap.getBoundingClientRect();
        if (!wRect.width) return;
        svg.setAttribute('viewBox', `0 0 ${wRect.width} 80`);
        svg.style.height = '80px';
        svg.querySelectorAll('line').forEach(l => l.remove());

        MAP.forEach((bIdx, tIdx) => {
            const tEl = document.getElementById(`at-${tIdx}`);
            const bEl = document.getElementById(`ab-${bIdx}`);
            if (!tEl || !bEl) return;
            const tR = tEl.getBoundingClientRect();
            const bR = bEl.getBoundingClientRect();
            const x1 = tR.left + tR.width / 2 - wRect.left;
            const x2 = bR.left + bR.width / 2 - wRect.left;
            const y1 = 4, y2 = 76;
            const len = Math.hypot(x2 - x1, y2 - y1);

            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', x1); line.setAttribute('y1', y1);
            line.setAttribute('x2', x2); line.setAttribute('y2', y2);
            line.setAttribute('stroke', '#9ca3af');
            line.setAttribute('stroke-width', '1.5');
            line.setAttribute('stroke-linecap', 'round');
            line.setAttribute('marker-end', 'url(#ag-arr-dim)');
            line.setAttribute('opacity', '0.45');
            line.setAttribute('stroke-dasharray', len);
            line.setAttribute('stroke-dashoffset', '0');
            line.dataset.idx = tIdx;
            svg.appendChild(line);
        });
    }

    if (document.readyState === 'complete') buildLines();
    else window.addEventListener('load', buildLines);
    window.addEventListener('resize', buildLines);
    window.addEventListener('orientationchange', () => setTimeout(buildLines, 200));
    setTimeout(buildLines, 150);
    // The font-size clamp + single-column reflow change #anagram's width without
    // always firing a window resize (e.g. mobile address-bar collapse); observe
    // the element directly so the connector lines stay aligned to the letters.
    if (typeof ResizeObserver !== 'undefined') {
        new ResizeObserver(buildLines).observe(wrap);
    }

    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduced) return;

    let activeIdx = -1;
    let cycleCount = 0;
    setInterval(() => {
        cycleCount++;
        activeIdx = (cycleCount % 10 < 8) ? (cycleCount % 10) : -1;

        topWord.forEach((_, i) => document.getElementById(`at-${i}`)?.classList.remove('active'));
        botWord.forEach((_, i) => document.getElementById(`ab-${i}`)?.classList.remove('active'));
        svg.querySelectorAll('line').forEach(l => {
            l.setAttribute('stroke', '#9ca3af');
            l.setAttribute('stroke-width', '1.5');
            l.setAttribute('opacity', '0.45');
            l.setAttribute('marker-end', 'url(#ag-arr-dim)');
        });

        if (activeIdx >= 0 && activeIdx < 8) {
            document.getElementById(`at-${activeIdx}`)?.classList.add('active');
            document.getElementById(`ab-${MAP[activeIdx]}`)?.classList.add('active');
            svg.querySelectorAll('line').forEach(l => {
                if (parseInt(l.dataset.idx, 10) === activeIdx) {
                    l.setAttribute('stroke', '#0EA37B');
                    l.setAttribute('stroke-width', '2.5');
                    l.setAttribute('opacity', '1');
                    l.setAttribute('marker-end', 'url(#ag-arr-active)');
                }
            });
        }
    }, 600);
})();
