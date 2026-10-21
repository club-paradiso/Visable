(function () {
  'use strict';
  var labels = {
    ko: ['전체 도구', '비자·체류 검색', 'Waymaker 상담'],
    en: ['All services', 'Visa & stay search', 'Ask Waymaker'],
    'zh-CN': ['全部工具', '签证与居留搜索', '咨询 Waymaker'],
    'zh-TW': ['全部工具', '簽證與居留搜尋', '諮詢 Waymaker'],
    ja: ['すべてのツール', 'ビザ・在留検索', 'Waymaker に相談'],
    vi: ['Tất cả công cụ', 'Tìm visa và cư trú', 'Hỏi Waymaker'],
    id: ['Semua layanan', 'Cari visa dan izin tinggal', 'Tanya Waymaker'],
    ar: ['جميع الخدمات', 'بحث التأشيرة والإقامة', 'اسأل Waymaker'],
    fr: ['Tous les services', 'Visa et séjour', 'Demander à Waymaker'],
    es: ['Todos los servicios', 'Visados y estancia', 'Consultar a Waymaker'],
    de: ['Alle Dienste', 'Visum und Aufenthalt', 'Waymaker fragen'],
    ru: ['Все сервисы', 'Визы и пребывание', 'Спросить Waymaker'],
    tr: ['Tüm hizmetler', 'Vize ve ikamet', "Waymaker’a sor"],
    uk: ['Усі сервіси', 'Візи та перебування', 'Запитати Waymaker'],
    tl: ['Lahat ng serbisyo', 'Visa at pananatili', 'Magtanong sa Waymaker']
  };
  function update() {
    var text = labels[document.documentElement.lang] || labels.en;
    document.querySelectorAll('[data-vs-service-nav] a').forEach(function (link, i) { link.textContent = text[i]; });
  }
  update();

  // Keep active product visible in the shared service switcher.
  var current = (window.location.pathname.split('/').pop() || 'index.html').toLowerCase();
  document.querySelectorAll('[data-vs-service-nav] a').forEach(function (link) {
    var path = (link.getAttribute('href') || '').split('#')[0].toLowerCase();
    if (path === current && path !== 'index.html') link.setAttribute('aria-current', 'page');
  });
  new MutationObserver(update).observe(document.documentElement, { attributes: true, attributeFilter: ['lang'] });
  document.addEventListener('paradiso-language-applied', update);
})();
