// ============================================================
// 설정 파일 (config.js)
// 이 파일 하나만 수정하면 지도 공급자, 광고, 데이터 파일을 바꿀 수 있습니다.
// ============================================================

const APP_CONFIG = {
  // ---- 지도 공급자 ----
  // "osm"   : Leaflet + OpenStreetMap. API 키 필요 없음. 완전 무료. 기본값.
  // "kakao" : 카카오맵 JavaScript SDK. 국내 주소/도로 표기가 더 정확하지만
  //           카카오 디벨로퍼스에서 무료 앱키 발급 및 도메인 등록이 필요합니다.
  //           (무료 쿼터: 지도 SDK 1일 300,000건 - 소규모 서비스에는 사실상 무료)
  MAP_PROVIDER: "osm",

  // 카카오맵 사용 시에만 필요. https://developers.kakao.com 에서 발급.
  KAKAO_APP_KEY: "YOUR_KAKAO_JAVASCRIPT_KEY",

  // ---- 데이터 파일 ----
  // 실제 서비스 시 data/bins.json (실 데이터)로 교체하고 아래 경로를 수정하세요.
  DATA_URL: "data/bins.json",

  // ---- 지도 초기 위치 (위치 접근 거부 시 기본값) ----
  DEFAULT_CENTER: { lat: 37.5665, lng: 126.9780 }, // 서울시청
  DEFAULT_ZOOM: 14,

  // ---- 목록에 표시할 최대 개수 ----
  MAX_LIST_ITEMS: 30,

  // ---- Google AdSense ----
  // 애드센스 승인 후 발급받은 client ID로 교체하세요. (예: "ca-pub-1234567890123456")
  // 승인 전에는 광고가 표시되지 않아도 정상입니다.
  ADSENSE_CLIENT: "ca-pub-XXXXXXXXXXXXXXXX",

  // ---- 위치 제보 (선택) ----
  // 무료 Google 설문지를 만들어 링크를 넣으면 사용자가 새 수거함 위치를 제보할 수 있습니다.
  REPORT_FORM_URL: "https://forms.gle/YOUR_FORM_ID"
};
