#!/usr/bin/env python3
"""
総務省「全国地方公共団体コード」Excel から municipalities.js を生成する。
- シート「R6.1.1現在の団体」「R6.1.1政令指定都市」をマージ（同一6桁コードは後シート優先）
- 出典URLは denshijiti/code.html の最新ファイル名に合わせて DOWNLOAD_URL を更新すること
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from urllib.request import urlretrieve

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "municipalities.js"
# ページ https://www.soumu.go.jp/denshijiti/code.html の最新 xlsx に差し替え
DOWNLOAD_URL = "https://www.soumu.go.jp/main_content/000925835.xlsx"


def load_sheet(wb: openpyxl.Workbook, name: str) -> dict[str, str]:
    ws = wb[name]
    out: dict[str, str] = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        code, _pref, city = row[0], row[1], row[2]
        if not code or city is None or str(city).strip() == "":
            continue
        s = str(code).strip().zfill(6)
        if len(s) != 6 or not s.isdigit():
            continue
        out[s] = str(city).strip()
    return out


def main() -> int:
    xlsx = Path("/tmp/soumu-municipality-codes.xlsx")
    if len(sys.argv) > 1:
        xlsx = Path(sys.argv[1])
    else:
        print("Downloading:", DOWNLOAD_URL, file=sys.stderr)
        urlretrieve(DOWNLOAD_URL, xlsx)

    wb = openpyxl.load_workbook(xlsx, read_only=True, data_only=True)
    merged = {**load_sheet(wb, "R6.1.1現在の団体"), **load_sheet(wb, "R6.1.1政令指定都市")}
    by_pref: dict[str, list[dict[str, str]]] = defaultdict(list)
    for code, name in merged.items():
        by_pref[code[:2]].append({"code": code, "name": name})
    for pc in by_pref:
        by_pref[pc].sort(key=lambda x: x["name"])
    obj = {k: by_pref[k] for k in sorted(by_pref.keys())}

    header = """/* AUTO-GENERATED — 全国地方公共団体コード（6桁）
 * 出典: 総務省 全国地方公共団体コードの一覧（ダウンロードデータ）
 * シート「R6.1.1現在の団体」と「R6.1.1政令指定都市」をマージ（同一コードは後者優先）
 * 再生成: python3 scripts/build-municipalities.py
 */
"""
    body = "window.MUNICIPALITY_BY_PREF = " + json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + ";\n"
    OUT.write_text(header + body, encoding="utf-8")
    total = sum(len(v) for v in obj.values())
    print(f"Wrote {OUT} ({len(obj)} prefs, {total} municipalities)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
