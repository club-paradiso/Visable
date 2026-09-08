(function () {
  'use strict';

  function escapeHtml(value) {
    return String(value || '').replace(/[&<>"']/g, function (character) {
      return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character];
    });
  }

  function confirmedDurationDays() {
    var rows = document.querySelectorAll('#confirmed-facts > div');
    for (var i = 0; i < rows.length; i += 1) {
      var label = rows[i].querySelector('dt');
      var value = rows[i].querySelector('dd');
      if (!label || !value || label.textContent.trim() !== '기간') continue;
      var match = value.textContent.match(/(\d+)\s*일/);
      return match ? Number(match[1]) : null;
    }
    return null;
  }

  function appendNotice(parent, className, title, body) {
    if (!parent || parent.querySelector('.' + className)) return;
    var notice = document.createElement('div');
    notice.className = className;
    notice.innerHTML = '<strong>' + escapeHtml(title) + '</strong><span>' + escapeHtml(body) + '</span>';
    parent.appendChild(notice);
  }

  function enhanceResult() {
    var root = document.getElementById('result-root');
    if (!root || !root.children.length) return;

    var predictionCard = root.querySelector('.result-card.prediction');
    if (predictionCard) {
      var amount = predictionCard.querySelector('.amount');
      if (amount && amount.textContent.trim() === '생성하지 못함') {
        amount.textContent = 'AI 추정 보류';
        var explanation = amount.nextElementSibling;
        if (explanation) {
          explanation.textContent = '유효성 검증을 통과한 구조화 예측이 없어 금액을 임의로 만들지 않았습니다.';
        }
        appendNotice(
          predictionCard,
          'prediction-degraded-note',
          '법령 계산은 그대로 유효합니다',
          'AI 예측 실패와 법령 기준 산출 실패는 다른 상태입니다. 왼쪽 법령 기준을 우선 확인하세요.'
        );
      }
    }

    var dispositionLead = root.querySelector('.result-lead');
    if (dispositionLead) {
      var unavailable = dispositionLead.querySelector('.subtle');
      if (unavailable && /가장 유력한 처분을 특정하기 어렵습니다/.test(unavailable.textContent || '')) {
        unavailable.textContent = '공개 근거만으로 처분 종류의 우열을 단정하지 않습니다. 확인되지 않은 처분을 억지로 하나 고르지 않고 불확실성을 그대로 표시합니다.';
      }
    }

    var baselineCard = root.querySelector('.result-card.baseline');
    var duration = confirmedDurationDays();
    if (baselineCard && duration === 30) {
      appendNotice(
        baselineCard,
        'baseline-boundary-note',
        '30일은 월 단위 경계에 걸릴 수 있습니다',
        '별표 7은 “개월” 단위 기준을 사용합니다. 30일만 입력한 사례는 시작일·종료일에 따라 월 단위 판단이 달라질 수 있으므로, 정확한 날짜를 적으면 경계 판단이 더 정확해집니다.'
      );
    }
  }

  function start() {
    var root = document.getElementById('result-root');
    if (!root) return;
    var observer = new MutationObserver(enhanceResult);
    observer.observe(root, { childList: true, subtree: true });
    enhanceResult();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start, { once: true });
  } else {
    start();
  }
})();