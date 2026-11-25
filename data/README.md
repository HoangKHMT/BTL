# Tổ chức dữ liệu 3 tầng — ĐT05

Theo Mục 5.1 hướng dẫn BTL CSC4007 và quy định bản quyền (`license: other` trên `VLUS06/VietOnlineNews`), dữ liệu được tách thành 3 tầng:

1. **Tầng nguồn gốc (raw/references):**
   - Tham chiếu Hugging Face: `VLUS06/VietOnlineNews`, revision `bd8d2a865c8981d34cb9d85f69f62bda7c40b520`, `retrieved_at=2026-11-25T09:51:48+07:00`.
   - Danh sách ID ứng viên kinh tế có từ khóa số liệu: [`vietonline_news_economic_numeric_ids.txt`](vietonline_news_economic_numeric_ids.txt).
   - Schema gốc: [`vietonline_news_schema.txt`](vietonline_news_schema.txt).
   - Không lưu hoặc đẩy bản dump toàn văn gốc lên GitHub.

2. **Tầng dữ liệu xử lý (`processed/` — cục bộ, trong `.gitignore`):**
   - Tái tạo bằng `python data/prepare_data.py`.
   - `selected_articles.jsonl`: 60 bài đã làm sạch HTML/Unicode NFC và loại trùng.
   - `numeric_facts_audit.csv`: ứng viên số liệu trích bằng regex để hỗ trợ kiểm tra.
   - `data_manifest.csv`: manifest 60 bài theo lược đồ chuẩn 13 cột.

3. **Tầng dữ liệu đánh giá (`splits/` & `annotations/`):**
   - `splits/`: danh sách `dev_ids.txt` (10 bài) và `test_ids.txt` (50 bài) đã khóa, `split_history.json`, `selection_config.json`.
   - `annotations/`: hướng dẫn [`../annotation_guideline.md`](../annotation_guideline.md), bản khóa [`annotations/guideline_lock.json`](annotations/guideline_lock.json). Các tệp chứa văn bản/trích câu nguồn (`gold_summaries.csv`, `gold_numeric_facts.csv`, `pilot_drafts.csv`, `review_log.csv`) được giữ cục bộ theo `.gitignore`.

Xem chi tiết kiểu dữ liệu và giá trị hợp lệ tại [`data_schema.md`](data_schema.md).
