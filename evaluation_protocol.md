# Evaluation Protocol — v1.0

**Status:** Protocol v1.0 đã được chốt trước khi chạy mô hình. E0 trên `dev` đã hoàn tất; E1 trên `dev` đang dở; E2 thật và tập `test` chưa chạy. Tóm tắt trạng thái và kết quả hiện có được ghi trong [`README.md`](README.md).
**Dataset:** VietOnlineNews sample, guideline v1.0, 10 dev / 50 test.

## 1. Mục tiêu và đơn vị đánh giá

Đánh giá tóm tắt tiếng Việt theo hai trục riêng:

1. **Độ tương đồng nội dung:** ROUGE-L là chỉ số chính; ROUGE-1 và ROUGE-2 là chỉ số phụ.
2. **Độ bảo toàn dữ kiện:** kiểm tra các claim trong tóm tắt so với bài nguồn và gold numeric fact sheet. ROUGE không được diễn giải như bằng chứng factuality.

Một đơn vị đánh giá là một bài: một dự đoán của hệ thống so với một reference summary cùng `item_id`. Báo cáo cả kết quả từng bài và trung bình macro trên các bài trong split.

## 2. Chuẩn hóa và tokenization cho ROUGE

Dùng tokenization theo **âm tiết tiếng Việt**, không chạy word segmenter:

1. Chuẩn hóa Unicode NFC.
2. Chuyển chữ về `casefold()` để không phân biệt hoa/thường.
3. Tách token bằng biểu thức Python Unicode `re.findall(r"[^\W_]+", text, flags=re.UNICODE)`. Dấu câu bị bỏ; chữ có dấu và chữ số được giữ. Các âm tiết tiếng Việt ngăn cách bằng khoảng trắng vẫn là token riêng.
4. Không stemming, không bỏ stopword, không chuẩn hóa từ đồng nghĩa.

Tính `rouge1`, `rouge2`, `rougeL` bằng F1 của `rouge-score==0.1.2`, `use_stemmer=False` và tokenizer trên. Chỉ số chính là `rougeL_f1`; `rouge1_f1` và `rouge2_f1` là chỉ số phụ. Tính F1 riêng cho từng bài rồi lấy trung bình macro; không gộp toàn bộ bài thành một chuỗi. Nếu đổi phiên bản thư viện hoặc tokenizer, phải ghi protocol version mới trước khi chạy test.

## 3. Trích ứng viên số liệu

Regex chỉ tạo **ứng viên cần kiểm tra**, không tự xác định một số liệu là đúng hay bịa. Nguồn triển khai chuẩn là `data/prepare_data.py` và `src/check_gold.py`.

### 3.1 Giá trị và đơn vị

Regex số gốc:

```python
NUM = r"\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?"
```

Danh sách `UNITS` được ghép theo thứ tự dài đến ngắn để ưu tiên đơn vị ghép:

```python
UNITS = [
    "triệu đồng/lượng", "triệu đồng/lần", "triệu đồng/m2", "triệu đồng/năm",
    "triệu NDT/năm", "tỷ đồng/căn hộ", "tỷ đồng/tháng",
    "USD/ounce", "USD/tấn", "USD/kg", "đồng/USD", "đồng/CP",
    "đồng/bánh", "đồng/kg", "%/năm", "con/phụ nữ", "giờ/ngày",
    "mẫu/ngày", "ngày/tuần",
    "nghìn tỷ đồng", "nghìn tỷ", "triệu tỷ", "tỷ đồng", "tỷ USD", "tỷ đô la", "tỷ đô",
    "triệu USD", "triệu đô la", "triệu đồng", "nghìn đồng", "điểm phần trăm", "phần trăm",
    "%", "USD", "đô la", "VND", "VNĐ", "đồng", "tỷ", "triệu", "nghìn", "ngàn", "điểm",
    "tấn", "kg", "ha", "m2", "m²", "cổ phiếu", "lượng", "chỉ",
]
```

Mẫu trích ứng viên có đơn vị:

```python
FACT_RE = re.compile(
    rf"(?<![\w.,/])({NUM})\s?({'|'.join(re.escape(u) for u in UNITS)})(?!\w)(?!\s?nghiệp)",
    re.IGNORECASE,
)
```

Ứng viên số không có đơn vị và số thập phân dấu chấm được phát hiện thêm bằng:

```python
TOKEN_RE = re.compile(rf"(?<![\w.,])({NUM})(?!\w)")
DOTDEC_RE = re.compile(r"(?<![\w.,])(\d+\.\d{1,2})(?![\d\w])(\s?%)?")
NON_METRIC_IDENTIFIER_RE = re.compile(r"\bS\s*&\s*P\s*500\b", re.IGNORECASE)
```

`DOTDEC_RE` là mẫu của checker dùng khi đối chiếu tóm tắt; `DOT_DECIMAL_PCT_RE = re.compile(r"(?<![\w.,])\d+\.\d{1,2}\s?%")` trong bước chuẩn bị chỉ gắn cờ phần trăm kiểu dấu chấm. Kỳ/thời gian được dò riêng để phân biệt với số liệu:

```python
PERIOD_RE = re.compile(
    r"(?:quý\s+(?:IV|III|II|I|[1-4])(?:\s?/\s?\d{4})?|tháng\s+\d{1,2}(?:\s?/\s?\d{4})?"
    r"|(?<!\d)\d{1,2}\s+tháng(?:\s+đầu\s+năm(?:\s+\d{4})?)?"
    r"|năm\s+\d{4}|(?<!\d)\d{1,2}/\d{1,2}/\d{4}|(?<!\d)\d{1,2}/\d{4})",
    re.IGNORECASE,
)
```

Trong nội dung Việt ngữ, dấu chấm ở nhóm `25.356` được hiểu theo quy ước phân tách hàng nghìn và dấu phẩy ở `12,8` là dấu thập phân; chỉ giữ số thập phân dấu chấm khi ngữ cảnh hỗ trợ. Không chuyển đổi nếu ngữ cảnh không đủ rõ. Khi trích, ưu tiên các span `FACT_RE`; `TOKEN_RE` chỉ bổ sung số không có đơn vị và không đếm lại token đã bắt đầu trong span fact. Các span kỳ từ `PERIOD_RE` và mã định danh/chỉ số như `S&P 500` bị loại khỏi candidate metric; số trong định nghĩa phổ thông và số không phải claim kinh tế được người đánh giá loại khỏi mẫu số sau khi đọc ngữ cảnh. Khoảng số như `5–10 USD/tấn` được người đánh giá gộp thành một claim khoảng gồm hai đầu mút; không đếm thành hai claim độc lập.

### 3.2 Đối chiếu và công thức

Mỗi lần xuất hiện của một claim số trong dự đoán được chấm một lần. Người đánh giá kiểm tra tối thiểu **giá trị, đơn vị, entity/indicator, kỳ, cơ sở so sánh và modality** (actual/planned/estimate/proposal) với bài nguồn. Chỉ thấy cùng chuỗi số trong bài không đủ để kết luận claim đúng; số đúng nhưng gắn sai entity, đơn vị, kỳ hoặc modality là claim sai/nghi vấn.

- `numeric_precision = supported_output_claims / all_output_numeric_claims`
- `numeric_hallucination_rate = (unsupported + contradicted_output_claims) / all_output_numeric_claims`
- `gold_numeric_recall = supported_gold_facts_reproduced / gold_numeric_facts`

Fact được tính `supported` khi bài nguồn xác nhận đầy đủ ý nghĩa của claim; `contradicted` khi nguồn nêu dữ kiện không tương thích; `unsupported` khi không tìm thấy bằng chứng đủ. Báo cáo số claim và tử/mẫu cùng tỷ lệ. Nếu không có claim số ở đầu ra, precision và hallucination rate ghi `N/A (0 claims)`, không ghi 0% hoặc 100%. Gold recall chỉ đo mức tái hiện fact sheet, không thay thế kiểm tra tính đúng so với nguồn vì một bản tóm tắt có thể chọn một fact đúng khác với reference.

## 4. Rubric factuality

Chấm mỗi tóm tắt theo thang 0–2 sau khi đối chiếu bài nguồn:

| Điểm | Tiêu chí |
|---:|---|
| 2 — grounded | Ý chính và các claim quan trọng được nguồn hỗ trợ; entity, số, đơn vị, kỳ, quan hệ so sánh và modality đúng; không có thông tin bịa. |
| 1 — mostly grounded | Không có mâu thuẫn trọng yếu; có thiếu sót nhỏ hoặc diễn đạt mơ hồ nhưng không làm đổi kết luận chính. Ghi rõ claim cần xem lại. |
| 0 — factual error | Có claim trọng yếu không được hỗ trợ/bị mâu thuẫn, nhầm entity/số/đơn vị/kỳ/modality, hoặc làm đảo nghĩa bài. |

Nếu chưa đủ bằng chứng để quyết định, ghi `uncertain`, không tự cho điểm 2; chuyển người rà soát phân xử. Báo cáo điểm từng bài, phân bố điểm và các lỗi số liệu/phi số liệu.

## 5. Chọn mô hình và quy tắc test

1. Dùng **dev (10 bài)** để phát triển prompt, chọn mô hình/cấu hình và điều chỉnh decoding. Ghi lại model/version, prompt, tham số sinh, seed nếu có, thư viện/runtime.
2. Trước khi mở test, khóa cấu hình được chọn và lưu hash/copy cấu hình. Không dùng kết quả test để chọn prompt, model hoặc tham số.
3. Chạy cấu hình đã khóa trên **test (50 bài) đúng một lần** cho kết quả cuối. Không chỉnh mô hình sau khi xem test. Nếu có lần chạy lại do lỗi kỹ thuật, ghi lý do, thời điểm và phân biệt rõ với lần đánh giá cuối; mọi lần thử test đều phải được công khai trong báo cáo.
4. Không đưa bài test hoặc gold test vào prompt, few-shot examples, retrieval index hoặc quá trình tinh chỉnh.
5. Với E2, nếu hậu kiểm đã sinh lại một lần nhưng vẫn phải loại câu chứa claim số không khớp, giữ nguyên bản sau hậu kiểm kể cả khi còn dưới 3 câu hoặc rỗng. Không chèn câu mới, không sinh thêm lần nữa và không khôi phục câu chưa qua hậu kiểm chỉ để đủ độ dài. Ghi rõ số câu còn lại, số câu bị bỏ và số lần sinh lại; xem đây là sai lệch độ dài so với yêu cầu sinh 3–5 câu, không phải đầu ra đạt định dạng.

## 6. Báo cáo kết quả và lưu trữ

Báo cáo riêng dev và test; test chỉ báo cáo sau khi cấu hình đã khóa. Bảng tổng hợp cần có số mẫu, ROUGE-L/1/2 macro-F1, phân bố factuality, numeric precision, numeric hallucination rate, gold numeric recall và số claim làm mẫu số. Đính kèm bảng per-item tối thiểu gồm:

`item_id, split, model_id, rouge1_f1, rouge2_f1, rougeL_f1, output_numeric_claims, supported_claims, unsupported_claims, contradicted_claims, numeric_precision, numeric_hallucination_rate, gold_numeric_recall, factuality_score, reviewer_note`.

Lưu output tóm tắt và log cấu hình cục bộ trong khi quyền tái phân phối chưa rõ; không đẩy văn bản bài báo, gold summary hoặc câu nguồn lên GitHub công khai. Ghi các trường hợp lỗi cụ thể trong báo cáo nhưng không trích nguyên văn bài báo nếu chưa được cấp quyền.

Nếu không có Git commit hợp lệ, không tạo hoặc giả lập commit: để `run_commit` trống, ghi `source_fingerprint` SHA-256 và `worktree_status=uncommitted` vào manifest/báo cáo. Fingerprint bao phủ nội dung trong thư mục dự án, bỏ qua `.git`, môi trường ảo, cache và `reports/`; đây chỉ là dấu vết provenance cho lần chạy dev, không thay thế commit/tag và không đáp ứng điều kiện mở test.
