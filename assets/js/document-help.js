(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.ParadisoDocumentHelp = api;

  /* index.html is intentionally monolithic and carries years of inline CSS.
     Install final mobile styles after parsing so phone layout has deterministic
     last layers without rewriting the legacy page wholesale. */
  if (typeof document !== 'undefined') {
    /* Do not prevent pinch zoom on phones. The legacy viewport declaration used
       maximum-scale=1 and user-scalable=no; normalize it at runtime while keeping
       viewport-fit=cover so safe-area insets continue to work on notched iPhones. */
    var viewportMeta = document.querySelector('meta[name="viewport"]');
    if (viewportMeta) {
      viewportMeta.setAttribute('content', 'width=device-width, initial-scale=1, viewport-fit=cover');
    }

    var installMobileAuthorityStyles = function () {
      var target = document.head || document.documentElement;
      if (!document.getElementById('visable-mobile-authority-styles')) {
        var link = document.createElement('link');
        link.id = 'visable-mobile-authority-styles';
        link.rel = 'stylesheet';
        link.media = '(max-width: 820px)';
        link.href = 'assets/css/visable-mobile-iphone-20260904.css?v=20260904';
        target.appendChild(link);
      }

      if (!document.getElementById('visable-mobile-qa-hardening-styles')) {
        var hardening = document.createElement('link');
        hardening.id = 'visable-mobile-qa-hardening-styles';
        hardening.rel = 'stylesheet';
        hardening.media = '(max-width: 820px)';
        hardening.href = 'assets/css/visable-mobile-qa-hardening-20260905.css?v=20260905';
        target.appendChild(hardening);
      }

      /* iPhones can exceed the portrait breakpoint when rotated. Keep the
         landscape-only fixes inline so 844-956px phone viewports do not fall
         through to legacy 14px controls just because their width got larger. */
      if (!document.getElementById('visable-mobile-landscape-compat')) {
        var landscapeCompat = document.createElement('style');
        landscapeCompat.id = 'visable-mobile-landscape-compat';
        landscapeCompat.textContent = '@media (orientation: landscape) and (max-height: 500px) and (pointer: coarse) {'
          + ' html, body { width:100%; max-width:100%; overflow-x:clip; }'
          + ' input, textarea, select { font-size:16px !important; }'
          + ' button, input, textarea, select, a, [role="button"] { touch-action:manipulation; -webkit-tap-highlight-color:rgba(11,115,87,.14); }'
          + ' .top-ctrls, #topCtrls, .hero-container, .results-area { padding-left:max(.75rem,env(safe-area-inset-left,0px)) !important; padding-right:max(.75rem,env(safe-area-inset-right,0px)) !important; }'
          + ' .p-gateway, .hero-actions, .sbar, .results-area, .rlist, #rlist, .us-layer, .us-interpret, .us-ai { min-width:0 !important; max-width:100%; }'
          + ' .modal-box, .hikorea-modal, .document-help-modal, .scenario-picker-panel-inner { max-height:calc(100vh - max(12px,env(safe-area-inset-top,0px))) !important; max-height:calc(100dvh - max(12px,env(safe-area-inset-top,0px))) !important; }'
          + ' button:focus-visible, a:focus-visible, input:focus-visible, textarea:focus-visible, select:focus-visible, [role="button"]:focus-visible, [tabindex]:focus-visible { outline:2px solid currentColor !important; outline-offset:2px !important; }'
          + ' }';
        target.appendChild(landscapeCompat);
      }

      /* Keep reduced-motion behavior valid even in engines that do not parse
         nested conditional group rules. This inline fallback remains intentional
         even though the QA stylesheet also carries the flat rule. */
      if (!document.getElementById('visable-mobile-reduced-motion-compat')) {
        var reducedMotionCompat = document.createElement('style');
        reducedMotionCompat.id = 'visable-mobile-reduced-motion-compat';
        reducedMotionCompat.textContent = '@media (prefers-reduced-motion: reduce) and (max-width: 820px) { .p-gw-card, .p-gw-util, .p-gw-newhome, .hero-actions .ha { transition: none !important; } }';
        target.appendChild(reducedMotionCompat);
      }
    };

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', installMobileAuthorityStyles, { once: true });
    } else {
      installMobileAuthorityStyles();
    }
  }
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  var UI = {
    ko: {
      open: '이 서류가 뭔가요?', close: '문서 안내 닫기', summary: '한 줄로 말하면',
      who: '누가 준비하나요?', when: '언제 필요한가요?', prepare: '작성/준비 방법',
      situations: '상황별 준비 방법', mistakes: '자주 하는 실수', questions: '관련 질문',
      sources: '공식 출처', checked: '확인일', category: {
        official_form: '공식 서식', evidence: '증빙서류', situational: '상황별 서류', caution: '주의 필요'
      },
      risk: {
        frequent_mistakes: '실수 잦음', office_confirmation: '관할청 확인 필요',
        original_confirmation: '원본 확인 필요', high: '주의 필요'
      }
    },
    en: {
      open: 'What is this document?', close: 'Close document guide', summary: 'In one sentence',
      who: 'Who prepares it?', when: 'When is it needed?', prepare: 'How to prepare it',
      situations: 'Guidance by situation', mistakes: 'Common mistakes', questions: 'Related questions',
      sources: 'Official sources', checked: 'Checked', category: {
        official_form: 'Official form', evidence: 'Supporting evidence', situational: 'Situation-specific', caution: 'Caution'
      },
      risk: {
        frequent_mistakes: 'Frequent mistakes', office_confirmation: 'Confirm with your office',
        original_confirmation: 'Check original requirements', high: 'Extra care needed'
      }
    }
  };

  function localeKey(locale) {
    return String(locale || '').toLowerCase().indexOf('en') === 0 ? 'en' : 'ko';
  }

  function ui(locale) { return UI[localeKey(locale)]; }

  function normalize(value) {
    return String(value == null ? '' : value)
      .normalize('NFKC')
      .toLowerCase()
      .replace(/\b(doc|document)\b/g, '')
      .replace(/[\s\u00a0·ㆍ･,.;:!?()[\]{}<>「」『』【】\/\\_\-–—'"*]+/g, '')
      .replace(/별지제?\d+(?:호의?\d*)?서식/g, '')
      .trim();
  }

  function unique(values) {
    var seen = Object.create(null);
    return values.filter(function (value) {
      var key = String(value || '');
      if (!key || seen[key]) return false;
      seen[key] = true;
      return true;
    });
  }

  function buildAliases(record) {
    return unique([record.id]
      .concat(record.docIds || [])
      .concat(record.aliasesKo || [])
      .concat(record.aliasesEn || [])
      .concat([record.titleKo, record.titleEn])
      .map(normalize)
      .filter(Boolean))
      .sort(function (a, b) { return b.length - a.length; });
  }

  function createMatcher(records) {
    var list = Array.isArray(records) ? records.filter(function (record) {
      return record && record.id;
    }).map(function (record) {
      return { record: record, aliases: buildAliases(record) };
    }) : [];
    var exact = Object.create(null);
    list.forEach(function (entry) {
      entry.aliases.forEach(function (alias) {
        if (!exact[alias]) exact[alias] = entry.record;
      });
    });

    return {
      records: list.map(function (entry) { return entry.record; }),
      find: function () {
        var candidates = Array.prototype.slice.call(arguments).map(normalize).filter(Boolean);
        var i;
        for (i = 0; i < candidates.length; i += 1) {
          if (exact[candidates[i]]) return exact[candidates[i]];
        }
        for (i = 0; i < candidates.length; i += 1) {
          var candidate = candidates[i];
          for (var j = 0; j < list.length; j += 1) {
            for (var k = 0; k < list[j].aliases.length; k += 1) {
              var alias = list[j].aliases[k];
              if (alias.length >= 4 && (candidate.indexOf(alias) !== -1 || (candidate.length >= 6 && alias.indexOf(candidate) !== -1))) {
                return list[j].record;
              }
            }
          }
        }
        return null;
      }
    };
  }

  function escapeHtml(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (char) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char];
    });
  }

  function local(record, base, locale) {
    var suffix = localeKey(locale) === 'en' ? 'En' : 'Ko';
    return record[base + suffix] || record[base + 'Ko'] || record[base + 'En'] || '';
  }

  function listHtml(items, className) {
    if (!Array.isArray(items) || !items.length) return '';
    return '<ul class="' + className + '">' + items.map(function (item) {
      return '<li>' + escapeHtml(item) + '</li>';
    }).join('') + '</ul>';
  }

  function section(title, body, className) {
    if (!body) return '';
    return '<section class="document-help-section ' + (className || '') + '"><h3>' + escapeHtml(title) + '</h3>' + body + '</section>';
  }

  function stepsHtml(items, locale) {
    if (!Array.isArray(items) || !items.length) return '';
    return '<div class="document-help-steps">' + items.map(function (item) {
      var title = local(item, 'sectionTitle', locale);
      var body = local(item, 'body', locale);
      if (!title && !body) return '';
      return '<article class="document-help-step"><h4>' + escapeHtml(title) + '</h4><p>' + escapeHtml(body) + '</p></article>';
    }).join('') + '</div>';
  }

  function sourcesHtml(refs, locale) {
    var labels = ui(locale);
    if (!Array.isArray(refs) || !refs.length) return '';
    var links = refs.map(function (ref) {
      var url = String(ref && ref.url || '');
      if (!/^https:\/\//i.test(url)) return '';
      var label = local(ref, 'label', locale) || url;
      var note = local(ref, 'evidenceNote', locale);
      var meta = [ref.sourceType, ref.checkedAt ? labels.checked + ' ' + ref.checkedAt : ''].filter(Boolean).join(' · ');
      return '<li><a href="' + escapeHtml(url) + '" target="_blank" rel="noopener noreferrer">' + escapeHtml(label) + '</a>'
        + (meta ? '<span class="document-help-source-meta">' + escapeHtml(meta) + '</span>' : '')
        + (note ? '<p>' + escapeHtml(note) + '</p>' : '') + '</li>';
    }).filter(Boolean).join('');
    return links ? '<ul class="document-help-sources">' + links + '</ul>' : '';
  }

  function renderPanel(record, locale) {
    if (!record) return '';
    var labels = ui(locale);
    var when = local(record, 'whenNeeded', locale);
    var situations = local(record, 'situationalGuidance', locale);
    var mistakes = local(record, 'commonMistakes', locale);
    var questions = local(record, 'userQuestions', locale);
    var warning = local(record, 'warning', locale);
    var disclaimer = local(record, 'disclaimer', locale);
    var categoryLabel = labels.category[record.category] || labels.category.caution;
    var riskLabel = labels.risk[record.riskLevel] || labels.risk.high;
    return '<div class="document-help-chips"><span>' + escapeHtml(categoryLabel) + '</span><span class="is-risk">' + escapeHtml(riskLabel) + '</span></div>'
      + section(labels.summary, '<p class="document-help-lead">' + escapeHtml(local(record, 'summary', locale)) + '</p>')
      + (warning ? '<div class="document-help-warning" role="note">' + escapeHtml(warning) + '</div>' : '')
      + section(labels.who, '<p>' + escapeHtml(local(record, 'whoPrepares', locale)) + '</p>')
      + section(labels.when, listHtml(when, 'document-help-list'))
      + section(labels.prepare, stepsHtml(record.howToPrepare, locale))
      + section(labels.situations, stepsHtml(situations, locale))
      + section(labels.mistakes, listHtml(mistakes, 'document-help-list document-help-mistakes'))
      + section(labels.questions, listHtml(questions, 'document-help-list document-help-questions'))
      + section(labels.sources, sourcesHtml(record.sourceRefs, locale), 'document-help-section--sources')
      + (disclaimer ? '<p class="document-help-disclaimer">' + escapeHtml(disclaimer) + '</p>' : '');
  }

  return { normalize: normalize, createMatcher: createMatcher, escapeHtml: escapeHtml, ui: ui, local: local, renderPanel: renderPanel };
});
