// Moved verbatim from the inline <script> block of ai.html (lines 3292-3353 before the move; Phase 5 of the frontend rebuild, 2026-11-04).
// Classic script loaded at the same document position, so it still runs synchronously at parse time in the same order.
    /* Waymaker surface switcher — a small, always-visible nav that links the
       EXISTING user-facing surfaces (AI consultation, procedure navigator, nationality coach
       chat, naturalization-interview coach chat, legal research panel). It
       adds no new AI mode; every target was already reachable via deep links. */
    (function () {
        'use strict';
        var header = document.querySelector('.chat-header');
        if (!header || document.getElementById('wmSurfaceSwitch')) return;

        var params = new URLSearchParams(location.search);
        var domain = (params.get('domain') || '').toLowerCase();
        var mode = (params.get('mode') || '').toLowerCase();
        var current = params.get('nav') === '1' ? 'navigator' : 'chat';
        if (domain === 'nationality' && params.get('nav') !== '1') {
            current = mode === 'naturalization_interview_prep' ? 'interview' : 'coach';
        }

        var items = [
            { key: 'chat', href: 'ai.html', label: 'AI 상담' },
            { key: 'navigator', href: 'ai.html?nav=1', label: '절차 내비게이터' },
            { key: 'coach', href: 'ai.html?domain=nationality', label: '국적·귀화 상담 코치' },
            { key: 'interview', href: 'ai.html?domain=nationality&mode=naturalization_interview_prep', label: '귀화면접 모의연습' },
            { key: 'research', href: 'ai.html#legalSourceSearchRoot', label: '법령·판례 리서치' }
        ];

        var css = document.createElement('style');
        css.textContent = '#wmSurfaceSwitch{display:flex;flex-wrap:wrap;align-items:center;gap:.4rem;padding:.45rem .9rem;background:var(--bg1,#111);border-bottom:1px solid var(--bd1,rgba(255,255,255,.08));}'
            + '#wmSurfaceSwitch .wm-ss-label{font-size:.72rem;color:var(--t3,#888);margin-right:.15rem;}'
            + '#wmSurfaceSwitch a{font-size:.78rem;line-height:1;padding:.42rem .7rem;border-radius:999px;border:1px solid var(--bd1,rgba(255,255,255,.14));color:var(--t2,#bbb);text-decoration:none;white-space:nowrap;}'
            + '#wmSurfaceSwitch a[aria-current="page"]{background:var(--acc,#4f7cff);border-color:var(--acc,#4f7cff);color:#fff;font-weight:700;}'
            + '#wmSurfaceSwitch a:focus-visible{outline:2px solid var(--acc,#4f7cff);outline-offset:2px;}'
            + '@media (max-width:480px){#wmSurfaceSwitch{padding:.4rem .6rem;}#wmSurfaceSwitch a{font-size:.74rem;padding:.4rem .55rem;}}';
        document.head.appendChild(css);

        var nav = document.createElement('nav');
        nav.id = 'wmSurfaceSwitch';
        nav.setAttribute('aria-label', 'Waymaker 화면 전환');
        var label = document.createElement('span');
        label.className = 'wm-ss-label';
        label.textContent = '바로가기';
        nav.appendChild(label);
        items.forEach(function (item) {
            var a = document.createElement('a');
            a.href = item.href;
            a.textContent = item.label;
            if (item.key === current) a.setAttribute('aria-current', 'page');
            // Same-surface research link: just scroll if the panel is already visible.
            if (item.key === 'research') {
                a.addEventListener('click', function (ev) {
                    var lr = document.getElementById('legalSourceSearchRoot');
                    if (lr && document.body.classList.contains('wm-active')) {
                        ev.preventDefault();
                        lr.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
                });
            }
            nav.appendChild(a);
        });
        header.insertAdjacentElement('afterend', nav);
    })();
