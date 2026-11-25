# Data Schema — ĐT05 (Tóm tắt tin tức kinh tế có kiểm chứng)

Tài liệu này mô tả tên trường, kiểu dữ liệu, tập giá trị hợp lệ và quy ước gắn nhãn của toàn bộ tệp dữ liệu trong dự án (theo Mục 5.1 và 5.2 hướng dẫn BTL CSC4007).

---

## 1. Dữ liệu nguồn gốc (`VLUS06/VietOnlineNews`)

Revision pin: `bd8d2a865c8981d34cb9d85f69f62bda7c40b520` (tổng 265.729 dòng; xem [`vietonline_news_schema.txt`](vietonline_news_schema.txt)).

| Trường | Kiểu | Mô tả |
|---|---|---|
| `id` | `string/int` | Định danh bài trong dataset gốc trên Hugging Face (`document_id`). |
| `title` | `string` | Tiêu đề bài báo gốc. |
| `description` | `string` | Đoạn sa-pô/mô tả ngắn gốc (**không dùng làm gold summary**). |
| `content` | `string` | Toàn văn thân bài gốc. |
| `category` | `string` | Chuyên mục gốc (13 lớp); ĐT05 chỉ lọc `Kinh doanh` và `Bất động sản`. |

---

## 2. `data/data_manifest.csv` (60 dòng, lưu cục bộ)

Tuân theo lược đồ chuẩn 13 cột của Mục 5.2:

| Cột | Kiểu | Giá trị hợp lệ / Quy ước |
|---|---|---|
| `item_id` | `string` | Khóa chính ổn định dạng `DT05-001` … `DT05-060`. |
| `document_id` | `string` | ID gốc từ `VLUS06/VietOnlineNews`. |
| `source_name` | `string` | Cố định `VLUS06/VietOnlineNews`. |
| `source_url` | `string` | `https://huggingface.co/datasets/VLUS06/VietOnlineNews`. |
| `source_version` | `string` | Hash revision Git của dataset trên Hub (`bd8d2a865c8981d34cb9d85f69f62bda7c40b520`). |
| `retrieved_at` | `ISO-8601` | Thời điểm tải snapshot: `2026-11-25T09:51:48+07:00`. |
| `published_at` | `string` | `unknown` (schema gốc không có ngày đăng; không suy ra từ ngày tải). |
| `language` | `string` | `vi`. |
| `original_category` | `string` | `Kinh doanh` hoặc `Bất động sản` (không đánh đồng với `task_label`). |
| `task_label` | `string` | `summary_reference_v1.0`. |
| `license_status` | `string` | `OTHER_UNVERIFIED` (chưa có giấy phép tái phân phối rõ ràng). |
| `split` | `enum` | `dev` (10 bài) hoặc `test` (50 bài). |
| `notes` | `string` | Chuỗi `key=value;` ghi `topic`, `n_facts`, `n_words`, `has_numbers`, `hf_split`. |

---

## 3. Dữ liệu xử lý (`data/processed/`, lưu cục bộ)

### 3.1 `selected_articles.jsonl` (60 dòng JSONL)

| Trường | Kiểu | Mô tả |
|---|---|---|
| `item_id` | `string` | Khóa chính `DT05-001` … `DT05-060`. |
| `document_id` | `string` | ID gốc từ VietOnlineNews. |
| `split` | `enum` | `dev` hoặc `test`. |
| `hf_split` | `enum` | Split gốc trên Hub (`train`, `validation`, `test`). |
| `category` | `string` | Chuyên mục gốc (`Kinh doanh` / `Bất động sản`). |
| `topic` | `enum` | Chủ đề gán bằng từ khóa: `vi_mo`, `tien_te_ngan_hang`, `chung_khoan`, `xuat_nhap_khau`, `doanh_nghiep`, `bat_dong_san`, `hang_hoa`, `khac`. |
| `title` | `string` | Tiêu đề sau làm sạch HTML và chuẩn hóa Unicode NFC. |
| `description` | `string` | Mô tả gốc sau làm sạch (chỉ tham khảo). |
| `content` | `string` | Thân bài sau làm sạch (250–900 từ). |
| `n_words` | `int` | Số từ trong `content`. |
| `n_facts` | `int` | Số ứng viên `FACT_RE` trích từ `content`. |
| `has_numbers` | `bool` | `true` nếu `n_facts >= 4`; `false` nếu bài ít/không có số liệu (12 bài: 2 dev, 10 test). |
| `cross_review_required` | `bool` | Cờ đánh dấu 25% mẫu cần người thứ hai hậu kiểm chéo. |
| `content_md5` | `string` | MD5 của `content` chuẩn hóa để kiểm tra toàn vẹn/trùng lặp. |

### 3.2 `numeric_facts_audit.csv`

Chứa các ứng viên số liệu thô trích bằng `FACT_RE` từ 60 bài để hỗ trợ kiểm tra ngữ cảnh (`item_id`, `split`, `topic`, `raw`, `value`, `unit`, `context`).

---

## 4. Dữ liệu đánh giá (`data/annotations/` và `data/splits/`)

### 4.1 `gold_summaries.csv` (60 dòng, lưu cục bộ)

| Cột | Kiểu | Giá trị hợp lệ / Quy ước |
|---|---|---|
| `item_id`, `document_id`, `split`, `title` | `string` | Khớp `data_manifest.csv` và `selected_articles.jsonl`. |
| `description_ref_NOT_GOLD` | `string` | Sa-pô gốc để đối chiếu chống chép nguyên văn. |
| `reference_summary` | `string` | Tóm tắt tham chiếu chuẩn hóa: 3–5 câu, khuyến nghị 50–120 từ, văn xuôi. |
| `draft_source` | `enum` | `human` hoặc `llm_edited` (bản nháp có LLM phải qua kiểm chứng từng số của người). |
| `annotator_id` | `enum` | `A1` (Cường) hoặc `A2` (Hoàng). |
| `reviewer_id` | `enum` | `A1` hoặc `A2`; bắt buộc khác `annotator_id` khi `review_status=reviewed`. |
| `review_status` | `enum` | `todo`, `annotated`, `reviewed`, `exclude`. |
| `guideline_version` | `string` | `v1.0` (đã khóa theo `guideline_lock.json`). |
| `cross_review_required` | `bool` | `True` / `False`. |
| `has_numbers` | `bool` | `True` / `False`. |
| `disagreement_note` | `string` | Ghi chú bất đồng nếu có. |

### 4.2 `gold_numeric_facts.csv` (220 dòng, lưu cục bộ)

Mỗi dòng tương ứng một dữ kiện định lượng xuất hiện trong `reference_summary`:

| Cột | Kiểu | Giá trị hợp lệ / Quy ước |
|---|---|---|
| `item_id`, `fact_id` | `string` | Mã bài và mã dữ kiện (`F1`, `F2`, ...), không trùng trong cùng bài. |
| `entity` | `string` | Chủ thể gắn với số liệu (doanh nghiệp, cơ quan, mặt hàng...). |
| `indicator` | `string` | Tên chỉ tiêu kinh tế/tài chính. |
| `value` | `string` | Giá trị số nguyên bản như trong bài nguồn (giữ dấu chấm hàng nghìn, phẩy thập phân). |
| `unit` | `string` | Đơn vị như trong bài nguồn (`%`, `tỷ đồng`, `triệu USD`, ...; trống nếu là số đếm). |
| `period` | `string` | Kỳ thời gian (`tháng 9/2025`, `năm`, ...) hoặc `unknown`. |
| `comparison_basis` | `string` | Cơ sở so sánh (`cùng kỳ`, `tháng trước`, ...; có thể trống). |
| `modality` | `enum` | `actual`, `estimate`, `forecast`, `target`, `proposal`, `planned`. |
| `source_sentence` | `string` | Trích nguyên văn một câu từ `content` chứa `value`. |
| `annotator_id` | `string` | `A1` hoặc `A2`. |
| `notes` | `string` | Ghi chú ngữ cảnh/đối chiếu. |

### 4.3 `review_log.csv` (lưu cục bộ)

| Cột | Kiểu | Giá trị hợp lệ |
|---|---|---|
| `item_id` | `string` | Mã bài được rà soát/loại. |
| `decision` | `enum` | `keep` hoặc `exclude`. |
| `reason` | `string` | Lý do giữ/loại. |
| `annotator_id`, `reviewer_id` | `string` | Hai mã khác nhau (`A1`/`A2`). |
| `disagreement` | `string` | Phân loại A (sai dữ kiện), B (chọn ý), C (diễn đạt) hoặc `none`. |
| `resolution` | `string` | Cách xử lý cuối cùng. |
| `guideline_version` | `string` | `v1.0`. |
| `reviewed_at` | `ISO-8601` | Thời điểm rà soát. |

### 4.4 `data/splits/`

- `dev_ids.txt`: 10 ID (1 bài/chủ đề cho 8 chủ đề chính + 2 bài bổ sung; gồm 8 `has_numbers=True`, 2 `has_numbers=False`).
- `test_ids.txt`: 50 ID khóa (40 `has_numbers=True`, 10 `has_numbers=False`).
- `split_history.json`: Nhật ký lần cập nhật split duy nhất trước khi gắn nhãn (`2026-11-25T10:14:05+07:00`).

---

## 5. Đầu ra thực nghiệm & đánh giá (`reports/`)

- `experiments.csv`: Nhật ký mọi lần chạy (`run_id`, `run_timestamp`, `experiment`, `split`, `method`, `model_id`, `run_label`, `prompt_version`, `temperature`, `api_endpoint`, `run_commit`, `protocol_tag`, `protocol_commit`, `config_tag`, `config_tag_commit`, `postcheck_policy`, ROUGE trước/sau hậu kiểm, số lượng & tỷ lệ khớp claim bề mặt, gold surface recall).
- `*_predictions_*.csv`: Kết quả từng bài (42 cột gồm ROUGE-1/2/L, claim bề mặt trước/sau và các cột đánh giá con người theo [`../evaluation_protocol.md`](../evaluation_protocol.md)).
- `*_numeric_claims_*.csv`: Danh sách chi tiết từng claim số trích ra và trạng thái đối chiếu bề mặt (`value_unit_match`, `value_unit_differs`, `value_only`, `not_found`).
- `human_eval_sheet.csv` & `numeric_error_table.csv`: Phiếu chấm rubric factuality (0–2) và bảng lỗi số liệu để rà soát thủ công.
- `metrics_summary.csv`: Bảng tổng hợp các chỉ số theo cấu hình và split.
