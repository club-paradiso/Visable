# 중요 라벨 사례별 잠재 위험 검토

v0 라벨의 오류이며 실제 법적 오답이나 위해 발생을 인적으로 확정한 표가 아니다.
모든 기준선에서 중요 오류로 표시된 사례의 합집합을 포함한다. B1의 fine 미출력은 오류로 추가하지 않는다.

| 분류 | 잠재 영향 |
|---|---|
| H-identity | 잘못된 자격·세부 자격·존재성으로 요건과 서류를 선택할 위험 |
| H-direction | 현재·목표 자격을 혼동해 전환 경로를 잘못 안내할 위험 |
| H-domain | 체류와 사증발급 절차를 섞어 담당 기관·신청 경로를 잘못 안내할 위험 |
| M-procedure | 같은 도메인에서 절차나 신고 유형을 놓쳐 서류·기한·접수 흐름을 잘못 제시할 위험 |
| M-clarify | 필요한 확인을 생략하거나 불필요한 확인을 요구할 위험 |

| 사례 | 기준선별 틀린 항목 | 위험 분류 | 개선판 잔여 중요 오류 |
|---|---|---|---|
| cls-en-2nd-year-trap | B2: not_status_token_respected, status_exact; B_fixed_before: procedure_fine | H-identity, M-procedure | 해소(v0 라벨 기준) |
| cls-en-d10-to-e7 | B1: status_exact | H-identity | 해소(v0 라벨 기준) |
| cls-en-d84s-visa-issuance | B1: procedure_coarse, subcode_exact, subcode_expected_present | H-identity, M-procedure | 해소(v0 라벨 기준) |
| cls-en-e7-evisa | B_fixed_before: procedure_fine | M-procedure | 해소(v0 라벨 기준) |
| cls-en-e7-visa-issuance | B1: procedure_coarse | M-procedure | 해소(v0 라벨 기준) |
| cls-en-e71-cvi | B1: procedure_coarse, subcode_exact, subcode_expected_present; B_fixed_before: procedure_coarse, procedure_fine | H-identity, M-procedure | 해소(v0 라벨 기준) |
| cls-en-g15-register | B1: procedure_coarse, subcode_exact, subcode_expected_present; B_fixed_before: procedure_coarse, procedure_fine | H-identity, M-procedure | 해소(v0 라벨 기준) |
| cls-ko-c39-visa-issuance | B1: procedure_coarse, subcode_exact, subcode_expected_present | H-identity, M-procedure | 해소(v0 라벨 기준) |
| cls-ko-d2-evisa | B2: procedure_fine; B_fixed_before: procedure_fine | M-procedure | 해소(v0 라벨 기준) |
| cls-ko-d41-to-d21 | B1: status_exact, subcode_exact, subcode_expected_present | H-identity | 해소(v0 라벨 기준) |
| cls-ko-d42k-registration | B1: subcode_exact, subcode_expected_present | H-identity | 해소(v0 라벨 기준) |
| cls-ko-e74r-condition-change | B1: subcode_exact, subcode_expected_present; B_fixed_before: procedure_fine | H-identity, M-procedure | 해소(v0 라벨 기준) |
| cls-ko-e74r-extension | B1: subcode_exact, subcode_expected_present | H-identity | 해소(v0 라벨 기준) |
| cls-ko-work-visa-issuance | B1: clarification, procedure_coarse | M-clarify, M-procedure | 해소(v0 라벨 기준) |
| cls-zh-d10-to-e71 | B1: procedure_coarse, status_exact, subcode_exact, subcode_expected_present, target_status_exact; B2: current_status_exact, procedure_coarse, procedure_fine, status_exact, subcode_exact, subcode_expected_present, target_status_exact | H-direction, H-identity, M-procedure | 해소(v0 라벨 기준) |
| cls-en-a3-month-trap | B1: not_status_token_respected, status_exact; B2: not_status_token_respected, status_exact | H-identity | 해소(v0 라벨 기준) |
| cls-en-d2-switch-d101 | B1: status_exact, subcode_exact, subcode_expected_present | H-identity | 해소(v0 라벨 기준) |
| cls-en-e74r-card-reissue | B1: subcode_exact, subcode_expected_present; B_fixed_before: procedure_fine | H-identity, M-procedure | 해소(v0 라벨 기준) |
| cls-en-e7s1-extension | B1: subcode_exact, subcode_expected_present | H-identity | 해소(v0 라벨 기준) |
| cls-en-f10-visa-application | B1: not_status_token_respected, procedure_coarse, status_exact; B2: status_exact; B_fixed_before: not_status_token_respected, procedure_coarse, procedure_fine, status_exact; B_fixed_after: not_status_token_respected, status_exact | H-identity, M-procedure | 잔여 |
| cls-en-f2r-condition-change | B1: subcode_exact, subcode_expected_present; B2: procedure_fine; B_fixed_before: procedure_fine | H-identity, M-procedure | 해소(v0 라벨 기준) |
| cls-ja-e7-cvi | B1: procedure_coarse; B2: procedure_coarse, procedure_fine | M-procedure | 해소(v0 라벨 기준) |
| cls-ja-e74r-card-reissue | B1: subcode_exact, subcode_expected_present; B_fixed_before: procedure_fine | H-identity, M-procedure | 해소(v0 라벨 기준) |
| cls-ko-d10-to-e71 | B1: status_exact, subcode_exact, subcode_expected_present | H-identity | 해소(v0 라벨 기준) |
| cls-ko-d10t-extension | B1: subcode_exact, subcode_expected_present | H-identity | 해소(v0 라벨 기준) |
| cls-ko-d21-glued-extension | B1: subcode_exact, subcode_expected_present | H-identity | 해소(v0 라벨 기준) |
| cls-ko-e7-cvi-employer | B1: procedure_coarse | M-procedure | 해소(v0 라벨 기준) |
| cls-ko-e71-evisa | B1: subcode_exact, subcode_expected_present; B_fixed_before: procedure_fine | H-identity, M-procedure | 해소(v0 라벨 기준) |
| cls-ko-e7t-cvi | B1: procedure_coarse, subcode_exact, subcode_expected_present | H-identity, M-procedure | 해소(v0 라벨 기준) |
| cls-ko-e9-to-e74 | B1: procedure_coarse, status_exact, subcode_exact, subcode_expected_present | H-identity, M-procedure | 해소(v0 라벨 기준) |
| cls-ko-f10-nonexistent | B1: not_status_token_respected, status_exact; B2: status_exact; B_fixed_before: not_status_token_respected, status_exact; B_fixed_after: not_status_token_respected, status_exact | H-identity | 잔여 |
| cls-ko-f27s-extension | B1: subcode_exact, subcode_expected_present | H-identity | 해소(v0 라벨 기준) |
| cls-ko-f2t-card-reissue | B1: subcode_exact, subcode_expected_present; B_fixed_before: procedure_fine | H-identity, M-procedure | 해소(v0 라벨 기준) |
| cls-ko-f6-to-e9 | B1: procedure_coarse, status_exact; B_fixed_before: procedure_coarse, procedure_fine, status_exact; B_fixed_after: status_exact | H-identity, M-procedure | 잔여 |
| cls-ko-g15-extension | B1: subcode_exact, subcode_expected_present | H-identity | 해소(v0 라벨 기준) |
| cls-ko-to-f5t | B1: subcode_exact, subcode_expected_present, target_status_exact | H-direction, H-identity | 해소(v0 라벨 기준) |
| cls-vi-f6-to-f5 | B1: procedure_coarse, status_exact, target_status_exact; B2: current_status_exact, procedure_coarse, procedure_fine, status_exact, target_status_exact | H-direction, H-identity, M-procedure | 해소(v0 라벨 기준) |
