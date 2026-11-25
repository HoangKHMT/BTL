# Nhật ký sử dụng AI

## 2026-11-25 (Phiên 1) — Hoàn thiện hồ sơ D1 và pre-audit dữ liệu

- **Công cụ AI:** AI assistant using Copilot SDK in VS Code. Model/version cụ thể không được hiển thị trong phiên làm việc.
- **Công cụ hỗ trợ:** Python và shell chạy cục bộ; Hugging Face Dataset Viewer/`datasets-server` để truy vấn mẫu dữ liệu công khai. Không tải lên gold, annotation hoặc văn bản cục bộ.
- **AI đã hỗ trợ:** soạn/sửa Data Card 14 mục và evaluation protocol; tổng hợp mã REVIEW/WARN từ báo cáo checker; đối chiếu sơ bộ 9 cặp cùng tiêu đề bằng mức tương đồng chuỗi nội dung; kiểm tra ngữ cảnh 12 ứng viên trong numeric audit; đọc mẫu nội dung để ghi nhận xét cho 8 bài `khac`.
- **Lịch sử bản nháp gold:** các dòng gold ghi `draft_source=llm_edited`; log hiện có không lưu model ID hoặc thời điểm tạo riêng cho từng bản nháp, nên không suy đoán các thông tin này. Việc người kiểm chứng được ghi riêng trong review log.
- **Giới hạn xác nhận:** các nhận xét trên được ghi là AI-assisted pre-audit, chưa có xác nhận độc lập của A1/A2. Không sửa tóm tắt hoặc fact sheet gold đã khóa; chưa chạy mô hình tóm tắt.
- **Phát hành:** chỉ code/tài liệu không chứa toàn văn hoặc gold được đẩy lên GitHub. Báo cáo kiểm tra có danh sách tiêu đề và các tệp dữ liệu/annotation tiếp tục ở local trong khi quyền tái phân phối chưa rõ.

## 2026-11-25 (Phiên 2) — Đóng gói cấu hình E0–E2, demo, công cụ đánh giá và hồ sơ nộp bài

- **Công cụ AI:** Gemini 4 Hydrogen (High) trong Antigravity IDE (chạy cục bộ, không có quyền truy cập mạng/API ngoài và không lưu `OLLAMA_API_KEY`).
- **AI đã hỗ trợ:**
  - Sửa lỗi khớp bề mặt trong `src/evaluate.py` (`source_surface_status` bổ sung tập giá trị từ `source_analysis["facts"]` để xử lý đơn vị viết liền như `30.000m2` trước khi chạy hậu kiểm E2).
  - Bổ sung bộ cấu hình `configs/` (`e0_lead3.json`, `e1_basic_v1.json`, `e2_numeric_v1.json`, `configs/README.md`), tài liệu `README.md`, `data/README.md`, `data/data_schema.md`.
  - Xây dựng công cụ đánh giá và tổng hợp: `src/build_human_eval_sheet.py`, `src/summarize_experiments.py`, `src/export_error_candidates.py`.
  - Xây dựng ứng dụng demo CLI + Web UI cục bộ (`app/demo.py`) kèm bài mẫu tự soạn `app/sample_input.txt` (không dùng dữ liệu VietOnlineNews) và bộ unit test `tests/test_pipeline.py`.
  - Soạn `reports/Tuyen_bo_su_dung_AI.md`, `reports/error_analysis.md` (dựa trên kết quả thực tế của E0 dev), `reports/Bao_cao_BTL.md` và script xuất `reports/Bao_cao_BTL.pdf`.
- **Xác minh thực tế:** Mọi thay đổi mã nguồn và demo đã được chạy kiểm thử cục bộ (`unittest`, `check_gold.py`, `demo.py`, `build_human_eval_sheet.py`, `summarize_experiments.py`). E1/E2 và tập `test` chưa chạy do thiếu `OLLAMA_API_KEY` trong môi trường chạy tự động và cần khóa `configs-frozen` sau khi rà dev.
