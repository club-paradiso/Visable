# Waymaker Artemis BLIND EVALUATION PROTOCOL (독립 맹검 평가 프로토콜)
## Clean-room Evaluation, Anti-Leakage Controls & Future Blind Set Standard

- **문서 버전**: 1.0.0
- **적용 대상**: Artemis Evaluation Subsystem (Mission 004-D / Mission 005)
- **발행일자**: 2026-10-29

---

## 1. 배경 및 현행 40개 홀드아웃 후보군의 한계

### 1.1 현행 상태: `isolation_not_verified`
현재 리포지토리에 존재하는 40개 홀드아웃 후보군(`artemis_eval_heldout_40.json`)은 개발 과정에서 정답(`expected`), 필수 사실(`required_facts`), 금지 진술(`forbidden_claims`)이 깃(git) 저장소에 평문으로 커밋되어 왔습니다.

따라서 다음과 같은 거버넌스 제약을 명시합니다:
1. **진정한 미공개(Unseen) 맹검 벤치마크 불인정**: 프롬프트 엔지니어링 에이전트와 모델 개발자가 저장소 코드를 읽는 과정에서 정답 레이블에 노출(contamination)되었을 위험이 상존합니다.
2. **평가 격리 상태 보고**: 런타임은 클린룸 규격이 완전히 충족되지 않는 한 `isolation_not_verified`로 보고해야 하며, 허위로 클린룸 완전성을 주장해서는 안 됩니다.

---

## 2. 맹검 입력 투영 및 누출 방지 체계 (`evaluation_isolation.py`)

### 2.1 맹검 입력 투영 (Blind Input Projection)
모델 추론 단계에서는 모델 어댑터에 전달되는 데이터 구조에서 채점 기준을 완전히 제거합니다:
- **보존 항목**: `id`, `question`, `user_context`, `metadata` (분할, 영역), RAG 시 필요한 공공기관 법령/지침 원문 텍스트.
- **엄격 제거 항목**: `expected` 전체 (`allowed_statuses`, `required_facts`, `forbidden_claims`, `abstention_criteria`), 채점 루브릭, 기존 검토자 판정 의견.

### 2.2 누출 및 오염 감지 (Leakage & Contamination Detector)
`detect_prompt_leakage`는 정답 레이블과 겹치는 문자열을 찾아 진단 목록으로 반환합니다.
이 검사는 경고를 자동 발생시키거나 입력을 차단하지 않습니다. 실제 추론 경계는
`waymaker_ai.inference_input`의 허용 목록 투영으로 보호합니다. 증거 본문과 인용
정보는 유지하고, 중첩 검토 의견·정답·루브릭·승인 표시와 임의 필드는 전달하지 않습니다.

### 2.3 독립 격리 상태와 검증 근거

독립 문항의 frozen manifest도 `isolation_not_verified`, `clean_room_verified: false`입니다.
`blind_projection_only`는 데이터 투영 방식만 뜻합니다. 해시, 역할 문자열, 작성자
자기 선언이나 서명 digest는 접근 통제·신원·독립성을 인증하지 않습니다.

검증 상태로 전환하려면 외부 시스템이 강제하는 신원·접근 권한, 독립적인 정답 키
관리, 격리 채점기, 접근 거부 실험, 불변 접근 로그와 독립 감사 증거가 필요합니다.
증거는 실행 ID와 동결된 파티션 해시에 연결하고 유효기간·철회 절차를 명시해야 합니다.
이 근거를 검증하는 신뢰할 수 있는 외부 검증기는 현재 연결되어 있지 않습니다.
따라서 로컬 API로 `isolation_verified`로 승격할 수 없습니다. 향후 검증된 실행도
권한 변경·증거 만료·누출이 발견되면 `isolation_not_verified`로 되돌려야 합니다.
같은 조건과 상태 전이는 `evaluation_isolation.isolation_verification_policy()`가 관리합니다.

### 2.4 오염 검사의 범위

빈 코퍼스, 분석할 수 없는 참조 자료 또는 질문·정답은 `unknown`, 점수 `null`로
보고합니다. 분석 가능한 경우에도 clean은 제공한 코퍼스에서 큰 어휘 중복을
찾지 못했다는 뜻입니다. 독립성이나 학습 데이터 비노출을 인증하지 않습니다.
`check_item_report()`에는 코퍼스 식별자·해시, 공급·분석 문서 수, 비교 범위,
정규화 방식, 임계값과 누락 가능한 의미·의역 중복의 한계를 기록합니다.

---

## 3. 차기 완전 독립 맹검 세트 (Future Independent Blind Set) 프로토콜

향후 신뢰성 있는 법률 AI 벤치마킹을 위해 수립된 5단계 클린룸 맹검 프로토콜입니다:

```
[ 1. 에어갭 저작 ] ---> [ 2. 공개키 암호화 ] ---> [ 3. 샌드박스 추론 ] ---> [ 4. 서명 해시 봉인 ] ---> [ 5. 복호화 및 채점 ]
 (외부 독립 변호사)     (정답 비공개 봉인)     (인터넷 차단 컨테이너)     (코드/가중치/응답 서명)      (독립 감사관 입회)
```

1. **외부 독립 저작 (Air-gapped Authoring)**:
   - 개발팀과 완전 분리된 독립 법률 전문가(출입국 전문 행정사·변호사)가 저장소 외부에서 새로운 법률 문항 100건을 저작.
2. **비대칭 암호화 봉인 (Asymmetric Encryption)**:
   - 질문과 맥락만 평문 공개하고, 정답 레이블 및 채점 루브릭은 독립 감사관의 공개키로 암호화하여 저장소에 보관.
3. **격리 컨테이너 맹검 추론 (Isolated Sandbox Inference)**:
   - 인터넷 접속이 차단된 격리 환경에서 모델이 질문 파일만 읽고 응답을 생성하여 기록.
4. **추론 결과 암호학적 봉인 (Cryptographic Run Manifest)**:
   - 추론에 사용된 모델 가중치 해시, 실행 코드 커밋, 생성 응답 JSONL의 SHA-256을 기록하여 `run_manifest.json` 생성.
5. **감사관 입회 복호화 및 공식 채점 (Decryption Ceremony & Official Scoring)**:
   - 독립 감사관의 개인키로 정답 루브릭을 복호화하여 일괄 채점하고 공식 골드 지표 발행.
