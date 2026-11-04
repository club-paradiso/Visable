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
function showJurisdiction() {
    const sido = document.getElementById('jurSido').value, sigungu = document.getElementById('jurSigungu').value, card = document.getElementById('jurResultCard');
    if (!sido || !sigungu) { card.classList.remove('active'); return; }
    const officeName = JUR_DB[sido][sigungu], officeInfo = OFFICE_INFO[officeName];
    if (!officeInfo) { showToast(tx('jurMissingInfo')); return; }
    document.getElementById('jurMsg').innerHTML = tx('jurResultMsg', { office: escapeHtml(officeName) });
    document.getElementById('jurOfficeName').textContent = officeName;
    document.getElementById('jurOfficeAddr').textContent = officeInfo.addr;
    document.getElementById('jurNaver').href = officeInfo.naver; document.getElementById('jurKakao').href = officeInfo.kakao;
    const officialLink = document.getElementById('jurOfficialSource');
    if (officialLink) officialLink.href = JUR_SOURCE_URL[sido] || 'https://www.immigration.go.kr/immigration/index.do';
    card.classList.add('active');
}
function openJurisdictionModal() { openModal('jurisdictionModalOverlay'); initJurisdictionSelects(); }

export { initJurisdictionSelects, updateSigungu, showJurisdiction, openJurisdictionModal };
