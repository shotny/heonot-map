const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', headless: true });
  const context = await browser.newContext({
    geolocation: { latitude: 37.5006, longitude: 127.0364 }, // 강남구 역삼동 근처
    permissions: ['geolocation']
  });
  const page = await context.newPage();

  const consoleErrors = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });
  page.on('pageerror', (err) => consoleErrors.push('pageerror: ' + err.message));

  await page.goto('http://localhost:8933/index.html', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);

  const statusText = await page.textContent('#status-message');
  const resultCount = await page.textContent('#result-count');
  const listItemCount = await page.$$eval('#bin-list .bin-item', (els) => els.length);
  const firstDist = await page.$eval('#bin-list .bin-item .bin-dist', (el) => el.textContent).catch(() => null);
  const mapHasTiles = await page.$$eval('#map .leaflet-tile, #map img', (els) => els.length).catch(() => 0);

  // 검색 기능 테스트
  await page.fill('#search-input', '종로구');
  await page.waitForTimeout(300);
  const filteredCount = await page.$$eval('#bin-list .bin-item', (els) => els.length);
  await page.fill('#search-input', '');

  console.log(JSON.stringify({
    statusText,
    resultCount,
    listItemCount,
    firstDist,
    mapTileElements: mapHasTiles,
    filteredCountForJongno: filteredCount,
    consoleErrors
  }, null, 2));

  await browser.close();
})().catch((e) => {
  console.error('E2E test failed:', e);
  process.exit(1);
});
