// ============================================================
// app.js - 내 주변 헌옷수거함 지도
// 지도 렌더링(OSM/Leaflet 또는 카카오맵), 위치 기반 거리 계산,
// 목록/검색, 마커 표시를 담당합니다.
// ============================================================

(function () {
  "use strict";

  const state = {
    allBins: [],
    userLocation: null, // { lat, lng } or null
    map: null,
    provider: APP_CONFIG.MAP_PROVIDER,
    markers: [], // { marker, bin }
    kakaoMarkers: [],
    selectedId: null
  };

  const els = {};

  document.addEventListener("DOMContentLoaded", init);

  async function init() {
    cacheEls();
    bindUI();
    await loadData();
    try {
      await initMap();
    } catch (err) {
      console.error("지도 초기화 실패:", err);
      state.map = null;
      showMapError();
    }
    requestLocation(true);
  }

  function showMapError() {
    const container = document.getElementById("map");
    if (container) {
      container.innerHTML =
        '<div class="map-fallback">지도를 불러오지 못했습니다. 아래 목록에서 거리순으로 확인해주세요.</div>';
    }
  }

  function cacheEls() {
    els.list = document.getElementById("bin-list");
    els.status = document.getElementById("status-message");
    els.searchInput = document.getElementById("search-input");
    els.locateBtn = document.getElementById("locate-btn");
    els.resultCount = document.getElementById("result-count");
    els.dataUpdated = document.getElementById("data-updated");
    els.reportLink = document.getElementById("report-link");
  }

  function bindUI() {
    els.locateBtn.addEventListener("click", () => requestLocation(false));
    let _searchTimer;
    els.searchInput.addEventListener("input", () => {
      clearTimeout(_searchTimer);
      _searchTimer = setTimeout(renderList, 200);
    });
    if (APP_CONFIG.REPORT_FORM_URL && els.reportLink) {
      els.reportLink.href = APP_CONFIG.REPORT_FORM_URL;
    }
  }

  // ---------------- 데이터 로드 ----------------
  async function loadData() {
    setStatus("수거함 데이터를 불러오는 중...");
    try {
      const res = await fetch(APP_CONFIG.DATA_URL, { cache: "no-store" });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const json = await res.json();
      state.allBins = (json.bins || []).filter(
        (b) => typeof b.lat === "number" && typeof b.lng === "number"
      );
      if (els.dataUpdated && json.updated_at) {
        els.dataUpdated.textContent = "데이터 기준일: " + json.updated_at;
      }
      setStatus(state.allBins.length + "개의 수거함 데이터를 불러왔습니다.");
    } catch (err) {
      console.error(err);
      setStatus("데이터를 불러오지 못했습니다. 네트워크 연결을 확인하고 새로고침 해주세요.");
      state.allBins = [];
    }
  }

  // ---------------- 지도 초기화 ----------------
  async function initMap() {
    const center = APP_CONFIG.DEFAULT_CENTER;

    if (state.provider === "kakao" && window.kakao && window.kakao.maps) {
      const container = document.getElementById("map");
      state.map = new kakao.maps.Map(container, {
        center: new kakao.maps.LatLng(center.lat, center.lng),
        level: 5
      });
      return;
    }

    // 기본값: Leaflet + OpenStreetMap (API 키 불필요)
    if (typeof L === "undefined") {
      throw new Error("Leaflet(L)이 로드되지 않았습니다. 네트워크 연결 또는 CDN 차단 여부를 확인하세요.");
    }
    state.provider = "osm";
    state.map = L.map("map").setView([center.lat, center.lng], APP_CONFIG.DEFAULT_ZOOM);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(state.map);
  }

  // ---------------- 위치 요청 ----------------
  function requestLocation(silent) {
    if (!navigator.geolocation) {
      setStatus("이 브라우저는 위치 정보를 지원하지 않습니다. 검색으로 찾아보세요.");
      renderList();
      return;
    }
    setStatus("현재 위치를 확인하는 중...");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        state.userLocation = {
          lat: pos.coords.latitude,
          lng: pos.coords.longitude
        };
        panTo(state.userLocation, 6);
        addUserMarker(state.userLocation);
        setStatus("내 위치 기준 가까운 순으로 정렬했습니다.");
        renderList();
        renderMarkers();
      },
      (err) => {
        console.warn(err);
        if (!silent) {
          setStatus("위치 접근이 거부되었습니다. 검색창으로 지역(구/동)을 찾아보세요.");
        } else {
          setStatus("위치 접근 시 더 정확한 거리순 정렬을 볼 수 있어요. 검색으로도 찾을 수 있습니다.");
        }
        renderList();
        renderMarkers();
      },
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 60000 }
    );
  }

  function addUserMarker(loc) {
    if (!state.map) return;
    if (state.provider === "kakao") {
      const pos = new kakao.maps.LatLng(loc.lat, loc.lng);
      new kakao.maps.Marker({
        map: state.map,
        position: pos,
        image: new kakao.maps.MarkerImage(
          "https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/marker_red.png",
          new kakao.maps.Size(24, 35)
        )
      });
    } else {
      L.circleMarker([loc.lat, loc.lng], {
        radius: 8,
        color: "#2563eb",
        fillColor: "#3b82f6",
        fillOpacity: 0.9
      })
        .addTo(state.map)
        .bindPopup("내 위치");
    }
  }

  function panTo(loc, level) {
    if (!state.map) return;
    if (state.provider === "kakao") {
      state.map.setCenter(new kakao.maps.LatLng(loc.lat, loc.lng));
      if (level) state.map.setLevel(level);
    } else {
      state.map.setView([loc.lat, loc.lng], APP_CONFIG.DEFAULT_ZOOM);
    }
  }

  // ---------------- 거리 계산 (Haversine) ----------------
  function distanceMeters(a, b) {
    const R = 6371000;
    const toRad = (d) => (d * Math.PI) / 180;
    const dLat = toRad(b.lat - a.lat);
    const dLng = toRad(b.lng - a.lng);
    const lat1 = toRad(a.lat);
    const lat2 = toRad(b.lat);
    const h =
      Math.sin(dLat / 2) ** 2 +
      Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(h));
  }

  function formatDistance(m) {
    if (m < 1000) return Math.round(m) + "m";
    return (m / 1000).toFixed(1) + "km";
  }

  // ---------------- 목록/검색 렌더링 ----------------
  function getFilteredSorted() {
    const keyword = (els.searchInput.value || "").trim().toLowerCase();
    let bins = state.allBins;

    if (keyword) {
      bins = bins.filter((b) => {
        const hay = [b.name, b.address, b.gu, b.dong].join(" ").toLowerCase();
        return hay.includes(keyword);
      });
    }

    if (state.userLocation) {
      bins = bins
        .map((b) => ({ ...b, _dist: distanceMeters(state.userLocation, b) }))
        .sort((x, y) => x._dist - y._dist);
    } else {
      bins = bins.map((b) => ({ ...b, _dist: null }));
    }

    return bins.slice(0, APP_CONFIG.MAX_LIST_ITEMS);
  }

  function renderList() {
    const bins = getFilteredSorted();
    els.resultCount.textContent = bins.length + "개 표시 중";
    els.list.innerHTML = "";

    if (bins.length === 0) {
      const empty = document.createElement("li");
      empty.className = "empty";
      empty.textContent = "검색 결과가 없습니다. 다른 지역명(구/동)으로 검색해보세요.";
      els.list.appendChild(empty);
      renderMarkers(bins);
      return;
    }

    bins.forEach((bin) => {
      const li = document.createElement("li");
      li.className = "bin-item" + (bin.id === state.selectedId ? " selected" : "");
      li.dataset.id = bin.id;

      const distLabel = bin._dist != null ? formatDistance(bin._dist) : "-";
      const directionsUrl =
        "https://map.kakao.com/link/to/" +
        encodeURIComponent(bin.name || "수거함") +
        "," +
        bin.lat +
        "," +
        bin.lng;

      li.innerHTML =
        '<div class="bin-item-main">' +
        '<span class="bin-dist">' + distLabel + "</span>" +
        '<span class="bin-name">' + escapeHtml(bin.name || "의류수거함") + "</span>" +
        "</div>" +
        '<div class="bin-address">' + escapeHtml(bin.address || "") + "</div>" +
        '<a class="bin-directions" target="_blank" rel="noopener" href="' +
        directionsUrl +
        '">길찾기 &rarr;</a>';

      li.addEventListener("click", () => {
        state.selectedId = bin.id;
        panTo({ lat: bin.lat, lng: bin.lng }, 3);
        renderList();
      });

      els.list.appendChild(li);
    });

    renderMarkers(bins);
  }

  // ---------------- 지도 마커 렌더링 ----------------
  function renderMarkers(bins) {
    if (!state.map) return;
    bins = bins || getFilteredSorted();

    if (state.provider === "kakao") {
      state.kakaoMarkers.forEach((m) => m.setMap(null));
      state.kakaoMarkers = [];
      bins.forEach((bin) => {
        const marker = new kakao.maps.Marker({
          map: state.map,
          position: new kakao.maps.LatLng(bin.lat, bin.lng)
        });
        const info = new kakao.maps.InfoWindow({
          content:
            '<div style="padding:6px 10px;font-size:12px;">' +
            escapeHtml(bin.name || "의류수거함") +
            "</div>"
        });
        kakao.maps.event.addListener(marker, "click", () => {
          info.open(state.map, marker);
          state.selectedId = bin.id;
          renderList();
        });
        state.kakaoMarkers.push(marker);
      });
    } else {
      state.markers.forEach((m) => state.map.removeLayer(m.marker));
      state.markers = [];
      bins.forEach((bin) => {
        const marker = L.marker([bin.lat, bin.lng]).addTo(state.map);
        marker.bindPopup(escapeHtml(bin.name || "의류수거함") + "<br>" + escapeHtml(bin.address || ""));
        marker.on("click", () => {
          state.selectedId = bin.id;
          renderList();
        });
        state.markers.push({ marker, bin });
      });
    }
  }

  function setStatus(msg) {
    if (els.status) els.status.textContent = msg;
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
})();
