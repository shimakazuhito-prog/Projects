#!/usr/bin/env python3
"""
data.js の各 program について、officialUrl と sourceUrls[] のすべてに HTTP GET し、
<title> / meta description / og:description を取得して official-meta.js を出力する。

ブラウザでは他ドメインを直接 fetch できない（CORS）ため、更新時はローカルで本スクリプトを実行する。
  python3 scripts/fetch_official_meta.py

必要に応じて各サイトの利用条件・robots.txt を確認すること。
certifi 推奨: python3 -m pip install certifi
"""
from __future__ import annotations

import json
import re
import ssl
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    import certifi

    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CTX = ssl.create_default_context()

ROOT = Path(__file__).resolve().parents[1]
DATA_JS = ROOT / "data.js"
OUT_JS = ROOT / "official-meta.js"

USER_AGENT = (
    "Mozilla/5.0 (compatible; VisitNursingSubsidyRef/1.0; +https://example.local; "
    "metadata-fetch-for-display)"
)
TIMEOUT_SEC = 45


def extract_programs_inner(text: str) -> str:
    key = "programs:"
    i = text.find(key)
    if i == -1:
        return ""
    i = text.find("[", i)
    if i == -1:
        return ""
    depth = 0
    for k in range(i, len(text)):
        if text[k] == "[":
            depth += 1
        elif text[k] == "]":
            depth -= 1
            if depth == 0:
                return text[i + 1 : k]
    return ""


def program_blocks(section: str) -> list[tuple[str, str]]:
    ms = list(re.finditer(r'\n\s*id:\s*"([^"]+)"', section))
    out: list[tuple[str, str]] = []
    for i, m in enumerate(ms):
        pid = m.group(1)
        a = m.start()
        b = ms[i + 1].start() if i + 1 < len(ms) else len(section)
        out.append((pid, section[a:b]))
    return out


def extract_urls_from_block(block: str) -> list[str]:
    urls: list[str] = []
    om = re.search(r'officialUrl:\s*"([^"]+)"', block)
    if om:
        urls.append(om.group(1))
    sm = re.search(r"sourceUrls:\s*\[", block)
    if sm:
        bracket_start = block.find("[", sm.start())
        depth = 0
        for k in range(bracket_start, len(block)):
            c = block[k]
            if c == "[":
                depth += 1
            elif c == "]":
                depth -= 1
                if depth == 0:
                    inner = block[bracket_start + 1 : k]
                    for u in re.findall(r'"([^"]+)"', inner):
                        if u.startswith("http://") or u.startswith("https://"):
                            if u not in urls:
                                urls.append(u)
                    break
    return urls


def parse_program_sources(data_js_text: str) -> list[tuple[str, list[str]]]:
    inner = extract_programs_inner(data_js_text)
    if not inner.strip():
        return []
    out: list[tuple[str, list[str]]] = []
    for pid, block in program_blocks(inner):
        urls = extract_urls_from_block(block)
        if urls:
            out.append((pid, urls))
    return out


class HeadParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._in_title = False
        self._title_parts: list[str] = []
        self.description: str | None = None
        self.og_description: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        ad = {k.lower(): (v or "") for k, v in attrs}
        if tag.lower() == "title":
            self._in_title = True
            self._title_parts = []
        elif tag.lower() == "meta":
            name = ad.get("name", "").lower()
            prop = ad.get("property", "").lower()
            content = ad.get("content", "").strip()
            if not content:
                return
            if name == "description" and self.description is None:
                self.description = content
            if prop == "og:description" and self.og_description is None:
                self.og_description = content

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)

    @property
    def title(self) -> str | None:
        t = "".join(self._title_parts).strip()
        return t or None


def fetch_meta(url: str) -> dict:
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "ja,en;q=0.8"})
    last_err: dict | None = None
    for _attempt in range(2):
        try:
            with urlopen(req, timeout=TIMEOUT_SEC, context=SSL_CTX) as resp:
                final_url = resp.geturl()
                raw = resp.read(400_000)
                ctype = resp.headers.get_content_charset() or "utf-8"
            return _parse_html(raw, ctype, final_url)
        except HTTPError as e:
            return {
                "ok": False,
                "error": f"HTTP {e.code}",
                "finalUrl": getattr(e, "url", url) or url,
            }
        except URLError as e:
            last_err = {"ok": False, "error": str(e.reason or e), "finalUrl": url}
        except TimeoutError:
            last_err = {"ok": False, "error": "timeout", "finalUrl": url}
        except Exception as e:
            last_err = {"ok": False, "error": str(e), "finalUrl": url}
    return last_err or {"ok": False, "error": "unknown", "finalUrl": url}


def _parse_html(raw: bytes, ctype: str, final_url: str) -> dict:
    try:
        text = raw.decode(ctype, errors="replace")
    except LookupError:
        text = raw.decode("utf-8", errors="replace")

    parser = HeadParser()
    try:
        parser.feed(text)
    except Exception:
        pass

    desc = parser.og_description or parser.description
    return {
        "ok": True,
        "error": None,
        "finalUrl": final_url,
        "pageTitle": parser.title,
        "description": desc[:800] if desc else None,
    }


def main() -> int:
    if not DATA_JS.is_file():
        print("Missing data.js", file=sys.stderr)
        return 1
    text = DATA_JS.read_text(encoding="utf-8")
    items = parse_program_sources(text)
    if not items:
        print("No programs with URLs found in data.js", file=sys.stderr)
        return 1

    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out: dict[str, object] = {
        "_meta": {
            "generatedAt": now,
            "source": "scripts/fetch_official_meta.py",
            "note": "複数URLからメタ情報のみ自動取得。全文ではない。最終確認は利用者の責任で各公式サイトへ。",
        }
    }

    for pid, urls in items:
        sources: list[dict] = []
        for u in urls:
            print(f"Fetching {pid} … {u}", file=sys.stderr)
            meta = fetch_meta(u)
            sources.append(
                {
                    "requestedUrl": u,
                    "finalUrl": meta.get("finalUrl"),
                    "pageTitle": meta.get("pageTitle"),
                    "description": meta.get("description"),
                    "ok": meta.get("ok", False),
                    "error": meta.get("error"),
                }
            )
        out[pid] = {"fetchedAt": now, "sources": sources}

    OUT_JS.write_text(
        "/* AUTO-GENERATED — 複数公式URLから取得したメタ情報。再生成: python3 scripts/fetch_official_meta.py */\n"
        "window.OFFICIAL_PAGE_META = "
        + json.dumps(out, ensure_ascii=False, indent=2)
        + ";\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUT_JS}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
