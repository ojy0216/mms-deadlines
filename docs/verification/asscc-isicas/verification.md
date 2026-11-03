# ESSERC · A-SSCC · ISICAS 반영 검증

2026-11-03에 로컬 작업 트리에서 검증했습니다. 기존 49개 회차의 ID와 확인된 날짜를 모두 보존하고 A-SSCC 2024–2026, ISICAS 2024–2027을 추가해 총 56개 회차입니다. ESSERC 2024–2028도 그대로 유지됩니다. 아래 결과는 로컬 검증 시점의 기록입니다.

## 반영 결과

- Circuit 학회를 명시적인 집합으로 분류하고 A-SSCC와 ISICAS를 기존 매일 00:00 KST 수집 workflow에 포함했습니다.
- `submission_tracks`에 선언한 저널별 paper 이벤트를 초기화합니다. 공통 paper 이벤트는 생성하지 않습니다. `(kind, track)`별 병합·중복 검증·연장·실패 격리·수동 보정과 반복 동기화 보존을 확인했습니다. 기존 보정 키도 유지됩니다.
- ISICAS 2026의 TCAS-I·TBioCAS·TCAS-AI·TVLSI는 5월 11일, TCAS-II·OJCAS는 6월 1일입니다. 모두 날짜만 저장하며 UTC 시각을 만들지 않습니다. 호환용 `deadline`은 TBA입니다.
- 상세와 캘린더에서 여섯 저널 마감을 모두 표시합니다. 저널별 ICS UID는 서로 다르고 제목에 저널명을 포함합니다. 기존 이벤트의 UID와 상세 URL은 유지됩니다.
- ISICAS 2027은 IEEE 공식 발표로 개최 기간과 장소를 확인했습니다. 발표되지 않은 제출 일정과 저널 목록은 추정하지 않았습니다.
- 수동으로 확인한 A-SSCC 2024 개최 장소는 보정의 출처와 확인 시각을 유지합니다. 자동 수집 실패가 이 보정이나 저널별 보정을 지우지 않습니다.

## 공식 출처와 샘플

| 회차 | 공식 출처 | 확인 내용 |
| --- | --- | --- |
| A-SSCC 2024 | [IEEE Xplore](https://ieeexplore.ieee.org/document/10849111/) | 11월 18–21일, Hiroshima. 공식 검색 색인으로 확인한 개최 정보만 수동 보정. 제출은 TBA. |
| A-SSCC 2025 | [학회 홈페이지](https://www.a-sscc2025.org/) | 취소선 처리된 6월 4일을 제외하고 6월 18일 20:00 GMT 연장 마감 수집. 본회의는 11월 3–5일. |
| A-SSCC 2026 | [IEEE 대만 지부 CFP PDF](https://ieee.org.tw/wp-content/uploads/2026/05/A-SSCC_2026_CFP_260408.pdf) | 6월 3일 20:00 GMT 제출, 8월 8일 채택 발표, 11월 1–4일 개최, The Lin Hotel, Taichung. |
| ISICAS 2024 | [IEEE CASS 행사](https://ieee-cas.org/event/conference/2024-ieee-international-symposium-integrated-circuits-and-systems), [공식 CFP PDF](https://ieee-cas.org/files/ieeecass/2024-03/ISICAS-2024_Call%20for%20Papers.pdf) | 당시 4개 저널의 갱신된 4월 29일 마감, 7월 3일 채택 발표, New Delhi 개최. |
| ISICAS 2025 | [저널별 최종 연장 표](https://2025.ieee-isicas.org/authors/ps.html), [홈페이지](https://2025.ieee-isicas.org/) | 저널별 3월 6일/20일 마감, 최종 홈페이지의 10월 26–27일 Qingdao 개최. |
| ISICAS 2026 | [Important Dates](https://2026.ieee-isicas.org/authors/important-dates.html) | 여섯 저널의 두 마감, 9월 14일 채택 발표, 12월 4–6일 Torino 개최. |
| ISICAS 2027 | [IEEE CASS 행사](https://ieee-cas.org/event/conference/2027-ieee-international-symposium-integrated-circuits-and-systems) | 10월 25–27일 Athens 개최. |

다운로드한 공식 HTML/PDF 8개와 URL·수집일·SHA-256을 `tests/fixtures/raw/manifest.json`에 추가했습니다. 이 샘플로 날짜 정밀도와 연장 마감을 회귀 테스트합니다. 원래 A-SSCC 2024 도메인은 현재 학회와 무관한 페이지를 제공하므로 데이터 출처로 사용하지 않습니다.

## 검증 결과

| 검증 | 결과 |
| --- | --- |
| `.venv/bin/python -m utils.collector.sync --validate-only` | 통과, 13개 학회·56개 회차 |
| `.venv/bin/python -m unittest discover -s tests -v` | 41개 테스트 통과 |
| `node tests/test_schedule.js` | 5개 렌더링 회귀 테스트 통과. 추가 패키지 없이 Node 내장 테스트·VM 사용 |
| Python compileall, JavaScript/Ruby 구문 검사, `git diff --check` | 통과 |
| `bundle exec jekyll build --future` | 통과. 아래 로컬 Ruby 환경 참고 |
| `.venv/bin/python -m utils.validate_site` | JSON과 57개 ICS 피드, 152개 공개 이벤트 일치. 종일 종료일·UTC·UID·저널명·기존 상세 URL 검사 |
| 내부 HTMLProofer | HTML 3개 페이지, 내부 링크·이미지·스크립트·favicon 검사 통과 |
| 실제 Chromium | Circuit 필터, 상세, 세 학회 다운로드, 저널별 달력, 상태 전환, 과거 일정 참고, 모바일 가로 넘침 검사 통과. JS 예외·로컬 HTTP 오류 0개 |

내부 HTMLProofer 명령:

```sh
bundle exec htmlproofer ./_site --disable-external --check-favicon --check-html --url-swap '^/mms-deadlines/:/'
```

로컬에는 Ruby 3.2만 있어 기존 Liquid 4.0.3이 호출하는 제거된 `untaint`·`taint`·`tainted?` 메서드를 `/tmp`의 무동작 호환 파일로 제공하고 `RUBYOPT`로 빌드·HTMLProofer에 적용했습니다. 잠긴 gem은 임시 Ruby 헤더를 사용해 소스 빌드했습니다. Gemfile·Gemfile.lock·Python requirements에는 변경이 없습니다. 프로젝트 권장 및 GitHub Actions의 Ruby 3.1에는 이 임시 호환 처리가 필요하지 않습니다.

## 브라우저 시나리오와 화면

실제 생성된 `schedule.json`과 ICS를 로컬 서버에서 읽었습니다. 기본 화면은 브라우저 시각을 2026-11-03, 시간대를 Asia/Seoul로 고정했습니다. 경계 시나리오만 브라우저 시각 또는 응답을 바꿨으며 저장 데이터는 바꾸지 않았습니다.

| 시나리오 | 기대 결과와 확인 |
| --- | --- |
| Circuit 전체 목록 | ESSERC 2024–2028 모두 존재 |
| Circuit / 2026 | ESSERC·A-SSCC·ISICAS를 포함한 Circuit 6개만 노출 |
| 세 학회 상세·다운로드 | ESSERC 3개, A-SSCC 3개, ISICAS 8개 공개 이벤트를 실제 다운로드 |
| ISICAS 2026 상세·달력 | 여섯 저널 제목과 마감 모두 존재. ICS 제목·서로 다른 UID도 확인 |
| 2026-05-20 | 첫 마감과 마지막 마감 사이에 Upcoming & ongoing, 다음 일정은 TCAS-II |
| 2026-06-01 | 날짜만 알려진 마감 당일에 접수 종료로 판단하지 않음. Node 회귀 테스트 |
| 2026-06-02 | 모든 저널 마감이 확인되고 지났으므로 Submissions closed |
| 2026-06-02 + OJCAS TBA 응답 | Upcoming & ongoing 유지 |
| 2027 회차 개최일 TBA 응답 | 2026 과거 일정 참고에 여섯 저널 모두 표시 |
| 390px 모바일 상세 | 가로 넘침 없음 |

- [Circuit 필터](circuit-2026.png)
- [A-SSCC 상세](asscc-2026-detail.png)
- [ISICAS 전체 상세](isicas-2026-detail.png)
- [ISICAS 캘린더](isicas-2026-calendar.png)
- [두 마감 사이 접수 중 화면](isicas-between-deadlines.png)
- [브라우저 검사 결과 JSON](browser-checks.json)

`browser-check.cjs`는 실제 브라우저 검사 재현용 보조 스크립트입니다. 저장소 의존성은 추가하지 않았고 Playwright는 `/tmp`에, Chromium은 사용자 캐시에 설치한 검증 도구로만 사용했습니다. 로컬 사이트를 `http://127.0.0.1:4000/mms-deadlines/`에서 제공하고, 검증 도구의 모듈 경로를 지정하면 재실행할 수 있습니다.

```sh
NODE_PATH=/tmp/mms-browser/node_modules node docs/verification/asscc-isicas/browser-check.cjs
```

다른 주소는 `SITE_ORIGIN`으로 지정합니다. 이번 제한된 환경에서는 `/tmp`에 푼 브라우저 공유 라이브러리 경로도 `LD_LIBRARY_PATH`로 지정했습니다.

## 외부 수집 상태

내부 렌더링 오류는 없었습니다. 외부 자료 접근·구조 문제와 미발표/TBA는 `_data/sync_status.yml`과 회차별 `issues`에 남겼습니다.

- A-SSCC 2024: Xplore 자동 요청 응답에서 회차 제목을 확인하지 못했습니다. 공식 색인으로 확인한 개최 정보는 보정으로 유지하며, 확인하지 못한 제출·채택 발표는 TBA입니다.
- A-SSCC 2025: 초기 직접 요청은 403이었지만 실제 수집 요청은 성공했습니다. 공식 원본 HTML 회귀 샘플로 연장 마감을 추출하며 임시 보정은 제거했습니다.
- 기존 VLSI 2026–2028, CICC 2026 공식 URL 일부는 401/404, ESSERC 2025는 회차 제목 검증 실패를 반환했습니다. 기존 확인 값과 수동 보정을 보존했습니다.
- ISICAS 2025 채택 발표 등 확보하지 못한 값, 2027 제출 일정 등 미발표 값은 TBA입니다. 학회별 일반 초록 마감이 발표되지 않은 경우에도 기존 정책대로 확인 필요 상태를 유지합니다.
- 기존 공식 샘플의 CST 시간대 경고와 일부 외부 HTML의 문자 디코딩 경고가 발생했습니다. 이 작업에서 임의 시간대나 시각으로 보정하지 않았습니다.
