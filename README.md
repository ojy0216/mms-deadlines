# Circuit / Algorithm Conference Deadlines

공식 학회 일정을 매일 확인하는 Jekyll 사이트입니다.

**사이트:** https://ojy0216.github.io/mms-deadlines/

- Circuit: ISSCC, VLSI (IEEE/JSAP Symposium on VLSI Technology & Circuits), CICC, ESSERC
- Algorithm: NeurIPS, ICLR, ICML, EMNLP, ECCV, ICCV
- 개최 연도 기준 올해와 이전 2개년, 그리고 공식 발표된 미래 회차를 포함합니다. 2026년에는 2024년부터 표시하며, 2027년부터 2024년 회차는 제외됩니다.
- 본 논문의 초록·제출·채택 발표, EMNLP ARR 제출·commitment, 개최 기간·장소를 추적합니다. Workshop, late-news, 별도 부가 트랙의 제출 일정은 포함하지 않습니다.

## 표시와 데이터 의미

목록은 Circuit / Algorithm, 학회명, 연도로 필터링합니다. 제출이 끝났어도 개최 전이면 예정 학회이며, 개최 종료 회차와 개최일 미정 회차를 별도로 표시합니다. 기존 `/conference/?id=iclr25` 형식의 상세 주소를 유지합니다.

정확한 시각과 시간대가 확인된 일정에만 카운트다운과 브라우저 현지 시간을 표시합니다. 날짜만 있는 일정은 임의로 자정이나 AoE 마감 시각을 붙이지 않습니다. 공식 HTML에 포함된 UTC 카운트다운 값도 출처의 명시적인 시각으로 사용합니다. `TBA`는 미발표 또는 확보하지 못한 과거 정보이며, 상세 화면의 확인 필요 사유를 함께 확인해야 합니다.

개최 기간은 공식 자료가 본 회의 날짜를 구분하면 그 기간을 사용합니다. 개최 기간만 발표한 경우에는 발표된 기간을 사용합니다. 개별 workshop 일정은 생성하지 않습니다. 여러 개최지가 있는 회차는 공식 자료에 따라 장소와 기간을 표시합니다.

목록, 상세, 캘린더 및 ICS는 `_data/conferences.yml`의 동일한 `events`를 사용합니다. 종일 일정의 ICS `DTEND`는 종료일 다음 날(배타적 종료)이며, 시간 일정은 UTC로 내보냅니다. TBA는 ICS에서 제외됩니다. 전체 구독 주소는 `/mms-deadlines/ai-deadlines.ics`, 개별 회차 다운로드는 `/mms-deadlines/calendar/<id>.ics`입니다.

## 최초 GitHub Pages 설정

1. 저장소 **Settings → Pages → Build and deployment → Source**를 **GitHub Actions**로 설정합니다. 사용자 정의 도메인은 비워 둡니다.
2. 기본 브랜치(`gh-pages`)에 `.github/workflows/sync.yml`을 포함합니다. 브랜치 이름을 변경하면 workflow의 `push.branches`도 변경합니다.
3. **Settings → Actions → General**에서 Actions 실행을 허용합니다. Workflow는 데이터 커밋용 `contents: write`, Pages 배포용 `pages: write`와 `id-token: write` 권한을 요청합니다. 브랜치 보호를 사용하는 경우 자동 데이터 커밋을 허용하는 정책이 필요합니다.
4. Actions에서 **Sync official conference schedules and deploy Pages → Run workflow**를 실행합니다. 최초 실행 시 `github-pages` 환경의 배포 승인 규칙이 있다면 승인합니다.
5. 성공한 실행의 **Deploy Pages** 단계가 제공하는 주소에서 사이트를 확인합니다.

설정은 `_config.yml`의 `url: https://ojy0216.github.io`, `baseurl: /mms-deadlines`를 사용합니다. 기존 upstream 도메인용 `CNAME`은 제거했습니다.

[GitHub Pages 게시 소스 설정](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)

## 매일 갱신 및 수동 Sync

매일 **00:00 KST = 전날 15:00 UTC** (`0 15 * * *`)에 기본 브랜치에서 실행합니다. GitHub의 예약 실행은 지연되거나 비활성화될 수 있으므로 실시간 갱신을 보장하지 않습니다.

사이트의 **Sync**는 GitHub Actions 실행 화면으로 연결됩니다. 저장소 쓰기 권한이 있는 사용자가 GitHub에 로그인한 후 **Run workflow**를 눌러 수동 갱신합니다. 사이트에 토큰을 넣거나 방문자에게 저장소 쓰기 권한을 부여하지 않습니다.

실행 순서:

1. 공식 자료 수집 (학회·출처별 실패 격리)
2. 데이터 검증 및 파서 회귀 테스트
3. Jekyll 빌드 및 내부 HTML/링크 검증
4. 검증된 데이터 커밋 및 일반 push
5. 같은 실행의 Pages artifact 업로드 및 명시적 배포

전체 데이터 검증, 테스트, 빌드, 내부 HTML 검증 또는 push가 실패하면 배포하지 않습니다. 일부 공식 사이트 접속 실패는 기존 값을 보존하고 확인 필요 상태를 남기며, 다른 학회의 정상 갱신을 막지 않습니다. 자동 커밋이 다른 Pages 실행을 유발한다고 가정하지 않습니다. Workflow 동시 실행은 `conference-pages` 그룹으로 직렬화하며 강제 push를 사용하지 않습니다.

[GitHub Actions 수동 실행](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow)

## 로컬 실행

Python 3.12 및 Ruby 3.1과 Bundler를 권장합니다. 별도 서버나 유료 LLM API는 필요하지 않습니다.

```sh
python3 -m venv .venv
.venv/bin/pip install -r utils/requirements.txt
bundle install
.venv/bin/python -m utils.collector.sync
.venv/bin/python -m utils.collector.sync --validate-only
.venv/bin/python -m unittest discover -s tests -v
bundle exec jekyll build --future
.venv/bin/python -m utils.validate_site
bundle exec htmlproofer ./_site --disable-external --check-favicon --check-html --url-swap '^/mms-deadlines/:/'
bundle exec jekyll serve --future
```

미리보기: http://localhost:4000/mms-deadlines/

외부 링크까지 확인하는 저장소의 기존 검증 명령은 다음과 같습니다. 실제 프로젝트 하위 경로를 로컬 출력과 연결하기 위해 `--url-swap`을 추가합니다.

```sh
bundle exec htmlproofer ./_site --only-4xx --check-favicon --check-html --url-ignore '/#.*/' --http-status-ignore '400,441' --url-swap '^/mms-deadlines/:/'
```

외부 사이트의 403/429, 접속 차단 및 일시 장애는 내부 렌더링 오류와 구분해서 기록합니다. 배포 게이트는 외부 사이트 장애 때문에 정상 사이트 배포까지 중단하지 않도록 내부 검증을 사용합니다.

`github-pages` gem은 고정된 Jekyll 의존성 집합으로 사용하되 `require: false`로 자동 로딩을 막습니다. 자동 로딩하면 safe mode가 로컬 JSON/ICS 생성기를 건너뛰므로, Actions가 직접 Jekyll을 빌드해야 합니다.

## 수집 경로 및 파서 유지보수

- `utils/sources.yml`: 공식 홈페이지, 연도별 Dates/CFP/PDF, 미래 행사 목록, 파서 규칙
- `utils/collector/parsers.py`: EventHosts 공통 파서, EMNLP 두 단계 제출, 공식 PDF/HTML 규칙, 미래 행사 목록
- `utils/collector/model.py`: 날짜 정밀도, 시간대 변환, 충돌/연장/override 병합 및 검증
- `utils/collector/sync.py`: 수집 실행, 실패 격리, rolling window, 파일 갱신
- `_data/conferences.yml`: 회차별 일정과 출처·확인 시각
- `_data/sync_status.yml`: 마지막 시도·성공 시각, 학회별 확인 필요 상태
- `_data/overrides.yml`: 수동 보정
- `tests/fixtures/`: 공식 HTML/PDF 회귀 샘플

URL의 연도만 바꿔 접속에 성공했다는 이유로 미래 회차를 만들지 않습니다. 공식 홈페이지의 연도 링크와 해당 회차 제목을 함께 검증하거나, 공식 미래 행사 목록의 명시적인 회차를 읽습니다. 발표됐지만 별도 사이트·날짜가 없는 회차도 TBA로 보존합니다. 공식 사이트 구조가 바뀌면 등록된 CSS 선택자/문구와 회귀 샘플을 갱신해야 합니다.

## 확인 필요 상태와 복구

1. 사이트의 **Collection health & official sources**, 해당 회차 상세, 또는 `_data/sync_status.yml`에서 실패 출처와 영향을 받은 일정을 확인합니다.
2. 공식 URL을 직접 열어 접속 문제, 문구/HTML 구조 변경, 연장 발표, 서로 다른 공식 자료의 충돌 여부를 구분합니다.
3. 접속 문제는 다음 예약 실행 또는 수동 Sync로 다시 확인합니다. 200 응답이어도 학회 제목·연도가 다르거나 PDF URL이 HTML 오류 페이지를 반환하면 성공으로 취급하지 않습니다.
4. 구조가 바뀌었다면 `utils/sources.yml`/파서를 수정하고 공식 샘플 회귀 테스트를 추가합니다. 변경된 날짜를 전년도 값으로 채우지 않습니다.
5. 공식 연장 공지는 명시적인 extension 규칙으로 반영합니다. 오래된 CFP가 나중에 수집되어도 이미 확인한 연장 날짜로 되돌리지 않습니다. 서로 충돌하는 새 발표 또는 파싱 실패는 기존 값을 유지하며 확인 필요 상태가 남습니다.
6. 긴급 보정은 아래 override를 사용합니다. 수정 후 데이터 검증, 테스트, 빌드 및 HTML 검증을 실행하고 수동 Sync를 다시 실행합니다.
7. 자동 push가 non-fast-forward로 실패하면 기본 브랜치 최신 변경을 확인한 후 workflow를 재실행합니다. 강제 push하지 않습니다.

## 수동 override

회차 ID 아래 `events`와 일정 종류를 지정합니다. 예시는 구조 설명용이며 실제 날짜는 반드시 공식 자료로 확인해야 합니다.

```yaml
iclr27:
  events:
    paper:
      date: '2026-09-25 23:59:59'
      precision: datetime
      timezone: UTC-12
      sources:
        - https://iclr.cc/Conferences/2027/Dates
      checked_at: '2026-09-07T00:00:00Z'
      reason: '공식 발표를 직접 확인한 보정 사유'
```

날짜만 확인했다면 `date: '2026-09-25'`, `precision: date`를 사용합니다. `precision: tba`는 `date: TBA`로 지정합니다. 자동 계산된 `utc`는 직접 작성할 필요가 없습니다. 출처, 확인 시각, 보정 사유를 누락하지 마세요. Override는 매 수집 후 마지막에 적용되므로 자동 파서가 덮어쓰지 않습니다.

현재 보정 파일에는 직접 접속이 불가능한 공식 ESSERC 2025 페이지의 연장 마감·결과 발표 시각과 VLSI 2027 페이지의 제출 마감이 있습니다. 공식 검색 색인에서 확인한 값이며 출처·확인 시각·사유를 기록했습니다. 직접 수집이 복구되면 공식 값과 대조한 뒤 해당 override를 제거합니다.

## 기여

변경 PR에는 공식 출처, 변경 전후 동작, 실행한 검증과 남은 외부 수집 실패를 적어 주세요. 화면을 변경하면 목록·상세·필터·카운트다운·캘린더·ICS를 `/mms-deadlines/`에서 확인하고 스크린샷을 첨부합니다. 기존 프로젝트의 LICENSE를 유지합니다.
