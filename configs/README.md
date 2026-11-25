# Cấu hình thí nghiệm E0–E2

Thư mục này lưu đặc tả cấu hình, giả thuyết và prompt template chính thức của ba cấu hình đối chứng theo Mục 6.1 và 6.4 của hướng dẫn BTL CSC4007:

| Cấu hình | Tệp | Phương pháp | Yếu tố thay đổi / giả thuyết |
|---|---|---|---|
| `E0` | [`e0_lead3.json`](e0_lead3.json) | Lead-3 extractive | Baseline tái lập hoàn toàn: lấy 3 câu đầu của thân bài; đặt mốc ROUGE và tỷ lệ khớp số/đơn vị bề mặt. |
| `E1` | [`e1_basic_v1.json`](e1_basic_v1.json) | LLM (`deepseek-v4.1-flash`, `temperature=0.1`, `e1-basic-v1`) | Prompt tóm tắt tin kinh tế cơ bản (3–5 câu, 50–120 từ); kiểm chứng giả thuyết LLM cải thiện độ bao phủ ý chính và ROUGE so với Lead-3 nhưng có thể rơi rớt đơn vị hoặc suy diễn kỳ/chủ thể. |
| `E2` | [`e2_numeric_v1.json`](e2_numeric_v1.json) | LLM (`deepseek-v4.1-flash`, `temperature=0.1`, `e2-numeric-v1`) + `regenerate_once_then_drop` | Bổ sung ràng buộc bảo toàn số/đơn vị/kỳ/modality trong prompt và hậu kiểm bề mặt (`unsupported_sentence_indexes`): nếu có claim số+đơn vị không khớp thân bài thì yêu cầu viết lại 1 lần, nếu vẫn còn thì loại câu vi phạm. |

## Quy tắc khóa cấu hình trước khi chạy `test`

1. Mọi tinh chỉnh prompt, temperature hoặc post-check policy chỉ thực hiện trên **dev (10 bài)**.
2. Khi hài lòng với kết quả trên dev, commit toàn bộ `configs/`, `src/` và tài liệu lên nhánh Git trong `repo-BTL-NLP`, sau đó gắn tag Git `configs-frozen`:
   ```bash
   git -C ../repo-BTL-NLP tag -a configs-frozen -m "Freeze E0-E2 configs before single test run"
   git -C ../repo-BTL-NLP rev-parse configs-frozen^{}
   ```
3. Truyền `--config-tag configs-frozen --config-tag-commit <HASH> --confirm-test-once` khi chạy `src/run_ollama.py` và `src/evaluate.py` trên `--split test`. Script từ chối chạy `test` lần thứ hai hoặc chạy khi tag chưa khớp.
