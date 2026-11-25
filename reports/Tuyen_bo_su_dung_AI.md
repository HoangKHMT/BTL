# Tuyên bố sử dụng công cụ AI (AI Usage Declaration)

- **Học phần:** CSC4007 – Xử lý ngôn ngữ tự nhiên (2026–2027)
- **Đề tài:** ĐT05 – Tóm tắt tin tức kinh tế tiếng Việt có kiểm chứng dữ kiện
- **Thành viên nhóm:** Cường (`A1`), Hoàng (`A2`)

## 1. Phạm vi và nguyên tắc sử dụng AI

1. **Hỗ trợ kỹ thuật và tài liệu:** Nhóm sử dụng trợ lý AI lập trình trong IDE để hỗ trợ rà soát schema, viết/kiểm thử mã nguồn Python (`evaluate.py`, `run_ollama.py`, `build_human_eval_sheet.py`, `summarize_experiments.py`, `export_error_candidates.py`, `app/demo.py`, `tests/`), và chuẩn hóa tài liệu kỹ thuật (`data_card.md`, `data_schema.md`, `README.md`, `error_analysis.md`, `Bao_cao_BTL.md`).
2. **Hỗ trợ nháp gold (`llm_edited`):** Theo `annotation_guideline.md` (Mục 11), các bản nháp tóm tắt tham chiếu được ghi rõ `draft_source=llm_edited`, sau đó toàn bộ 60 bài đều được thành viên nhóm (`A1`/`A2`) đối chiếu từng số liệu với thân bài gốc; 38/60 bài (63,3%, trong đó 13/13 bài test đánh dấu hậu kiểm chéo và 7/10 bài dev) có trạng thái `reviewed` độc lập khác người gắn nhãn. Không coi output thô của LLM là gold khi chưa có người kiểm chứng.
3. **Mô hình thí nghiệm đối chứng (E1/E2):** Mô hình `deepseek-v4.1-flash` qua Ollama Cloud được dùng làm hệ thống đối chứng tóm tắt ở E1 và E2, tách biệt với baseline E0 (`Lead-3`), có lưu prompt template (`configs/`), log gọi API cục bộ và script chấm điểm tái lập.

## 2. Cam kết minh bạch, đạo đức và bảo vệ dữ liệu

- **Không lộ khóa API / bí mật:** Tuyệt đối không lưu `OLLAMA_API_KEY` hay bất kỳ token xác thực nào trong mã nguồn, cấu hình, nhật ký, báo cáo hoặc commit Git.
- **Không vi phạm bản quyền dữ liệu:** Do `VLUS06/VietOnlineNews` khai báo `license: other` và chưa có xác nhận tái phân phối bằng văn bản, toàn văn bài báo, `gold_summaries.csv`, `gold_numeric_facts.csv`, `review_log.csv` và đầu ra tóm tắt theo từng mẫu được giữ cục bộ qua `.gitignore`, không đẩy lên repository công khai.
- **Không ngụy tạo kết quả thực nghiệm:** Mọi con số đánh giá đều được sinh tự động bởi script (`src/check_gold.py`, `src/evaluate.py`, `src/summarize_experiments.py`). Những phần chưa chạy (E1, E2 và tập test độc lập khi chưa khóa cấu hình / chưa có `OLLAMA_API_KEY`) được ghi nhận trung thực là chưa chạy.
- **Trách nhiệm giải trình:** Các thành viên nhóm chịu trách nhiệm hoàn toàn về tính chính xác của dữ liệu, mã nguồn, phương pháp đánh giá, phân tích lỗi và nội dung bảo vệ cuối kỳ.

*Nhật ký chi tiết từng phiên làm việc được ghi tại [`../Nhat_ky_su_dung_AI.md`](../Nhat_ky_su_dung_AI.md).*
