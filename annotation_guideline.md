# Hướng dẫn gắn nhãn tóm tắt tham chiếu – ĐT05

**Đề tài:** Tóm tắt tin tức kinh tế tiếng Việt có kiểm chứng dữ kiện (CSC4007)
**Phiên bản:** v1.0 (đã khóa ngày 2026-11-25 sau khi hoàn tất rà soát 10 bài dev và rà chéo theo quy trình).
**Áp dụng cho:** 60 bài trong `data/data_manifest.csv` (10 dev, 50 test).

## 1. Mục đích

Mỗi bài có một **tóm tắt tham chiếu** (reference summary) do người viết và rà soát. Tóm tắt này dùng để:

1. Tính ROUGE cho E0, E1, E2.
2. Làm chuẩn so sánh khi chấm độ đúng dữ kiện (chủ thể, số, đơn vị, mốc thời gian).

Trường `description` của dataset **không phải gold**. Nó có thể là câu dẫn, có thể thiếu ý hoặc chứa thông tin không có trong bài. Chỉ dùng để tham khảo (cột `description_ref_NOT_GOLD`).

## 2. Vai trò và tệp

| Vai trò | Việc | Tệp |
|---|---|---|
| Người gắn nhãn (A) | Đọc toàn bài, viết tóm tắt, điền phiếu số liệu | `gold_summaries.csv`, `gold_numeric_facts.csv`, `pilot_drafts.csv` |
| Người rà soát (R) | Kiểm tra độc lập bài được đánh dấu `cross_review_required=True` | `review_log.csv` |

- Người rà soát **phải khác** người gắn nhãn của bài đó.
- Ít nhất 20% bài (script đã đánh dấu 25%) cần người thứ hai rà soát. Nên chọn ít nhất vài bài thuộc dev và vài bài thuộc test.
- Nhóm hiện dùng hai mã `A1` và `A2`: `A1` là Cường, `A2` là Hoàng. `A3` chưa được phân công và không dùng trong phiên bản này. Các tệp annotation tiếp tục chỉ ghi mã, không ghi tên.
- Điền `annotator_id`, `reviewer_id` và `draft_source` trong `gold_summaries.csv` theo phân công. Với bài chưa viết, để `draft_source` trống; sau khi viết ghi `human` hoặc `llm_edited`.
- Với bài có hậu kiểm, reviewer là người còn lại: A1 rà bài của A2 và ngược lại.

## 3. Quy trình cho mỗi bài

1. Đọc **toàn bộ** `content`, không chỉ tiêu đề và `description`.
2. Quyết định bài có dùng được không (mục 7). Nếu không, ghi trạng thái `exclude` và dừng.
3. Viết tóm tắt theo mục 4 và 5.
4. Điền phiếu số liệu cho **mọi** số liệu trong tóm tắt (mục 6).
5. Tự kiểm bằng checklist ở mục 9.
6. Đổi `review_status` thành `annotated`. Bài cần rà soát thì chuyển cho R.

## 4. Quy tắc viết tóm tắt

**Độ dài và hình thức**
- 3–5 câu, khoảng 50–120 từ. Mỗi câu một ý chính, tối đa khoảng 35 từ. Không ghép nhiều ý vào một câu bằng dấu chấm phẩy để lách giới hạn.
- Viết văn xuôi, không gạch đầu dòng, không tiêu đề, không ký hiệu đặc biệt.
- Được diễn đạt lại bằng từ ngữ của mình. Cũng được dùng lại nguyên câu của bài nếu câu đó đã cô đọng.

**Thứ tự ý gợi ý**
1. Sự kiện hoặc kết luận chính (ai làm gì, điều gì xảy ra).
2. Một đến ba số liệu then chốt chứng minh ý chính.
3. Nguyên nhân hoặc bối cảnh quan trọng mà bài nêu.
4. Tác động, dự báo hoặc bước tiếp theo, nếu bài có nêu.

**Chỉ dùng thông tin trong bài**
- Không thêm kiến thức bên ngoài, không suy diễn, không đưa nhận xét hay đánh giá của người viết.
- Không dùng thông tin chỉ có trong tiêu đề hoặc `description` mà thân bài không nêu.
- Nếu thân bài chỉ ghi ngày/tháng nhưng tiêu đề có thêm năm, không tự ghép năm từ tiêu đề vào ngày trong tóm tắt.
- Không đổi lập trường của bài. Nhận định của một bên phải nêu rõ là của bên đó ("theo Bộ Công Thương", "chuyên gia cho rằng").

## 5. Quy tắc bảo toàn dữ kiện

Đây là phần quan trọng nhất vì đề tài đánh giá độ đúng số liệu.

| Nội dung | Quy tắc |
|---|---|
| **Chủ thể** | Giữ đúng tên doanh nghiệp, cơ quan, người, mã cổ phiếu như trong bài. Không thay bằng đối tượng khác hoặc khái quát hóa sai. |
| **Con số** | Giữ nguyên giá trị. Không làm tròn, không tự tính lại, không cộng trừ nếu bài không nêu sẵn. |
| **Cách viết số** | Giữ cách viết trong bài: dấu phẩy thập phân (3,2%), dấu chấm hàng nghìn (1.250). Không đổi 1,5 nghìn tỷ thành 1.500 tỷ. Nếu bài viết một số theo hai cách, dùng cách xuất hiện trước. |
| **Đơn vị** | Giữ nguyên: %, điểm phần trăm, tỷ đồng, nghìn tỷ đồng, triệu USD... Không đổi đơn vị tiền tệ hay đổi quy mô (tỷ ↔ triệu). |
| **Hướng thay đổi** | Dùng từ tăng/giảm đúng như bài. Không viết số âm thay cho "giảm". |
| **Mốc thời gian** | Giữ đúng tháng, quý, năm. "9 tháng đầu năm" là số lũy kế, không phải số của một tháng. Bài không nêu năm thì **không tự thêm năm**, vì ngày đăng của dataset chưa rõ. |
| **Kỳ so sánh** | Giữ nguyên cơ sở so sánh: so với cùng kỳ, so với tháng trước, so với quý trước, so với kế hoạch. Số "tăng 5%" mà thiếu kỳ so sánh là chưa đủ. |
| **Mức độ chắc chắn** | Giữ phân biệt giữa **thực tế**, **ước tính/sơ bộ**, **dự báo**, **kế hoạch/mục tiêu**. Không biến dự báo thành sự thật. |
| **Từ chỉ xấp xỉ** | Giữ "khoảng", "gần", "hơn", "ước tính". Giữ khoảng giá trị ("từ 5 đến 7%") nguyên dạng. |
| **Số liệu mâu thuẫn trong bài** | Dùng số mà bài trình bày là chính thức hoặc mới nhất, ghi lý do vào cột `notes` của phiếu số liệu. |

**Chọn số liệu nào đưa vào tóm tắt:** chỉ những số liệu cần cho ý chính, thường 1–3 số. Không cần liệt kê mọi số. Nhưng đã đưa vào thì phải đúng và đủ chủ thể, đơn vị, kỳ.

**Không gộp số liệu của các nhóm khác nhau:** nếu bài nêu kết quả riêng cho từng nhóm, phải giữ đúng nhóm gắn với từng giá trị. Không tạo một khoảng số bằng cách lấy giá trị nhỏ nhất và lớn nhất của các nhóm rồi gán khoảng đó cho tất cả. Ví dụ, nếu nhóm dịch vụ ăn uống giảm chi phí 16% còn cửa hàng bán lẻ tiết kiệm 25%, không viết chung rằng hơn 2.100 hộ giảm 16–25% chi phí.

## 6. Phiếu số liệu (`gold_numeric_facts.csv`)

Mỗi số liệu xuất hiện trong tóm tắt tham chiếu có một dòng:

| Cột | Ý nghĩa |
|---|---|
| `item_id`, `fact_id` | Mã bài và mã số liệu trong bài (F1, F2...) |
| `entity` | Chủ thể (doanh nghiệp, cơ quan, chỉ tiêu thuộc về ai) |
| `indicator` | Chỉ tiêu (CPI, doanh thu, kim ngạch xuất khẩu...) |
| `value`, `unit` | Giá trị và đơn vị, **như viết trong bài** |
| `period` | Kỳ của số liệu (quý II/2026, 9 tháng đầu năm...), hoặc `unknown` |
| `comparison_basis` | Cơ sở so sánh nếu có (cùng kỳ, tháng trước...), nếu không để trống |
| `modality` | `actual`, `estimate`, `forecast`, `target`, `proposal` hoặc `planned`; dùng `proposal` cho chính sách đang được đề xuất và `planned` cho mốc/kết quả đã được lên lịch trong tương lai |
| `source_sentence` | **Một câu** trong bài chứa số liệu này, chép nguyên văn |
| `annotator_id`, `notes` | Mã người gắn nhãn, ghi chú |

Phiếu này dùng để (a) kiểm tra mọi số trong tóm tắt có trong bài, (b) làm chuẩn cho câu nguồn bảo chứng mà hệ thống phải đưa ra.

Số liệu nằm ở nhiều câu nguồn thì chọn câu chứa giá trị. Nếu cần thêm câu khác để rõ chủ thể hoặc kỳ, ghi vào `notes`.

## 7. Bài không có hoặc ít số liệu

- Bài ít số liệu (`has_numbers=False`) vẫn được viết tóm tắt như bình thường. **Không thêm số liệu** cho "giống" bài khác.
- Nếu bài hầu như không có số thì phiếu số liệu có thể không có dòng nào. Đây là kết quả hợp lệ.
- Nhóm bài này dùng để kiểm tra hệ thống có tự bịa số khi bài gốc không có hay không, nên tóm tắt tham chiếu **không được chứa số nào ngoài số có trong bài**.

**Loại bài (`review_status=exclude`) khi:**
- Không phải tin kinh tế (chuyên mục gốc không đúng nội dung).
- Bài cụt, thiếu nội dung, hoặc chủ yếu là bảng/danh sách giá, không thể tóm tắt thành 3–5 câu có nghĩa.
- Nội dung quảng cáo/PR không có sự kiện hoặc thông tin cụ thể.
- Phát hiện muộn là cùng sự kiện hoặc đăng lại bài khác trong 60 bài.

Quy tắc loại bài:
- Quyết định loại phải đưa ra **trước khi xem bất kỳ kết quả mô hình nào** và ghi lý do vào `review_log.csv`. Không loại bài chỉ vì "khó tóm tắt".
- Tổng số bài loại tối đa 10 (để còn ít nhất 50 bài, trong đó test ≥ 40).
- Trong `review_log.csv`, ghi `decision=exclude` và lý do cụ thể vào `reason`; không chỉ xóa bài khỏi file.
- Nếu bài dev bị loại sau khi split đã khóa, phải chọn bài thay thế cùng chủ đề, tạo lại hai danh sách ID, ghi lý do trong `split_history.json` và commit khóa mới **trước khi viết gold**. Không tự đổi split sau khi bắt đầu gắn nhãn.
- Nếu loại bài test, giữ lại tối thiểu 40 bài test và 50 bài tổng; nếu không đạt ngưỡng thì phải bổ sung/thay mẫu và khóa lại trước khi gắn nhãn.

## 8. Thử nghiệm trên dev và khóa guideline

1. **Pilot:** A1 và A2 viết độc lập tóm tắt cho ít nhất 5 bài dev; lưu hai bản riêng trong `pilot_drafts.csv`, chưa ghi chúng thành gold. Pilot đề xuất: `DT05-004`, `DT05-059` (doanh nghiệp), `DT05-006` (vĩ mô), `DT05-018` (ít số liệu), `DT05-011` (tiền tệ/ngân hàng).
2. **So sánh:** đối chiếu từng cặp theo checklist mục 9. Liệt kê chỗ bất đồng và phân loại (mục 10).
3. **Sửa guideline:** bổ sung quy tắc cho các tình huống phát sinh, kèm ví dụ. Đánh dấu phiên bản mới trong bảng thay đổi cuối tệp.
4. **Hoàn thành 10 bài dev** theo phiên bản mới.
5. **Khóa v1.0:** ghi ngày khóa vào bảng thay đổi, rồi mới bắt đầu viết gold cho test.

Sau khi khóa:
- Mỗi dòng gold ghi `guideline_version`. Nếu phải đổi quy tắc, tăng phiên bản (v1.1...) và rà lại các bài đã viết.
- **Không sửa guideline hay tóm tắt tham chiếu dựa trên kết quả mô hình.** Người gắn nhãn không được xem đầu ra của E0/E1/E2 trên bài test trước khi gold test hoàn tất.
- Nếu cần ví dụ few-shot cho prompt, chỉ lấy từ bài dev, không dùng tóm tắt tham chiếu của test.

## 9. Checklist tự kiểm (mỗi bài)

- [ ] 3–5 câu, 50–120 từ, văn xuôi.
- [ ] Ý chính của bài đã có trong câu đầu.
- [ ] Mọi số liệu trong tóm tắt **có trong thân bài** (kiểm bằng cách tìm lại, không dựa vào trí nhớ).
- [ ] Giá trị, dấu thập phân, đơn vị khớp bài (3,2% không thành 32%; tỷ không thành triệu).
- [ ] Số nào cũng có chủ thể, kỳ và (nếu bài có) cơ sở so sánh.
- [ ] Dự báo, ước tính, kế hoạch không bị viết thành sự thật.
- [ ] Không có thông tin, nhận định hay năm tháng tự thêm.
- [ ] Không gộp số liệu của các nhóm/chỉ tiêu khác nhau; không lấy năm chỉ có trong tiêu đề.
- [ ] Mỗi số liệu có một dòng trong `gold_numeric_facts.csv` kèm câu nguồn.
- [ ] Không chép nguyên `description` mà chưa đối chiếu với thân bài.

## 10. Rà soát và xử lý bất đồng

Người rà soát kiểm từng số liệu với thân bài và đọc checklist mục 9. Mỗi chênh lệch được phân loại:

| Loại | Ví dụ | Cách xử lý |
|---|---|---|
| **A. Sai dữ kiện** (khách quan) | Sai số, đơn vị, kỳ, chủ thể; có thông tin không có trong bài | Sửa theo thân bài, không cần tranh luận. Người gắn nhãn sửa, R xác nhận. |
| **B. Chọn ý** (chủ quan) | Hai người chọn số liệu hay ý chính khác nhau, cả hai đều đúng | Giữ bản của người gắn nhãn; ghi nhận lựa chọn khác trong `review_log.csv`. Không sửa chỉ vì sở thích của R. |
| **C. Diễn đạt** | Khác cách dùng từ, độ dài | Không sửa. |

Mỗi bài được rà soát hoặc loại ghi một dòng vào `review_log.csv`: `item_id`, `decision` (`keep`/`exclude`), `reason`, `annotator_id`, `reviewer_id`, `disagreement` (loại A/B/C và mô tả ngắn), `resolution`, `guideline_version`, `reviewed_at`. Với bất đồng loại A, sửa theo thân bài và để reviewer xác nhận.

Thống kê cần báo cáo trong `data_quality_report.md`: số bài được rà soát, tỷ lệ bài có chênh lệch loại A và B, các loại lỗi phổ biến.

Nếu bất đồng loại B không giải quyết được, ghi `unresolved` và để bản của A. Với hai người cùng không chắc, hỏi người thứ ba hoặc giảng viên, không để tùy tiện.

## 11. Dùng LLM hỗ trợ

- Khuyến nghị **viết tay** (`draft_source=human`). Khi chưa có bản nháp, để `draft_source` trống.
- Nếu dùng LLM tạo bản nháp: người viết phải đối chiếu **từng số** với thân bài và chỉnh sửa. Ghi trong cột `draft_source` (`human` hoặc `llm_edited`) và ghi vào nhật ký sử dụng AI (tên mô hình, ngày, prompt).
- **Không dùng chính mô hình sẽ chạy ở E1/E2** để tạo bản nháp. Làm vậy có thể khiến ROUGE thiên về mô hình đó, và phải khai báo nếu xảy ra.
- Nhãn do LLM tạo ra mà chưa được người kiểm chứng **không được coi là gold**.

## 12. Ví dụ minh họa (tự soạn, không lấy từ dataset)

**Đoạn bài giả định:**
> Theo Tổng cục Thống kê, chỉ số giá tiêu dùng (CPI) tháng 10/2026 tăng 3,2% so với cùng kỳ năm trước và tăng 0,4% so với tháng trước. Giá nhóm giao thông tăng mạnh do giá xăng dầu điều chỉnh. Cơ quan này dự báo CPI bình quân cả năm khoảng 3,5%.

**Tóm tắt đạt:**
> Tổng cục Thống kê cho biết CPI tháng 10/2026 tăng 3,2% so với cùng kỳ năm trước và tăng 0,4% so với tháng trước. Nhóm giao thông tăng mạnh vì giá xăng dầu được điều chỉnh. Cơ quan này dự báo CPI bình quân cả năm khoảng 3,5%.

**Các lỗi hay gặp:**

| Bản viết | Lỗi | Lý do |
|---|---|---|
| "CPI tháng 10 tăng 32%" | Sai số | Mất dấu phẩy thập phân |
| "CPI tăng 3,2% so với tháng trước" | Sai kỳ | Bài nói so với cùng kỳ năm trước |
| "CPI cả năm sẽ đạt 3,5%" | Sai mức chắc chắn | Bài chỉ nói dự báo "khoảng 3,5%" |
| "Bộ Tài chính cho biết CPI..." | Sai chủ thể | Nguồn là Tổng cục Thống kê |
| "Giá xăng dầu tăng 8%" | Bịa số | Bài không nêu con số này |
| "CPI tháng 10 tăng 3,2%" | Thiếu kỳ so sánh | Không rõ so với kỳ nào |

## 13. Bảng thay đổi phiên bản

| Phiên bản | Ngày | Thay đổi | Người cập nhật |
|---|---|---|---|
| v0.1 | 2026-11-25 | Bản nháp ban đầu | |
| v0.2 | 2026-11-25 | Thêm pilot IDs, hai annotator A1/A2 (A1=Cường, A2=Hoàng), schema ghi loại bài, `draft_source`, phiếu số liệu và quy tắc xử lý bất đồng | |
| v0.3 | 2026-11-25 | Làm rõ không gộp số liệu giữa các nhóm, không thêm năm chỉ xuất hiện trong tiêu đề, và phân biệt số liệu chính sách đề xuất/kế hoạch theo kết quả pilot | |
| v1.0 | 2026-11-25 | Khóa sau khi hoàn tất 10 bài dev, xác minh phiếu số liệu và rà chéo theo phân công | Cường (A1) |
