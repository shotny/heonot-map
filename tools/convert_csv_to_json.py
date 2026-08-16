#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
convert_csv_to_json.py
공공데이터포털에서 내려받은 지자체별 "의류수거함 위치현황" CSV 파일들을
사이트가 사용하는 data/bins.json 형식으로 합쳐줍니다.

사용법:
  python3 convert_csv_to_json.py 강남구.csv 종로구.csv 금천구.csv -o ../data/bins.json

CSV 컬럼명은 지자체마다 제각각이라(위도/경도/lat/lng/좌표Y 등) COLUMN_ALIASES 에서
자주 쓰이는 이름들을 매핑합니다. 목록에 없는 컬럼명이 있으면 이 딕셔너리에 추가하세요.

위도/경도가 없는 행은 --geocode 옵션과 카카오 REST API 키(KAKAO_REST_KEY 환경변수)를
사용해 도로명주소 -> 좌표 변환을 시도할 수 있습니다. (카카오 로컬 API 무료 쿼터: 1일 100,000건)
"""

import argparse
import csv
import json
import os
import sys
import urllib.request
import urllib.parse

COLUMN_ALIASES = {
    "name": ["수거함명", "명칭", "시설명", "관리번호", "수거함번호", "이름"],
    "gu": ["자치구", "구", "시군구", "구명"],
    "dong": ["행정동", "동", "법정동", "동명"],
    "address": [
        "소재지도로명주소", "도로명주소", "소재지지번주소", "지번주소",
        "주소", "설치장소", "소재지"
    ],
    "lat": ["위도", "lat", "LAT", "Y좌표", "y좌표", "위도(Y)"],
    "lng": ["경도", "lng", "lon", "LNG", "X좌표", "x좌표", "경도(X)"]
}

KAKAO_GEOCODE_URL = "https://dapi.kakao.com/v2/local/search/address.json"


def find_column(fieldnames, candidates):
    lowered = {f.strip().lower(): f for f in fieldnames}
    for cand in candidates:
        if cand.lower() in lowered:
            return lowered[cand.lower()]
    return None


def geocode_address(address, rest_key):
    if not rest_key or not address:
        return None, None
    try:
        url = KAKAO_GEOCODE_URL + "?" + urllib.parse.urlencode({"query": address})
        req = urllib.request.Request(url, headers={"Authorization": "KakaoAK " + rest_key})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        docs = data.get("documents") or []
        if not docs:
            return None, None
        return float(docs[0]["y"]), float(docs[0]["x"])
    except Exception as e:
        print("  geocode 실패: %s (%s)" % (address, e), file=sys.stderr)
        return None, None


def convert(files, geocode, rest_key):
    bins = []
    counter = 1
    for path in files:
        gu_guess = os.path.splitext(os.path.basename(path))[0]
        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            cols = {k: find_column(fieldnames, v) for k, v in COLUMN_ALIASES.items()}

            for row in reader:
                address = (row.get(cols["address"]) or "").strip() if cols["address"] else ""
                lat = row.get(cols["lat"]) if cols["lat"] else None
                lng = row.get(cols["lng"]) if cols["lng"] else None

                try:
                    lat = float(lat) if lat not in (None, "") else None
                    lng = float(lng) if lng not in (None, "") else None
                except ValueError:
                    lat, lng = None, None

                if (lat is None or lng is None) and geocode and address:
                    lat, lng = geocode_address(address, rest_key)

                if lat is None or lng is None:
                    print("  좌표 없음, 건너뜀: %s" % address, file=sys.stderr)
                    continue

                bins.append({
                    "id": "bin-%04d" % counter,
                    "name": (row.get(cols["name"]) if cols["name"] else None) or "의류수거함",
                    "gu": (row.get(cols["gu"]) if cols["gu"] else None) or gu_guess,
                    "dong": (row.get(cols["dong"]) if cols["dong"] else None) or "",
                    "address": address,
                    "lat": lat,
                    "lng": lng
                })
                counter += 1
    return bins


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv_files", nargs="+", help="변환할 CSV 파일 경로들")
    parser.add_argument("-o", "--output", default="data/bins.json", help="출력 JSON 경로")
    parser.add_argument("--geocode", action="store_true", help="좌표 없는 행을 카카오 API로 지오코딩")
    args = parser.parse_args()

    rest_key = os.environ.get("KAKAO_REST_KEY", "")
    if args.geocode and not rest_key:
        print("경고: --geocode 옵션을 쓰려면 KAKAO_REST_KEY 환경변수를 설정하세요.", file=sys.stderr)

    bins = convert(args.csv_files, args.geocode, rest_key)

    output = {
        "_readme": "convert_csv_to_json.py 로 생성됨. 데이터 정확성은 원본 공공데이터 출처를 따릅니다.",
        "updated_at": "",  # 배포 전 오늘 날짜(YYYY-MM-DD)로 채우세요
        "source": "공공데이터포털(data.go.kr) 지자체별 의류수거함 위치현황",
        "bins": bins
    }

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("완료: %d개 항목 -> %s" % (len(bins), args.output))


if __name__ == "__main__":
    main()
