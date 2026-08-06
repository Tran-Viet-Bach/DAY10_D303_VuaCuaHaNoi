# CP1 — Cleaning, data model & quality gates

> Mốc: 00:30–01:05 · Lệnh kiểm chứng: `ls data/clean`

## 1. Pass criteria — trạng thái

| Tiêu chí | Trạng thái | Bằng chứng |
|---|---|---|
| Clean CSV/JSON đọc được | ĐẠT | `papers_clean.csv` 23×13, `papers_clean.json` 23 records, đọc lại đúng schema |
| `paper_id` unique | ĐẠT | 23/23 unique, non-null, sống sót qua CSV roundtrip |
| `text_for_embedding` có mặt | ĐẠT | 23/23 non-empty |
| `age_days` có mặt | ĐẠT | dtype `int64`, khoảng 5–175 ngày |
| Count/lý do record bị loại truy vết được | ĐẠT | `data/clean/cleaning_log.json` |

**Phương trình kiểm toán cân bằng:** `24 input = 23 output + 1 dropped + 0 deduped`.

## 2. Artifact bàn giao

| File | Nội dung |
|---|---|
| `data/clean/papers_clean.csv` | 23 hàng × 13 cột |
| `data/clean/papers_clean.json` | cùng dữ liệu, dạng list record |
| `data/clean/cleaning_log.json` | count + lý do từng record bị loại, ngưỡng, anomalies |

## 3. Clean schema

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `paper_id` | str | DOI chuẩn hoá — khoá lineage |
| `title` | str | |
| `summary` | str | Abstract đã bỏ markup và section heading |
| `authors_joined` | str | `", "` — **không** giữ cột list |
| `categories_joined` | str | `", "` |
| `primary_category` | str | |
| `published` | str | ISO `YYYY-MM-DD` — **giữ dạng chuỗi** |
| `updated` | str | |
| `age_days` | int | `run_date - published` |
| `summary_chars` | int | |
| `abs_url` / `pdf_url` | str | |
| `text_for_embedding` | str | `Title: X \| Authors: Y \| Summary: Z` — đúng format đề bài |

Hai quyết định schema có lý do kỹ thuật, **đừng đổi nếu chưa đọc phần này**:

- **Không có cột kiểu list.** `authors`/`categories` chỉ tồn tại ở dạng `*_joined`. Lý do: `write_csv` sẽ biến list thành chuỗi `"['a', 'b']"` và đọc lại ra chuỗi chứ không ra list — CSV và JSON sẽ lệch nhau. Mọi consumer hiện tại (`index.py`, `qa.py`) đều dùng dạng `*_joined`.
- **`published` là string, không phải Timestamp.** `LocalEmbeddingIndex._build_documents` đẩy thẳng `row["published"]` vào Chroma metadata, mà Chroma chỉ nhận scalar `str/int/float/bool`. Một `pd.Timestamp` sẽ làm bước index fail.

Đã xác minh: 9/9 cột mà `_build_documents` đòi hỏi đều có mặt, và không cột nào chứa list/dict.

`text_for_embedding` theo đúng format đề bài: `Title: X | Authors: Y | Summary: Z`. `categories` và `published` **không** nằm trong text được embed. Điều đó chấp nhận được vì `qa.py::_extract_answer` đọc thẳng từ Chroma metadata (`metadata["published"]`, `metadata["categories_joined"]`) chứ không đọc từ content — nên câu trả lời vẫn đúng miễn là retrieve trúng document. Hệ quả duy nhất: câu hỏi *chỉ* nêu ngày tháng hoặc category mà không nhắc title/nội dung sẽ khó match hơn (xem cảnh báo mục 7).

## 4. Quy tắc loại record

| Rule | Ngưỡng | Loại ở lần chạy này |
|---|---|---|
| `missing_paper_id` | paper_id rỗng | 0 |
| `title_too_short` | < 10 ký tự | 0 |
| `summary_too_short` | < 100 ký tự | 0 |
| `non_english_summary` | non-ASCII > 30% | **1** |
| `unparsable_published` | không parse được ngày | 0 |
| dedupe theo `paper_id` | giữ bản đầu tiên | 0 |

Ngưỡng nằm ở module level trong `src/ingestion/cleaning.py` (`MIN_SUMMARY_CHARS`, `MIN_TITLE_CHARS`, `MAX_NON_ASCII_RATIO`) và được ghi vào `cleaning_log.json` mỗi lần chạy, nên report luôn nói đúng ngưỡng đã dùng.

**Record duy nhất bị loại:** `10.47576/2949-1894.2026.7.7.023` — abstract tiếng Nga, 40% ký tự non-ASCII. Lý do loại: evaluation set là tiếng Anh và `all-MiniLM-L6-v2` xử lý tiếng Nga rất kém, nên record này chỉ làm nhiễu index. Đây là **quyết định có thể đảo ngược**: đổi `MAX_NON_ASCII_RATIO` là nó quay lại.

### Cố ý KHÔNG drop

- **Title trùng nhau** → chỉ ghi vào `anomalies.duplicate_titles`. Preprint và bản published có cùng title nhưng khác DOI là chuyện bình thường; drop sẽ làm mất bản ghi hợp lệ. Lần chạy này: 0 trùng.
- **`published` ở tương lai** (`age_days < 0`) → giữ, ghi vào `anomalies.future_published_ids`. Crossref cho phép tạp chí đề ngày phát hành sau. Lần chạy này: 0.
- **Thiếu `pdf_url`** (7/23) → giữ, vì `pdf_url` không tham gia retrieval.

## 5. Sửa ở tầng parse, không phải tầng cleaning

Phát hiện khi rà `text_for_embedding` thật: 4/24 abstract mở đầu bằng section heading (`Abstract`, `ABSTRACT`, `Summary`), và Crossref dùng cả `<jats:title>` lẫn `<title>` trần.

Sửa ở `_strip_markup` trong `src/ingestion/crossref.py` chứ **không** ở cleaning, vì đó là tầng cuối còn thông tin tag: khi text đã phẳng thì không còn phân biệt được `"Summary"` (nhãn mục) với `"Summary"` (một từ trong câu). Cắt bằng regex ở tầng cleaning sẽ cắt nhầm văn xuôi.

Bằng chứng cho thấy phân tầng đúng: record `10.21203/rs.3.rs-9770645/v1` vẫn giữ nguyên `"Background. Insurance penetration in Kenya…"` — chữ "Background." đó nằm trong `<p>`, tức là văn xuôi tác giả viết, không phải heading.

Sau sửa: 9/24 summary sạch hơn, `paper_id` và `title` không đổi. **Raw records được parse lại từ `crossref_response.json` đã lưu, không gọi lại Crossref** — snapshot nguồn giữ nguyên nên so sánh về sau vẫn công bằng.

## 6. Tính lặp lại

| Kiểm tra | Kết quả |
|---|---|
| Chạy 2 lần cùng `run_date` → dataframe giống hệt | `df.equals()` True |
| Thứ tự hàng giống nhau | True (sort `published` desc, `paper_id` asc) |
| Cleaning log giống hệt | True |
| Dữ liệu trên đĩa == build lại | True (11 cột không phụ thuộc `run_date`) |
| `age_days` là hàm của `run_date` | `run_date` +10 ngày → mọi `age_days` +10 |
| JSON dump được | clean JSON + cleaning log đều OK |
| NaN/chuỗi rỗng ở cột bắt buộc | 0 |

## 7. Bàn giao cho CP2

| Nhận | Từ | Dùng để |
|---|---|---|
| `papers_clean.csv` | clean | `rag` build `papers-baseline`; `eval` chọn paper ra đề |
| `cleaning_log.json` | clean | `observe` làm baseline signals |

Ba điểm cần biết trước khi ra đề ở CP2:

0. **Câu hỏi phải nhắc tới title hoặc nội dung.** Vì `text_for_embedding` chỉ chứa title + authors + summary, câu hỏi dạng *"which paper was published on 2026-08-01"* hay *"what papers are in category X"* — không nêu title, không nêu nội dung — sẽ retrieve kém. Ra đề bám vào title/summary, rồi hỏi về ngày/category của paper đó (`_extract_answer` sẽ lấy đáp án từ metadata).
1. **`categories_joined` không phải chủ đề học thuật.** `subject` rỗng 0/24 trên Crossref nên giá trị đang là *tên tạp chí + loại tài liệu* (ví dụ `"SPE Journal, journal-article"`). Có 4 record mang `"In Review"` — đó là container-title của Research Square. Ra câu hỏi dạng *"what categories…"* trên dữ liệu này sẽ cho ground truth khó bảo vệ. Cân nhắc giảm tỉ trọng loại câu hỏi đó.
2. **`ground_truth_doc_ids` phải lấy từ `paper_id` trong `papers_clean.csv`**, không lấy từ raw (raw còn record đã bị loại) và không tự bịa ID.
3. **Baseline để `observe` đối chiếu sau corruption:** 23 hàng, `age_days` 5–175, `summary_chars` median ~1,690, 7/23 thiếu `pdf_url`, 0 trùng title, 0 ngày tương lai.
