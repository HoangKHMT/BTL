# Báo cáo tự kiểm gold (tự sinh bởi src/check_gold.py)

> **Giới hạn:** script chỉ so khớp chuỗi/số với thân bài. Nó không xác nhận được chủ thể, kỳ/cơ sở so sánh, dự báo hay thực tế, ý chính, hay ý nghĩa của số dạng `3.2%`. Không có ERROR **không có nghĩa** gold đúng; mọi mục REVIEW và các bài được rà soát chéo vẫn phải do người kiểm.

- Guideline đã khóa: v1.0
- Phiên bản guideline đang dùng trong gold: {'v1.0': 60}

## Tiến độ

| Split | Trạng thái | Số bài |
|---|---|---:|
| dev | annotated | 3 |
| dev | reviewed | 7 |
| test | annotated | 19 |
| test | reviewed | 31 |

- Đã viết (annotated/reviewed): 60 | đã rà soát chéo (reviewed): 38 (63%; yêu cầu >= 20%)
- Bài đánh dấu cần hậu kiểm chéo đã viết xong: 20

## Tổng hợp

- ERROR: 0 | REVIEW: 23 | WARN: 14

| Mức | Bài | Mã | Chi tiết |
|---|---|---|---|
| REVIEW | DT05-001 | article_dot_decimal | thân bài có số dạng chấm thập phân ['1.7', '24.10', '7.11']; kiểm tra tóm tắt/phiếu không bị đổi nghĩa |
| REVIEW | DT05-001 | low_number_article_has_numbers | bài ít số liệu nhưng tóm tắt có số: xác nhận từng số có trong bài (nhóm này dùng đo việc bịa số) |
| REVIEW | DT05-003 | article_dot_decimal | thân bài có số dạng chấm thập phân ['20.7']; kiểm tra tóm tắt/phiếu không bị đổi nghĩa |
| REVIEW | DT05-006 | article_dot_decimal | thân bài có số dạng chấm thập phân ['12.8']; kiểm tra tóm tắt/phiếu không bị đổi nghĩa |
| REVIEW | DT05-007 | article_dot_decimal | thân bài có số dạng chấm thập phân ['27.9']; kiểm tra tóm tắt/phiếu không bị đổi nghĩa |
| REVIEW | DT05-008 | low_number_article_has_numbers | bài ít số liệu nhưng tóm tắt có số: xác nhận từng số có trong bài (nhóm này dùng đo việc bịa số) |
| REVIEW | DT05-009 | article_dot_decimal | thân bài có số dạng chấm thập phân ['2.9', '3.9']; kiểm tra tóm tắt/phiếu không bị đổi nghĩa |
| REVIEW | DT05-010 | article_dot_decimal | thân bài có số dạng chấm thập phân ['13.3', '27.3', '28.3']; kiểm tra tóm tắt/phiếu không bị đổi nghĩa |
| REVIEW | DT05-011 | article_dot_decimal | thân bài có số dạng chấm thập phân ['10.12', '9.12']; kiểm tra tóm tắt/phiếu không bị đổi nghĩa |
| REVIEW | DT05-013 | article_dot_decimal | thân bài có số dạng chấm thập phân ['22.10', '24.10']; kiểm tra tóm tắt/phiếu không bị đổi nghĩa |
| REVIEW | DT05-014 | article_dot_decimal | thân bài có số dạng chấm thập phân ['8.5']; kiểm tra tóm tắt/phiếu không bị đổi nghĩa |
| REVIEW | DT05-015 | article_dot_decimal | thân bài có số dạng chấm thập phân ['12.9']; kiểm tra tóm tắt/phiếu không bị đổi nghĩa |
| REVIEW | DT05-016 | article_dot_decimal | thân bài có số dạng chấm thập phân ['2.2']; kiểm tra tóm tắt/phiếu không bị đổi nghĩa |
| REVIEW | DT05-018 | low_number_article_has_numbers | bài ít số liệu nhưng tóm tắt có số: xác nhận từng số có trong bài (nhóm này dùng đo việc bịa số) |
| REVIEW | DT05-023 | low_number_article_has_numbers | bài ít số liệu nhưng tóm tắt có số: xác nhận từng số có trong bài (nhóm này dùng đo việc bịa số) |
| REVIEW | DT05-026 | low_number_article_has_numbers | bài ít số liệu nhưng tóm tắt có số: xác nhận từng số có trong bài (nhóm này dùng đo việc bịa số) |
| REVIEW | DT05-035 | low_number_article_has_numbers | bài ít số liệu nhưng tóm tắt có số: xác nhận từng số có trong bài (nhóm này dùng đo việc bịa số) |
| REVIEW | DT05-039 | unit_unverifiable | '114,2 triệu': bài có số này nhưng máy không gắn được đơn vị; xem tay |
| REVIEW | DT05-041 | low_number_article_has_numbers | bài ít số liệu nhưng tóm tắt có số: xác nhận từng số có trong bài (nhóm này dùng đo việc bịa số) |
| REVIEW | DT05-045 | low_number_article_has_numbers | bài ít số liệu nhưng tóm tắt có số: xác nhận từng số có trong bài (nhóm này dùng đo việc bịa số) |
| REVIEW | DT05-054 | low_number_article_has_numbers | bài ít số liệu nhưng tóm tắt có số: xác nhận từng số có trong bài (nhóm này dùng đo việc bịa số) |
| REVIEW | DT05-058 | low_number_article_has_numbers | bài ít số liệu nhưng tóm tắt có số: xác nhận từng số có trong bài (nhóm này dùng đo việc bịa số) |
| REVIEW | DT05-060 | low_number_article_has_numbers | bài ít số liệu nhưng tóm tắt có số: xác nhận từng số có trong bài (nhóm này dùng đo việc bịa số) |
| WARN | DT05-003 | unit_shortened | '5 usd/tấn': bài viết đơn vị là ['%', 'usd'] |
| WARN | DT05-004 | unit_shortened | '200 triệu đồng': bài viết đơn vị là ['triệu đồng/năm'] |
| WARN | DT05-004 | unit_shortened | '500 triệu đồng': bài viết đơn vị là ['triệu đồng/năm'] |
| WARN | DT05-004 | unit_shortened | '500 triệu đồng': bài viết đơn vị là ['triệu đồng/năm'] |
| WARN | DT05-004 | unit_shortened | '500 triệu đồng': bài viết đơn vị là ['triệu đồng/năm'] |
| WARN | DT05-009 | unit_shortened | '133,4 triệu đồng/lượng': bài viết đơn vị là ['triệu đồng'] |
| WARN | DT05-011 | unit_shortened | '25.155 đồng/usd': bài viết đơn vị là ['đồng'] |
| WARN | DT05-015 | unit_shortened | '132,8 triệu đồng/lượng': bài viết đơn vị là ['triệu đồng'] |
| WARN | DT05-022 | unit_shortened | '1 tỷ đồng': bài viết đơn vị là ['triệu', 'tỷ', 'tỷ đồng/căn hộ'] |
| WARN | DT05-031 | unit_shortened | '2.400 đồng': bài viết đơn vị là ['đồng/cp'] |
| WARN | DT05-035 | unit_shortened | '30 triệu đồng': bài viết đơn vị là ['triệu đồng/năm'] |
| WARN | DT05-036 | unit_shortened | '5.800 tỷ đồng': bài viết đơn vị là ['tỷ đồng/tháng'] |
| WARN | DT05-051 | unit_shortened | '60.000 đồng': bài viết đơn vị là ['đồng/bánh'] |
| WARN | DT05-051 | unit_shortened | '55.000 đồng': bài viết đơn vị là ['đồng/bánh'] |
