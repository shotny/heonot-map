#!/usr/bin/env python3
"""
공공데이터포털(data.go.kr) API에서 의류수거함 데이터를 가져와 data/bins.json을 갱신합니다.

사용법:
    python tools/fetch_data.py
    python tools/fetch_data.py --key YOUR_KEY

환경변수:
    DATA_GO_KR_KEY   API 키 (data.go.kr 마이페이지 > 인증키 발급현황)
"""

import argparse
import csv
import io
import json
import os
import re
import sys
import urllib.request
import urllib.parse
from datetime import date

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR   = os.path.join(SCRIPT_DIR, "..")
DATASETS_FILE = os.path.join(SCRIPT_DIR, "datasets.json")
OUT_FILE      = os.path.join(ROOT_DIR, "data", "bins.json")
ENV_FILE      = os.path.join(ROOT_DIR, ".env")


def load_dotenv(path):
    """.env 파일의 KEY=VALUE 줄을 환경변수로 로드 (이미 설정된 값은 덮어쓰지 않음)"""
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


load_dotenv(ENV_FILE)

# ── 컬럼명 매핑 ────────────────────────────────────────────────────────────
LAT_KEYS  = {"위도", "lat", "latitude", "y좌표", "y_coord", "wgs84위도", "y"}
LNG_KEYS  = {"경도", "lng", "lot", "longitude", "x좌표", "x_coord", "wgs84경도", "x"}
ADDR_KEYS = {"lctn_road_nm_addr", "lctn_lotno_addr", "소재지도로명주소", "소재지지번주소",
             "소재지주소", "address", "설치장소주소", "지번주소", "도로명주소", "소재지"}
NAME_KEYS = {"instl_plc_nm", "설치장소명", "명칭", "name", "설치장소", "수거함명",
             "설치위치", "위치명", "장소명", "dtl_pstn"}
GU_KEYS   = {"sgg_nm", "시군구명", "구", "gu", "자치구", "시군구", "구명"}
DONG_KEYS = {"dong", "행정동", "읍면동", "읍면동명", "동명", "동"}


def nk(s):
    return s.strip().lower().replace(" ", "").replace("_", "")


def find_col(keys, candidates):
    for cand in candidates:
        cn = nk(cand)
        for k in keys:
            if nk(k) == cn:
                return k
    # 부분 매치 (접두어)
    for cand in candidates:
        cn = nk(cand)
        for k in keys:
            if nk(k).startswith(cn) or cn.startswith(nk(k)):
                return k
    return None


def extract_gu_from_address(address):
    """구/시군 컬럼이 없는 데이터는 주소 두번째 토큰(예: '서울특별시 동작구 ...' → '동작구')에서 추출"""
    parts = address.split()
    if len(parts) < 2:
        return ""
    candidate = parts[1]
    return candidate if candidate.endswith(("구", "시", "군")) else ""


def parse_float(v):
    try:
        return float(str(v).strip().replace(",", ""))
    except (ValueError, TypeError):
        return None


def valid_coords(lat, lng):
    return lat and lng and (33.0 <= lat <= 38.9) and (124.0 <= lng <= 132.0)


def rows_to_bins(rows, start_idx=1, default_gu=""):
    bins = []
    idx  = start_idx
    for row in rows:
        keys  = list(row.keys())
        lat_k = find_col(keys, LAT_KEYS)
        lng_k = find_col(keys, LNG_KEYS)
        if not lat_k or not lng_k:
            continue

        lat = parse_float(row.get(lat_k))
        lng = parse_float(row.get(lng_k))
        if not valid_coords(lat, lng):
            continue

        addr_k = find_col(keys, ADDR_KEYS)
        name_k = find_col(keys, NAME_KEYS)
        gu_k   = find_col(keys, GU_KEYS)
        dong_k = find_col(keys, DONG_KEYS)

        address = str(row.get(addr_k, "")).strip() if addr_k else ""
        name    = str(row.get(name_k, "")).strip() if name_k else ""
        gu      = str(row.get(gu_k,   "")).strip() if gu_k   else ""
        dong    = str(row.get(dong_k, "")).strip() if dong_k else ""

        if not gu:
            gu = extract_gu_from_address(address) or default_gu

        if not name:
            name = f"{gu} {dong} 의류수거함".strip() or "의류수거함"

        bins.append({
            "id":      f"bin-{idx:05d}",
            "name":    name,
            "gu":      gu,
            "dong":    dong,
            "address": address,
            "lat":     lat,
            "lng":     lng,
        })
        idx += 1

    return bins, idx


# ── api.data.go.kr 표준 API (전국의류수거함표준데이터 등) ──────────────────

def fetch_standard_api(endpoint, service_key):
    """pageNo / numOfRows / type=JSON 방식의 표준 API"""
    NUM_ROWS = 1000
    page_no  = 1
    all_rows = []

    while True:
        params = urllib.parse.urlencode({
            "serviceKey": service_key,
            "pageNo":     page_no,
            "numOfRows":  NUM_ROWS,
            "type":       "JSON",
        })
        url = f"{endpoint}?{params}"

        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))

        # 응답 구조: response.body.items.item  또는  response.body.items (리스트)
        resp_body = body.get("response", body).get("body", {})
        items     = resp_body.get("items", {})
        if isinstance(items, dict):
            rows = items.get("item", [])
        elif isinstance(items, list):
            rows = items
        else:
            rows = []

        if not rows:
            break

        # 단일 결과일 때 dict로 오는 경우 처리
        if isinstance(rows, dict):
            rows = [rows]

        all_rows.extend(rows)

        total = int(resp_body.get("totalCount", 0))
        if len(all_rows) >= total:
            break
        page_no += 1

    return all_rows


# ── api.odcloud.kr REST API ───────────────────────────────────────────────

def fetch_odcloud(dataset_id, service_key):
    PER_PAGE = 1000
    page     = 1
    all_rows = []

    if "/v1/" in dataset_id:
        path = dataset_id
    else:
        path = f"{dataset_id}/v1/uddi:{dataset_id}"

    while True:
        params = urllib.parse.urlencode({
            "serviceKey": service_key,
            "page":       page,
            "perPage":    PER_PAGE,
            "returnType": "JSON",
        })
        url = f"https://api.odcloud.kr/api/{path}?{params}"

        with urllib.request.urlopen(url, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))

        rows = body.get("data", [])
        if not rows:
            break
        all_rows.extend(rows)

        total = int(body.get("totalCount") or body.get("matchCount") or 0)
        if len(all_rows) >= total:
            break
        page += 1

    return all_rows


# ── data.go.kr 개별 파일데이터(지자체별 CSV) ────────────────────────────────
# 표준 API(전국의류수거함표준데이터)에 없는 지자체는 data.go.kr에 개별 파일로만
# 등록된 경우가 많다. fileData.do 페이지를 그대로 파싱해 다운로드 URL을 얻는다.

FILE_DOWN_RE = re.compile(
    r"fn_fileDataDown\('([^']*)',\s*'([^']*)',\s*'([^']*)',\s*'([^']*)',\s*'([^']*)'\)"
)


def fetch_data_go_kr_file(public_data_pk):
    page_url = f"https://www.data.go.kr/data/{public_data_pk}/fileData.do"
    req = urllib.request.Request(page_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    matches = FILE_DOWN_RE.findall(html)
    if not matches:
        raise RuntimeError("다운로드 정보를 찾을 수 없음 (페이지 구조가 다르거나 파일형 데이터가 아님)")

    all_rows = []
    seen = set()
    for pk, detail_pk, _atch, file_detail_sn, _hist_sn in matches:
        if (detail_pk, file_detail_sn) in seen:
            continue
        seen.add((detail_pk, file_detail_sn))

        body = urllib.parse.urlencode({
            "publicDataDetailPk": detail_pk,
            "publicDataPk":       pk,
            "atchFileId":         "",
            "fileDetailSn":       file_detail_sn,
            "publicDataTyCode":   "PR0051",
        }).encode("utf-8")
        req2 = urllib.request.Request(
            "https://www.data.go.kr/tcs/dss/selectFileDataDownload.do",
            data=body,
            headers={
                "Content-Type":     "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
                "User-Agent":       "Mozilla/5.0",
                "Referer":          page_url,
            },
        )
        with urllib.request.urlopen(req2, timeout=30) as resp2:
            meta = json.loads(resp2.read().decode("utf-8"))
        atch_file_id = meta.get("atchFileId")
        if not atch_file_id:
            continue

        dl_url = "https://www.data.go.kr/cmm/cmm/fileDownload.do?" + urllib.parse.urlencode({
            "atchFileId":   atch_file_id,
            "fileDetailSn": file_detail_sn,
            "dataNm":       "data",
        })
        req3 = urllib.request.Request(dl_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req3, timeout=30) as resp3:
            raw = resp3.read()

        if raw[:2] == b"PK":
            # xlsx/zip - 이 스크립트는 CSV만 지원
            continue

        for enc in ("utf-8-sig", "cp949", "utf-8"):
            try:
                text = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            continue

        all_rows.extend(csv.DictReader(io.StringIO(text)))

    return all_rows


# ── CSV URL 직접 다운로드 ─────────────────────────────────────────────────

def fetch_csv_url(url):
    with urllib.request.urlopen(url, timeout=30) as resp:
        raw = resp.read()
    for enc in ("utf-8-sig", "cp949", "utf-8"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("인코딩 감지 실패")
    return list(csv.DictReader(io.StringIO(text)))


# ── 메인 ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="data.go.kr 의류수거함 데이터 자동 갱신")
    parser.add_argument("--key",      default=os.environ.get("DATA_GO_KR_KEY", ""))
    parser.add_argument("--datasets", default=DATASETS_FILE)
    parser.add_argument("--out",      default=OUT_FILE)
    args = parser.parse_args()

    with open(args.datasets, encoding="utf-8") as f:
        config = json.load(f)

    sources = [s for s in config.get("sources", []) if not s.get("disabled")]
    if not sources:
        print("오류: datasets.json에 sources가 없습니다.", file=sys.stderr)
        sys.exit(1)

    needs_key = any(s.get("type", "odcloud") in ("odcloud", "standard_api") for s in sources)
    if needs_key and not args.key:
        print("오류: API 키가 없습니다.", file=sys.stderr)
        print("  DATA_GO_KR_KEY 환경변수 또는 --key 옵션을 설정하세요.", file=sys.stderr)
        print("  data.go.kr 마이페이지 > 인증키 발급현황 에서 무료 발급 가능합니다.", file=sys.stderr)
        sys.exit(1)

    all_bins     = []
    idx          = 1
    source_names = []

    for src in sources:
        src_name = src.get("name", "Unknown")
        src_type = src.get("type", "odcloud")
        print(f"  [{src_type}] {src_name} ...", end=" ", flush=True)

        try:
            if src_type == "standard_api":
                rows = fetch_standard_api(src["endpoint"], args.key)
            elif src_type == "odcloud":
                rows = fetch_odcloud(src["dataset_id"], args.key)
            elif src_type == "csv_url":
                rows = fetch_csv_url(src["url"])
            elif src_type == "data_go_kr_file":
                rows = fetch_data_go_kr_file(src["id"])
            else:
                print(f"알 수 없는 type '{src_type}', 건너뜀")
                continue

            bins, idx = rows_to_bins(rows, idx, default_gu=src.get("region", ""))
            all_bins.extend(bins)
            print(f"{len(bins)}개")
            source_names.append(src_name)

        except Exception as e:
            print(f"실패 → {e}")

    if not all_bins:
        print("\n경고: 수집된 데이터가 없습니다.", file=sys.stderr)
        print("  - API 키가 올바른지 확인하세요.", file=sys.stderr)
        print("  - data.go.kr에서 해당 데이터셋 활용신청을 완료했는지 확인하세요.", file=sys.stderr)
        sys.exit(1)

    result = {
        "updated_at": str(date.today()),
        "source":     ", ".join(source_names),
        "bins":       all_bins,
    }

    out_path = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n완료: 총 {len(all_bins)}개 수거함 → {out_path}")


if __name__ == "__main__":
    main()
