# CP0 — Khởi động, contract & ingestion raw

> Mốc: 00:00–00:30 · Lệnh kiểm chứng: `ls data/raw`

## 1. Pass criteria — trạng thái

| Tiêu chí | Trạng thái | Bằng chứng |
|---|---|---|
| Raw response tồn tại | ĐẠT | `data/raw/crossref_response.json` — 129,376 bytes |
| Raw records JSON tồn tại | ĐẠT | `data/raw/crossref_records.json` — 64,130 bytes, 24 records |
| `PaperRecord` có stable `paper_id` | ĐẠT | 24/24 non-empty, unique, 100% đúng định dạng DOI |
| Mỗi người biết artifact mình bàn giao | ĐẠT | Bảng ownership ở mục 5 |

Kiểm chứng tính ổn định của `paper_id`:

- Parse lại cùng payload đã lưu → danh sách `paper_id` **không đổi** (`reparsed == records`).
- Ghi ra JSON rồi `load_raw_records` đọc lại → **bằng đúng object gốc** (roundtrip equal).

## 2. Môi trường đã chốt

| Hạng mục | Giá trị |
|---|---|
| Python | 3.12.10 (yêu cầu `>=3.11,<3.14`) |
| Virtualenv | `.venv/` tạo bằng `py -3.12 -m venv .venv` |
| Cài đặt | `pip install -e ".[dev]"` — `pip check`: no broken requirements |
| LLM provider | `openrouter` · model `google/gemini-2.5-flash` |
| Credential | `OPENROUTER_API_KEY` đã set — `require_llm_credentials()` PASS |
| Embedding | `sentence-transformers/all-MiniLM-L6-v2` |
| Collections | `papers-baseline` / `papers-corrupted` / `papers-repaired` |
| `top_k` | 4 |
| Ngưỡng freshness | 180 ngày |

`.env` nằm trong `.gitignore` — key không vào Git. Không hard-code credential trong source.

## 3. Contract ingestion

| Câu hỏi | Trả lời |
|---|---|
| Source nào? | Crossref REST API — `https://api.crossref.org/works` |
| Query | `agentic retrieval augmented generation large language model` |
| Filter | `from-pub-date:<hôm nay - 180 ngày>,has-abstract:true` |
| Số lượng | `rows=24` (`settings.max_results`) |
| Kết quả | 100,907 bản ghi khớp trên Crossref → lấy 24 → 24 hợp lệ, 0 bị loại |

### Record schema — `PaperRecord`

| Field | Nguồn Crossref | Ghi chú |
|---|---|---|
| `paper_id` | `DOI` | Bỏ prefix resolver + lowercase. **Đây là khoá lineage xuyên suốt raw → clean → index → eval** |
| `title` | `title[0]` (+ `subtitle[0]`) | Ghép subtitle nếu chưa nằm trong title |
| `summary` | `abstract` | Crossref trả **JATS XML**: strip tag + unescape entity, và xoá hẳn element `<title>`/`<jats:title>` vì đó là section heading chứ không phải nội dung |
| `authors` | `author[]` | `given family`, fallback `name` cho tác giả là tổ chức |
| `categories` | `subject` → `container-title` → `short-container-title` → `group-title` → `type` | Xem cảnh báo mục 6 |
| `primary_category` | `categories[0]` | |
| `published` | `issued` → `published` → `published-online` → `posted` → `created` | `date-parts` thiếu tháng/ngày sẽ được pad về `01` |
| `updated` | `deposited` → `indexed` → `created` | Ưu tiên `date-time` có giờ |
| `abs_url` | `URL` | |
| `pdf_url` | `link[]` ưu tiên `application/pdf`, rồi `text-mining` | 16/24 có, phần còn lại `link` là `null` |
| `comment` | `type \| container-title \| publisher` | Provenance ngắn để truy vết nguồn phát hành |

### Nguyên tắc phân tầng

`parse_crossref_payload` **chỉ loại record thiếu `DOI`, `title` hoặc `abstract`** — ba field mà toàn bộ pipeline phía sau phụ thuộc. Mọi quyết định khác (dedupe, lọc ngôn ngữ, lọc độ dài, cắt prefix "Abstract") thuộc về bước cleaning, để raw snapshot còn phản ánh đúng những gì source trả về.

Raw response được ghi xuống đĩa **trước khi parse**: nếu parsing sai thì vẫn còn nguyên payload gốc để debug hoặc repair mà không phải gọi lại source.

### Chống lỗi tạm thời

Retry với exponential backoff cho `429/500/502/503/504`, tối đa 5 lần, tôn trọng header `Retry-After` khi Crossref gửi về. Hết số lần thì raise `RuntimeError` — **không** nuốt lỗi và **không** thay bằng dữ liệu bịa.

## 4. Sơ đồ handoff

```text
Crossref REST API
  │  fetch_source_records()          [ingest]
  ├─► data/raw/crossref_response.json   ← snapshot payload gốc
  └─► data/raw/crossref_records.json    ← list[PaperRecord]
        │  build_clean_dataframe()    [clean]
        ├─► data/clean/papers_clean.csv | .json
        │     │  LocalEmbeddingIndex   [rag]
        │     ├─► data/embeddings/papers_embeddings.json
        │     └─► data/chroma/ (papers-baseline)
        │           │  build_test_set() + evaluate()   [eval]
        │           ├─► data/eval/test_set.json
        │           └─► data/results/baseline_metrics.json | baseline_answers.json
        │                 │  quality + freshness + report   [observe]
        │                 ├─► data/quality/freshness_report.json
        │                 └─► data/reports/phase1_report.md
        │
        └─► corruption → repair → so sánh 3 trạng thái   [CP5–CP6]
```

Khoá nối các tầng là `paper_id`. Ở CP3 phải chứng minh được **một** `paper_id` đi xuyên suốt raw → clean → index metadata → `ground_truth_doc_ids`.

## 5. Ownership — ai bàn giao artifact nào

| Role | Người phụ trách | Nhận input từ | Bàn giao artifact | Tiêu chí hoàn thành |
|---|---|---|---|---|
| **lead** | _(điền tên)_ | — | `src/core/config.py`, `src/pipelines/phase1.py`, `corruption_flow.py` | Chạy được `script/run_phase1.py` end-to-end, artifact khớp report |
| **ingest** | _(điền tên)_ | Crossref API | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | 2 file tồn tại, `paper_id` unique + stable, có log số record bị loại |
| **clean** | _(điền tên)_ | `crossref_records.json` | `data/clean/papers_clean.csv` + `.json` | Có `text_for_embedding`, `age_days`; `paper_id` unique; truy vết được lý do loại record |
| **rag** | _(điền tên)_ | `papers_clean.csv` | `data/embeddings/papers_embeddings.json`, collection `papers-baseline` | Semantic search + exact lookup trả kết quả có nguồn |
| **eval** | _(điền tên)_ | `papers_clean.csv` + index | `data/eval/test_set.json`, `data/results/baseline_metrics.json`, `baseline_answers.json` | `ground_truth_doc_ids` lấy từ `paper_id` clean, mọi ID tồn tại trong index |
| **observe** | _(điền tên)_ | clean + metrics | `data/quality/`, `data/reports/phase1_report.md`, `corruption_report.md` | Report khớp số liệu JSON/CSV thật, không hard-code pass |

### Gộp vai theo quy mô nhóm

| Quy mô | Cách gộp |
|---|---|
| 3 người | `lead+ingest+clean` · `rag+eval` · `observe` |
| 4 người | `lead` · `ingest+clean` · `rag` · `eval+observe` |
| 5 người | `lead` · `ingest` · `clean` · `rag` · `eval+observe` |
| 6 người | Mỗi người một role |

## 6. Rủi ro chuyển sang CP1

Bốn điểm dưới đây là **quyết định của owner cleaning**, đã cố ý không xử lý ở tầng raw:

1. **`subject` rỗng 0/24.** Crossref hầu như không trả `subject` cho nhóm publisher này. `categories` hiện đang lấy từ fallback chain, nên giá trị thực tế là *tên tạp chí* chứ không phải chủ đề. Hệ quả: 4/24 record có `primary_category = "In Review"` (đó là container-title của Research Square, không mang nghĩa phân loại). Nếu CP2 định ra câu hỏi về category thì phải cân nhắc — dữ liệu này yếu.

2. ~~**8/24 summary bắt đầu bằng "Abstract".**~~ **ĐÃ XỬ LÝ ở CP1** — nhưng sửa tại tầng parse này, không phải tầng cleaning. Crossref bọc section heading trong `<jats:title>` **và** `<title>` trần (`Abstract`, `ABSTRACT`, `Summary`, `Introduction`, `BACKGROUND`…). Chỉ strip tag sẽ để lại chính chữ heading dính vào đầu summary. `_strip_markup` nay xoá cả tag lẫn nội dung của element `title`. Đây là tầng duy nhất còn phân biệt được heading với văn xuôi: sau khi về plain text thì "Summary" (nhãn mục) và "Summary" (từ trong câu) là một. Kết quả: 9/24 summary được làm sạch, `paper_id` và `title` không đổi.

3. **1/24 record tiếng Nga** (`10.47576/2949-1894.2026.7.7.023`, 40% ký tự non-ASCII). Query là free-text nên lọt record không phải tiếng Anh. MiniLM xử lý tiếng Nga rất kém → cân nhắc lọc ở cleaning. Lưu ý: **không** dùng field `language` của Crossref để lọc — field này không nằm trong whitelist của tham số `select` (API trả 400), và cũng không có mặt trên phần lớn record.

4. **8/24 thiếu `pdf_url`** do `link` là `null`. Không chặn pipeline nhưng cần quyết định: để rỗng hay drop — và data quality check ở CP1 phải phản ánh đúng con số này.

Ngoài ra: `published` trải từ 2026-02-12 đến 2026-08-01, độ dài summary 826–2,610 ký tự (median 1,687), 1–7 tác giả mỗi record. Đây là baseline để `observe` phát hiện bất thường sau corruption.
