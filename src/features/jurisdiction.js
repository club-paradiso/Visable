// @ts-nocheck
/**
 * "관할 출입국 찾기" (Phase 3, moved verbatim from index.html lines 18560-18584). Uses the inline globals
 * tx(), escapeHtml(), openModal(), showToast() (compatibility surface, ADR-009). Exposed on
 * window.Visable.features.jurisdiction; the inline stubs with the same names delegate here.
 * Covered by tests/golden/specs/jurisdiction.spec.mjs.
 */
import { JUR_DB, OFFICE_INFO, JUR_SOURCE_URL } from './jurisdiction-data.js';

function initJurisdictionSelects() {
    const sidoSel = document.getElementById('jurSido');
    if (!sidoSel || sidoSel.options.length > 1) return;
    sidoSel.innerHTML = `<option value="">${escapeHtml(tx('jurSidoPlaceholder'))}</option>`;
    Object.keys(JUR_DB).forEach(sido => { const opt = document.createElement('option'); opt.value = sido; opt.textContent = sido; sidoSel.appendChild(opt); });
}
function updateSigungu() {
    const sido = document.getElementById('jurSido').value, sigunguSel = document.getElementById('jurSigungu'), card = document.getElementById('jurResultCard');
    card.classList.remove('active'); sigunguSel.innerHTML = `<option value="">${escapeHtml(tx('jurSigunguPlaceholder'))}</option>`;
    if (!sido) { sigunguSel.disabled = true; return; }
    sigunguSel.disabled = false;
    Object.keys(JUR_DB[sido]).forEach(sigungu => { const opt = document.createElement('option'); opt.value = sigungu; opt.textContent = sigungu; sigunguSel.appendChild(opt); });
}
/**
 * Show physical service counters separately from the competent office name.
 * Do not send everyone to the same building when an office has multiple sites.
 */
function renderServiceLocations(officeInfo) {
    const address = document.getElementById('jurOfficeAddr');
    const mapButtons = document.querySelector('#jurResultCard > .jur-map-btns');
    let container = document.getElementById('jurServiceLocations');
    if (!container) {
        container = document.createElement('div');
        container.id = 'jurServiceLocations';
        container.className = 'jur-service-locations';
        address.insertAdjacentElement('afterend', container);
    }
    const locations = officeInfo.serviceLocations || [];
    const split = locations.length > 0;
    address.hidden = split;
    address.style.display = split ? 'none' : '';
    if (mapButtons) {
        mapButtons.hidden = split;
        mapButtons.style.display = split ? 'none' : '';
    }
    container.replaceChildren();
    container.hidden = !split;
    if (!split) return;

    const ko = (document.documentElement.lang || 'ko').toLowerCase().startsWith('ko');
    const heading = document.createElement('div');
    heading.className = 'jur-sub';
    heading.textContent = ko ? '업무별 방문 청사' : 'Building by service';
    heading.style.margin = '0.85rem 0 0.3rem';
    container.appendChild(heading);

    locations.forEach(site => {
        const section = document.createElement('div');
        section.className = 'jur-service-location';
        section.style.cssText = 'padding:0.7rem 0;border-bottom:1px solid var(--bd, rgba(128,128,128,.25))';
        const name = document.createElement('div');
        name.className = 'jur-office-name';
        name.textContent = ko ? site.name : site.name_en;
        const services = document.createElement('div');
        services.className = 'jur-sub';
        services.textContent = ko ? site.services : site.services_en;
        const street = document.createElement('div');
        street.className = 'jur-office-addr';
        street.textContent = site.addr;
        street.style.margin = '0.45rem 0 0.6rem';
        const links = document.createElement('div');
        links.className = 'jur-map-btns';
        for (const [type, url, label] of [
            ['naver', site.naver, tx('jurNaverMap')],
            ['kakao', site.kakao, tx('jurKakaoMap')]
        ]) {
            const link = document.createElement('a');
            link.className = 'jur-map-btn btn-' + type;
            link.href = url;
            link.target = '_blank';
            link.rel = 'noopener noreferrer';
            link.textContent = label;
            links.appendChild(link);
        }
        section.append(name, services, street, links);
        container.appendChild(section);
    });
}

function showJurisdiction() {
    const sido = document.getElementById('jurSido').value, sigungu = document.getElementById('jurSigungu').value, card = document.getElementById('jurResultCard');
    if (!sido || !sigungu) { card.classList.remove('active'); return; }
    const officeName = JUR_DB[sido][sigungu], officeInfo = OFFICE_INFO[officeName];
    if (!officeInfo) { showToast(tx('jurMissingInfo')); return; }
    document.getElementById('jurMsg').innerHTML = tx('jurResultMsg', { office: escapeHtml(officeName) });
    document.getElementById('jurOfficeName').textContent = officeName;
    document.getElementById('jurOfficeAddr').textContent = officeInfo.addr;
    renderServiceLocations(officeInfo);
    document.getElementById('jurNaver').href = officeInfo.naver; document.getElementById('jurKakao').href = officeInfo.kakao;
    const officialLink = document.getElementById('jurOfficialSource');
    if (officialLink) officialLink.href = JUR_SOURCE_URL[sido] || 'https://www.immigration.go.kr/immigration/index.do';
    card.classList.add('active');
}
function openJurisdictionModal() { openModal('jurisdictionModalOverlay'); initJurisdictionSelects(); }

export { initJurisdictionSelects, updateSigungu, showJurisdiction, openJurisdictionModal };
