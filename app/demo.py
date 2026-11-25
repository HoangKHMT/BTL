#!/usr/bin/env python3
"""Interactive CLI and local Web UI demo for DT05 economic news summarization with numeric citations."""

from __future__ import annotations

import argparse
import html
import http.client
import ipaddress
import json
import os
import socket
import ssl
import sys
from dataclasses import dataclass
from email.message import Message
from http import HTTPStatus
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin, urlsplit, urlunsplit

import requests

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from check_gold import analyze, split_sentences, to_float  # noqa: E402
from evaluate import lead3, numeric_claims, source_surface_status  # noqa: E402
from run_ollama import (  # noqa: E402
    DEFAULT_MODEL,
    call_ollama,
    prompt_messages,
    retry_messages,
    unsupported_sentence_indexes,
)

DISCLAIMER = (
    "Lưu ý sử dụng: Đây là hệ thống minh họa nghiên cứu NLP (ĐT05), chỉ kiểm tra khớp bề mặt "
    "số/đơn vị với bài nguồn và KHÔNG thay thế kiểm chứng độc lập cho quyết định đầu tư, "
    "tín dụng hoặc chính sách."
)
MOCK_MODEL_ID = "MOCK-SYNTHETIC"

MAX_ARTICLE_HTML_BYTES = 2_000_000
MAX_ARTICLE_TEXT_CHARS = 100_000
MAX_ARTICLE_REDIRECTS = 5
ARTICLE_FETCH_TIMEOUT = 10
REDIRECT_STATUSES = {301, 302, 303, 307, 308}


def mock_summary_response(
    mode: str,
    messages: list[dict[str, str]],
) -> tuple[str, dict[str, Any]]:
    if mode == "E1":
        content = "MOCK-SYNTHETIC: Placeholder response; this is not an article summary."
    elif len(messages) > 2:
        content = (
            "MOCK-SYNTHETIC: Unsupported synthetic value 987654321%. "
            "MOCK-SYNTHETIC: Retry path completed."
        )
    else:
        content = "MOCK-SYNTHETIC: Synthetic numeric test 987654321%."
    return content, {"model": MOCK_MODEL_ID, "mock": True}


class ArticleFetchError(ValueError):
    """Raised when an article URL cannot be fetched or parsed safely."""


@dataclass(frozen=True)
class _ValidatedArticleURL:
    url: str
    scheme: str
    hostname: str
    port: int
    address: str
    target: str


def _validate_article_url(url: str) -> _ValidatedArticleURL:
    if not url or len(url) > 2048 or any(ord(char) < 32 for char in url) or "\\" in url:
        raise ArticleFetchError("URL bài báo không hợp lệ.")
    try:
        parsed = urlsplit(url.strip())
        port = parsed.port
    except ValueError as exc:
        raise ArticleFetchError("URL bài báo không hợp lệ.") from exc

    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"} or not parsed.hostname:
        raise ArticleFetchError("Chỉ hỗ trợ URL công khai bắt đầu bằng http:// hoặc https://.")
    if parsed.username is not None or parsed.password is not None:
        raise ArticleFetchError("Không hỗ trợ URL có thông tin đăng nhập.")

    hostname = parsed.hostname.rstrip(".").lower()
    if not hostname or hostname.endswith(
        (".localhost", ".local", ".internal", ".test", ".invalid", ".example")
    ) or hostname == "localhost":
        raise ArticleFetchError("URL phải trỏ tới một tên miền công khai.")
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        raise ArticleFetchError("Hãy dùng tên miền công khai thay vì địa chỉ IP.")

    try:
        hostname = hostname.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise ArticleFetchError("Tên miền trong URL không hợp lệ.") from exc

    expected_port = 443 if scheme == "https" else 80
    if port is not None and port != expected_port:
        raise ArticleFetchError("Chỉ hỗ trợ cổng HTTPS 443 và HTTP 80.")
    port = expected_port

    try:
        records = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise ArticleFetchError("Không phân giải được tên miền của bài báo.") from exc
    addresses = list(dict.fromkeys(record[4][0].split("%", 1)[0] for record in records))
    if not addresses:
        raise ArticleFetchError("Tên miền bài báo không có địa chỉ mạng hợp lệ.")
    try:
        parsed_addresses = [ipaddress.ip_address(address) for address in addresses]
    except ValueError as exc:
        raise ArticleFetchError("Tên miền bài báo trả về địa chỉ mạng không hợp lệ.") from exc
    if any(not address.is_global for address in parsed_addresses):
        raise ArticleFetchError("Không tải được URL trỏ tới địa chỉ mạng nội bộ.")

    netloc = hostname if port == expected_port else f"{hostname}:{port}"
    normalized_url = urlunsplit((scheme, netloc, parsed.path or "/", parsed.query, ""))
    target = quote(parsed.path or "/", safe="/%:@&=+$,!~*'();-._")
    if parsed.query:
        target += "?" + quote(parsed.query, safe="=&;%:@/?+$,!~*'()-._")
    return _ValidatedArticleURL(
        url=normalized_url,
        scheme=scheme,
        hostname=hostname,
        port=port,
        address=addresses[0],
        target=target,
    )


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, hostname: str, address: str, port: int) -> None:
        super().__init__(hostname, port=port, timeout=ARTICLE_FETCH_TIMEOUT)
        self._address = address

    def connect(self) -> None:
        self.sock = socket.create_connection((self._address, self.port), self.timeout)


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, hostname: str, address: str, port: int) -> None:
        super().__init__(
            hostname,
            port=port,
            timeout=ARTICLE_FETCH_TIMEOUT,
            context=ssl.create_default_context(),
        )
        self._address = address

    def connect(self) -> None:
        raw_socket = socket.create_connection((self._address, self.port), self.timeout)
        self.sock = self._context.wrap_socket(raw_socket, server_hostname=self.host)


def _request_article_page(
    article_url: _ValidatedArticleURL,
) -> tuple[int, str | None, str | None, bytes]:
    connection: http.client.HTTPConnection
    if article_url.scheme == "https":
        connection = _PinnedHTTPSConnection(
            article_url.hostname, article_url.address, article_url.port
        )
    else:
        connection = _PinnedHTTPConnection(
            article_url.hostname, article_url.address, article_url.port
        )

    try:
        connection.request(
            "GET",
            article_url.target,
            headers={
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Encoding": "identity",
                "User-Agent": "DT05-Article-Demo/1.0",
            },
        )
        response = connection.getresponse()
        location = response.getheader("Location")
        content_type = response.getheader("Content-Type")
        if response.status in REDIRECT_STATUSES:
            return response.status, location, content_type, b""
        if response.status != HTTPStatus.OK:
            raise ArticleFetchError(f"Trang bài báo trả về HTTP {response.status}.")
        if not content_type or content_type.split(";", 1)[0].strip().lower() not in {
            "text/html",
            "application/xhtml+xml",
        }:
            raise ArticleFetchError("URL không trả về trang HTML.")
        if response.getheader("Content-Encoding", "identity").lower() not in {
            "",
            "identity",
        }:
            raise ArticleFetchError("Trang dùng kiểu nén không được hỗ trợ.")
        content_length = response.getheader("Content-Length")
        if content_length:
            try:
                content_length_value = int(content_length)
            except ValueError as exc:
                raise ArticleFetchError("Trang trả về Content-Length không hợp lệ.") from exc
            if content_length_value < 0:
                raise ArticleFetchError("Trang trả về Content-Length không hợp lệ.")
            if content_length_value > MAX_ARTICLE_HTML_BYTES:
                raise ArticleFetchError("Trang HTML vượt giới hạn tải 2 MB.")
        body = response.read(MAX_ARTICLE_HTML_BYTES + 1)
        if len(body) > MAX_ARTICLE_HTML_BYTES:
            raise ArticleFetchError("Trang HTML vượt giới hạn tải 2 MB.")
        return response.status, location, content_type, body
    except (http.client.HTTPException, OSError, UnicodeError) as exc:
        raise ArticleFetchError(
            f"Không tải được trang bài báo ({type(exc).__name__})."
        ) from exc
    finally:
        connection.close()


class _ArticleHTMLParser(HTMLParser):
    _skip_tags = {
        "aside",
        "button",
        "footer",
        "form",
        "iframe",
        "nav",
        "noscript",
        "script",
        "style",
        "svg",
    }
    _block_tags = {
        "article",
        "br",
        "div",
        "h1",
        "h2",
        "h3",
        "li",
        "main",
        "p",
        "section",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._article_depth = 0
        self._main_depth = 0
        self._title_depth = 0
        self._h1_depth = 0
        self._meta_title = ""
        self._title_parts: list[str] = []
        self._h1_parts: list[str] = []
        self._body_parts: list[str] = []
        self._main_parts: list[str] = []
        self._article_parts: list[str] = []

    @staticmethod
    def _clean(parts: list[str]) -> str:
        return " ".join("".join(parts).split())

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._skip_depth:
            if tag in self._skip_tags:
                self._skip_depth += 1
            return
        if tag in self._skip_tags:
            self._skip_depth = 1
            return

        attributes = dict(attrs)
        if tag == "meta":
            key = (attributes.get("property") or attributes.get("name") or "").lower()
            if key in {"og:title", "twitter:title", "title"} and not self._meta_title:
                self._meta_title = (attributes.get("content") or "").strip()
        if tag == "article":
            self._article_depth += 1
        if tag == "main":
            self._main_depth += 1
        if tag == "title":
            self._title_depth += 1
        if tag == "h1":
            self._h1_depth += 1
        if tag in self._block_tags:
            self._body_parts.append("\n")
            if self._article_depth:
                self._article_parts.append("\n")
            if self._main_depth:
                self._main_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if self._skip_depth:
            if tag in self._skip_tags:
                self._skip_depth -= 1
            return
        if tag == "article" and self._article_depth:
            self._article_depth -= 1
        if tag == "main" and self._main_depth:
            self._main_depth -= 1
        if tag == "title" and self._title_depth:
            self._title_depth -= 1
        if tag == "h1" and self._h1_depth:
            self._h1_depth -= 1
        if tag in self._block_tags:
            self._body_parts.append("\n")
            if self._article_depth:
                self._article_parts.append("\n")
            if self._main_depth:
                self._main_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth or not data.strip():
            return
        if self._title_depth:
            self._title_parts.append(data)
        if self._h1_depth:
            self._h1_parts.append(data)
        self._body_parts.append(data)
        if self._article_depth:
            self._article_parts.append(data)
        if self._main_depth:
            self._main_parts.append(data)

    def extract(self) -> tuple[str, str]:
        title = (
            self._meta_title
            or self._clean(self._h1_parts)
            or self._clean(self._title_parts)
        )
        candidates = [
            self._clean(self._article_parts),
            self._clean(self._main_parts),
            self._clean(self._body_parts),
        ]
        content = next((text for text in candidates if len(text) >= 300), "")
        if not content:
            content = max(candidates, key=len)
        return title, content


def fetch_article_url(url: str) -> tuple[str, str, str]:
    current_url = url.strip()
    for redirects in range(MAX_ARTICLE_REDIRECTS + 1):
        validated_url = _validate_article_url(current_url)
        status, location, content_type, body = _request_article_page(validated_url)
        if status in REDIRECT_STATUSES:
            if not location:
                raise ArticleFetchError("Trang chuyển hướng nhưng không cung cấp URL đích.")
            if redirects == MAX_ARTICLE_REDIRECTS:
                raise ArticleFetchError("Trang chuyển hướng quá nhiều lần.")
            current_url = urljoin(validated_url.url, location)
            continue

        message = Message()
        message["content-type"] = content_type or "text/html; charset=utf-8"
        charset = message.get_content_charset() or "utf-8"
        try:
            page = body.decode(charset, errors="replace")
        except LookupError:
            page = body.decode("utf-8", errors="replace")
        parser = _ArticleHTMLParser()
        parser.feed(page)
        parser.close()
        title, content = parser.extract()
        if len(content) < 80:
            raise ArticleFetchError(
                "Không trích được nội dung bài viết. Trang có thể cần JavaScript, "
                "chặn truy cập tự động hoặc không phải bài báo HTML."
            )
        if len(content) > MAX_ARTICLE_TEXT_CHARS:
            raise ArticleFetchError("Nội dung trích xuất vượt giới hạn 100.000 ký tự.")
        return title, content, validated_url.url
    raise ArticleFetchError("Không tải được bài báo sau khi chuyển hướng.")


def find_source_citations(claim: dict[str, str], source_text: str) -> list[dict[str, Any]]:
    """Find sentences in source_text containing the claim's numeric value (and unit when possible)."""
    sentences = split_sentences(source_text)
    try:
        target_val = to_float(claim["value"])
    except ValueError:
        target_val = None

    exact_matches: list[dict[str, Any]] = []
    value_matches: list[dict[str, Any]] = []
    claim_unit = claim.get("unit", "").strip().lower()

    for idx, sent in enumerate(sentences, start=1):
        parsed = analyze(sent)
        sent_vals = (
            {to_float(x) for x in parsed["tokens"]}
            | {to_float(x) for x, _ in parsed["facts"]}
            | {to_float(x) for x, _ in parsed["dotdec"]}
        )
        if target_val is None or target_val not in sent_vals:
            continue
        fact_units = {
            u.lower()
            for v, u in parsed["facts"]
            if to_float(v) == target_val
        } | {
            u.lower()
            for v, u in parsed["dotdec"]
            if u and to_float(v) == target_val
        }
        entry = {"sentence_index": idx, "sentence": sent}
        if claim_unit and claim_unit in fact_units:
            exact_matches.append(entry)
        else:
            value_matches.append(entry)

    return exact_matches or value_matches


def summarize_and_verify(
    title: str,
    content: str,
    mode: str = "E0",
    model_id: str = DEFAULT_MODEL,
    temperature: float = 0.1,
    api_key: str | None = None,
    mock_api: bool = False,
) -> dict[str, Any]:
    """Summarize an economic news article and attach source-sentence citations per numeric claim."""
    clean_content = content.strip()
    if not clean_content:
        raise ValueError("Nội dung bài báo trống. Vui lòng nhập hoặc dán toàn văn thân bài.")

    warnings: list[str] = []
    article_words = len(clean_content.split())
    if article_words < 60:
        warnings.append(
            f"Bài viết ngắn ({article_words} từ < 60 từ), ngoài khoảng 250–900 từ của tập nghiên cứu; "
            "tóm tắt có thể thiếu ngữ cảnh."
        )
    elif article_words < 250 or article_words > 900:
        warnings.append(
            f"Độ dài bài viết ({article_words} từ) nằm ngoài khoảng 250–900 từ của tập dữ liệu BTL."
        )

    article = {"title": title.strip() or "(Không có tiêu đề)", "content": clean_content}
    retry_triggered = False
    dropped_sentences: list[str] = []
    summary_before = ""

    if mode == "E0":
        summary_after = lead3(clean_content)
        summary_before = summary_after
    elif mode in {"E1", "E2"}:
        messages = prompt_messages(mode, article)
        if mock_api:
            summary_before, _ = mock_summary_response(mode, messages)
        else:
            key = api_key or os.environ.get("OLLAMA_API_KEY")
            if not key:
                raise RuntimeError(
                    f"Chế độ {mode} cần biến môi trường OLLAMA_API_KEY. "
                    "Hãy chạy với --mode E0 (offline) hoặc cấu hình OLLAMA_API_KEY trong terminal."
                )
            summary_before, _ = call_ollama(key, model_id, temperature, messages)
        summary_after = summary_before
        if mode == "E2":
            bad_idx, bad_claims = unsupported_sentence_indexes(summary_before, clean_content)
            if bad_idx:
                retry_triggered = True
                messages = retry_messages(article, summary_before, bad_claims)
                if mock_api:
                    regenerated, _ = mock_summary_response(mode, messages)
                else:
                    regenerated, _ = call_ollama(
                        key, model_id, temperature, messages
                    )
                bad_after, _ = unsupported_sentence_indexes(regenerated, clean_content)
                regen_sents = split_sentences(regenerated)
                dropped_sentences = [
                    sent for i, sent in enumerate(regen_sents) if i in bad_after
                ]
                summary_after = " ".join(
                    sent for i, sent in enumerate(regen_sents) if i not in bad_after
                )
    else:
        raise ValueError(f"Chế độ không hợp lệ: {mode}")

    source_analysis = analyze(clean_content)
    claims = numeric_claims(summary_after)
    verified_claims: list[dict[str, Any]] = []
    unmatched_count = 0
    for claim in claims:
        status = source_surface_status(claim, source_analysis)
        if status in {"not_found", "value_unit_differs"}:
            unmatched_count += 1
        citations = find_source_citations(claim, clean_content)
        verified_claims.append(
            {
                **claim,
                "source_surface_status": status,
                "citations": citations,
            }
        )

    out_words = len(summary_after.split())
    out_sents = len(split_sentences(summary_after)) if summary_after else 0
    if out_words < 50 or out_words > 120:
        warnings.append(f"Độ dài tóm tắt ({out_words} từ) nằm ngoài khuyến nghị 50–120 từ.")
    if out_sents < 3 or out_sents > 5:
        warnings.append(f"Số câu tóm tắt ({out_sents} câu) nằm ngoài khuyến nghị 3–5 câu.")
    if unmatched_count > 0:
        warnings.append(
            f"Phát hiện {unmatched_count} phát biểu số liệu có cờ { '{not_found, value_unit_differs}' }; "
            "cần đối chiếu nguyên văn trước khi dùng."
        )
    if mock_api and mode in {"E1", "E2"}:
        warnings.append(
            "MOCK API: phản hồi giả lập để minh họa luồng xử lý; không phải bản tóm tắt thật."
        )

    return {
        "mode": mode,
        "model_id": (
            "Lead-3" if mode == "E0" else MOCK_MODEL_ID if mock_api else model_id
        ),
        "article_word_count": article_words,
        "summary_before_postcheck": summary_before,
        "summary": summary_after,
        "summary_word_count": out_words,
        "summary_sentence_count": out_sents,
        "retry_triggered": retry_triggered,
        "dropped_sentences": dropped_sentences,
        "claims": verified_claims,
        "warnings": warnings,
        "disclaimer": DISCLAIMER,
    }


def format_cli_report(result: dict[str, Any]) -> str:
    lines = [
        "=" * 72,
        f"CHẾ ĐỘ: {result['mode']} ({result['model_id']})",
        f"Độ dài bài nguồn: {result['article_word_count']} từ | "
        f"Tóm tắt: {result['summary_word_count']} từ, {result['summary_sentence_count']} câu",
        "=" * 72,
        "",
        "[TÓM TẮT]",
        result["summary"] or "(Trống sau hậu kiểm)",
        "",
    ]
    if result["mode"] == "E2" and result["retry_triggered"]:
        lines.extend(
            [
                "[HẬU KIỂM E2]",
                f"- Đã kích hoạt sinh lại 1 lần; số câu bị loại sau sinh lại: {len(result['dropped_sentences'])}",
                "",
            ]
        )
    lines.append("[KIỂM CHỨNG & CHÚ THÍCH NGUỒN CHO PHÁT BIỂU ĐỊNH LƯỢNG]")
    if not result["claims"]:
        lines.append("- Không phát hiện claim số liệu nào trong tóm tắt.")
    else:
        for i, c in enumerate(result["claims"], start=1):
            unit_disp = c["unit"] or "(không đơn vị)"
            lines.append(
                f"{i}. `{c['raw']}` [loại={c['claim_type']}, giá_trị={c['value']}, "
                f"đơn_vị={unit_disp}] -> trạng_thái={c['source_surface_status']}"
            )
            if c["citations"]:
                for cit in c["citations"][:2]:
                    lines.append(f"   ↳ Nguồn [Câu {cit['sentence_index']}]: {cit['sentence']}")
            else:
                lines.append("   ↳ Nguồn: KHÔNG TÌM THẤY CÂU CHỨA GIÁ TRỊ NÀY TRONG BÀI")
    if result["warnings"]:
        lines.append("")
        lines.append("[CẢNH BÁO]")
        for w in result["warnings"]:
            lines.append(f"! {w}")
    lines.extend(["", result["disclaimer"]])
    return "\n".join(lines)


def load_sample_article() -> tuple[str, str]:
    sample_path = Path(__file__).resolve().parent / "sample_input.txt"
    if not sample_path.exists():
        return ("", "")
    text = sample_path.read_text(encoding="utf-8").strip()
    lines = text.splitlines()
    if lines and lines[0].startswith("Tiêu đề:"):
        title = lines[0].removeprefix("Tiêu đề:").strip()
        body = "\n".join(lines[1:]).strip()
        return title, body
    return ("Bài mẫu tổng hợp", text)


def render_web_page(
    title: str = "",
    content: str = "",
    mode: str = "E0",
    result: dict[str, Any] | None = None,
    error: str | None = None,
    article_url: str = "",
    source_url: str = "",
    mock_api: bool = False,
) -> str:
    claims_html = ""
    if result is not None:
        postcheck_html = ""
        if result["mode"] == "E2":
            retry_label = "đã sinh lại một lần" if result["retry_triggered"] else "không cần sinh lại"
            precheck_summary = html.escape(result["summary_before_postcheck"])
            postcheck_html = (
                "<p class='meta'>Hậu kiểm E2: "
                f"{retry_label}; đã loại {len(result['dropped_sentences'])} câu.</p>"
                "<details><summary>Bản trước hậu kiểm</summary>"
                f"<p class='summary'>{precheck_summary}</p></details>"
            )
        rows = []
        for c in result["claims"]:
            status = c["source_surface_status"]
            badge_color = "#137333" if status == "value_unit_match" else ("#b06000" if status == "value_only" else "#c5221f")
            cit_html = (
                "<br>".join(
                    f"<strong>[Câu {cit['sentence_index']}]</strong> {html.escape(cit['sentence'])}"
                    for cit in c["citations"][:2]
                )
                if c["citations"]
                else "<em>Không tìm thấy câu nguồn khớp</em>"
            )
            rows.append(
                "<tr>"
                f"<td><code>{html.escape(c['raw'])}</code></td>"
                f"<td>{html.escape(c['claim_type'])}</td>"
                f"<td><span style='color:{badge_color};font-weight:600'>{html.escape(status)}</span></td>"
                f"<td>{cit_html}</td>"
                "</tr>"
            )
        claims_table = (
            "<table><thead><tr><th>Phát biểu số</th><th>Loại</th><th>Khớp bề mặt</th><th>Câu nguồn bảo chứng</th></tr></thead>"
            f"<tbody>{''.join(rows) if rows else '<tr><td colspan=4>Không có claim số liệu trong tóm tắt.</td></tr>'}</tbody></table>"
        )
        warn_html = (
            "<div class='warn'>" + "<br>".join(html.escape(w) for w in result["warnings"]) + "</div>"
            if result["warnings"]
            else ""
        )
        source_html = (
            "<p class='meta'>Nguồn bài báo: "
            f"<a href='{html.escape(source_url, quote=True)}' target='_blank' "
            f"rel='noopener noreferrer'>{html.escape(source_url)}</a></p>"
            if source_url
            else ""
        )
        claims_html = (
            "<section class='card'>"
            f"<h2>Kết quả tóm tắt ({html.escape(result['mode'])} — {html.escape(result['model_id'])})</h2>"
            f"{source_html}"
            f"{postcheck_html}"
            f"<p class='meta'>Bài nguồn: {result['article_word_count']} từ | "
            f"Tóm tắt: {result['summary_word_count']} từ, {result['summary_sentence_count']} câu</p>"
            f"<p class='summary'>{html.escape(result['summary'])}</p>"
            f"{warn_html}"
            "<h3>Chú thích nguồn cho phát biểu định lượng</h3>"
            f"{claims_table}"
            f"<p class='disclaimer'>{html.escape(result['disclaimer'])}</p>"
            "</section>"
        )

    err_html = f"<div class='error'>{html.escape(error)}</div>" if error else ""
    e1_label = (
        "E1 — Ollama Basic (Mock API)"
        if mock_api
        else "E1 — Ollama Basic (cần OLLAMA_API_KEY)"
    )
    e2_label = (
        "E2 — Ollama Numeric + Post-check (Mock API)"
        if mock_api
        else "E2 — Ollama Numeric + Post-check (cần OLLAMA_API_KEY)"
    )
    options = "".join(
        f"<option value='{m}' {'selected' if m == mode else ''}>{label}</option>"
        for m, label in [
            ("E0", "E0 — Lead-3 (Offline Baseline)"),
            ("E1", e1_label),
            ("E2", e2_label),
        ]
    )
    mode_descriptions = {
        "E0": "E0: lấy 3 câu đầu, chạy offline và không cần API key.",
        "E1": (
            "E1: phản hồi mô phỏng, không cần API key và không gọi Ollama."
            if mock_api
            else "E1: tóm tắt bằng Ollama với prompt cơ bản; cần OLLAMA_API_KEY."
        ),
        "E2": (
            "E2: phản hồi mô phỏng để kiểm tra hậu kiểm; không cần API key và không gọi Ollama."
            if mock_api
            else "E2: dùng prompt ưu tiên số liệu, thử sinh lại một lần nếu claim số không khớp rồi bỏ câu còn lỗi; cần OLLAMA_API_KEY."
        ),
    }
    mode_descriptions_json = json.dumps(mode_descriptions, ensure_ascii=False)
    privacy_note = (
        "E0 chạy cục bộ. E1/E2 đang ở chế độ MOCK API nên không gọi Ollama; URL bài báo vẫn được "
        "tải từ website bạn nhập."
        if mock_api
        else "E0 chạy cục bộ. E1/E2 gửi nội dung bài báo (kể cả nội dung tải từ URL) đến Ollama Cloud; "
        "chỉ dùng nội dung bạn có quyền xử lý. Nội dung trang ngoài có thể chứa thông tin không đáng tin, "
        "hãy rà soát trước khi dùng."
    )
    return f"""<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<title>Demo ĐT05 — Tóm tắt tin kinh tế có kiểm chứng dữ kiện</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; max-width: 960px; margin: 24px auto; padding: 0 16px; color: #202124; background: #f8f9fa; }}
  h1 {{ font-size: 1.4rem; margin-bottom: 4px; }}
  .card {{ background: #fff; border: 1px solid #dadce0; border-radius: 8px; padding: 16px; margin-top: 16px; }}
  label {{ display: block; font-weight: 600; margin-top: 12px; margin-bottom: 4px; }}
  input[type=text], textarea, select {{ width: 100%; box-sizing: border-box; padding: 8px; border: 1px solid #dadce0; border-radius: 6px; font-family: inherit; font-size: 0.95rem; }}
  textarea {{ min-height: 200px; }}
  button {{ margin-top: 12px; padding: 10px 18px; border: none; border-radius: 6px; background: #1a73e8; color: #fff; font-weight: 600; cursor: pointer; }}
  .secondary {{ background: #5f6368; margin-left: 8px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 0.9rem; }}
  th, td {{ border: 1px solid #dadce0; padding: 8px; text-align: left; vertical-align: top; }}
  th {{ background: #f1f3f4; }}
  .summary {{ background: #f1f8ff; padding: 12px; border-left: 4px solid #1a73e8; border-radius: 4px; line-height: 1.5; }}
  details {{ margin: 8px 0; }}
  summary {{ cursor: pointer; color: #5f6368; }}
  .warn {{ background: #fef7e0; border: 1px solid #fbbc04; padding: 10px; border-radius: 6px; margin: 10px 0; font-size: 0.9rem; }}
  .error {{ background: #fce8e6; border: 1px solid #c5221f; color: #c5221f; padding: 10px; border-radius: 6px; margin-top: 12px; }}
  .meta, .disclaimer {{ color: #5f6368; font-size: 0.85rem; }}
</style>
</head>
<body>
  <h1>ĐT05 — Tóm tắt tin tức kinh tế tiếng Việt có kiểm chứng dữ kiện</h1>
  <p class="meta">Nhập URL bài báo công khai hoặc dán nội dung để sinh tóm tắt và kiểm tra câu nguồn cho số liệu.</p>
  <form method="post" class="card">
    <label for="mode">Cấu hình tóm tắt</label>
    <select id="mode" name="mode">{options}</select>
    <p id="mode-help" class="meta"></p>
    <label for="article_url">Link bài báo (tùy chọn)</label>
    <input id="article_url" name="article_url" type="url" value="{html.escape(article_url)}"
      placeholder="https://example.com/bai-bao">
    <p class="meta">Nếu có URL, demo sẽ tải trang HTML và trích nội dung; URL được ưu tiên hơn phần nội dung dán bên dưới. Một số trang cần JavaScript, chặn truy cập tự động hoặc yêu cầu đăng nhập nên có thể không trích được.</p>
    <label for="title">Tiêu đề bài báo</label>
    <input id="title" name="title" type="text" value="{html.escape(title)}">
    <label for="content">Toàn văn thân bài</label>
    <textarea id="content" name="content">{html.escape(content)}</textarea>
    <button type="submit">Tóm tắt &amp; Kiểm chứng số liệu</button>
    <button type="submit" name="load_sample" value="1" class="secondary">Nạp bài mẫu tự soạn</button>
    <p class="meta">{html.escape(privacy_note)}</p>
  </form>
  {err_html}
  {claims_html}
  <script>
    const modeDescriptions = {mode_descriptions_json};
    const modeSelect = document.getElementById("mode");
    const modeHelp = document.getElementById("mode-help");
    function updateModeHelp() {{
      modeHelp.textContent = modeDescriptions[modeSelect.value] || modeDescriptions.E0;
    }}
    modeSelect.addEventListener("change", updateModeHelp);
    updateModeHelp();
  </script>
</body>
</html>"""


class DemoHandler(BaseHTTPRequestHandler):
    mock_api = False

    def do_GET(self) -> None:
        title, content = load_sample_article()
        body = render_web_page(
            title=title,
            content=content,
            mock_api=self.mock_api,
        ).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        from urllib.parse import parse_qs

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8", errors="replace")
        form = parse_qs(raw, keep_blank_values=True)
        mode = form.get("mode", ["E0"])[0]
        if form.get("load_sample"):
            title, content = load_sample_article()
            body = render_web_page(
                title=title,
                content=content,
                mode=mode,
                mock_api=self.mock_api,
            ).encode("utf-8")
        else:
            article_url = form.get("article_url", [""])[0].strip()
            source_url = ""
            try:
                if article_url:
                    title, content, source_url = fetch_article_url(article_url)
                else:
                    title = form.get("title", [""])[0]
                    content = form.get("content", [""])[0]
                result = summarize_and_verify(
                    title=title,
                    content=content,
                    mode=mode,
                    mock_api=self.mock_api,
                )
                body = render_web_page(
                    title=title,
                    content=content,
                    mode=mode,
                    result=result,
                    article_url=source_url or article_url,
                    source_url=source_url,
                    mock_api=self.mock_api,
                ).encode("utf-8")
            except (ValueError, RuntimeError, requests.RequestException) as exc:
                title = form.get("title", [""])[0]
                content = form.get("content", [""])[0]
                body = render_web_page(
                    title=title,
                    content=content,
                    mode=mode,
                    error=str(exc),
                    article_url=article_url,
                    mock_api=self.mock_api,
                ).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-file", type=Path, help="Path to UTF-8 text file containing article")
    parser.add_argument("--text", help="Direct article content string")
    parser.add_argument("--title", default="", help="Optional article title")
    parser.add_argument("--mode", choices=("E0", "E1", "E2"), default="E0")
    parser.add_argument("--model-id", default=DEFAULT_MODEL)
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    parser.add_argument("--serve", action="store_true", help="Run local HTTP web UI")
    parser.add_argument(
        "--mock-api",
        action="store_true",
        help="Use clearly labeled synthetic responses for E1/E2; never call Ollama",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if args.serve:
        DemoHandler.mock_api = args.mock_api
        server = ThreadingHTTPServer((args.host, args.port), DemoHandler)
        mode_note = " [MOCK API: E1/E2 synthetic]" if args.mock_api else ""
        print(
            f"Serving DT05 demo at http://{args.host}:{args.port}"
            f"{mode_note} (Ctrl+C to stop)"
        )
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")
        return

    title = args.title
    if args.input_file:
        raw_text = args.input_file.read_text(encoding="utf-8").strip()
        lines = raw_text.splitlines()
        if not title and lines and lines[0].startswith("Tiêu đề:"):
            title = lines[0].removeprefix("Tiêu đề:").strip()
            content = "\n".join(lines[1:]).strip()
        else:
            content = raw_text
    elif args.text:
        content = args.text
    elif not sys.stdin.isatty():
        content = sys.stdin.read()
    else:
        print("Dán bài báo (nhấn Ctrl-D để kết thúc):")
        content = sys.stdin.read()

    result = summarize_and_verify(
        title=title,
        content=content,
        mode=args.mode,
        model_id=args.model_id,
        temperature=args.temperature,
        mock_api=args.mock_api,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_cli_report(result))


if __name__ == "__main__":
    main()
