#!/usr/bin/env python3
"""
공공데이터포털(data.go.kr) API에서 의류수거함 데이터를 가져와 data/bins.json을 갱신합니다.

사용법:
    python tools/fetch_data.py
    python tools/fetch_data.py --key YOUR_KEY --datasets tools/datasets.json --out data/bins.json

환경변수:
    DATA_GO_KR_KEY   API 키 (--key 보다 우선)
"""

import argparse
import csv
import io
import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import date

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.join(SCRIPT_DIR, "..")
DATASETS_FILE = os.path.join(SCRIPT_DIR, "datasets.json")
OUT_FILE = os.path.join(ROOT_DIR, "data", "bins.json")

LAT_KEYS  = {"위도", "lat", "latitude", "y좌표", "y_coord", "wgs84위도", "y", "위도(wgs84)"}
LNG_KEYS  = {"경도", "lng", "longitude", "x좌표", "x_coord", "wgs84경도", "x", "경도(wgs84)"}
ADDR_KEYS = {"주소", "address", "소재지주소", "소재지도로명주소", "소재지지번주소", "설치장소주소", "지번주소", "도로명주소", "소재지"}
NAME_KEYS = {"명칭", "name", "설치장소", "수거함명", "설치위치", "위치명", "장소명"}
GU_KEYS   = {"구", "gu", "자치구", "시군구", "시군구명", "구명"}
DONG_KEYS = {"동", "dong", "행정동", "읍면동", "읍면동명", "동명"}


def nk(s):
    return s.strip().lower().replace(" ", "").replace("_", "")


def find_col(keys, candidates):
    for cand in candidates:
        cn = nk(cand)
        for k in keys:
            if nk(k) == cn or nk(k).startswith(cn):
                return k
    return None


def parse_float(v):
    try:
        return float(str(v).strip().replace(",", ""))
    except (ValueError, TypeError):
        return None


def valid_coords(lat, lng):
    return lat and lng and (33.0 <= lat <= 38.9) and (124.0 <= lng <= 132.0)


def rows_to_bins(rows, start_idx=1):
    bins = []
    idx = start_idx
    for row in rows:
        keys = list(row.keys())

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


# ── odcloud REST API ────────────────────────────────────────────────────────

def odcloud_url(dataset_id, service_key, page, per_page):
    # dataset_id가 'full/path/v1/uddi:xxx' 형태면 그대로, 숫자만이면 추측
    if "/v1/" in dataset_id:
        path = dataset_id
    else:
        path = f"{dataset_id}/v1/uddi:{dataset_id}"
    params = urllib.parse.urlencode({
        "serviceKey": service_key,
        "page":       page,
        "perPage":    per_page,
        "returnType": "JSON",
    })
    return f"https://api.odcloud.kr/api/{path}?{params}"


def fetch_odcloud(dataset_id, service_key):
    PER_PAGE = 1000
    page = 1
    all_rows = []

    while True:
        url = odcloud_url(dataset_id, service_key, page, PER_PAGE)
        with urllib.request.urlopen(url, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))

        rows = body.get("data", [])
        if not rows:
            break
        all_rows.extend(rows)

        total = body.get("totalCount") or body.get("matchCount") or 0
        if len(all_rows) >= int(total):
            break
        page += 1

    return all_rows


# ── CSV URL 직접 다운로드 ────────────────────────────────────────────────────

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

    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


# ── 메인 ────────────────────────────────────────────────────────────────────

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

    # odcloud 방식은 API 키 필요
    needs_key = any(s.get("type", "odcloud") == "odcloud" for s in sources)
    if needs_key and not args.key:
        print("오류: DATA_GO_KR_KEY 환경변수 또는 --key 옵션으로 API 키를 지정하세요.", file=sys.stderr)
        print("       data.go.kr 마이페이지 > 인증키 발급현황에서 무료 발급 가능합니다.", file=sys.stderr)
        sys.exit(1)

    all_bins = []
    idx = 1
    source_names = []

    for src in sources:
        src_name = src.get("name", "Unknown")
        src_type = src.get("type", "odcloud")
        print(f"  [{src_type}] {src_name} ...", end=" ", flush=True)

        try:
            if src_type == "odcloud":
                rows = fetch_odcloud(src["dataset_id"], args.key)
            elif src_type == "csv_url":
                rows = fetch_csv_url(src["url"])
            else:
                print(f"알 수 없는 type: {src_type}, 건너뜀")
                continue

            bins, idx = rows_to_bins(rows, idx)
            all_bins.extend(bins)
            print(f"{len(bins)}개")
            source_names.append(src_name)

        except Exception as e:
            print(f"실패 → {e}")

    if not all_bins:
        print("\n경고: 수집된 데이터가 없습니다.", file=sys.stderr)
        print("  - datasets.json의 dataset_id가 정확한지 확인하세요.", file=sys.stderr)
        print("  - data.go.kr에서 해당 데이터셋의 활용신청이 승인되었는지 확인하세요.", file=sys.stderr)
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

    print(f"\n완료: 총 {len(all_bins)}개 수거함 데이터 → {out_path}")


if __name__ == "__main__":
    main()
