# Data Quality Report (tự sinh bởi data/prepare_data.py)

- Dataset: `VLUS06/VietOnlineNews` | revision: `bd8d2a865c8981d34cb9d85f69f62bda7c40b520` | retrieved_at: 2026-11-25T09:51:48+07:00
- Seed: 42 | guideline: v1.0
- `published_at` = unknown (dataset không có cột ngày đăng; không suy ra từ ngày tải).
- license_status = OTHER_UNVERIFIED: Hub khai báo `other`; file LICENSE rỗng; quyền sử dụng/tái phân phối chưa được xác minh.

## 1. Kiểm đếm trước/sau từng bước

| Bước | Số bị loại | Còn lại |
|---|---:|---:|
| Tổng số dòng ban đầu (mọi split, 13 chuyên mục) | 0 | 265729 |
| Giữ chuyên mục ['Kinh doanh', 'Bất động sản'] | 225851 | 39878 |
| ID trùng | 0 | 39878 |
| Tiêu đề/nội dung rỗng | 0 | 39878 |
| Trùng nội dung chính xác | 0 | 39878 |
| Trùng tiêu đề | 155 | 39723 |
| Độ dài ngoài [250, 900] từ | 12712 | 27011 |
| Lấy ngẫu nhiên pool 4000 bài (seed=42) - bước lấy mẫu, không phải loại lỗi | 23011 | 4000 |
| Gần trùng/đăng lại (TF-IDF cosine >= 0.8) | 27 | 3973 |
| Chọn mẫu cuối (đa dạng chủ đề, event-sim < 0.4) | 3913 | 60 |

Danh sách ID bị loại và lý do: `reports/excluded_items.csv`.

## 2. Phân bố chuyên mục của toàn dataset (13 nhãn gốc)

| Chuyên mục | Số bài |
|---|---:|
| Giải trí | 40864 |
| Kinh doanh | 33242 |
| Thể thao | 32278 |
| Thời sự | 27399 |
| Giáo dục | 22433 |
| Khoa học công nghệ | 21008 |
| Đời sống | 19116 |
| Xe | 18805 |
| Sức khỏe | 16666 |
| Thế giới | 14847 |
| Du lịch | 9179 |
| Bất động sản | 6636 |
| Pháp luật | 3256 |

## 3. Mẫu đã chọn

- Tổng: 60 | dev: 10 | test: 50
- Bài có số liệu (>= 4 dữ kiện): 48 | dev: 8 | test: 40
- Bài đánh dấu hậu kiểm chéo: 15 (25%)
- Số từ: min 283, trung vị 559, max 899
- Số dữ kiện định lượng/bài: min 0, trung vị 8, max 32

| Chuyên mục gốc | Số bài |
|---|---:|
| Kinh doanh | 52 |
| Bất động sản | 8 |

| Chủ đề (gán bằng từ khóa) | Tổng | Dev | Test |
|---|---:|---:|---:|
| bat_dong_san | 7 | 2 | 5 |
| chung_khoan | 7 | 2 | 5 |
| doanh_nghiep | 8 | 0 | 8 |
| hang_hoa | 8 | 2 | 6 |
| khac | 8 | 0 | 8 |
| tien_te_ngan_hang | 7 | 2 | 5 |
| vi_mo | 7 | 1 | 6 |
| xuat_nhap_khau | 8 | 1 | 7 |

## 4. Cờ chất lượng trong mẫu chọn

- Nội dung còn thẻ HTML trước khi làm sạch: 0
- Nội dung bị đổi khi chuẩn hóa Unicode NFC: 0
- Bài có số kiểu dấu chấm thập phân (vd 3.2%) cần xem tay: 0 -> không có
- Bài ít/không có số liệu: 12
- Rà soát số liệu: regex tạo ứng viên, không xác nhận tính đúng; đối chiếu ngữ cảnh, đơn vị, kỳ và ý nghĩa. Mẫu kiểm tra ở mục 7.

## 5. Chống rò rỉ (leakage)

- Gần trùng loại bỏ ở ngưỡng cosine 0.8; khi chọn mẫu, không chọn 2 bài có cosine >= 0.4 (tránh cùng sự kiện nằm ở cả dev và test).
- Mỗi bài chỉ xuất hiện đúng một lần (một bài = một mẫu, không chia chunk).
- Giới hạn: kiểm tra trùng chỉ thực hiện trong pool ngẫu nhiên, không trên toàn bộ dataset; TF-IDF không bắt được bài viết lại bằng từ ngữ khác. Rà soát mẫu tiêu đề ở mục 7 cho thấy title-only dedup có thể loại nhầm bài khác nội dung.

## 6. Danh sách bài đã chọn

| item_id | document_id | split | chủ đề | số từ | số dữ kiện | tiêu đề |
|---|---|---|---|---:|---:|---|
| DT05-001 | 104164 | test | xuat_nhap_khau | 515 | 0 | Xuất khẩu sầu riêng bị gián đoạn, Chính phủ yêu cầu làm rõ trách nhiệm |
| DT05-002 | 1047 | test | bat_dong_san | 613 | 10 | Thị trường bất động sản phục hồi, chủ đầu tư CaraWorld ghi nhận kết qu |
| DT05-003 | 106023 | test | xuat_nhap_khau | 356 | 12 | Nóng: Ấn Độ ‘lộ’ tin sẽ siết thêm xuất khẩu gạo |
| DT05-004 | 106199 | test | doanh_nghiep | 589 | 6 | Bộ tài chính đề xuất tăng doanh thu tính thuế hộ kinh doanh lên 500 tr |
| DT05-005 | 106210 | test | vi_mo | 329 | 16 | Số thu thuế thu nhập cá nhân 11 tháng vượt kế hoạch cả năm |
| DT05-006 | 106438 | test | vi_mo | 489 | 8 | Ứng dụng chuyển đổi số, kinh tế số giúp hộ kinh doanh tiết kiệm tiền t |
| DT05-007 | 108411 | test | xuat_nhap_khau | 878 | 7 | Người trồng rừng có thêm nguồn thu hơn 1.000 tỉ đồng từ bán tín chỉ ca |
| DT05-008 | 108921 | test | vi_mo | 515 | 0 | IFC đầu tư vào nông nghiệp tại Việt Nam |
| DT05-009 | 110166 | test | hang_hoa | 417 | 15 | Giá vàng hôm nay 3.9.2025: SJC tăng sốc, áp sát ngưỡng 134 triệu đồng/ |
| DT05-010 | 110211 | test | tien_te_ngan_hang | 477 | 22 | Giá USD hôm nay 28.3.2023: Thị trường tự do thua xa ngân hàng |
| DT05-011 | 110518 | test | tien_te_ngan_hang | 390 | 26 | Giá USD hôm nay 10.12.2025: Đô tự do tiếp tục đi lùi |
| DT05-012 | 111333 | test | tien_te_ngan_hang | 301 | 16 | Giá USD hôm nay 13.4.2024: Đô la tự do đi lên |
| DT05-013 | 112618 | test | tien_te_ngan_hang | 348 | 16 | Giá USD hôm nay 22.10.2024: Đồng loạt tăng, đô tự do hướng đến 25.600  |
| DT05-014 | 112769 | dev | hang_hoa | 347 | 25 | Ba đơn vị trúng thầu 3.400 lượng vàng |
| DT05-015 | 112964 | test | hang_hoa | 404 | 20 | Giá vàng hôm nay 12.9.2025: Lao dốc khiến người mua lúc đỉnh lỗ 6 triệ |
| DT05-016 | 113410 | dev | tien_te_ngan_hang | 354 | 15 | Giá USD hôm nay 2.2.2024: 'Đô' tự do tiếp tục trượt giảm không phanh |
| DT05-017 | 148574 | test | xuat_nhap_khau | 429 | 8 | TPHCM công bố 462 trang doanh nghiệp nợ thuế: Địa ốc nợ 'khủng' cả ngh |
| DT05-018 | 150266 | test | bat_dong_san | 334 | 2 | Toàn cảnh khu đất dự án công viên Hello Kitty vừa bị thu hồi |
| DT05-019 | 152102 | test | bat_dong_san | 655 | 10 | Phòng trọ chục người ở chung chỉ cách nhau tấm rèm; ‘nóng’ đấu giá đất |
| DT05-020 | 152225 | test | khac | 431 | 0 | Không làm sổ đỏ trước 2026 người dân có thể phải đóng thêm nhiều tiền |
| DT05-021 | 152564 | test | khac | 476 | 16 | Hưng Yên đấu giá 138 suất đất, khởi điểm thấp nhất hơn 800 triệu đồng |
| DT05-022 | 152795 | dev | bat_dong_san | 871 | 15 | Thu nhập 15 triệu/tháng, gia đình trẻ loay hoay bài toán mua nhà |
| DT05-023 | 18532 | dev | xuat_nhap_khau | 790 | 2 | Lợi dụng thương mại điện tử để lừa đảo ngày càng tinh vi, khó lường |
| DT05-024 | 188463 | test | doanh_nghiep | 775 | 10 | Trung Quốc vượt mốc 1 TW điện mặt trời: 'Mỏ vàng' từ hàng triệu mái nh |
| DT05-025 | 188484 | test | doanh_nghiep | 754 | 7 | ‘Cây tiền’ mọc từ rừng: Cách ngôi làng nghèo kiếm hơn 1,9 tỷ đồng/năm |
| DT05-026 | 188967 | test | khac | 417 | 2 | Chiết xuất uranium từ nước biển, mở ra nguồn năng lượng giá rẻ vô tận |
| DT05-027 | 190415 | test | khac | 283 | 8 | Vietlott tìm thấy vé số trúng độc đắc lên tới hơn 127 tỷ đồng |
| DT05-028 | 190597 | test | doanh_nghiep | 879 | 16 | PNJ bị chuyển hồ sơ sang công an, cổ phiếu giảm mạnh |
| DT05-029 | 191064 | dev | bat_dong_san | 503 | 6 | 'Ông lớn' bất động sản Masterise Group thành tổ chức liên quan đến Tec |
| DT05-030 | 191755 | test | hang_hoa | 807 | 25 | Giá vàng vừa hạ vội bán tháo, nhiều người tiếc ‘đứt ruột’ khi vàng tăn |
| DT05-031 | 192232 | dev | chung_khoan | 727 | 13 | Công ty bà Đặng Thị Hoàng Yến không mua cổ phiếu Tân Tạo trước lệnh dừ |
| DT05-032 | 192868 | test | bat_dong_san | 534 | 11 | Ngân hàng xiết nợ chủ dự án bà Trương Mỹ Lan từng thâu tóm |
| DT05-033 | 19469 | test | khac | 724 | 5 | Dòng kim cương gây ‘sốt’ bởi kiểu cắt tinh xảo |
| DT05-034 | 194693 | dev | vi_mo | 896 | 15 | ‘Cá mập’ tiếp tục mua vàng, giá vàng duy trì ở mức cao |
| DT05-035 | 195089 | test | tien_te_ngan_hang | 782 | 2 | Khách tố tư vấn bảo hiểm không trung thực, Ngân hàng phản hồi |
| DT05-036 | 195222 | test | khac | 404 | 6 | Chính phủ đồng ý giảm thuế giá trị gia tăng từ 10% xuống 8% |
| DT05-037 | 195295 | test | hang_hoa | 443 | 30 | Bản tin tài chính sáng 8/4: Giá vàng giảm nhẹ, USD đi lên |
| DT05-038 | 195700 | test | xuat_nhap_khau | 353 | 4 | Facebook, Google, Apple... kê khai, nộp thuế 1.800 tỷ đồng |
| DT05-039 | 195870 | test | vi_mo | 885 | 8 | Cơ hội từ dân số vàng: Yếu tố then chốt cho tăng trưởng kinh tế |
| DT05-040 | 196457 | test | vi_mo | 629 | 32 | Khách quốc tế đến Việt Nam tăng kỷ lục tháng đầu năm |
| DT05-041 | 197066 | dev | hang_hoa | 731 | 0 | Trả lại tàu bay cỡ nhỏ, Bamboo Airways dừng bay thẳng từ Hà Nội đến Cô |
| DT05-042 | 197521 | test | bat_dong_san | 804 | 18 | A0 rời EVN, Bộ Công Thương lo vốn khó khăn, cần tiền từ EVN |
| DT05-043 | 197536 | test | hang_hoa | 753 | 7 | Tham vọng của Starbucks khi đầu tư 'khủng' vào Trung Quốc |
| DT05-044 | 197757 | test | vi_mo | 480 | 20 | Bamboo Airways tiếp tục là hãng bay đúng giờ nhất 5 tháng đầu năm 2023 |
| DT05-045 | 197792 | test | doanh_nghiep | 561 | 2 | Phó Thủ tướng chỉ đạo xử nghiêm vi phạm của các ông lớn xây dựng khi t |
| DT05-046 | 198650 | test | doanh_nghiep | 894 | 9 | Về quê khởi nghiệp, cô gái giúp 1.100 hộ dân thoát nghèo, thu 231 tỷ đ |
| DT05-047 | 199155 | test | chung_khoan | 513 | 23 | Mắc kẹt với khoản vay hơn 5.800 lượng vàng SJC, DN vẫn chi tiền gom cổ |
| DT05-048 | 199506 | test | xuat_nhap_khau | 341 | 8 | Cá tra tỷ USD của Việt Nam đón tin vui thuế quan từ Mỹ |
| DT05-049 | 200780 | test | khac | 777 | 13 | Cua ‘quý tộc’ Trung Quốc thành hàng bình dân ở chợ Việt, mua dễ như ra |
| DT05-050 | 200833 | test | xuat_nhap_khau | 557 | 4 | Chi 1,24 tỷ USD nhập khẩu thịt, phát hiện hơn 1.300 tấn nhiễm khuẩn Sa |
| DT05-051 | 201028 | test | khac | 638 | 5 | Bánh trung thu siêu khủng đổ bộ, hàng Trung Quốc ‘thượng hạng’ giá rẻ  |
| DT05-052 | 202622 | test | chung_khoan | 787 | 9 | Tỷ phú Warren Buffett tiền mặt khủng, chờ gom hàng giá hời |
| DT05-053 | 203148 | dev | tien_te_ngan_hang | 865 | 7 | Cần lưu ý gì khi rút tiền mặt từ thẻ tín dụng? |
| DT05-054 | 22763 | test | chung_khoan | 505 | 2 | Cơ quan Phát triển Xuất khẩu Canada và Masan ký Bản ghi nhớ |
| DT05-055 | 23492 | dev | chung_khoan | 884 | 16 | Chứng khoán Việt giảm kỷ lục giữa sắc xanh toàn châu Á: Chuyên gia giả |
| DT05-056 | 24169 | test | chung_khoan | 430 | 11 | Vì sao Tập đoàn Đầu tư Việt Phương bán ra 17 triệu cổ phiếu, rút bớt v |
| DT05-057 | 24773 | test | chung_khoan | 775 | 4 | Một công ty chứng khoán nhập nhằng tiền khách hàng, vi phạm khi giao d |
| DT05-058 | 25128 | test | doanh_nghiep | 899 | 0 | Kiến nghị bỏ quy định bắt buộc mua bảo hiểm xe máy |
| DT05-059 | 25910 | test | doanh_nghiep | 868 | 8 | Sacombank ‘ngâm’ cổ tức: Cổ đông mong, vì sao ngân hàng chưa chia? |
| DT05-060 | 435 | test | hang_hoa | 628 | 2 | Vì sao đất rừng ở triền núi Nhỏ, Vũng Tàu được cấp thổ cư? |

## 7. Kiểm tra thủ công

Các ghi chú dưới đây là **AI-assisted pre-audit** dựa trên metadata/toàn văn cục bộ; không được tính là xác nhận độc lập của A1/A2. Các trường hợp có cờ `review`/`needs confirmation` cần người trong nhóm quyết định trước khi dùng làm bằng chứng nghiệm thu. Không đưa câu trích hoặc toàn văn vào báo cáo này.

### 7.1. Mẫu 9 cặp tiêu đề trùng

Lấy mẫu xác định từ danh sách 155 ID bị loại. So tiêu đề sau chuẩn hóa chữ thường/khoảng trắng và tính `SequenceMatcher.ratio()` trên nội dung sau chuẩn hóa khoảng trắng/chữ thường. Tỷ lệ là chỉ báo tương đồng chuỗi, không phải đánh giá ngữ nghĩa. Cả 9 cặp có tiêu đề trùng sau chuẩn hóa; không cặp nào có nội dung giống hệt.

| ID bị loại | ID cùng tiêu đề | Tương đồng nội dung | Ghi chú sàng lọc |
|---|---|---:|---|
| 23877 | 190219 | 0.930 | Nội dung tương đồng cao; có thể là bản đăng lại/cập nhật. |
| 199067 | 17993 | 0.964 | Nội dung tương đồng cao; có thể là bản đăng lại/cập nhật. |
| 195373 | 194829 | 0.305 | Nội dung khác đáng kể; cần người rà xác nhận có phải tin cập nhật khác ngày. |
| 195373 | 195052 | 0.208 | Nội dung khác đáng kể; cùng tiêu đề chung, cần xác nhận trước khi coi là trùng bài. |
| 110544 | 24181 | 0.704 | Tương đồng một phần; cần rà nội dung/phiên bản. |
| 23695 | 106844 | 0.051 | Nội dung rất khác; có nguy cơ loại nhầm bài chỉ vì headline giống. |
| 25230 | 110002 | 0.882 | Nội dung tương đồng cao; có thể là bản đăng lại/cập nhật. |
| 112933 | 113584 | 0.024 | Nội dung rất khác; có nguy cơ là các bản tin lãi suất riêng biệt. |
| 111889 | 25043 | 0.867 | Headline chỉ khác cách viết hoa; nội dung tương đồng cao. |

Tóm tắt sàng lọc: 4 cặp tương đồng chuỗi ≥0.85, 1 cặp ở mức 0.704, 4 cặp <0.35. Kết quả cho thấy loại trùng theo headline là bảo thủ nhưng có thể loại nhầm bài khác nhau. Không thay đổi tập 60 bài/split đã khóa; ở lần chuẩn bị dữ liệu tiếp theo nên dùng so sánh nội dung và xác nhận thủ công thay vì chỉ dựa vào tiêu đề.

### 7.2. Mẫu 12 ứng viên trong numeric audit

Đối chiếu token/đơn vị được trích với ngữ cảnh bài nguồn. `PASS` chỉ xác nhận lần trích bề mặt trong mẫu; không thay thế kiểm tra toàn bộ 635 dòng.

| item_id | Token / đơn vị | Kết quả | Ghi chú |
|---|---|---|---|
| DT05-002 | `73%` | PASS | Nằm trong ngữ cảnh tăng doanh thu so với cùng kỳ. |
| DT05-004 | `200 triệu đồng` | PASS | Ngưỡng doanh thu tính thuế; giá trị/đơn vị khớp. |
| DT05-017 | `25.356 tỷ đồng` | PASS | Tổng nợ thuế; dấu chấm là phân tách hàng nghìn theo ngữ cảnh tiếng Việt, giữ nguyên raw token. |
| DT05-003 | `10 USD` | REVIEW | Số tiền tăng theo đơn vị ngầm USD/tấn trong cùng câu; regex chỉ ghi USD, cần giữ/khôi phục mẫu số theo ngữ cảnh. |
| DT05-018 | `30.000m2` | PASS | Diện tích; token và đơn vị khớp. |
| DT05-007 | `1 tấn` | CONTEXT | Nằm trong định nghĩa chung về tín chỉ carbon, không phải quan sát kinh tế cụ thể; không tính làm economic fact. |
| DT05-049 | `1kg` | PASS | Khối lượng trong ngữ cảnh giá cua theo kg. |
| DT05-019 | `5ha` | PASS | Diện tích đất; token và đơn vị khớp. |
| DT05-006 | `19 triệu USD` | PASS | Giá trị hiệu quả kinh doanh; token và đơn vị khớp. |
| DT05-043 | `1,3 tỷ USD` | PASS | Giá trị thương vụ; dấu phẩy thập phân được giữ. |
| DT05-014 | `16.800 lượng` | PASS | Khối lượng vàng đấu thầu; token và đơn vị khớp. |
| DT05-010 | `102,62 điểm` | PASS | Mức chỉ số USD-Index; token và đơn vị khớp. |

Kết quả: 10 lần trích bề mặt đạt, 1 trường hợp cần đối chiếu đơn vị theo ngữ cảnh, 1 trường hợp là định nghĩa không thuộc economic-fact denominator. Đây là mẫu kiểm tra hỗ trợ, chưa được ghi nhận là review thủ công độc lập.

### 7.3. Ghi chú 8 bài được gán topic `khac`

`khac` là nhãn fallback do bộ từ khóa, không đồng nghĩa bài không liên quan kinh tế. Nhận xét dưới đây đánh giá độ phù hợp với phạm vi BTL; không tự sửa topic hoặc thay đổi tập đã khóa.

| item_id | Nhận xét sơ bộ |
|---|---|
| DT05-020 | Quy định bảng giá đất và chi phí làm sổ đỏ; phù hợp bất động sản/đất đai. `khac` nhiều khả năng do bộ từ khóa chưa bắt cụm này. |
| DT05-021 | Đấu giá quyền sử dụng đất và giá khởi điểm; phù hợp bất động sản. Có thể phân loại BĐS nếu taxonomy được hiệu chỉnh ở phiên bản sau. |
| DT05-026 | Bài khoa học về chiết xuất uranium và năng lượng hạt nhân; có liên hệ kinh tế năng lượng nhưng trọng tâm là nghiên cứu công nghệ. Borderline với phạm vi tin kinh tế. |
| DT05-027 | Tin xổ số, tiền thưởng và thuế; có số liệu tài chính nhưng không phải tin kinh tế cốt lõi. Cần quyết định giữ như bài biên hay loại ở vòng chọn dữ liệu sau. |
| DT05-033 | Nội dung kim cương/trang sức có lời chào bán và thông tin khuyến mại; dấu hiệu advertorial/tiếp thị. Cần A1/A2 xác nhận độ phù hợp trước khi xem là ví dụ tin kinh tế trung tính. |
| DT05-036 | Chính sách giảm thuế VAT; rõ ràng thuộc kinh tế vĩ mô/tài khóa. `khac` nhiều khả năng do taxonomy chưa có từ khóa thuế/VAT. |
| DT05-049 | Giá và mức độ phổ biến của cua nhập khẩu trên thị trường bán lẻ; phù hợp hàng hóa/tiêu dùng và thương mại. |
| DT05-051 | Thị trường bánh trung thu, giá bán và hàng nhập khẩu; phù hợp bán lẻ/thương mại nhưng có yếu tố quảng bá sản phẩm. |

Các mục borderline/advertorial cần quyết định của nhóm. Ghi chú này không thay thế rà soát A1/A2 và không được dùng để âm thầm thay gold test.

## 8. Giới hạn từ gold checker

Gold test đang khóa; các cờ dưới đây được phân loại để diễn giải, không sửa gold. Tổng lần chạy: **0 ERROR, 23 REVIEW, 14 WARN**.

| Severity / code | Số cờ | Bài bị ảnh hưởng | Ý nghĩa và ảnh hưởng |
|---|---:|---|---|
| REVIEW `article_dot_decimal` | 11 | DT05-001, 003, 006, 007, 009, 010, 011, 013, 014, 015, 016 | Có chuỗi số chấm có thể là ngày/tháng hoặc số thập phân; cần đọc ngữ cảnh để tránh hiểu sai. Có thể ảnh hưởng độ tin cậy của đối chiếu văn bản reference nếu gold nhầm giá trị, nhưng cờ không tự kết luận có lỗi. |
| REVIEW `low_number_article_has_numbers` | 11 | DT05-001, 008, 018, 023, 026, 035, 041, 045, 054, 058, 060 | Bài nguồn dưới ngưỡng số liệu nhưng summary có số; đây là nhóm kiểm thử khả năng bịa số. Xác minh từng claim với thân bài, không xem số lượng ít là lỗi. |
| REVIEW `unit_unverifiable` | 1 | DT05-039 | `114,2 triệu` có trong bài nhưng checker không gắn được đơn vị. Cần xác nhận đơn vị theo thân bài; không tự đoán. |
| WARN `unit_shortened` | 14 | DT05-003, 004, 009, 011, 015, 022, 031, 035, 036, 051 | Phiếu/gold dùng đơn vị rút gọn so với biểu thức trong bài (14 cờ trên 10 bài; có cờ lặp cho nhiều facts). Cần đối chiếu đơn vị và mẫu số theo ngữ cảnh; đây không tự động là sai fact. |

### Tách chỉ số đánh giá khỏi cảnh báo gold

- **ROUGE** so dự đoán với tóm tắt tham chiếu; vì vậy reference là thành phần của điểm ROUGE và mọi sai sót thật sự trong reference (nếu phát hiện) cần được nêu như giới hạn. Gold test vẫn giữ nguyên sau khi khóa.
- **Numeric precision / hallucination rate** của hệ thống theo protocol v1.0 được xác định bằng cách đối chiếu từng claim số trong đầu ra với **thân bài nguồn**, không lấy kết quả WARN của checker làm nhãn đúng/sai. Do đó các WARN `unit_shortened` không trực tiếp làm lệch hai chỉ số này; chúng có thể ảnh hưởng riêng `gold_numeric_recall`, vốn so với fact sheet.
- Không có REVIEW/WARN nào được tự động quy thành ERROR. Lần rà soát cờ của checker không thay thế xác nhận pre-audit độc lập A1/A2; xác nhận này vẫn đang chờ.
