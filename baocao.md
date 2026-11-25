# Báo cáo thí nghiệm và đánh giá

**Đề tài:** ĐT05 – Tóm tắt tin tức kinh tế tiếng Việt có kiểm chứng dữ kiện  
**Học phần:** CSC4007 – Xử lý ngôn ngữ tự nhiên, năm học 2026–2027  
**Nhóm:** Cường (`A1`), Hoàng (`A2`)  
**Cập nhật:** 25/11/2026

## 1. Mục tiêu và giao thức đánh giá

Đầu vào là bài báo kinh tế tiếng Việt (`title`, `content`); đầu ra kỳ vọng là tóm tắt 3–5 câu, dài 50–120 từ. Đánh giá gồm độ tương đồng với reference và mức bảo toàn dữ kiện; ROUGE không được xem là bằng chứng độc lập về tính đúng sự thật.

- **ROUGE:** ROUGE-L là metric chính; ROUGE-1/2 là metric phụ. Áp dụng cùng tokenizer theo âm tiết tiếng Việt cho mọi cấu hình: Unicode NFC, `casefold()`, tách token bằng `re.findall(r"[^\W_]+", text, flags=re.UNICODE)`, không stemming hoặc bỏ stopword. Tính F1 từng mẫu rồi lấy trung bình macro.
- **Kiểm tra số liệu:** bộ dò trích xuất ứng viên claim số, sau đó đối chiếu bề mặt giá trị + đơn vị và độ phủ fact trong gold. Đây là kiểm tra tự động, có thể bỏ sót hoặc nhận nhầm ngữ cảnh; không thay thế chấm đúng/sai theo chủ thể, đơn vị, kỳ, cơ sở so sánh và mức độ chắc chắn.
- **Chấm factuality/readability:** protocol quy định factuality theo thang 0–2 và đánh giá khả năng đọc. Các trường chấm người hiện vẫn `pending`, do đó báo cáo này không đưa ra điểm factuality, `numeric_precision`, `numeric_hallucination_rate` hay readability.
- **Protocol:** v1.0, trạng thái `protocol-frozen`; chi tiết tại [`evaluation_protocol.md`](evaluation_protocol.md). Dataset source revision: `bd8d2a865c8981d34cb9d85f69f62bda7c40b520`.

Bộ đánh giá có 60 mẫu: 10 `dev` và 50 `test`. Test benchmark thật chưa được chạy; sau đó có smoke test pipeline bằng API mô phỏng trên split test, không tính là kết quả thực nghiệm. Các kết quả dưới đây chỉ dùng artifact quan sát được trong workspace; dữ liệu mock không được tính là kết quả mô hình.

## 2. Cấu hình và kết quả

| Thí nghiệm | Split / số mẫu | Cấu hình ghi nhận | ROUGE-1 F1 macro | ROUGE-2 F1 macro | ROUGE-L F1 macro | Đối chiếu số liệu tự động | Trạng thái |
|---|---:|---|---:|---:|---:|---|---|
| E0 | `dev`, 10 | Lead-3, lấy 3 câu đầu | 0.3921 | 0.2086 | 0.2516 | 16/40 claim khớp bề mặt giá trị + đơn vị (40%); gold fact surface recall macro 0.2533 | Hoàn tất |
| E1 thật | `dev`, 0/10 | `e1-basic-v1`, `temperature=0.1`; hai lần thử ghi model `deepseek-v4.1-flash` và `kimi-k2.7-code` | — | — | — | Không có prediction được chấm | Cả hai run `partial`, `HTTPError` tại `DT05-004` |
| E2 thật | `dev`, 0/10 | `e2-numeric-v1`, `temperature=0.1`, `regenerate_once_then_drop` | — | — | — | — | Chưa có run thật |
| E1/E2 mock | `dev`, 10 mỗi cấu hình | Phản hồi `MOCK-SYNTHETIC` | — | — | — | Smoke test, không tính metric | Hoàn tất |
| E1/E2 mock | `test`, 50 mỗi cấu hình | Phản hồi `MOCK-SYNTHETIC`; cấu hình chưa đóng băng | — | — | — | Không chấm điểm, không xem là benchmark | Smoke test hoàn tất; benchmark thật chưa chạy |

E0 được ghi tại run `2026-11-25T16-19-49+07-00-d20c2ed5`; các số tổng hợp lấy từ [`reports/metrics_summary.csv`](reports/metrics_summary.csv). Prediction từng mẫu: [`reports/dev_predictions_E0.csv`](reports/dev_predictions_E0.csv), hiện là artifact cục bộ. Log E1: `20261125T122128Z-600f3317` và `run-e1-dev-kimi`; cả hai chưa hoàn tất mẫu nào. E2 mock run: `MOCK-E2-20261125T192159`.

**Diễn giải các chỉ số:** 16/40 (40%) là tỷ lệ claim tự động khớp bề mặt giá trị và đơn vị, không phải tỷ lệ factuality. Gold fact surface recall là độ phủ fact gold qua checker tự động. ROUGE đo độ trùng lặp với reference. Không chỉ số nào trong số này xác nhận rằng mọi claim đều đúng với bài nguồn.

## 3. Phân tích 10 trường hợp E0 trên `dev`

Các trường hợp dưới đây được xác định từ prediction E0 và phép đối chiếu tự động với reference/gold fact sheet. Đây là sai lệch quan sát được hoặc ứng viên lỗi cần người rà soát, không phải kết luận factuality đã được người chấm xác nhận. “Fact khớp” là số fact gold mà checker nhận diện.

| ID | ROUGE-L | Chứng cứ từ prediction và đối chiếu | Sai lệch quan sát được |
|---|---:|---|---|
| `DT05-004` | 0.2394 | 188 từ; checker khớp 2/4 gold facts. Prediction nêu ngưỡng 200 và 500 triệu đồng/năm nhưng không có thuế suất 15% và ngưỡng 3 tỉ đồng trong reference. | Quá giới hạn 50–120 từ; thiếu dữ kiện chính sách ở phần sau bài. |
| `DT05-006` | 0.1245 | 168 từ; 0/4 gold facts khớp. Prediction tập trung vào ngày/hội thảo và hơn 2.100 hộ kinh doanh, không nêu các kết quả 16%, 25% và 19 triệu USD trong 8 tháng. | Dài hơn yêu cầu; bỏ sót các kết quả định lượng cốt lõi. |
| `DT05-011` | 0.2993 | 71 từ; 1/6 gold facts khớp. Prediction liệt kê tỷ giá các ngân hàng; reference còn có giá USD tự do 27.240/27.340 đồng và dự báo Fed 87,4%. | Chọn nhiều số liệu cục bộ, thiếu diễn biến thị trường và bối cảnh so sánh. |
| `DT05-017` | 0.4412 | 54 từ; 1/3 gold facts khớp. Prediction có tổng nợ hơn 25.356 tỷ đồng nhưng không có khoản nợ hơn 1.828 tỷ đồng; đầu ra còn dính chữ (`ThuếTPHCMvừa`, `tiềnthuếvà`). | Bỏ sót khoản nợ nổi bật; giảm khả năng đọc. |
| `DT05-018` | 0.1714 | Prediction có diện tích `30.000m2`; 1/2 gold facts khớp. Checker đánh dấu claim diện tích `not_found` và có 0/4 claim khớp chính xác giá trị + đơn vị. | Có dấu hiệu sai lệch của checker với đơn vị viết liền; số địa chỉ/số quyết định cần phân loại theo ngữ cảnh. |
| `DT05-020` | 0.2247 | 91 từ; 0/2 gold facts khớp theo checker. Prediction đề cập số hiệu điều luật và mốc hết hạn 31/12/2025 nhưng không nêu ngày áp dụng bảng giá mới 1/1/2026 được reference nhấn mạnh. | Nặng phần trích dẫn pháp lý; thiếu mốc áp dụng và hệ quả với người dân. |
| `DT05-043` | 0.2737 | 109 từ; 1/2 gold facts khớp. Prediction giữ khoản đầu tư hơn 220 triệu USD nhưng không nêu diện tích 7.400 m2. | Thiếu quy mô cơ sở trong khi chỉ giữ được một trong hai dữ kiện số chính. |
| `DT05-047` | 0.2073 | 74 từ; 1/3 gold facts khớp. Prediction tập trung vào giao dịch TL4 và tỷ lệ sở hữu 14,89%, không nêu khoản vay 5.833 lượng vàng SJC và tiền lãi vượt 804 tỷ đồng. | Không đưa rủi ro nợ lớn vào tóm tắt, thiếu bối cảnh tài chính quan trọng. |
| `DT05-050` | 0.3837 | 91 từ; 1/5 gold facts khớp. Prediction dừng giữa phần nêu 55 lô dương tính; không có mẫu số 6.679 lô, tỷ lệ gần 1% hay ước tính 1.320 tấn trong reference. | Đầu ra bị cắt cụt; thiếu quy mô rủi ro an toàn thực phẩm. |
| `DT05-059` | 0.1512 | 84 từ; 0/2 gold facts khớp. Prediction mở đầu bằng caption ảnh và có cụm dính chữ; không nêu lợi nhuận giữ lại 18.387 tỉ đồng hay tỷ lệ 32,5% cổ phần STB trong reference. | Nhiễu caption/lỗi khoảng trắng và bỏ sót dữ kiện tài chính chính. |

Phân tích mở rộng theo từng mẫu có tại [`reports/error_analysis.md`](reports/error_analysis.md). Không đưa toàn văn bài báo hoặc reference summary vào báo cáo này vì giấy phép dữ liệu chưa được xác minh; bản prediction đầy đủ được giữ cục bộ.

## 4. Kết luận và giới hạn

Trên 10 mẫu `dev`, E0 đạt ROUGE-L macro 0.2516. Các prediction cho thấy một số hạn chế của Lead-3: bỏ sót dữ kiện nằm ngoài ba câu đầu, vượt giới hạn độ dài, lỗi dính chữ và một đầu ra bị cắt. Kết quả chỉ mang tính mô tả trên tập dev nhỏ, không chứng minh khả năng tổng quát hóa.

Chưa thể so sánh E0/E1/E2: E1 chưa có prediction thật hoàn chỉnh, E2 chưa có run thật và chưa có điểm factuality do người chấm. Tập `test` chỉ được dùng để smoke test giả lập, chưa có benchmark thật. Bước tiếp theo là khắc phục lỗi API, hoàn tất E1 và chạy E2 thật trên `dev`, chấm thủ công factuality/readability, rồi khóa cấu hình trước khi chạy test theo protocol. Không sử dụng dữ liệu mock thay cho kết quả thực nghiệm.

## 5. Kiểm thử pipeline bằng API mô phỏng

Đã chạy E1/E2 giả lập trên toàn bộ 10 mẫu `dev` và 50 mẫu `test` để kiểm tra nạp split, ghi prediction, manifest và hậu kiểm E2. Không gọi Ollama hoặc dịch vụ mạng; endpoint trong manifest là `mock://synthetic`. Phản hồi E1 là placeholder; phản hồi E2 chứa một claim số giả lập để ép luồng retry. Tất cả đầu ra được đánh dấu `MOCK-SYNTHETIC`, không phải bản tóm tắt hợp lệ và không được chấm ROUGE/factuality.

| Run ID | Split | Số mẫu hoàn tất | Kết quả kiểm tra |
|---|---|---:|---|
| `MOCK-20261125T2044-E1-DEV` | `dev` | 10/10 | Ghi prediction và manifest thành công |
| `MOCK-20261125T2044-E2-DEV` | `dev` | 10/10 | Cả 10 mẫu retry một lần; bỏ 1 câu chứa claim số giả |
| `MOCK-20261125T2044-E1-TEST` | `test` | 50/50 | Smoke test pipeline; không chấm điểm |
| `MOCK-20261125T2044-E2-TEST` | `test` | 50/50 | Cả 50 mẫu retry một lần; bỏ 1 câu chứa claim số giả |

Artifact nằm trong [`reports/mock_synthetic/20261125T204408/`](reports/mock_synthetic/20261125T204408/). Để giữ rõ ranh giới với test benchmark, lượt test dùng config tag `MOCK-UNFROZEN-NOT-BENCHMARK`, không có config commit; kiểm tra tag đóng băng được bỏ qua trong lần chạy giả lập. **Đây không phải kết quả đánh giá trên test và không đáp ứng protocol chạy test sau khi đóng băng cấu hình.**

Unit tests sau khi chạy mô phỏng: **15/15 đạt** (`python -m unittest discover -s tests -v`).
