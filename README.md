# ĐT05 – Tóm tắt tin tức kinh tế tiếng Việt có kiểm chứng dữ kiện

Bài tập lớn học phần **CSC4007 – Xử lý ngôn ngữ tự nhiên** (năm học 2026–2027).

- **Nhóm thực hiện:** Cường (`A1`), Hoàng (`A2`)
- **Đề tài:** ĐT05 – Tóm tắt tin tức kinh tế có kiểm chứng
- **Đầu vào → Đầu ra:** Bài báo kinh tế tiếng Việt (`title`, `content`) → bản tóm tắt 3–5 câu (50–120 từ) bảo toàn chủ thể, số liệu, đơn vị, mốc thời gian, kèm trích xuất/đối chiếu câu nguồn cho các phát biểu định lượng.
- **Metric chính:** ROUGE-L (âm tiết tiếng Việt, phụ: ROUGE-1/2), đối chiếu claim số/đơn vị bề mặt và rubric factuality (0–2), `numeric_precision`, `numeric_hallucination_rate`, `gold_numeric_recall` (chi tiết tại [`evaluation_protocol.md`](evaluation_protocol.md)).

> [!IMPORTANT]
> **Quyền dữ liệu & phạm vi phát hành:** Nguồn dữ liệu [`VLUS06/VietOnlineNews`](https://huggingface.co/datasets/VLUS06/VietOnlineNews) (revision `bd8d2a865c8981d34cb9d85f69f62bda7c40b520`) khai báo `license: other` với tệp `LICENSE` rỗng (`OTHER_UNVERIFIED`). Các tệp chứa toàn văn bài báo, `reference_summary` hoặc `source_sentence` trích nguyên văn được `.gitignore` giữ cục bộ và **không đẩy lên GitHub công khai**.

## Thí nghiệm và đánh giá

Báo cáo này dùng các artifact hiện có trong workspace, không suy diễn kết quả cho cấu hình chưa chạy. Bộ đánh giá có 60 mẫu theo guideline v1.0: 10 `dev` và 50 `test`; protocol ROUGE và rubric factuality được mô tả trong [`evaluation_protocol.md`](evaluation_protocol.md).

### Kết quả tổng hợp đã xác minh

| Thí nghiệm | Split / số mẫu | Cấu hình | ROUGE-1 F1 macro | ROUGE-2 F1 macro | ROUGE-L F1 macro | Đối chiếu số liệu tự động | Trạng thái |
|---|---:|---|---:|---:|---:|---|---|
| E0 | `dev`, 10 | Lead-3, 3 câu đầu | 0.3921 | 0.2086 | 0.2516 | 16/40 claim khớp bề mặt giá trị + đơn vị (40%); gold fact surface recall macro 0.2533 | Hoàn tất |
| E1 thật | `dev`, 0/10 | `e1-basic-v1`, `temperature=0.1`; hai lần thử ghi model `deepseek-v4.1-flash` và `kimi-k2.7-code` | — | — | — | Không có dự đoán được chấm | Cả hai run `partial`, `HTTPError` tại `DT05-004` |
| E2 thật | `dev`, 0/10 | `e2-numeric-v1`, `temperature=0.1`, `regenerate_once_then_drop` | — | — | — | — | Chưa có run thật |
| E1/E2 mock | `dev`, 10 mỗi cấu hình | Phản hồi giả lập `MOCK-SYNTHETIC` | — | — | — | Chỉ kiểm tra luồng chạy; không tính metric | Hoàn tất smoke test |
| E1/E2 mock | `test`, 50 mỗi cấu hình | Phản hồi giả lập `MOCK-SYNTHETIC`; cấu hình chưa đóng băng | — | — | — | Không chấm điểm, không xem là benchmark | Hoàn tất smoke test; test benchmark thật chưa chạy |

E0 lấy số tổng hợp từ [`reports/metrics_summary.csv`](reports/metrics_summary.csv); các dự đoán từng mẫu nằm trong [`reports/dev_predictions_E0.csv`](reports/dev_predictions_E0.csv) (artifact cục bộ). `16/40` là tỷ lệ khớp bề mặt **giá trị và đơn vị**, không phải factuality. ROUGE đo độ trùng lặp với reference, còn `gold_fact_surface_recall` đo độ phủ fact trong gold theo bộ kiểm tra tự động; cả hai không chứng minh mọi phát biểu trong tóm tắt đúng với nguồn.

Các ô đánh giá người trong [`reports/human_eval_sheet.csv`](reports/human_eval_sheet.csv) vẫn ở trạng thái `pending`. Vì vậy chưa có `numeric_precision`, `numeric_hallucination_rate`, điểm factuality hoặc điểm readability đã được người chấm xác nhận. Không kết luận E1/E2 tốt hơn E0; không dùng fixture mock làm kết quả; và không báo cáo điểm test benchmark khi chưa chạy cấu hình đã khóa.

### Chạy pipeline bằng API mô phỏng

Để kiểm tra đường chạy E1/E2 mà không gọi dịch vụ thật, đã chạy mock trên toàn bộ 10 mẫu `dev` và 50 mẫu `test`. E1 dùng phản hồi placeholder; E2 dùng claim số giả lập để kích hoạt thử lại và hậu kiểm. Mỗi đầu ra đều mang nhãn `MOCK-SYNTHETIC`, không phải bản tóm tắt thực.

| Cấu hình | Dev | Test | Hậu kiểm E2 |
|---|---:|---:|---|
| E1 mock | 10/10 hoàn tất | 50/50 hoàn tất | Không áp dụng |
| E2 mock | 10/10 hoàn tất | 50/50 hoàn tất | 60/60 mẫu được thử lại một lần; mỗi lần bỏ 1 câu giả chứa số không được hỗ trợ |

Các log, manifest và prediction mô phỏng nằm tại [`reports/mock_synthetic/20261125T204408/`](reports/mock_synthetic/20261125T204408/), với run IDs `MOCK-20261125T2044-E1-DEV`, `MOCK-20261125T2044-E2-DEV`, `MOCK-20261125T2044-E1-TEST` và `MOCK-20261125T2044-E2-TEST`. Endpoint trong manifest là `mock://synthetic`; không gửi request đến Ollama. Lượt mock trên `test` dùng nhãn `MOCK-UNFROZEN-NOT-BENCHMARK`; kiểm tra tag đóng băng được bỏ qua chỉ cho lần mô phỏng này. Vì vậy không tạo ROUGE/factuality score và không xem đây là lần đánh giá test theo protocol.

### Phân tích 10 trường hợp E0 trên `dev`

Bảng dưới đây đối chiếu dự đoán thực tế với reference/gold fact sheet. Đây là **các sai lệch hoặc ứng viên lỗi được phát hiện tự động**, chưa phải kết luận factuality đã qua chấm người. ROUGE-L là điểm theo từng mẫu; “fact khớp” là số fact gold được checker nhận diện, không phải đánh giá đầy đủ ý nghĩa ngữ cảnh.

| ID | ROUGE-L | Chứng cứ từ prediction và đối chiếu | Sai lệch quan sát được |
|---|---:|---|---|
| `DT05-004` | 0.2394 | 188 từ; checker khớp 2/4 gold facts. Prediction nêu các ngưỡng 200 và 500 triệu đồng/năm nhưng không có thuế suất 15% và ngưỡng 3 tỉ đồng trong reference. | Quá giới hạn 50–120 từ; thiếu dữ kiện chính sách ở phần sau bài. |
| `DT05-006` | 0.1245 | 168 từ; 0/4 gold facts khớp. Prediction tập trung vào ngày/hội thảo và hơn 2.100 hộ kinh doanh, không nêu các kết quả 16%, 25% và 19 triệu USD trong 8 tháng. | Dài hơn yêu cầu, bỏ sót các kết quả định lượng cốt lõi. |
| `DT05-011` | 0.2993 | 71 từ; 1/6 gold facts khớp. Prediction liệt kê tỷ giá các ngân hàng; reference còn có giá USD tự do 27.240/27.340 đồng và dự báo Fed 87,4%. | Chọn nhiều số liệu cục bộ, thiếu diễn biến thị trường và bối cảnh so sánh. |
| `DT05-017` | 0.4412 | 54 từ; 1/3 gold facts khớp. Prediction có tổng nợ hơn 25.356 tỷ đồng nhưng không có khoản nợ hơn 1.828 tỷ đồng; văn bản đầu ra còn dính chữ (`ThuếTPHCMvừa`, `tiềnthuếvà`). | Bỏ sót chủ thể/khoản nợ nổi bật; giảm khả năng đọc. |
| `DT05-018` | 0.1714 | Prediction có diện tích `30.000m2`; 1/2 gold facts khớp, nhưng bộ dò bề mặt đánh dấu claim diện tích `not_found` và có 0/4 claim khớp chính xác giá trị + đơn vị. | Có dấu hiệu sai lệch ở checker với đơn vị viết liền; các số địa chỉ/số quyết định cũng cần phân loại theo ngữ cảnh. |
| `DT05-020` | 0.2247 | 91 từ; 0/2 gold facts khớp theo checker. Prediction đề cập các số hiệu điều luật và mốc hết hạn 31/12/2025 nhưng không nêu ngày áp dụng bảng giá mới 1/1/2026 được reference nhấn mạnh. | Nặng phần trích dẫn pháp lý, thiếu mốc áp dụng và hệ quả với người dân. |
| `DT05-043` | 0.2737 | 109 từ; 1/2 gold facts khớp. Prediction giữ khoản đầu tư hơn 220 triệu USD nhưng không nêu diện tích 7.400 m2. | Thiếu quy mô cơ sở trong khi chỉ giữ được một trong hai dữ kiện số chính. |
| `DT05-047` | 0.2073 | 74 từ; 1/3 gold facts khớp. Prediction tập trung vào giao dịch TL4 và tỷ lệ sở hữu 14,89%, không nêu khoản vay 5.833 lượng vàng SJC và tiền lãi vượt 804 tỷ đồng. | Không đưa rủi ro nợ lớn vào tóm tắt, làm thiếu bối cảnh tài chính quan trọng. |
| `DT05-050` | 0.3837 | 91 từ; 1/5 gold facts khớp. Prediction dừng giữa phần nêu 55 lô dương tính; không có mẫu số 6.679 lô, tỷ lệ gần 1% hay ước tính 1.320 tấn trong reference. | Đầu ra bị cắt cụt và thiếu quy mô rủi ro an toàn thực phẩm. |
| `DT05-059` | 0.1512 | 84 từ; 0/2 gold facts khớp. Prediction mở đầu bằng caption ảnh và có cụm dính chữ; không nêu lợi nhuận giữ lại 18.387 tỉ đồng hay tỷ lệ 32,5% cổ phần STB trong reference. | Nhiễu caption/lỗi khoảng trắng và bỏ sót dữ kiện tài chính chính. |

Các điểm ROUGE-L, độ dài, số claim và số gold fact khớp được lấy từ dự đoán E0 và phiếu đánh giá máy theo từng `item_id`; đối chiếu định tính được trình bày thêm trong [`reports/error_analysis.md`](reports/error_analysis.md). Không trích nguyên văn toàn văn bài báo hoặc reference summary trong README do tình trạng giấy phép dữ liệu chưa được xác minh.

### Kết luận và giới hạn

Trên 10 mẫu `dev`, E0 cho thấy điểm ROUGE-L macro 0.2516 và nhiều trường hợp bỏ sót dữ kiện nằm ngoài ba câu đầu; một số đầu ra còn quá dài, dính chữ hoặc bị cắt. Đây là kết quả mô tả trên tập dev nhỏ, không phải bằng chứng về khả năng tổng quát hóa. Chưa thể so sánh E0/E1/E2 vì E1 chưa có dự đoán thật hoàn chỉnh, E2 chưa có run thật và chưa có điểm factuality do người chấm. Tập `test` chỉ được dùng cho smoke test giả lập, chưa có benchmark thật.

**Bước tiếp theo:** khắc phục lỗi gọi API, hoàn tất E1 và chạy E2 thật trên `dev`, chấm thủ công factuality/readability và ghi đầy đủ kết quả từng mẫu; sau đó đóng băng cấu hình trước khi chạy `test` theo [`evaluation_protocol.md`](evaluation_protocol.md). Không dùng kết quả mock hoặc mở tập test để thay cho các bước này.

---

## 1. Cấu trúc thư mục và bảng ánh xạ vị trí minh chứng

Theo Mục 10.1 của hướng dẫn BTL CSC4007, bảng dưới đây ánh xạ vị trí từng minh chứng trong dự án:

| Minh chứng theo hướng dẫn | Đường dẫn trong dự án | Ghi chú phát hành |
|---|---|---|
| README hướng dẫn chạy | [`README.md`](README.md) | Công khai |
| Danh sách thư viện | [`requirements.txt`](requirements.txt) | Công khai |
| Data Card 14 mục | [`data_card.md`](data_card.md) | Công khai |
| Tài liệu tầng dữ liệu & Schema | [`data/README.md`](data/README.md), [`data/data_schema.md`](data/data_schema.md) | Công khai |
| Manifest & toàn văn/annotation | `data/data_manifest.csv`, `data/processed/*`, `data/annotations/gold_*.csv`, `review_log.csv` | **Cục bộ** (`.gitignore` vì `license: other`) |
| Chia split & khóa guideline | [`data/splits/dev_ids.txt`](data/splits/dev_ids.txt), [`data/splits/test_ids.txt`](data/splits/test_ids.txt), [`data/splits/split_history.json`](data/splits/split_history.json), [`annotation_guideline.md`](annotation_guideline.md), [`data/annotations/guideline_lock.json`](data/annotations/guideline_lock.json) | Công khai |
| Cấu hình & prompt E0–E2 | [`configs/`](configs/README.md) (`e0_lead3.json`, `e1_basic_v1.json`, `e2_numeric_v1.json`) | Công khai |
| Mã nguồn chuẩn hóa, kiểm gold, suy luận, đánh giá | [`data/prepare_data.py`](data/prepare_data.py), [`src/check_gold.py`](src/check_gold.py), [`src/run_ollama.py`](src/run_ollama.py), [`src/evaluate.py`](src/evaluate.py), [`src/build_human_eval_sheet.py`](src/build_human_eval_sheet.py), [`src/summarize_experiments.py`](src/summarize_experiments.py), [`src/export_error_candidates.py`](src/export_error_candidates.py) | Công khai |
| Giao thức đánh giá | [`evaluation_protocol.md`](evaluation_protocol.md) | Công khai (`protocol-frozen`) |
| Báo cáo chất lượng & kiểm gold | `reports/data_quality_report.md` (cục bộ), [`reports/gold_check_report.md`](reports/gold_check_report.md), [`reports/gold_check_issues.csv`](reports/gold_check_issues.csv) | `gold_check_*` công khai |
| Nhật ký thí nghiệm, dự đoán & chấm người | `reports/experiments.csv`, `reports/*_predictions_*.csv`, `reports/*_numeric_claims_*.csv`, `reports/human_eval_sheet.csv`, `reports/numeric_error_table.csv` | **Cục bộ** (chứa văn bản tóm tắt/tham chiếu) |
| Bảng tổng hợp chỉ số | [`reports/metrics_summary.csv`](reports/metrics_summary.csv) | Công khai (chỉ số tổng hợp) |
| Phân tích lỗi (≥10 mẫu) | [`reports/error_analysis.md`](reports/error_analysis.md) | Công khai (không trích nguyên văn bài báo) |
| Nhật ký & tuyên bố sử dụng AI | [`Nhat_ky_su_dung_AI.md`](Nhat_ky_su_dung_AI.md), [`reports/Tuyen_bo_su_dung_AI.md`](reports/Tuyen_bo_su_dung_AI.md) | Công khai |
| Báo cáo kỹ thuật | [`reports/Bao_cao_BTL.md`](reports/Bao_cao_BTL.md), `reports/Bao_cao_BTL.pdf` | `.pdf` nộp cục bộ/ZIP |
| Demo & ca kiểm thử mẫu | [`app/`](app/README.md) (`demo.py`, `sample_input.txt`, `sample_output.json`) | Công khai |
| Kiểm thử tự động | [`tests/test_pipeline.py`](tests/test_pipeline.py) | Công khai |

---

## 2. Cài đặt môi trường

Yêu cầu Python 3.10+ (đã kiểm thử với Python 3.13 trong `.venv`):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Nếu chạy E1/E2 hoặc chế độ LLM của demo qua Ollama Cloud, cấu hình biến môi trường ở shell cục bộ (**không lưu hoặc commit vào mã nguồn**):

```bash
export OLLAMA_API_KEY="<your-ollama-cloud-api-key>"
```

Trong PowerShell, có thể nhập key theo kiểu không hiển thị trên màn hình:

```powershell
$secure = Read-Host "OLLAMA_API_KEY" -AsSecureString
$env:OLLAMA_API_KEY = [System.Net.NetworkCredential]::new("", $secure).Password
```

Khi bản sao làm việc chưa có Git commit hợp lệ, chạy lệnh từ thư mục `BTL` và bỏ `--repo-root`. Runner để trống `run_commit`, ghi SHA-256 của mã nguồn/dữ liệu/config vào `source_fingerprint` và đặt `worktree_status` là `uncommitted`; fingerprint loại trừ `.git`, môi trường ảo, cache và `reports/`. Không dùng fingerprint như một Git commit hoặc để mở tập test.

---

## 3. Quy trình tái lập từng bước

### Bước 1: Kiểm tra dữ liệu và bộ gold (D1)

```bash
# Dựng lại tập dữ liệu từ Hugging Face revision đã pin (nếu chạy trong thư mục mới)
python data/prepare_data.py --out /tmp/btl_rebuild

# Kiểm tra tự động 60 bài gold theo guideline v1.0 đã khóa
python src/check_gold.py --root . --locked-version v1.0
```

### Bước 2: Chạy và chấm các cấu hình trên tập `dev` (10 bài)

```bash
# E0: Baseline Lead-3 (chạy cục bộ, không cần API key)
python src/evaluate.py --root . --repo-root ../repo-BTL-NLP --split dev --experiment E0

# E1: Prompt cơ bản với Ollama Cloud
python src/run_ollama.py --repo-root ../repo-BTL-NLP --experiment E1 --split dev
python src/evaluate.py --root . --repo-root ../repo-BTL-NLP --split dev --experiment E1 \
  --predictions reports/dev_ollama_predictions_E1_<RUN_ID>.csv \
  --model-id deepseek-v4.1-flash --run-label <RUN_ID> \
  --prompt-version e1-basic-v1 --temperature 0.1 \
  --api-endpoint https://ollama.com/api/chat

# E2: Prompt ràng buộc số liệu + hậu kiểm regenerate_once_then_drop
python src/run_ollama.py --repo-root ../repo-BTL-NLP --experiment E2 --split dev
python src/evaluate.py --root . --repo-root ../repo-BTL-NLP --split dev --experiment E2 \
  --predictions reports/dev_ollama_predictions_E2_<RUN_ID>.csv \
  --model-id deepseek-v4.1-flash --run-label <RUN_ID> \
  --prompt-version e2-numeric-v1 --temperature 0.1 \
  --api-endpoint https://ollama.com/api/chat \
  --postcheck-policy regenerate_once_then_drop
```

### Bước 3: Khóa cấu hình và chạy `test` đúng một lần (50 bài)

Chỉ thực hiện sau khi hoàn tất đánh giá trên `dev` và không còn chỉnh sửa prompt/tham số:

```bash
# 1. Commit và gắn tag configs-frozen trên repo-BTL-NLP
git -C ../repo-BTL-NLP tag -a configs-frozen -m "Freeze E0-E2 configs before single test run"
CONFIG_COMMIT=$(git -C ../repo-BTL-NLP rev-parse configs-frozen^{})

# 2. Chấm E0 trên test (1 lần duy nhất)
python src/evaluate.py --root . --repo-root ../repo-BTL-NLP --split test --experiment E0 \
  --config-tag configs-frozen --config-tag-commit "$CONFIG_COMMIT" --confirm-test-once

# 3. Chạy và chấm E1, E2 trên test (1 lần duy nhất mỗi cấu hình)
python src/run_ollama.py --repo-root ../repo-BTL-NLP --experiment E1 --split test \
  --config-tag configs-frozen --config-tag-commit "$CONFIG_COMMIT" --confirm-test-once
python src/evaluate.py --root . --repo-root ../repo-BTL-NLP --split test --experiment E1 \
  --predictions reports/test_ollama_predictions_E1_<RUN_ID>.csv \
  --model-id deepseek-v4.1-flash --run-label <RUN_ID> \
  --prompt-version e1-basic-v1 --temperature 0.1 \
  --api-endpoint https://ollama.com/api/chat \
  --config-tag configs-frozen --config-tag-commit "$CONFIG_COMMIT" --confirm-test-once

python src/run_ollama.py --repo-root ../repo-BTL-NLP --experiment E2 --split test \
  --config-tag configs-frozen --config-tag-commit "$CONFIG_COMMIT" --confirm-test-once
python src/evaluate.py --root . --repo-root ../repo-BTL-NLP --split test --experiment E2 \
  --predictions reports/test_ollama_predictions_E2_<RUN_ID>.csv \
  --model-id deepseek-v4.1-flash --run-label <RUN_ID> \
  --prompt-version e2-numeric-v1 --temperature 0.1 \
  --api-endpoint https://ollama.com/api/chat \
  --postcheck-policy regenerate_once_then_drop \
  --config-tag configs-frozen --config-tag-commit "$CONFIG_COMMIT" --confirm-test-once
```

### Bước 4: Xuất phiếu chấm con người, bảng lỗi số liệu & tổng hợp chỉ số

```bash
python src/build_human_eval_sheet.py --root .
python src/summarize_experiments.py --root .
python src/export_error_candidates.py --root .
```

### Bước 5: Chạy Demo & kiểm thử đơn vị

```bash
# Chạy CLI demo với bài mẫu (E0 offline)
python app/demo.py --mode E0 --input-file app/sample_input.txt

# Hoặc khởi chạy giao diện web cục bộ
python app/demo.py --serve --port 8000

# Chạy toàn bộ unit tests
python -m unittest discover -s tests -v
```
