# Demo minh họa — ĐT05 (Tóm tắt tin kinh tế có kiểm chứng dữ kiện)

Ứng dụng demo trong [`demo.py`](demo.py) cho phép người dùng nhập URL bài báo công khai hoặc dán bài báo kinh tế tiếng Việt, nhận bản tóm tắt và bảng **chú thích câu nguồn bảo chứng** cho từng phát biểu định lượng theo chuẩn trích xuất và đối chiếu của [`../evaluation_protocol.md`](../evaluation_protocol.md).

## 1. Tính năng

- **Ba chế độ:**
  - `E0` (Lead-3): chạy hoàn toàn **offline**, không cần mạng hay API key.
  - `E1` (`e1-basic-v1`) và `E2` (`e2-numeric-v1` + hậu kiểm `regenerate_once_then_drop`): gọi Ollama Cloud khi biến môi trường `OLLAMA_API_KEY` được cấu hình.
- **Chú thích nguồn cho số liệu:** tách mọi phát biểu số/đơn vị từ tóm tắt, kiểm tra trạng thái khớp bề mặt (`value_unit_match`, `value_only`, `value_unit_differs`, `not_found`) và trích nguyên câu tương ứng trong bài nguồn (`[Câu k]`).
- **Nhập bài từ URL:** hỗ trợ URL HTTP/HTTPS công khai trả về HTML tĩnh; chỉ tải tối đa 2 MB và theo tối đa 5 lần chuyển hướng. URL dùng địa chỉ nội bộ/IP trực tiếp bị từ chối. Trang cần JavaScript, đăng nhập, paywall hoặc chặn bot có thể không trích được; khi đó hãy dán nội dung bài vào ô văn bản.
- **Cảnh báo & từ chối:** từ chối đầu vào rỗng; cảnh báo nếu bài viết quá ngắn (< 60 từ) hoặc ngoài phạm vi 250–900 từ; cảnh báo khi tóm tắt vượt 50–120 từ / 3–5 câu hoặc có số liệu không khớp bề mặt nguồn; không dùng cho tư vấn tài chính hoặc quyết định chính sách.
- **Quyền riêng tư:** E0 chạy cục bộ. E1/E2 gửi nội dung bài báo tới Ollama Cloud để sinh tóm tắt; chỉ dùng URL và nội dung bạn có quyền xử lý. Demo không lưu bài đã tải vào tệp.

## 2. Cách chạy

Cài đặt phụ thuộc từ thư mục gốc `BTL/`:

```bash
pip install -r requirements.txt
```

### Chạy CLI

```bash
# E0 chạy offline, không cần API key
python app/demo.py --input-file app/sample_input.txt --mode E0

# E1/E2 cần Ollama Cloud và biến môi trường OLLAMA_API_KEY
python app/demo.py --input-file app/sample_input.txt --mode E1
python app/demo.py --input-file app/sample_input.txt --mode E2
```

Để tránh ghi key vào lịch sử lệnh, có thể nạp key an toàn trong PowerShell:

```powershell
$secure = Read-Host "OLLAMA_API_KEY" -AsSecureString
$env:OLLAMA_API_KEY = [System.Net.NetworkCredential]::new("", $secure).Password
```

Thêm `--json` để xuất kết quả theo JSON, ví dụ:

```bash
python app/demo.py --input-file app/sample_input.txt --mode E2 --json
```

### Chạy giao diện Web cục bộ (không cần cài thêm thư viện ngoài `requirements.txt`)

```bash
python app/demo.py --serve --port 8000
```

Sau đó mở trình duyệt tại `http://127.0.0.1:8000`.

Trong giao diện, chọn `E0`, `E1` hoặc `E2` ở **Cấu hình tóm tắt**, sau đó dán URL bài báo vào trường **Link bài báo** hoặc dán nội dung vào ô văn bản và chọn **Tóm tắt & Kiểm chứng số liệu**. E0 chạy offline; E1/E2 cần `OLLAMA_API_KEY` trong terminal đang chạy demo. E2 có thể bỏ câu sau lần sinh lại nếu claim số vẫn không khớp, vì vậy kết quả có thể ngắn hơn 3 câu và sẽ kèm cảnh báo. Nếu có URL, ứng dụng dùng nội dung tải từ URL thay cho phần văn bản dán. Hãy kiểm tra nội dung trích xuất trước khi gửi cho E1/E2.

Để trình diễn E1/E2 mà không có API key, chạy demo với phản hồi tổng hợp:

```bash
python app/demo.py --serve --port 8000 --mock-api
```

Giao diện sẽ đánh dấu rõ **MOCK API**. E1 trả placeholder; E2 tạo claim số giả để minh họa retry/hậu kiểm. Đây không phải bản tóm tắt thật và không gửi nội dung bài báo tới Ollama. Nếu nhập URL, demo vẫn tải trang được chọn để trích nội dung.

## 3. Dữ liệu mẫu kiểm thử

[`sample_input.txt`](sample_input.txt) là bài báo **tổng hợp giả định do nhóm tự soạn** (không trích từ VietOnlineNews để tuân thủ quy định bản quyền). Kết quả chạy mẫu được lưu tại [`sample_expected_output.md`](sample_expected_output.md).
