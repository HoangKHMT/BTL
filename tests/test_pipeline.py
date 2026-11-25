#!/usr/bin/env python3
"""Unit tests for CSC4007 DT05 evaluation, postcheck, config sync, and demo pipeline."""

from __future__ import annotations

import json
import socket
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))
sys.path.insert(0, str(ROOT_DIR / "app"))

import demo  # noqa: E402
import evaluate  # noqa: E402
import run_ollama  # noqa: E402
from check_gold import analyze  # noqa: E402


class PipelineTests(unittest.TestCase):
    def test_syllable_tokenizer_matches_protocol(self) -> None:
        tok = evaluate.SyllableTokenizer()
        tokens = tok.tokenize("GDP quý III/2026 tăng 3,2%, đạt 15,8 triệu tỷ đồng.")
        self.assertEqual(
            tokens,
            ["gdp", "quý", "iii", "2026", "tăng", "3", "2", "đạt", "15", "8", "triệu", "tỷ", "đồng"],
        )

    def test_attached_unit_surface_status_matches(self) -> None:
        source = "Khu đất rộng 30.000m2 nằm tại Tây Hồ, Hà Nội."
        source_analysis = analyze(source)
        claims = evaluate.numeric_claims("Dự án có diện tích 30.000 m2 tại Hà Nội.")
        statuses = [evaluate.source_surface_status(c, source_analysis) for c in claims]
        self.assertEqual(statuses, ["value_unit_match"])

    def test_unsupported_sentence_indexes_flags_hallucination(self) -> None:
        source = "Doanh thu quý I đạt 120 tỷ đồng, tăng 8,5% so với cùng kỳ."
        summary = "Doanh thu đạt 120 tỷ đồng. Lợi nhuận tăng 99% trong năm 2025."
        bad_idx, bad_claims = run_ollama.unsupported_sentence_indexes(summary, source)
        self.assertEqual(bad_idx, {1})
        self.assertEqual(bad_claims, ["99 %"])

    def test_gold_fact_recall_with_related_units(self) -> None:
        gold = {(200.0, "triệu đồng/năm"), (15.0, "%")}
        claims = evaluate.numeric_claims("Mức miễn thuế là 200 triệu đồng và thuế suất 15%.")
        matched, rate = evaluate.gold_fact_recall(claims, gold)
        self.assertEqual(matched, 2)
        self.assertEqual(rate, "1.000000")

    def test_configs_match_run_ollama_prompts_and_params(self) -> None:
        sample_article = {"title": "Tiêu đề mẫu", "content": "Nội dung mẫu."}
        e1_cfg = json.loads((ROOT_DIR / "configs/e1_basic_v1.json").read_text(encoding="utf-8"))
        e2_cfg = json.loads((ROOT_DIR / "configs/e2_numeric_v1.json").read_text(encoding="utf-8"))

        self.assertEqual(e1_cfg["model_id"], run_ollama.DEFAULT_MODEL)
        self.assertEqual(e1_cfg["prompt_version"], run_ollama.PROMPT_VERSIONS["E1"])
        self.assertEqual(e2_cfg["prompt_version"], run_ollama.PROMPT_VERSIONS["E2"])
        self.assertEqual(e2_cfg["postcheck_policy"], run_ollama.POSTCHECK_POLICY)

        e1_msgs = run_ollama.prompt_messages("E1", sample_article)
        self.assertEqual(e1_msgs[0]["content"], e1_cfg["prompt_template"]["system"])
        expected_e1_user = e1_cfg["prompt_template"]["user_format"].format(
            shared_constraints=e1_cfg["prompt_template"]["shared_constraints"],
            task=e1_cfg["prompt_template"]["task"],
            title=sample_article["title"],
            content=sample_article["content"],
        )
        self.assertEqual(e1_msgs[1]["content"], expected_e1_user)

        e2_msgs = run_ollama.prompt_messages("E2", sample_article)
        self.assertEqual(e2_msgs[0]["content"], e2_cfg["prompt_template"]["system"])
        expected_e2_user = e2_cfg["prompt_template"]["user_format"].format(
            shared_constraints=e2_cfg["prompt_template"]["shared_constraints"],
            task=e2_cfg["prompt_template"]["task"],
            title=sample_article["title"],
            content=sample_article["content"],
        )
        self.assertEqual(e2_msgs[1]["content"], expected_e2_user)

    def test_demo_e0_and_mocked_e2_postcheck(self) -> None:
        sample_text = (ROOT_DIR / "app/sample_input.txt").read_text(encoding="utf-8")
        lines = sample_text.splitlines()
        title = lines[0].removeprefix("Tiêu đề:").strip()
        body = "\n".join(lines[1:]).strip()

        res_e0 = demo.summarize_and_verify(title=title, content=body, mode="E0")
        self.assertEqual(res_e0["mode"], "E0")
        self.assertEqual(res_e0["summary_sentence_count"], 3)
        self.assertTrue(len(res_e0["claims"]) >= 3)
        self.assertTrue(all(c["citations"] for c in res_e0["claims"]))

        fake_responses = [
            (
                "Tín dụng tăng 11,2% sau 10 tháng. Lãi suất tăng lên 99% tại nhiều ngân hàng. CPI tăng 3,4%.",
                {"done": True},
            ),
            (
                "Tín dụng tăng 11,2% sau 10 tháng. Lãi suất tiết kiệm 12 tháng tại nhóm ngân hàng nhà nước giữ ở mức 4,7%/năm. CPI bình quân tăng 3,4%.",
                {"done": True},
            ),
        ]
        with patch.object(demo, "call_ollama", side_effect=fake_responses):
            res_e2 = demo.summarize_and_verify(
                title=title,
                content=body,
                mode="E2",
                api_key="dummy-test-key",
            )
        self.assertTrue(res_e2["retry_triggered"])
        self.assertEqual(res_e2["dropped_sentences"], [])
        self.assertIn("4,7%/năm", res_e2["summary"])

    def test_demo_e1_uses_cloud_generation_without_postcheck(self) -> None:
        fake_summary = (
            "Tín dụng tăng trong kỳ báo cáo. Lãi suất huy động thay đổi nhẹ. "
            "CPI vẫn trong phạm vi mục tiêu."
        )
        with patch.object(
            demo,
            "call_ollama",
            return_value=(fake_summary, {"model": "mock-model"}),
        ) as call:
            result = demo.summarize_and_verify(
                title="Tin kinh tế",
                content="Bài viết mẫu đủ nội dung để thử nghiệm chế độ tóm tắt.",
                mode="E1",
                model_id="mock-model",
                temperature=0.2,
                api_key="dummy-test-key",
            )

        call.assert_called_once()
        self.assertEqual(call.call_args.args[1:3], ("mock-model", 0.2))
        self.assertEqual(result["mode"], "E1")
        self.assertEqual(result["summary"], fake_summary)
        self.assertFalse(result["retry_triggered"])

    def test_demo_mock_api_runs_e1_and_e2_without_network(self) -> None:
        content = "Bài viết mẫu không chứa giá trị kiểm tra giả lập."
        with patch.object(
            demo,
            "call_ollama",
            side_effect=AssertionError("mock mode must not call Ollama"),
        ):
            result_e1 = demo.summarize_and_verify(
                title="Tin kinh tế",
                content=content,
                mode="E1",
                mock_api=True,
            )
            result_e2 = demo.summarize_and_verify(
                title="Tin kinh tế",
                content=content,
                mode="E2",
                mock_api=True,
            )

        self.assertEqual(result_e1["model_id"], "MOCK-SYNTHETIC")
        self.assertIn("MOCK-SYNTHETIC", result_e1["summary"])
        self.assertTrue(any("MOCK API" in warning for warning in result_e1["warnings"]))
        self.assertTrue(result_e2["retry_triggered"])
        self.assertEqual(len(result_e2["dropped_sentences"]), 1)
        self.assertNotIn("987654321", result_e2["summary"])
        page = demo.render_web_page(mode="E2", result=result_e2, mock_api=True)
        self.assertIn("Hậu kiểm E2: đã sinh lại một lần; đã loại 1 câu.", page)
        self.assertIn("Bản trước hậu kiểm", page)

    def test_demo_rejects_empty_input(self) -> None:
        with self.assertRaises(ValueError):
            demo.summarize_and_verify(title="Test", content="   ", mode="E0")

    def test_write_csv_atomic_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "out.csv"
            evaluate.write_csv_atomic(p, ["a", "b"], [{"a": "1", "b": "tiếng Việt"}])
            self.assertIn("tiếng Việt", p.read_text(encoding="utf-8-sig"))


class ArticleURLDemoTests(unittest.TestCase):
    @staticmethod
    def public_dns_record(port: int = 443) -> tuple:
            return (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("93.184.216.34", port),
            )

    def test_article_html_extracts_main_content_and_title(self) -> None:
            page = """
            <html><head><title>Tiêu đề trình duyệt</title>
            <meta property="og:title" content="Tin kinh tế hôm nay"></head>
            <body><nav>Liên kết điều hướng không phải nội dung.</nav>
            <main><article><h1>Tiêu đề bài</h1>
            <p>Doanh nghiệp công bố doanh thu quý gần nhất tăng trưởng so với cùng kỳ,
            đồng thời mở rộng hoạt động tại nhiều tỉnh thành. Bài viết phân tích thị trường,
            kế hoạch đầu tư, triển vọng sản xuất và các yếu tố ảnh hưởng đến kết quả kinh doanh.</p>
            </article></main><script>Không đưa nội dung script vào bài.</script></body></html>
            """
            parser = demo._ArticleHTMLParser()
            parser.feed(page)
            title, content = parser.extract()

            self.assertEqual(title, "Tin kinh tế hôm nay")
            self.assertIn("Doanh nghiệp công bố doanh thu", content)
            self.assertNotIn("Liên kết điều hướng", content)
            self.assertNotIn("script", content)

    def test_article_url_rejects_non_public_targets(self) -> None:
            invalid_urls = [
                "file:///C:/Windows/win.ini",
                "http://127.0.0.1/",
                "http://localhost/",
                "https://user:password@news-site.com/",
            ]
            for url in invalid_urls:
                with self.subTest(url=url), self.assertRaises(demo.ArticleFetchError):
                    demo._validate_article_url(url)

    def test_article_url_rejects_private_dns_results(self) -> None:
            private_record = (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("10.0.0.8", 443),
            )
            with patch.object(demo.socket, "getaddrinfo", return_value=[private_record]):
                with self.assertRaises(demo.ArticleFetchError):
                    demo._validate_article_url("https://news-site.com/")

    def test_article_url_revalidates_redirect_destination(self) -> None:
            with (
                patch.object(
                    demo.socket, "getaddrinfo", return_value=[self.public_dns_record()]
                ),
                patch.object(
                    demo,
                    "_request_article_page",
                    return_value=(302, "http://127.0.0.1/private", "text/html", b""),
                ) as request_page,
            ):
                with self.assertRaises(demo.ArticleFetchError):
                    demo.fetch_article_url("https://news-site.com/")
            request_page.assert_called_once()

    def test_article_url_fetch_extracts_page(self) -> None:
            page = (
                "<html><head><title>Trang tin</title></head><body><article>"
                "<p>Ngành sản xuất ghi nhận đơn hàng tăng trong quý vừa qua. "
                "Doanh nghiệp dự kiến mở rộng dây chuyền, tuyển thêm lao động và "
                "đẩy mạnh xuất khẩu trong các tháng tiếp theo.</p>"
                "</article></body></html>"
            ).encode("utf-8")
            with (
                patch.object(
                    demo.socket, "getaddrinfo", return_value=[self.public_dns_record()]
                ),
                patch.object(
                    demo,
                    "_request_article_page",
                    return_value=(200, None, "text/html; charset=utf-8", page),
                ),
            ):
                title, content, source_url = demo.fetch_article_url(
                    "https://news-site.com/story"
                )

            self.assertEqual(title, "Trang tin")
            self.assertIn("Ngành sản xuất ghi nhận", content)
            self.assertEqual(source_url, "https://news-site.com/story")

    def test_web_form_accepts_article_url_and_discloses_cloud_mode(self) -> None:
            page = demo.render_web_page()

            self.assertIn('id="article_url" name="article_url"', page)
            self.assertIn("E1/E2 gửi nội dung bài báo", page)
            self.assertIn('value=\'E1\'', page)
            self.assertIn('value=\'E2\'', page)
            self.assertIn('id="mode-help"', page)
            self.assertIn("E2: dùng prompt ưu tiên số liệu", page)
            mock_page = demo.render_web_page(mode="E2", mock_api=True)
            self.assertIn("E2 — Ollama Numeric + Post-check (Mock API)", mock_page)
            self.assertIn("không gọi Ollama", mock_page)
            self.assertNotIn("<div class='warn'><strong>MOCK API:", mock_page)


if __name__ == "__main__":
    unittest.main()
