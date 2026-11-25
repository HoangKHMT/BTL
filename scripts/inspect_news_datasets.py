from collections import Counter
from datetime import datetime
from pathlib import Path
import re

from datasets import load_dataset


ROOT = Path(__file__).resolve().parents[1]
DATASET_REVISIONS = {
    "VLUS06/VietOnlineNews": "bd8d2a865c8981d34cb9d85f69f62bda7c40b520",
    "undertheseanlp/UVN-1": "42a81b44e1e8228146e56a3fa066cc035384b7d9",
}
ECONOMIC_MARKERS = {
    "%": re.compile(r"%", re.IGNORECASE),
    "tỷ đồng": re.compile(r"tỷ\s+đồng", re.IGNORECASE),
    "USD": re.compile(r"USD", re.IGNORECASE),
    "quý": re.compile(r"\bquý\b", re.IGNORECASE),
}


def main() -> None:
    retrieved_at = datetime.now().astimezone().isoformat(timespec="seconds")
    news = load_dataset(
        "VLUS06/VietOnlineNews",
        revision=DATASET_REVISIONS["VLUS06/VietOnlineNews"],
    )
    split_rows = {name: len(split) for name, split in news.items()}
    total_rows = sum(split_rows.values())
    columns = news["train"].column_names
    category_counts = Counter()
    for split in news.values():
        category_counts.update(split["category"])

    marker_counts = Counter()
    economic_ids: set[str] = set()
    for split in news.values():
        selected = split.select_columns(
            ["id", "category", "title", "description", "content"]
        )
        for row in selected:
            if row["category"] != "Kinh doanh":
                continue
            text = " ".join(
                row[field] or "" for field in ("title", "description", "content")
            )
            matching_markers = [
                marker
                for marker, pattern in ECONOMIC_MARKERS.items()
                if pattern.search(text)
            ]
            if matching_markers:
                economic_ids.add(str(row["id"]))
                marker_counts.update(matching_markers)

    uvn = load_dataset(
        "undertheseanlp/UVN-1",
        revision=DATASET_REVISIONS["undertheseanlp/UVN-1"],
    )
    uvn_train = uvn["train"]
    uvn_dates = [
        str(value)[:10]
        for value in uvn_train["publish_date"]
        if value is not None
    ]
    uvn_date_range = (
        f"{min(uvn_dates)} đến {max(uvn_dates)}" if uvn_dates else "không có dữ liệu"
    )

    ids_path = ROOT / "data" / "vietonline_news_economic_numeric_ids.txt"
    ids_path.parent.mkdir(parents=True, exist_ok=True)
    ids_path.write_text(
        "\n".join(sorted(economic_ids)) + "\n",
        encoding="utf-8",
    )
    categories = sorted(category_counts)
    schema_path = ROOT / "data" / "vietonline_news_schema.txt"
    schema_lines = [
        "Dataset: VLUS06/VietOnlineNews",
        f"Retrieved at: {retrieved_at}",
        f"Revision: {DATASET_REVISIONS['VLUS06/VietOnlineNews']}",
        f"column_names: {', '.join(columns)}",
        f"category ({len(categories)}):",
        *(f"- {category}" for category in categories),
    ]
    schema_path.write_text("\n".join(schema_lines) + "\n", encoding="utf-8")

    report = render_data_card(
        retrieved_at=retrieved_at,
        columns=columns,
        split_rows=split_rows,
        total_rows=total_rows,
        category_counts=category_counts,
        marker_counts=marker_counts,
        economic_match_count=len(economic_ids),
        ids_path=ids_path.relative_to(ROOT).as_posix(),
        uvn_rows=len(uvn_train),
        uvn_columns=uvn_train.column_names,
        uvn_date_range=uvn_date_range,
    )
    card_path = ROOT / "data_card.md"
    previous_card = card_path.read_text(encoding="utf-8") if card_path.exists() else ""
    manual_section = previous_card.find("\n## 7. ")
    if manual_section >= 0:
        report = f"{report.rstrip()}\n\n{previous_card[manual_section + 1:]}"
    card_path.write_text(report, encoding="utf-8")

    print(f"VietOnlineNews columns: {columns}")
    print(f"VietOnlineNews rows by split: {split_rows} (total={total_rows})")
    print("VietOnlineNews category distribution:")
    for category, count in sorted(category_counts.items()):
        print(f"  {category}: {count} ({count / total_rows:.2%})")
    print("Kinh doanh articles matching numeric markers:")
    for marker in ECONOMIC_MARKERS:
        print(f"  {marker}: {marker_counts[marker]}")
    print(f"  unique matching articles: {len(economic_ids)}")
    print(f"UVN-1 columns: {uvn_train.column_names}")
    print(f"UVN-1 rows: {len(uvn_train)}")
    print(f"UVN-1 publish_date range: {uvn_date_range}")
    print(f"Wrote {card_path}")
    print(f"Wrote ID-only list {ids_path}")
    print(f"Wrote schema and categories {schema_path}")


def render_data_card(
    *,
    retrieved_at: str,
    columns: list[str],
    split_rows: dict[str, int],
    total_rows: int,
    category_counts: Counter,
    marker_counts: Counter,
    economic_match_count: int,
    ids_path: str,
    uvn_rows: int,
    uvn_columns: list[str],
    uvn_date_range: str,
) -> str:
    split_table = "\n".join(
        f"| {name} | {count:,} |" for name, count in split_rows.items()
    )
    category_table = "\n".join(
        f"| {category} | {count:,} | {count / total_rows:.2%} |"
        for category, count in sorted(
            category_counts.items(), key=lambda item: (-item[1], item[0])
        )
    )
    marker_table = "\n".join(
        f"| `{marker}` | {marker_counts[marker]:,} |"
        for marker in ECONOMIC_MARKERS
    )
    return f"""# Data Card — VietOnlineNews

## 1. Dataset Summary & Intended Use

Nguồn dữ liệu chính của BTL là `VLUS06/VietOnlineNews`, dùng để xây dựng bộ tham chiếu cho tóm tắt tin kinh tế tiếng Việt và kiểm tra độ bảo toàn dữ kiện định lượng. Dataset gốc là dữ liệu phân loại chủ đề, không có nhãn tóm tắt. Nhóm tự tạo gold cho 60 bài (10 dev, 50 test). Không dùng các dataset tóm tắt tin tên gần giống như `Linhz/Vietnews` hoặc `harouzie/vietnews`.

## 2. Dataset Sources & Versions

| Thuộc tính | VietOnlineNews |
|---|---|
| Hugging Face ID | [`VLUS06/VietOnlineNews`](https://huggingface.co/datasets/VLUS06/VietOnlineNews) |
| Ngôn ngữ / tác vụ gốc | Tiếng Việt / phân loại chủ đề đơn nhãn |
| Revision đã pin | `{DATASET_REVISIONS["VLUS06/VietOnlineNews"]}` |
| Retrieved at | `{retrieved_at}` |
| Hub README mô tả nguồn | VietnamNet, Thanh Niên, Tuổi Trẻ; giai đoạn 2023–2025 |

Schema không có trường `source`, `url` hoặc ngày đăng ở cấp bài nên các thuộc tính này không được suy đoán cho VietOnlineNews; `published_at` được ghi `unknown`, không suy ra từ ngày tải. Dataset đối chiếu UVN-1 không được dùng làm nguồn chính: [`undertheseanlp/UVN-1`](https://huggingface.co/datasets/undertheseanlp/UVN-1), revision `{DATASET_REVISIONS["undertheseanlp/UVN-1"]}`, {uvn_rows:,} dòng, cột `{", ".join(uvn_columns)}`. Metadata UVN-1 có `publish_date` trong khoảng {uvn_date_range}; đây là thông tin metadata, không suy ra từ ngày tải.

## 3. License & Access

Hugging Face Hub khai báo `license: other`; không có SPDX license cụ thể. Mục `LICENSE` trong dataset repository rỗng khi kiểm tra, nên **quyền sử dụng và tái phân phối chưa được xác minh**. Cần xác nhận bằng văn bản với chủ dataset hoặc giảng viên, đồng thời kiểm tra quyền từ các nguồn báo trước khi công bố. Chỉ truy cập qua trang Hub ở trên; không xem việc tải công khai là giấy phép tái phân phối.

Không commit/push tiêu đề, mô tả, toàn văn, bản dump hoặc annotation chứa trích câu nguồn lên repository công khai trong khi chưa rõ quyền. Dữ liệu toàn văn phục vụ gán nhãn chỉ lưu cục bộ; `.gitignore` loại các tệp này khỏi Git.

## 4. Data Structure

Schema gốc: `{", ".join(columns)}`. `category` là nhãn chủ đề gốc, không phải nhãn tóm tắt. Các split tại revision đã tải:

| Split | Số dòng |
|---|---:|
{split_table}
| **Tổng** | **{total_rows:,}** |

Con số loader quan sát được khác Hub README (README ghi 187,682 / 40,218 / 40,218, tổng 268,118); dùng số đếm trực tiếp từ revision đã pin và ghi nhận sai khác này, chưa giải thích nguyên nhân.

## 5. Composition & Distributions

| Category gốc | Số bài | Tỷ lệ |
|---|---:|---:|
{category_table}

Trong category `Kinh doanh`, số bài có ít nhất một chuỗi trong `title`, `description` hoặc `content`:

| Chuỗi dò | Số bài |
|---|---:|
{marker_table}
| **Khớp ít nhất một chuỗi (duy nhất)** | **{economic_match_count:,}** |

Đây là phép dò từ khóa thô, không chứng minh bài có số liệu tài chính hợp lệ. Danh sách kết quả chỉ gồm ID: [`{ids_path}`]({ids_path}).

## 6. Collection & Sampling

Từ 265,729 dòng gốc, giữ 39,878 bài thuộc `Kinh doanh` hoặc `Bất động sản`; loại 155 tiêu đề trùng, 12,712 bài ngoài khoảng 250–900 từ, lấy pool ngẫu nhiên 4,000 bài (seed 42), loại 27 bài gần trùng theo TF-IDF cosine ≥0.8, rồi chọn 60 bài đa dạng chủ đề và tránh bài cùng sự kiện với cosine ≥0.4. Mẫu cuối có 52 bài category `Kinh doanh`, 8 `Bất động sản`; chia 10 dev / 50 test; 48 bài có ít nhất 4 ứng viên số liệu regex (8 dev, 40 test), 12 bài dưới ngưỡng (2 dev, 10 test). Phân bố topic rule-based: `bat_dong_san` 7, `chung_khoan` 7, `doanh_nghiep` 8, `hang_hoa` 8, `khac` 8, `tien_te_ngan_hang` 7, `vi_mo` 7, `xuat_nhap_khau` 8. `khac` là nhãn fallback, không có nghĩa bài chắc chắn phi kinh tế. Quy trình không lấy mẫu đại diện cho toàn bộ dataset.
"""


if __name__ == "__main__":
    main()
