#!/usr/bin/env python3
"""Generate prefecture-portal-programs.js (46 prefs; Tokyo 13 is detailed in data.js)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "prefecture-portal-programs.js"

PREFS: list[tuple[str, str, str, list[str]]] = [
    ("01", "北海道", "https://www.pref.hokkaido.lg.jp/", []),
    ("02", "青森県", "https://www.pref.aomori.lg.jp/", []),
    ("03", "岩手県", "https://www.pref.iwate.jp/", []),
    ("04", "宮城県", "https://www.pref.miyagi.jp/", []),
    ("05", "秋田県", "https://www.pref.akita.lg.jp/", []),
    ("06", "山形県", "https://www.pref.yamagata.jp/", []),
    ("07", "福島県", "https://www.pref.fukushima.lg.jp/", []),
    ("08", "茨城県", "https://www.pref.ibaraki.jp/", []),
    ("09", "栃木県", "https://www.pref.tochigi.lg.jp/", []),
    ("10", "群馬県", "https://www.pref.gunma.jp/", []),
    ("11", "埼玉県", "https://www.pref.saitama.lg.jp/", []),
    ("12", "千葉県", "https://www.pref.chiba.lg.jp/", []),
    ("14", "神奈川県", "https://www.pref.kanagawa.jp/", ["https://www.kanagawa-seisha.or.jp/top/"]),
    ("15", "新潟県", "https://www.pref.niigata.lg.jp/", []),
    ("16", "富山県", "https://www.pref.toyama.jp/", []),
    ("17", "石川県", "https://www.pref.ishikawa.lg.jp/", []),
    ("18", "福井県", "https://www.pref.fukui.lg.jp/", []),
    ("19", "山梨県", "https://www.pref.yamanashi.jp/", []),
    ("20", "長野県", "https://www.pref.nagano.lg.jp/", []),
    ("21", "岐阜県", "https://www.pref.gifu.lg.jp/", []),
    ("22", "静岡県", "https://www.pref.shizuoka.jp/", []),
    ("23", "愛知県", "https://www.pref.aichi.jp/", []),
    ("24", "三重県", "https://www.pref.mie.lg.jp/", []),
    ("25", "滋賀県", "https://www.pref.shiga.lg.jp/", []),
    ("26", "京都府", "https://www.pref.kyoto.jp/", []),
    ("27", "大阪府", "https://www.pref.osaka.lg.jp/", ["https://www.osaka-sed-bank.jp/"]),
    ("28", "兵庫県", "https://web.pref.hyogo.lg.jp/", []),
    ("29", "奈良県", "https://www.pref.nara.jp/", []),
    ("30", "和歌山県", "https://www.pref.wakayama.lg.jp/", []),
    ("31", "鳥取県", "https://www.pref.tottori.lg.jp/", []),
    ("32", "島根県", "https://www.pref.shimane.lg.jp/", []),
    ("33", "岡山県", "https://www.pref.okayama.jp/", []),
    ("34", "広島県", "https://www.pref.hiroshima.lg.jp/", []),
    ("35", "山口県", "https://www.pref.yamaguchi.lg.jp/", []),
    ("36", "徳島県", "https://www.pref.tokushima.lg.jp/", []),
    ("37", "香川県", "https://www.pref.kagawa.lg.jp/", []),
    ("38", "愛媛県", "https://www.pref.ehime.jp/", []),
    ("39", "高知県", "https://www.pref.kochi.lg.jp/", []),
    ("40", "福岡県", "https://www.pref.fukuoka.lg.jp/", []),
    ("41", "佐賀県", "https://www.pref.saga.lg.jp/", []),
    ("42", "長崎県", "https://www.pref.nagasaki.jp/", []),
    ("43", "熊本県", "https://www.pref.kumamoto.jp/", []),
    ("44", "大分県", "https://www.pref.oita.jp/", []),
    ("45", "宮崎県", "https://www.pref.miyazaki.lg.jp/", []),
    ("46", "鹿児島県", "https://www.pref.kagoshima.jp/", []),
    ("47", "沖縄県", "https://www.pref.okinawa.jp/", []),
]

NOTE = (
    "訪問看護に限らず、中小企業・人材・IT・物価対策など県独自制度が別部局にある場合があります。"
    "医療法人・社会福祉法人は対象外の制度も多いため、各要領で確認してください。"
    "東京都（コード13）を選ぶ場合は、data.js の都・福祉局・保健局の詳細カードをあわせて参照してください。"
)


def summary_for(name: str) -> str:
    if name == "北海道":
        head = "道の公式ポータルです。"
    elif name.endswith("府"):
        head = "府の公式ポータルです。"
    else:
        head = "県の公式ポータルです。"
    return (
        head
        + "保健福祉部・福祉局などの組織名は自治体ごとに異なります。"
        "サイト内検索やメニューから「介護保険」「高齢者福祉」「障害福祉」「医療」「事業者」「助成・補助」などを辿り、"
        "訪問看護ステーション・介護・医療事業者向けの独自助成や公募を確認してください。"
    )


def tags_for(name: str) -> list[str]:
    if name == "北海道":
        return ["北海道", "道公式", "福祉・保健"]
    if name.endswith("府"):
        return [name, "府公式", "福祉・保健"]
    return [name, "県公式", "福祉・保健"]


def main() -> None:
    entries: list[str] = []
    for code, name, url, extras in PREFS:
        title = f"{name} 公式サイト（福祉・介護・事業者向け情報の入口）"
        extras_fmt = json.dumps(extras, ensure_ascii=False)
        if extras:
            extras_fmt = extras_fmt.replace("[", "[\n      ").replace("]", "\n    ]")
        block = f"""    {{
      id: "pref-portal-{code}",
      title: {json.dumps(title, ensure_ascii=False)},
      level: "prefecture",
      prefectureCode: "{code}",
      cityCodes: null,
      tags: {json.dumps(tags_for(name), ensure_ascii=False)},
      summary:
        {json.dumps(summary_for(name), ensure_ascii=False)},
      note: {json.dumps(NOTE, ensure_ascii=False)},
      officialUrl: "{url}",
      sourceUrls: {extras_fmt},
      lastVerified: "2026-04-04",
    }}"""
        entries.append(block)
    body = ",\n".join(entries)
    text = (
        "/**\n"
        " * 全都道府県のうち東京都以外（46件）の県庁・道庁・府庁公式入口。\n"
        " * data.js 読込後に programs へ連結される。再生成: python3 scripts/build_prefecture_portals.py\n"
        " */\n"
        '(function () {\n'
        '  "use strict";\n'
        "  var portals = [\n"
        f"{body}\n"
        "  ];\n"
        "  if (window.SUBSIDY_REFERENCE_DATA && Array.isArray(window.SUBSIDY_REFERENCE_DATA.programs)) {\n"
        "    window.SUBSIDY_REFERENCE_DATA.programs =\n"
        "      window.SUBSIDY_REFERENCE_DATA.programs.concat(portals);\n"
        "  }\n"
        "})();\n"
    )
    OUT.write_text(text, encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
