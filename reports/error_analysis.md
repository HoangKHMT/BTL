# Phân tích lỗi (Error Analysis) — ĐT05

Tài liệu này phân tích chi tiết **10 trường hợp lỗi cụ thể** trên tập `dev` (10 bài) theo cấu trúc Mục 6.3 và Phụ lục B của hướng dẫn BTL CSC4007.

> [!NOTE]
> **Quy tắc bản quyền & trạng thái thực nghiệm:** Theo [`../evaluation_protocol.md`](../evaluation_protocol.md), báo cáo không trích nguyên văn đoạn văn bản bài báo hay gold summary của `VLUS06/VietOnlineNews`, mà mô tả đối tượng, số liệu/đơn vị, chỉ số định lượng và lỗi quan sát được. Hiện tại **E0 (`Lead-3`)** đã hoàn tất trên 10 bài `dev`; các cột **E1** và **E2** được để sẵn ở trạng thái `[Chờ chạy E1/E2 với OLLAMA_API_KEY]` và sẽ được điền sau khi chạy thực nghiệm trên `dev` và `test`.

---

## Tổng quan lỗi hệ thống trên Baseline E0 (`Lead-3`, `dev` n=10)

| Nhóm lỗi | Số bài dev bị ảnh hưởng | Đặc trưng quan sát được |
|---|---:|---|
| Bỏ sót số liệu then chốt ở giữa/cuối bài | 8/10 | `DT05-006`, `DT05-059`, `DT05-020` có `gold_fact_surface_recall = 0.0000`; trung bình macro toàn dev chỉ đạt `0.2533`. |
| Vượt giới hạn độ dài 50–120 từ | 2/10 | `DT05-004` (188 từ) và `DT05-006` (168 từ) do 3 câu đầu chứa câu dẫn/lời phát biểu quá dài. |
| Trích nhầm số phi kinh tế (ngày, điều luật, số trang) thành claim | 6/10 | `24/40` ứng viên trên dev chỉ là `value_only` (ngày `12.8`, `10.12`, Điều `257`, Luật `2024`, `462` trang...). |
| Lỗi tách token đơn vị viết liền (`30.000m2`) | 1/10 | `DT05-018`: `TOKEN_RE` có lookahead `(?!\w)` nên bỏ sót `30.000` khi `m2` viết liền; đã sửa trong `evaluate.py` (`source_surface_status`). |
| Nhiễu khoảng trắng/chú thích ảnh từ dữ liệu nguồn | 2/10 | `DT05-017` (`ThuếTPHCMvừa`), `DT05-059` (lẫn tên nhiếp ảnh gia trong caption đầu bài). |

---

## Chi tiết 10 trường hợp lỗi cụ thể

### 1. `DT05-004` — Lỗi vượt độ dài và thiếu mức thuế suất cốt lõi
- **item_id và loại lỗi:** `DT05-004` | Vượt độ dài (`188` từ > `120` từ), lặp số liệu và thiếu chi tiết chính sách trọng tâm.
- **Đầu vào / nguồn / chứng cứ hợp lệ:** Bài thuộc chủ đề `doanh_nghiep` (589 từ, 6 ứng viên số liệu) về đề xuất sửa đổi ngưỡng doanh thu chịu thuế TNCN và GTGT cho hộ kinh doanh.
- **Gold hoặc đáp án tham chiếu:** Nêu rõ 4 dữ kiện chính (`200 triệu đồng`, `500 triệu đồng`, ngưỡng trần `3 tỉ đồng` và thuế suất `15%` trên thu nhập thực tế) trong 3 câu cô đọng.
- **Prediction E0 / E1 / E2:**
  - **E0 (`Lead-3`):** `188` từ (3 câu), ROUGE-L `0.2394`, khớp `3/3` claim bề mặt nhưng chỉ đạt `2/4` (`0.5000`) gold fact recall; lặp lại `500 triệu đồng/năm` hai lần và bỏ sót `15%` và `3 tỉ đồng`.
  - **E1:** `[Chờ chạy dev E1]`
  - **E2:** `[Chờ chạy dev E2]`
- **Nguyên nhân khả dĩ:** Câu 1 của bài báo là một câu mở đầu văn bản hành chính dài 126 từ, khiến Lead-3 tiêu tốn gần toàn bộ dung lượng vào phần dẫn nhập và cắt trước khi tới đoạn nêu thuế suất `15%`.
- **Ảnh hưởng của lỗi đến người dùng:** Người đọc nắm được ngưỡng miễn thuế mới nhưng thiếu thông tin về mức thuế suất `15%` áp cho nhóm trên ngưỡng — yếu tố quyết định nghĩa vụ thuế thực tế.
- **Đề xuất thay đổi và phép thử kế tiếp:** So sánh với E1/E2 dùng prompt giới hạn `50–120` từ để kiểm tra khả năng nén câu dẫn hành chính và giữ đủ cả ngưỡng lẫn thuế suất.

### 2. `DT05-006` — Bỏ sót toàn bộ số liệu hiệu quả kinh tế (`0/4` gold facts)
- **item_id và loại lỗi:** `DT05-006` | Thiếu toàn bộ dữ kiện định lượng cốt lõi, ROUGE-L thấp nhất dev (`0.1245`), vượt độ dài (`168` từ).
- **Đầu vào / nguồn / chứng cứ hợp lệ:** Bài `vi_mo` (489 từ) đưa tin hội thảo kinh tế số; các số liệu định lượng (`16%`, `25%`, `19 triệu USD` trong `8 tháng`) nằm ở nửa sau thân bài.
- **Gold hoặc đáp án tham chiếu:** Nêu kết quả định lượng tách riêng theo từng nhóm đối tượng (dịch vụ ăn uống giảm `16%`, bán lẻ tiết kiệm `25%`, nhà máy đạt `19 triệu USD` trong `8 tháng`).
- **Prediction E0 / E1 / E2:**
  - **E0 (`Lead-3`):** `168` từ, ROUGE-L `0.1245`, `0/2` exact value+unit match (`12.8` là ngày hội thảo, `2.100` là số hộ kinh doanh), `0/4` gold fact recall.
  - **E1:** `[Chờ chạy dev E1]`
  - **E2:** `[Chờ chạy dev E2]`
- **Nguyên nhân khả dĩ:** Cấu trúc bài báo hội thảo đặt thông tin sự kiện/địa điểm/diễn giả ở 3 câu đầu, đẩy số liệu thực chứng xuống các đoạn ví dụ bên dưới.
- **Ảnh hưởng của lỗi đến người dùng:** Tóm tắt chỉ cho biết "có hội thảo thành công" mà không cung cấp bất kỳ bằng chứng định lượng nào về hiệu quả kinh tế.
- **Đề xuất thay đổi và phép thử kế tiếp:** Kiểm tra xem E1/E2 có trích được đủ 3 số liệu tách riêng theo từng chủ thể mà không gộp thành khoảng `16–25%` (lỗi gộp nhóm đã cảnh báo trong guideline v0.3).

### 3. `DT05-011` — Thiếu bối cảnh thị trường tự do/quốc tế và thiếu mẫu số đơn vị tỷ giá
- **item_id và loại lỗi:** `DT05-011` | Lệch phân bố ý chính (`1/6` gold fact recall) và thiếu mẫu số đơn vị (`đồng` thay vì `đồng/USD`).
- **Đầu vào / nguồn / chứng cứ hợp lệ:** Bài `tien_te_ngan_hang` (390 từ, 26 ứng viên số liệu) cập nhật tỷ giá trung tâm, giá USD tự do và dự báo xác suất Fed cắt giảm lãi suất.
- **Gold hoặc đáp án tham chiếu:** Kết hợp 3 tầng thông tin: tỷ giá trung tâm (`25.155 đồng/USD`), giá USD tự do (`27.240` / `27.340 đồng`), và dự báo Fed giảm lãi suất (`87,4%` cho mức `0,25%`).
- **Prediction E0 / E1 / E2:**
  - **E0 (`Lead-3`):** ROUGE-L `0.2993`; liệt kê 5 mức giá ngân hàng thương mại đầu bài (trùng `26.412 đồng` 2 lần), regex bắt ngày `10.12` thành `dot_decimal`, chỉ khớp `1/6` gold facts (`0.1667`).
  - **E1:** `[Chờ chạy dev E1]`
  - **E2:** `[Chờ chạy dev E2]`
- **Nguyên nhân khả dĩ:** Tin thị trường tỷ giá liệt kê bảng giá ngân hàng ngay phần mở đầu, khiến Lead-3 quá tải các con số mua/bán cục bộ và bỏ qua xu hướng tự do/Fed.
- **Ảnh hưởng của lỗi đến người dùng:** Không nắm được diễn biến giảm trên thị trường tự do và động lực vĩ mô từ Fed dù đây là thông tin phân biệt bản tin ngày hôm đó.
- **Đề xuất thay đổi và phép thử kế tiếp:** Đánh giá E2 xem prompt ưu tiên số liệu then chốt có chọn được bộ 3 tầng (trung tâm – tự do – Fed) mà không bịa thêm `/USD` nếu bài chỉ viết `đồng`.

### 4. `DT05-017` — Nhiễu khoảng trắng nguồn và bỏ sót doanh nghiệp nợ lớn nhất
- **item_id và loại lỗi:** `DT05-017` | Nhiễu tokenization/khoảng trắng từ thân bài gốc và bỏ sót thực thể trọng tâm.
- **Đầu vào / nguồn / chứng cứ hợp lệ:** Bài `xuat_nhap_khau` (429 từ) về danh sách nợ thuế tại TP.HCM (`31.655` người nộp thuế, tổng nợ `25.356 tỷ đồng`, doanh nghiệp đầu bảng nợ hơn `1.828 tỷ đồng`).
- **Gold hoặc đáp án tham chiếu:** Nêu tổng quan `31.655` người nộp thuế / `25.356 tỷ đồng`, nêu đích danh trường hợp nợ lớn nhất (`1.828 tỷ đồng`) và mục đích xử lý của cơ quan thuế.
- **Prediction E0 / E1 / E2:**
  - **E0 (`Lead-3`):** ROUGE-L cao nhất nhì dev (`0.4412`), nhưng chép nguyên chuỗi dính chữ `ThuếTPHCMvừa` và `tiềnthuếvà`, trích `27` (chi cục) và `462` (số trang) làm bare claims, và chỉ đạt `1/3` gold fact recall (`0.3333`).
  - **E1:** `[Chờ chạy dev E1]`
  - **E2:** `[Chờ chạy dev E2]`
- **Nguyên nhân khả dĩ:** Lỗi dính chữ từ nguồn HTML gốc sau khi loại thẻ HTML; Lead-3 dừng trước đoạn nêu chi tiết doanh nghiệp nợ đứng đầu.
- **Ảnh hưởng của lỗi đến người dùng:** Mất tính dễ đọc do lỗi dính chữ và thiếu thông tin định danh doanh nghiệp chiếm tỷ trọng nợ lớn.
- **Đề xuất thay đổi và phép thử kế tiếp:** LLM ở E1/E2 được kỳ vọng tự chuẩn hóa câu chữ trôi chảy; cần kiểm tra không làm biến đổi con số `25.356 tỷ đồng` hay `1.828 tỷ đồng`.

### 5. `DT05-018` — Lỗi regex bề mặt với đơn vị viết liền (`30.000m2`)
- **item_id và loại lỗi:** `DT05-018` | Lỗi bộ kiểm chứng bề mặt (`source_surface_status = not_found` dù xuất hiện nguyên văn trong bài) + thiếu thông tin tiến độ thanh lý.
- **Đầu vào / nguồn / chứng cứ hợp lệ:** Bài `bat_dong_san` (334 từ, ít số liệu) về việc thu hồi/chấm dứt dự án `30.000m2`, thời hạn `6 tháng`.
- **Gold hoặc đáp án tham chiếu:** Nêu quyết định chấm dứt dự án `30.000 m2`, hiện trạng khu đất, mốc `6 tháng` và hướng xử lý tiếp theo của nhà đầu tư.
- **Prediction E0 / E1 / E2:**
  - **E0 (`Lead-3`):** ROUGE-L `0.1714`; trên bản E0 ghi nhận tại commit `c9ba26c`, `30.000 m2` bị đánh dấu `not_found` (`0/4` exact match) do `TOKEN_RE` trong `check_gold.py` dùng `(?!\w)` nên bỏ sót `30.000` khi viết liền `30.000m2`, trong khi `evaluate.py` trước bản vá không cộng `source_analysis["facts"]` vào `source_values`. Đồng thời Lead-3 coi số nhà `151`, `153` và số quyết định `231` là bare numeric claims.
  - **E1:** `[Chờ chạy dev E1]`
  - **E2:** `[Chờ chạy dev E2]`
- **Nguyên nhân khả dĩ:** Lỗi kỹ thuật trong `source_surface_status` của `evaluate.py` (chưa hợp nhất `facts` vào `source_values`). Nếu không vá, cơ chế `regenerate_once_then_drop` ở E2 sẽ loại nhầm câu chứa `30.000m2` hoặc `50.000m2`!
- **Ảnh hưởng của lỗi đến người dùng:** Cảnh báo giả (`false positive hallucination`) hoặc xóa nhầm thông tin diện tích hợp lệ trong E2.
- **Đề xuất thay đổi và phép thử kế tiếp:** Đã vá `source_surface_status()` trong `src/evaluate.py` và bổ sung test hồi quy trong `tests/test_pipeline.py`; giữ nguyên số liệu E0 commit `c9ba26c` làm mốc lịch sử và kiểm chứng lại trên E2.

### 6. `DT05-020` — Toàn bộ claim là số hiệu điều luật/ngày tháng (`0%` khớp đơn vị, `0/2` gold facts)
- **item_id và loại lỗi:** `DT05-020` | Bài chính sách ít số liệu định lượng: Lead-3 trích 7 số hiệu điều luật/ngày tháng, bỏ sót quy định áp dụng bảng giá mới từ `1/1/2026`.
- **Đầu vào / nguồn / chứng cứ hợp lệ:** Bài `khac` (431 từ, `has_numbers=False`) giải thích quy định chuyển tiếp bảng giá đất theo Luật Đất đai 2024.
- **Gold hoặc đáp án tham chiếu:** Nêu mốc chuyển tiếp `31/12/2025`, mốc áp dụng bảng giá mới `1/1/2026` điều chỉnh hằng năm và tác động chi phí làm sổ đỏ.
- **Prediction E0 / E1 / E2:**
  - **E0 (`Lead-3`):** ROUGE-L `0.2247`; regex trích 7 số (`2024`, `1`, `8`, `1`, `257`, `2024`, `2013`) toàn bộ ở trạng thái `value_only`, không bắt được mốc `1/1/2026` nằm ở đoạn sau (`0/2` gold facts).
  - **E1:** `[Chờ chạy dev E1]`
  - **E2:** `[Chờ chạy dev E2]`
- **Nguyên nhân khả dĩ:** `PERIOD_RE` chưa phủ dạng `ngày dd/mm/yyyy` khi đứng lẻ hoặc bị cắt ở câu đầu; mặt khác các số như `Điều 257`, `khoản 1` không phải số liệu kinh tế.
- **Ảnh hưởng của lỗi đến người dùng:** Tóm tắt chỉ dừng ở trích dẫn điều khoản luật mà không trả lời câu hỏi thực tế của tiêu đề: từ khi nào chi phí làm sổ đỏ thay đổi.
- **Đề xuất thay đổi và phép thử kế tiếp:** Kiểm tra trên E1/E2 khả năng tổng hợp tác động chính sách và giữ đúng mốc `31/12/2025` vs `1/1/2026` không bị đảo ngược.

### 7. `DT05-043` — Thiếu dữ kiện quy mô cơ sở (`7.400 m2`) và thông tin địa điểm
- **item_id và loại lỗi:** `DT05-043` | Bỏ sót 1/2 dữ kiện số quan trọng và chi tiết thực thi ở thân bài.
- **Đầu vào / nguồn / chứng cứ hợp lệ:** Bài `hang_hoa` (753 từ) về dự án đầu tư trung tâm sản xuất/phân phối cà phê tại Trung Quốc (`220 triệu USD`, diện tích `7.400 m2`).
- **Gold hoặc đáp án tham chiếu:** Nêu khoản đầu tư `220 triệu USD`, địa điểm cụ thể, quy mô `7.400 m2`, mục tiêu chuỗi cung ứng và vai trò thị trường Trung Quốc.
- **Prediction E0 / E1 / E2:**
  - **E0 (`Lead-3`):** ROUGE-L `0.2737`, khớp đúng `220 triệu USD` (`1/1` surface match) nhưng chỉ đạt `1/2` gold fact recall vì thông tin `7.400 m2` nằm sau 3 câu đầu.
  - **E1:** `[Chờ chạy dev E1]`
  - **E2:** `[Chờ chạy dev E2]`
- **Nguyên nhân khả dĩ:** Bài dài 753 từ có phần mở đầu mang tính bình luận/dẫn dắt tổng quát, đẩy chi tiết vận hành xuống giữa bài.
- **Ảnh hưởng của lỗi đến người dùng:** Thiếu quy mô vật lý và bối cảnh triển khai cụ thể của dự án.
- **Đề xuất thay đổi và phép thử kế tiếp:** Kiểm tra E1/E2 có giữ chính xác cả `220 triệu USD` và `7.400 m2` không bị làm tròn hay đổi đơn vị.

### 8. `DT05-047` — Bỏ sót rủi ro nợ vàng cốt lõi (`5.833 lượng vàng`, `804 tỷ đồng` lãi)
- **item_id và loại lỗi:** `DT05-047` | Mất trọng tâm câu chuyện tài chính dù nhận diện đúng các số giao dịch cổ phiếu (`1/3` gold facts).
- **Đầu vào / nguồn / chứng cứ hợp lệ:** Bài `chung_khoan` (513 từ, 23 ứng viên số liệu) về doanh nghiệp mua cổ phiếu dù đang gánh khoản vay `5.833 lượng` vàng SJC với tiền lãi vượt `804 tỷ đồng`.
- **Gold hoặc đáp án tham chiếu:** Nêu tỷ lệ sở hữu mới (`14,89%`) đồng thời làm rõ gánh nặng nợ `5.833 lượng` vàng SJC, lãi vượt `804 tỷ đồng` và vướng mắc đấu giá/kiện tụng.
- **Prediction E0 / E1 / E2:**
  - **E0 (`Lead-3`):** ROUGE-L `0.2073`; trích đúng `4/5` claim giao dịch cổ phiếu (`1,5 triệu`, `766.000 cổ phiếu`, `5%`, `14,89%`), nhưng hoàn toàn không đề cập khoản vay vàng và lãi vay nằm ở nửa sau bài (`1/3` gold fact recall).
  - **E1:** `[Chờ chạy dev E1]`
  - **E2:** `[Chờ chạy dev E2]`
- **Nguyên nhân khả dĩ:** Tin doanh nghiệp/chứng khoán thường công bố giao dịch cổ phiếu ở 3 câu đầu rồi mới phân tích báo cáo tài chính/nợ phải trả ở đoạn sau.
- **Ảnh hưởng của lỗi đến người dùng:** Gây hiểu lệch hoàn toàn bức tranh sức khỏe tài chính của doanh nghiệp (chỉ thấy mua thêm cổ phiếu mà không thấy rủi ro nợ vàng).
- **Đề xuất thay đổi và phép thử kế tiếp:** Thử nghiệm E1/E2 xem mô hình có cân bằng được giữa sự kiện mua cổ phiếu và rủi ro nợ vàng/lãi vay mà không nhầm chủ thể ngân hàng.

### 9. `DT05-050` — Thiếu lượng thịt nhiễm khuẩn bị chặn (`1.320 tấn`) và bắt nhầm số hiệu thông tư
- **item_id và loại lỗi:** `DT05-050` | Đạt ROUGE-L cao nhất dev (`0.3837`) nhưng thiếu hệ quả định lượng chính (`1/5` gold facts).
- **Đầu vào / nguồn / chứng cứ hợp lệ:** Bài `xuat_nhap_khau` (557 từ) về nhập khẩu thịt (`1,24 tỷ USD`, tăng `19,2%`), phát hiện `55` lô dương tính Salmonella trên `6.679` lô xét nghiệm (gần `1%`), ngăn chặn nguy cơ nhập `1.320 tấn` thịt nhiễm khuẩn.
- **Gold hoặc đáp án tham chiếu:** Tổng hợp đầy đủ quy mô nhập khẩu `1,24 tỷ USD`, tỷ lệ nhiễm `55/6.679` lô (gần `1%`) và lượng rủi ro `1.320 tấn`.
- **Prediction E0 / E1 / E2:**
  - **E0 (`Lead-3`):** Câu 3 bị cắt giữa chừng ở dấu ba chấm của trích dẫn quy chuẩn; đạt `2/6` exact match (`1,24 tỷ USD`, `19,2%`), `4` bare numbers (`04` của Thông tư 04, `25` và `9` của ngày `25/9`, `55` lô), chỉ khớp `1/5` gold facts (`0.2000`).
  - **E1:** `[Chờ chạy dev E1]`
  - **E2:** `[Chờ chạy dev E2]`
- **Nguyên nhân khả dĩ:** Số liệu tổng hợp kết quả xét nghiệm (`6.679` lô, `1%`, `1.320 tấn`) nằm sau phần liệt kê danh sách quốc gia xuất khẩu.
- **Ảnh hưởng của lỗi đến người dùng:** Thiếu quy mô rủi ro an toàn thực phẩm (`1.320 tấn`) và mẫu số xét nghiệm (`6.679` lô) để hiểu tỷ lệ nhiễm khuẩn thực chất.
- **Đề xuất thay đổi và phép thử kế tiếp:** Kiểm tra E1/E2 có ghép đúng mẫu số `55/6.679` lô và giữ nguyên trạng thái giả định ("có thể đã nhập khẩu gần 1.320 tấn nếu không xét nghiệm").

### 10. `DT05-059` — Nhiễu caption ảnh đầu bài, bỏ sót 100% dữ kiện tài chính (`0/2` gold facts)
- **item_id và loại lỗi:** `DT05-059` | Nhiễu dữ liệu đầu vào (caption ảnh + lỗi dính chữ) khiến Lead-3 không chứa bất kỳ số liệu tài chính nào.
- **Đầu vào / nguồn / chứng cứ hợp lệ:** Bài `doanh_nghiep` (868 từ) về việc Sacombank chưa chia cổ tức dù lợi nhuận giữ lại `18.387 tỉ đồng` và tiến độ đấu giá `32,5%` cổ phần STB tại VAMC.
- **Gold hoặc đáp án tham chiếu:** Nêu việc chưa chia cổ tức, mức lợi nhuận giữ lại `18.387 tỉ đồng`, điều kiện phê duyệt tái cơ cấu và tỷ lệ `32,5%` cổ phần STB tại VAMC.
- **Prediction E0 / E1 / E2:**
  - **E0 (`Lead-3`):** ROUGE-L thấp thứ hai dev (`0.1512`); mở đầu dính tên nhiếp ảnh gia và cụm dính chữ `củaSacombankdự`, trích đúng 2 bare claims từ ngày `26-4` (`26`, `4`), `0/2` gold fact recall.
  - **E1:** `[Chờ chạy dev E1]`
  - **E2:** `[Chờ chạy dev E2]`
- **Nguyên nhân khả dĩ:** Bài báo dài (868 từ) mở đầu bằng chú thích ảnh và bối cảnh tổ chức ĐHĐCĐ, đẩy toàn bộ số liệu tài chính xuống phần thân bài.
- **Ảnh hưởng của lỗi đến người dùng:** Người đọc không nhận được con số lợi nhuận giữ lại hay tỷ lệ cổ phần VAMC — hai nguyên nhân trực tiếp giải thích câu hỏi ở tiêu đề.
- **Đề xuất thay đổi và phép thử kế tiếp:** Kiểm tra khả năng LLM (E1/E2) lọc bỏ nhiễu caption ảnh và trích đúng `18.387 tỉ đồng` cùng `32,5%`.
