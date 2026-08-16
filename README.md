# 내 주변 헌옷수거함 찾기

사용자 위치 기준으로 가까운 헌옷수거함(의류수거함)을 지도/목록으로 보여주는 정적 웹사이트입니다.
서버·데이터베이스 없이 HTML/CSS/JS 파일만으로 동작하며, **운영 비용 0원**을 목표로 설계했습니다.

## 폴더 구성

```
heonot-map/
├── index.html          메인 화면 (지도 + 검색 + 목록)
├── about.html           이용안내 / 배출 가이드 / FAQ / 데이터 출처
├── privacy.html          개인정보처리방침
├── css/style.css
├── js/config.js         설정 파일 (지도 공급자, API 키, 광고 ID 등 여기만 수정하면 됨)
├── js/app.js             지도/위치/목록 로직
├── data/bins.sample.json 데모용 예시 데이터 (실 데이터 아님, 반드시 교체 필요)
└── tools/
    ├── convert_csv_to_json.py   공공데이터 CSV → 사이트용 JSON 변환 스크립트
    └── e2e_check.js             (개발자용) Playwright 자동 점검 스크립트
```

## 1. 실제 데이터 구하기

`data/bins.sample.json`은 화면 동작 확인용 예시일 뿐 실제 위치가 아닙니다. 실서비스 전에 반드시 교체하세요.

1. [공공데이터포털](https://www.data.go.kr)에서 "의류수거함" 또는 "헌옷수거함"으로 검색하면 지자체별로 흩어진 데이터를 찾을 수 있습니다. 확인된 예시:
   - [서울특별시 강남구_의류수거함 위치 현황](https://www.data.go.kr/data/15127131/fileData.do)
   - [서울특별시 종로구_의류수거함 위치현황](https://www.data.go.kr/data/15104622/fileData.do)
   - [서울특별시 금천구_의류수거함 위치현황](https://www.data.go.kr/data/15106679/fileData.do)
   - [경기도 의정부시_의류수거함 현황](https://www.data.go.kr/data/15127238/fileData.do)
   - 원하는 지역명 + "의류수거함"으로 검색해 추가 지자체 데이터를 계속 모으세요.
2. 각 데이터셋 페이지에서 CSV(또는 XLSX)를 다운로드합니다. **컬럼명이 지자체마다 다릅니다**(위도/경도, 소재지도로명주소 등 표기가 제각각이고, 일부는 좌표 없이 주소만 있음).
3. 다운로드한 파일들을 한 번에 변환:
   ```bash
   cd tools
   python3 convert_csv_to_json.py 강남구.csv 종로구.csv 금천구.csv -o ../data/bins.json
   ```
4. 좌표가 없는 행이 많다면(주소만 있는 경우) 카카오 지오코딩으로 자동 보완할 수 있습니다:
   ```bash
   export KAKAO_REST_KEY="발급받은_REST_API_키"
   python3 convert_csv_to_json.py 강남구.csv --geocode -o ../data/bins.json
   ```
   (카카오 REST API 키는 JavaScript 키와 별개로 [Kakao Developers](https://developers.kakao.com)에서 무료 발급, 지오코딩 무료 쿼터 1일 100,000건)
5. `js/config.js`의 `DATA_URL`을 `"data/bins.json"`으로 바꾸고, 생성된 JSON의 `updated_at` 값을 오늘 날짜로 채우세요.
6. **데이터 출처 표기**: 공공데이터는 대부분 공공누리 조건에 따라 출처 표시가 필요합니다. `about.html`에 이미 출처 안내 문구가 있으니, 실제 사용한 데이터셋 목록으로 구체화하세요.

XLSX 파일만 있다면 엑셀/구글시트에서 "CSV로 다운로드"한 뒤 위 스크립트를 사용하면 됩니다.

## 2. 지도 설정

기본값은 **Leaflet + OpenStreetMap**으로, API 키 발급이나 가입 없이 바로 동작합니다.

국내 지도 품질(도로명, 건물명, 검색 등)을 높이고 싶다면 카카오맵으로 전환할 수 있습니다:

1. [Kakao Developers](https://developers.kakao.com)에서 무료 회원가입 후 애플리케이션 생성, JavaScript 키 발급
2. 앱 설정 > 플랫폼 > Web에 배포 도메인(예: `https://아이디.github.io`, 테스트용 `http://localhost:포트`) 등록
3. `js/config.js`에서 `MAP_PROVIDER: "kakao"`, `KAKAO_APP_KEY: "발급받은_키"`로 수정
4. `index.html`에서 카카오맵 스크립트 주석을 해제 (파일 내 안내 주석 참고)

카카오맵 JS SDK 무료 쿼터는 1일 300,000건으로, 개인/소규모 서비스에서는 사실상 비용이 발생하지 않습니다. 트래픽이 크게 늘면 [카카오 쿼터 정책](https://developers.kakao.com/docs/latest/ko/getting-started/quota)을 확인하세요.

주의: 기본 OSM 타일 서버는 개인 사용 정책이 있어 트래픽이 매우 커지면 접근이 제한될 수 있습니다([Tile Usage Policy](https://operations.osmfoundation.org/policies/tiles/)). 트래픽이 커지면 카카오맵으로 전환하거나 상용 타일 제공업체([switch2osm.org/providers](https://switch2osm.org/providers/))로 바꾸는 것을 권장합니다.

## 3. 무료로 배포하기 (GitHub Pages)

1. GitHub에 새 저장소 생성 (Public)
2. 이 폴더 전체를 저장소에 push
   ```bash
   git init
   git add .
   git commit -m "내 주변 헌옷수거함 사이트"
   git branch -M main
   git remote add origin https://github.com/사용자명/저장소명.git
   git push -u origin main
   ```
3. 저장소 Settings > Pages > Source에서 `main` 브랜치, `/ (root)` 선택 후 저장
4. 몇 분 후 `https://사용자명.github.io/저장소명/`으로 접속 가능 (완전 무료, 카드 등록 불필요)

대안: Vercel, Netlify도 정적 사이트 무료 티어를 제공하며 GitHub 저장소만 연결하면 자동 배포됩니다.

카카오맵을 쓰는 경우, 배포 후 실제 도메인을 Kakao Developers 플랫폼 설정에 반드시 추가해야 지도가 표시됩니다.

## 4. Google AdSense로 수익화하기

1. 먼저 위 1~3단계로 사이트에 실제 데이터를 넣고 배포를 완료하세요. **콘텐츠가 지도 기능뿐이면 "콘텐츠 부족/가치 낮음" 사유로 심사에서 거절되기 쉽습니다.** `about.html`의 이용안내·FAQ처럼 실제 텍스트 콘텐츠를 충분히 포함해야 합니다(이미 기본 제공되어 있으니, 지역별 안내를 더 추가하면 좋습니다).
2. [Google AdSense](https://www.google.com/adsense/)에 가입하고 사이트 URL을 등록해 심사를 신청합니다. (심사는 보통 며칠~2주 정도 소요될 수 있습니다)
3. 승인 후 발급되는 `client ID`(예: `ca-pub-1234567890123456`)와 광고 슬롯 ID를 `index.html`의 주석 처리된 광고 코드와 `js/config.js`의 `ADSENSE_CLIENT`에 넣고 주석을 해제하세요. 광고 삽입 위치는 이미 `index.html`에 `ad-slot` 클래스로 표시해두었습니다(상단 배너, 목록 하단 인라인).
4. `privacy.html`에 기본 개인정보처리방침 템플릿이 포함되어 있습니다. 실제 서비스 운영자명/연락처로 수정한 뒤 게시하세요(애드센스는 개인정보처리방침 페이지 존재를 요구합니다).

## 5. 위치 제보(크라우드소싱) 기능 (선택)

무료 [Google 설문지](https://forms.google.com)를 만들어 "지역/도로명주소/위도경도(선택)" 항목을 받고, 그 링크를 `js/config.js`의 `REPORT_FORM_URL`에 넣으면 사용자가 새 위치를 제보할 수 있습니다. 제출된 응답은 주기적으로 확인해 `data/bins.json`에 수동 반영하면 됩니다. (완전 자동화하려면 별도 백엔드가 필요하지만, 그 경우 무료 티어 이상 비용이 발생할 수 있어 기본 구성에는 포함하지 않았습니다.)

## 6. 로컬에서 테스트하기

```bash
cd heonot-map
python3 -m http.server 8000
# 브라우저에서 http://localhost:8000 접속
```

## 알아두어야 할 점

- 이 저장소에 포함된 `data/bins.sample.json`은 **개발/데모용 예시 데이터**이며 실제 수거함 위치가 아닙니다.
- 공공데이터는 지자체 갱신 주기에 따라 실제와 다를 수 있으므로, 정기적으로(예: 분기 1회) 원본 데이터를 다시 받아 갱신하는 것을 권장합니다.
- 위치 정보는 브라우저에서만 처리되고 서버로 전송되지 않도록 설계했습니다(`js/app.js` 참고).
- 전국 데이터를 모두 모으는 것은 지자체별로 흩어져 있어 시간이 걸립니다. 처음에는 거주 지역 등 일부 지자체부터 시작해 점차 확장하는 것을 추천합니다.
