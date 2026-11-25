# Data Card — VietOnlineNews

## 1. Dataset Summary & Intended Use

Nguồn dữ liệu chính của BTL là `VLUS06/VietOnlineNews`, dùng để xây dựng bộ tham chiếu cho tóm tắt tin kinh tế tiếng Việt và đánh giá việc bảo toàn dữ kiện. Dataset gốc là dữ liệu phân loại chủ đề, không có nhãn tóm tắt. Nhóm tự tạo gold cho 60 bài (10 dev, 50 test). Không dùng các dataset tóm tắt tin tên gần giống như `Linhz/Vietnews` hoặc `harouzie/vietnews`.

## 2. Dataset Sources & Versions

| Thuộc tính | Giá trị |
|---|---|
| Hugging Face ID | [`VLUS06/VietOnlineNews`](https://huggingface.co/datasets/VLUS06/VietOnlineNews) |
| Revision đã pin | `bd8d2a865c8981d34cb9d85f69f62bda7c40b520` |
| Retrieved at | `2026-11-25T09:51:48+07:00` |
| Nguồn được Hub README mô tả | VietnamNet, Thanh Niên, Tuổi Trẻ; giai đoạn 2023–2025 |
| `published_at` | Không có trong schema; ghi `unknown`, không suy ra từ ngày tải |

Schema không có trường `source`, `url` hoặc ngày đăng ở cấp bài nên các thuộc tính này không được suy đoán cho VietOnlineNews. Dataset đối chiếu UVN-1 không được dùng làm nguồn chính: [`undertheseanlp/UVN-1`](https://huggingface.co/datasets/undertheseanlp/UVN-1), revision `42a81b44e1e8228146e56a3fa066cc035384b7d9`, 3.268 dòng, cột `id, source, url, category, title, content, publish_date`. Metadata UVN-1 có `publish_date` trong khoảng 2011-06-28 đến 2026-01-29; đây là thông tin metadata, không suy ra từ ngày tải.

## 3. License & Access

Hugging Face Hub khai báo `license: other`; không có SPDX license cụ thể. Mục `LICENSE` trong dataset repository rỗng khi kiểm tra, nên **quyền sử dụng và tái phân phối chưa được xác minh**. Cần xác nhận bằng văn bản với chủ dataset hoặc giảng viên, đồng thời kiểm tra quyền từ các nguồn báo trước khi công bố. Chỉ truy cập qua trang Hub ở trên; không xem việc tải công khai là giấy phép tái phân phối.

Không commit/push tiêu đề, mô tả, toàn văn, bản dump hoặc annotation chứa trích câu nguồn lên repository công khai trong khi chưa rõ quyền. Dữ liệu toàn văn phục vụ gán nhãn chỉ lưu cục bộ; `.gitignore` loại các tệp này khỏi Git. **Cổng cấp phép D1 vẫn đang mở.**

## 4. Data Structure

Schema gốc: `id, title, description, content, category`. `category` là nhãn chủ đề gốc, không phải nhãn tóm tắt.

| Split gốc | Số dòng |
|---|---:|
| train | 186,010 |
| validation | 39,859 |
| test | 39,860 |
| **Tổng** | **265,729** |

Con số loader quan sát được khác Hub README (README ghi 187,682 / 40,218 / 40,218, tổng 268,118); dùng số đếm trực tiếp từ revision đã pin và ghi nhận sai khác này, chưa giải thích nguyên nhân. Bộ cục bộ của BTL có manifest 60 dòng, văn bản bài báo, tóm tắt tham chiếu và fact sheet. Các tệp có văn bản hoặc trích câu nguồn không được phát hành công khai.

## 5. Composition & Distributions

Phân bố category của toàn dataset tại revision đã pin:

| Category gốc | Số bài | Tỷ lệ |
|---|---:|---:|
| Giải trí | 40,864 | 15.38% |
| Kinh doanh | 33,242 | 12.51% |
| Thể thao | 32,278 | 12.15% |
| Thời sự | 27,399 | 10.31% |
| Giáo dục | 22,433 | 8.44% |
| Khoa học công nghệ | 21,008 | 7.91% |
| Đời sống | 19,116 | 7.19% |
| Xe | 18,805 | 7.08% |
| Sức khỏe | 16,666 | 6.27% |
| Thế giới | 14,847 | 5.59% |
| Du lịch | 9,179 | 3.45% |
| Bất động sản | 6,636 | 2.50% |
| Pháp luật | 3,256 | 1.23% |

Trong category `Kinh doanh`, số bài có ít nhất một chuỗi trong `title`, `description` hoặc `content`:

| Chuỗi dò | Số bài khớp |
|---|---:|
| `%` | 20,954 |
| `tỷ đồng` | 5,267 |
| `USD` | 11,095 |
| `quý` | 8,625 |
| **Khớp ít nhất một chuỗi (duy nhất)** | **25,182** |

Đây là phép dò từ khóa thô, không chứng minh bài có số liệu tài chính hợp lệ (đặc biệt `quý` có thể mang nghĩa khác). Danh sách kết quả chỉ gồm ID: [`data/vietonline_news_economic_numeric_ids.txt`](data/vietonline_news_economic_numeric_ids.txt).

Mẫu BTL cuối có 52 bài category `Kinh doanh`, 8 `Bất động sản`; chủ đề do bộ từ khóa gán: `bat_dong_san` 7, `chung_khoan` 7, `doanh_nghiep` 8, `hang_hoa` 8, `khac` 8, `tien_te_ngan_hang` 7, `vi_mo` 7, `xuat_nhap_khau` 8. Đây là phân bố của mẫu chọn, không phải phân bố đại diện của dataset.

## 6. Collection & Sampling

Từ 265,729 dòng gốc, giữ 39,878 bài thuộc `Kinh doanh` hoặc `Bất động sản`; loại 155 tiêu đề trùng và 12,712 bài ngoài khoảng 250–900 từ; lấy pool ngẫu nhiên 4,000 bài (seed 42); loại 27 bài gần trùng theo TF-IDF cosine ≥0.8; rồi chọn 60 bài đa dạng chủ đề và tránh bài cùng sự kiện với cosine ≥0.4. Mẫu cuối có 48 bài với ít nhất 4 ứng viên số liệu regex (8 dev, 40 test) và 12 bài dưới ngưỡng. Quy trình không lấy mẫu đại diện cho toàn bộ dataset.

## 7. Preprocessing

- Làm sạch HTML entity/tag, chuẩn hóa Unicode NFC, khoảng trắng và dòng mới.
- Loại dòng thiếu tiêu đề/nội dung, ID lặp, nội dung trùng chính xác sau chuẩn hóa khoảng trắng/chữ thường, tiêu đề trùng sau chuẩn hóa khoảng trắng/chữ thường, và bài ngoài khoảng 250–900 từ.
- Trích ứng viên số liệu bằng regex trong `data/prepare_data.py`; đây không phải bộ trích xuất sự kiện kinh tế đã được xác thực. Một số ứng viên có thể là ngày, chỉ số, định nghĩa phổ thông hoặc thiếu đơn vị hàm ý.
- Không chia bài thành chunk. Văn bản gốc được giữ ở bản cục bộ để kiểm chứng; không đưa toàn văn vào repository công khai.

## 8. Annotation Process

- Hướng dẫn gán nhãn đã khóa ở v1.0; gold gồm tóm tắt tham chiếu và fact sheet có entity/indicator, value, unit, period, comparison basis, modality và câu nguồn.
- Fact sheet hiện có 220 dòng dữ kiện số: 35 dev và 185 test. Cả 60 bài đều ghi `guideline_version = v1.0`.
- Bản nháp được ghi nguồn `llm_edited`; A1/Cường và A2/Hoàng chịu trách nhiệm kiểm tra theo phân công. Nhật ký review ghi quyết định, lý do, người gán nhãn/người rà soát và phiên bản guideline.
- Trong 50 test, 31 bài có trạng thái `reviewed`; trong 10 dev, 7 bài có trạng thái `reviewed`. Tổng cộng 38/60 bài (63.3%) có trạng thái này. Có 13/13 bài test được đánh dấu cần hậu kiểm chéo đã hoàn tất; các tự kiểm của người gán không được tính là review độc lập.
- Nhật ký có 59 quyết định `keep` và 0 mục `unresolved`; con số log bao gồm cả pilot/annotation decisions, không đồng nghĩa 59 bài đã được rà chéo.
- Pilot có 5 bài bất đồng: loại A ở 4/5 bài, loại B ở 5/5, loại C ở 0/5; các loại có thể chồng lấp. Cả 5 có resolution, không có `unresolved`.

## 9. Quality Checks

- Checker tại `src/check_gold.py` đã chạy với `--locked-version v1.0`: **0 ERROR, 23 REVIEW, 14 WARN**; kết quả ghi trong [`reports/gold_check_report.md`](reports/gold_check_report.md). Cả 50 test dùng v1.0; REVIEW/WARN là cờ cần diễn giải, không tự động đồng nghĩa lỗi annotation. Tóm tắt tham chiếu test không được chỉnh âm thầm sau khóa.
- REVIEW gồm `article_dot_decimal` 11, `low_number_article_has_numbers` 11 và `unit_unverifiable` 1. Cả 14 WARN là `unit_shortened`, trên 10 bài. Ý nghĩa và ảnh hưởng riêng của ROUGE, numeric precision/hallucination và gold recall được ghi trong báo cáo chất lượng.
- Kiểm tra mẫu cặp tiêu đề phát hiện trường hợp cùng tiêu đề nhưng nội dung khác đáng kể; xem ghi chú ở [`reports/data_quality_report.md`](reports/data_quality_report.md). Rà soát này do trợ lý thực hiện để sàng lọc, chưa thay thế xác nhận độc lập của A1/A2.
- Rà soát 12 ứng viên số liệu tìm thấy một trường hợp cần đối chiếu đơn vị theo ngữ cảnh và một ứng viên định nghĩa không nên tính là chỉ báo kinh tế. Chi tiết và ghi chú 8 bài `khac` nằm trong báo cáo chất lượng cục bộ.
- License và quyền tái phân phối chưa xác minh; chất lượng dữ liệu không đồng nghĩa quyền phát hành.

## 10. Splits & Leakage Prevention

- Có 10 bài dev và 50 bài test. Split được điều chỉnh một lần vào `2026-11-25T10:14:05+07:00`, trước khi gán nhãn; lịch sử ở [`data/splits/split_history.json`](data/splits/split_history.json). Dev có đại diện cả 8 chủ đề, 8 bài nhiều ứng viên số liệu và 2 bài dưới ngưỡng.
- Seed lấy mẫu là 42. Bước chọn mẫu loại các cặp gần trùng theo TF-IDF trong pool, đồng thời tránh cùng sự kiện có cosine ≥0.4. Việc loại tiêu đề trùng được áp dụng theo chuẩn hóa chữ thường/khoảng trắng; audit hậu kiểm cho thấy cách này có thể loại nhầm các bài cùng headline nhưng khác nội dung.
- Mỗi bài chỉ thuộc một split; danh sách ID ở [`data/splits/dev_ids.txt`](data/splits/dev_ids.txt) và [`data/splits/test_ids.txt`](data/splits/test_ids.txt). Test được giữ khóa.

## 11. Gold & Evaluation Protocol

Guideline v1.0 và hash khóa được ghi tại `data/annotations/guideline_lock.json`. Protocol đánh giá đã chốt trong [`evaluation_protocol.md`](evaluation_protocol.md): tokenization theo âm tiết, ROUGE-L chính, ROUGE-1/2 phụ; trích ứng viên số liệu bằng regex nhưng xác minh đúng/sai theo nguồn và ngữ cảnh; rubric factuality; chọn cấu hình trên dev rồi chạy test đúng một lần. Commit đóng băng protocol được gắn tag [`protocol-frozen`](https://github.com/Dragonkin1402/BTL-NLP/tree/protocol-frozen) tại `072666a471383d8596c03c28a70ec2c2ad6ee363`.

Dev-only E0 Lead-3 baseline đã chạy trên 10 bài tại commit `c9ba26c9c94c98ea3e69efc2a0c0d8d8ad7e4ee`: macro ROUGE-1/2/L lần lượt là 0.3921/0.2086/0.2516. Có 16/40 ứng viên đạt khớp bề mặt chính xác cả giá trị và đơn vị (40%); đây **không phải** numeric precision hay kết luận factuality, các metric ngữ nghĩa cần người rà soát. E1/E2 và test chưa chạy. Bảng theo từng bài và đầu ra được giữ cục bộ, không tái phân phối.

## 12. Biases, Ethics & Risks

- Chỉ chọn category `Kinh doanh` và `Bất động sản`, trong phạm vi chủ đề báo chí và khoảng dữ liệu của revision; không đại diện cho báo chí Việt Nam hoặc mọi lĩnh vực kinh tế.
- Topic nội bộ là gán bằng từ khóa, có thể bỏ sót chủ đề như thuế, đất đai, bán lẻ hoặc năng lượng; `khac` không đồng nghĩa bài phi kinh tế.
- Dataset gốc không cung cấp nguồn/URL/ngày đăng ở cấp bài trong schema đã tải. Bài báo có thể chứa thông tin sai, chưa cập nhật hoặc quan điểm biên tập/tiếp thị.
- Tóm tắt tự động có thể lược mất điều kiện, đơn vị, kỳ hoặc modality; mọi con số cần đối chiếu văn bản gốc trước khi sử dụng.

## 13. Limitations & Inappropriate Uses

- Không dùng làm căn cứ giao dịch/chọn cổ phiếu, tư vấn tài chính, quyết định tín dụng, quyết định chính sách hoặc phát ngôn công khai nếu chưa kiểm chứng độc lập.
- Không suy diễn độ chính xác toàn corpus từ 60 bài hoặc từ ROUGE; ROUGE đo trùng lặp bề mặt, không chứng minh factuality.
- Nhãn topic dựa từ khóa, regex số liệu có false positive/false negative. Mẫu audit cho thấy 4/9 cặp cùng tiêu đề có tương đồng chuỗi nội dung dưới 0.35; title-only dedup có thể loại nhầm bài khác nhau. Đây là giới hạn về độ bao phủ/mẫu chọn, không phải bằng chứng rò rỉ giữa dev và test.
- Không tái phân phối bài báo, trích đoạn nguồn hoặc các file chứa nội dung cho đến khi quyền được xác nhận.

## 14. Reproducibility & Access Instructions

- Dùng `datasets` để tải đúng revision `bd8d2a865c8981d34cb9d85f69f62bda7c40b520`; `python scripts/inspect_news_datasets.py` in schema/phân bố và cập nhật metadata. `python data/prepare_data.py` dựng lại pipeline trong một thư mục output mới; script từ chối ghi đè split đã khóa.
- Retrieved at của snapshot đã dùng: `2026-11-25T09:51:48+07:00`. VietOnlineNews không có trường ngày đăng; `published_at` ghi `unknown`.
- Nhật ký sử dụng AI: [`Nhat_ky_su_dung_AI.md`](Nhat_ky_su_dung_AI.md); các pre-audit cần người trong nhóm xác nhận vẫn được đánh dấu pending.
- ID mẫu công khai chỉ có thể phát hành theo chính sách quyền dữ liệu của lớp; không kèm toàn văn. Full text và annotation có câu nguồn vẫn ở local.
- Điều kiện còn mở trước nghiệm thu/phát hành D1: xác nhận license/quyền tái phân phối của dataset và các bài báo bằng văn bản.
