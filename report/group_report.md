# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | K3 |
| Tên nhóm         | Vua của Hà Nội |
| Repository         | https://github.com/Tran-Viet-Bach/DAY10_D303_VuaCuaHaNoi |
| Ngày hoàn thành | 2026-08-06 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Trần Vương Hưng | 2A202601789 | Lead / Pipeline Integrator | `src/core/`, `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py` — cấu hình, orchestration, release |
| 2 | Đoàn Quốc Việt | 2A202601623 | Ingestion owner | `src/ingestion/crossref.py`, `data/raw/` — fetch Crossref, raw snapshot, retry/backoff |
| 3 | Nguyễn Tuấn Khanh | 2A202601139 | Cleaning & Corruption owner | `src/ingestion/cleaning.py`, `src/ingestion/corruption.py` — clean schema, 6 kịch bản corruption, repair |
| 4 | Nguyễn Chính Nghĩa | 2A202601815 | RAG & Agent owner | `src/retrieval/` (`index.py`, `qa.py`, `agent.py`, `embeddings.py`, `llm.py`), `data/embeddings/` — embedding, ChromaDB, truy xuất, agent |
| 5 | Trần Việt Bách | 2A202601773 | Evaluation & Observability owner | `src/evaluation/`, `src/observability/` — test set, metrics, quality/freshness checks, báo cáo |

## 2. Tóm tắt kết quả

Nhóm đã hoàn thành toàn bộ pipeline end-to-end: ingestion từ Crossref REST API (24 bản ghi), cleaning thành schema 10 cột chuẩn hoá, embedding bằng MiniLM-L6-v2 vào ChromaDB (collection `papers-baseline`), xây dựng frozen test set gồm 8 câu hỏi thuộc 4 loại (summary, authors, date, categories), và đánh giá baseline cho ra `retrieval_hit_rate = 1.000`, `mean_token_f1 = 1.000`, `judge_accuracy = 0.750`, `mean_judge_score = 4.75` (giám khảo LLM: Ollama llama3.1). Toàn bộ 6 quality check (Volume, Completeness ×2, Uniqueness, Validity, Freshness) đều PASS, freshness baseline `is_fresh = true` với 0/24 dòng stale.

Nhóm đã tiêm 6 corruption có kiểm soát: xoá bản ghi (`drop_latest_record`), xoá trống tóm tắt (`blank_summary`), tiêm nhiễu (`add_noise`), cắt tiêu đề (`truncate_title`), đổi ngày thành 2000-01-01 (`stale_date`), và nhân đôi dòng (`duplicate_row`) — 4/6 kịch bản nhắm trực tiếp vào tài liệu thuộc ground truth. Corruption ảnh hưởng rõ nhất là **`blank_summary`**: tài liệu vẫn được truy xuất đúng (hit=True) nhưng token F1 của câu hỏi đó rơi về 0.000 vì không còn nội dung để rút trích, kéo `mean_token_f1` toàn cục từ 1.000 xuống 0.767. Ba quality check chuyển FAIL: `paper_id_unique` (do duplicate), `summary_min_length` (do blank), `freshness_age_days` (do stale_date), khiến `overall_status` chuyển PASS → FAIL.

Repair (chạy lại `build_clean_dataframe()` từ raw snapshot bất biến, không gọi lại API) phục hồi 100%: cả 4 metrics quay về đúng giá trị baseline, 6/6 quality check PASS trở lại, freshness `is_fresh = true`, và lineage check `set(paper_id)` baseline == repaired = **True**. Giới hạn quan trọng nhất: bộ test set được sinh từ chính dữ liệu clean (tiêu đề nhúng trong câu hỏi, đáp án lấy từ đúng trường mà logic rút trích trả về), nên baseline 1.0 tuyệt đối phản ánh một mốc chuẩn sạch chứ không phải năng lực tổng quát của hệ thống; 2/6 kịch bản corruption (`truncate_title`, `stale_date`) không làm thay đổi bất kỳ metric nào, chỉ bị quality/freshness check phát hiện — minh chứng cho việc metrics và data quality checks có điểm mù khác nhau và cần dùng song song.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API
    -> raw response/raw records (data/raw/)
    -> cleaning và data modeling (data/clean/)
    -> embedding + ChromaDB index (data/embeddings/, collection papers-baseline)
    -> evaluation baseline (data/results/baseline_metrics.json)
    -> quality/freshness reports (data/quality/)
    -> corruption (data/results/corruption_log.json, data/clean/papers_clean_corrupted.*)
    -> re-index và re-evaluate (collection papers-corrupted)
    -> repair từ raw snapshot (data/clean/papers_clean_repaired.*, collection papers-repaired)
    -> comparison report (data/reports/corruption_report.md)
```

### Trách nhiệm của từng khối

| Khối             | Input          | Xử lý chính             | Output/artifact          | Owner          |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion         | Crossref REST API (`query=agentic retrieval augmented generation large language model`, `filter=from-pub-date:...,has-abstract:true`) | Fetch với retry/backoff luỹ thừa cho mã 429/5xx (tối đa 5 lần); parse JSON → `PaperRecord`; ghi raw response trước khi parse | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Đoàn Quốc Việt |
| Cleaning          | 24 `PaperRecord` thô | Bóc thẻ JATS XML, lọc title/summary rỗng hoặc < 100 ký tự, chuẩn hoá authors/categories, tính `age_days`, dựng `text_for_embedding`, dedupe theo `paper_id`, `fillna` cho toàn bộ cột | `data/clean/papers_clean.csv`, `.json` | Nguyễn Tuấn Khanh |
| Embedding/index   | DataFrame sạch 24 dòng | Nhúng bằng `sentence-transformers/all-MiniLM-L6-v2` (384 chiều), lưu vào ChromaDB, không gian cosine | `data/embeddings/papers_embeddings.json`, collection `papers-baseline` | Nguyễn Chính Nghĩa |
| Evaluation        | DataFrame sạch + test set đóng băng | Sinh 8 câu hỏi (4 loại × 2), đánh giá qua `qa.py` (tra cứu chính xác + tìm kiếm ngữ nghĩa), tính `retrieval_hit_rate`, `mean_token_f1`, LLM judge | `data/eval/test_set.json`, `data/results/baseline_metrics.json`, `baseline_answers.json` | Trần Việt Bách |
| Observability     | DataFrame sạch/corrupted/repaired | 6 quality check (Volume, Completeness, Uniqueness, Validity, Freshness); freshness threshold 180 ngày | `data/quality/*_quality.json`, `*_freshness_report.json` | Trần Việt Bách |
| Corruption/repair | Baseline DataFrame + `ground_truth_doc_ids` | 6 kịch bản corruption có log before/after; repair bằng cách chạy lại cleaning từ raw snapshot | `data/results/corruption_log.json`, `data/clean/papers_clean_corrupted.*`, `papers_clean_repaired.*` | Nguyễn Tuấn Khanh |
| Orchestration     | Toàn bộ pipeline | `script/run_phase1.py` (baseline end-to-end), `script/run_corruption_flow.py` (corrupt → repair → compare) | `data/reports/phase1_report.md`, `corruption_report.md` | Trần Vương Hưng |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER`             | `ollama` |
| `LLM_MODEL`                | `llama3.1` |
| Embedding model              | `sentence-transformers/all-MiniLM-L6-v2` (384 chiều) |
| Số lượng Crossref records | 24 (`max_results=24`) |
| Retrieval `top_k`           | 4 |
| Freshness threshold          | 180 ngày |
| Random seed, nếu có        | Không dùng seed cố định; `temperature=0.0` cho LLM judge để giảm ngẫu nhiên |

Không dán nội dung API key hoặc file `.env` vào báo cáo. Ollama chạy cục bộ (`http://localhost:11434`), không cần API key.

### Lệnh cài đặt

```bash
uv sync
```

### Lệnh chạy

Baseline:

```bash
uv run python script/run_phase1.py
```

Corruption flow:

```bash
uv run python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh             | Trạng thái                                    | Thời điểm chạy gần nhất | Bằng chứng                         |
| ----------------- | ----------------------------------------------- | ----------------------------- | ------------------------------------ |
| Baseline pipeline | Thành công | 2026-08-06T03:15:32Z | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| Corruption flow   | Thành công | 2026-08-06T03:24:40Z | `data/results/corrupted_metrics.json`, `repaired_metrics.json`, `data/reports/corruption_report.md` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính                | Giá trị                             |
| --------------------------- | ------------------------------------- |
| Source                      | Crossref REST API — `https://api.crossref.org/works` |
| Query/filter                | `query=agentic retrieval augmented generation large language model`; `filter=from-pub-date:2026-02-07,has-abstract:true` |
| Thời điểm lấy dữ liệu | 2026-08-06 (cache raw snapshot, `REFRESH_SOURCE=false` cho các lần chạy sau) |
| Số record nhận được    | 24 (khớp `max_results`) |
| Cơ chế retry/backoff      | Retry tối đa 5 lần cho mã 429/500/502/503/504, backoff luỹ thừa (`1s × 2^attempt`), tôn trọng header `Retry-After` nếu có |

### Raw và clean schema

| Trường        | Kiểu dữ liệu | Bắt buộc?  | Ý nghĩa   | Xử lý khi thiếu/sai |
| --------------- | --------------- | ------------ | ----------- | ---------------------- |
| `paper_id` | string | Có | Slug từ DOI, khoá chính duy nhất | Bản ghi thiếu DOI bị loại ngay từ bước parse |
| `title` | string | Có | Tiêu đề bài báo, đã chuẩn hoá khoảng trắng | Rỗng → loại khỏi clean dataset |
| `summary` | string | Có | Abstract, đã bóc thẻ JATS XML | < 100 ký tự → loại khỏi clean dataset |
| `published` | string (ISO date) | Không | Ngày xuất bản | Parse lỗi → chuỗi rỗng, đồng thời `age_days = -1` (sentinel) |
| `authors_joined` | string | Không | Danh sách tác giả nối bằng dấu phẩy | Rỗng nếu Crossref không có trường `author` |
| `categories_joined` | string | Không | Danh mục, có 3 tầng dự phòng: `subject` → `container-title` → `type` | Rỗng nếu cả 3 tầng đều thiếu (không chặn bởi quality check, vì đây là hạn chế phổ biến của Crossref) |
| `age_days` | int | Có | `run_date − published`, tính theo ngày | Sentinel `-1` khi không parse được ngày; bị `freshness_age_days` check bắt cùng chiều với `> 180` |
| `text_for_embedding` | string | Có | Ghép `Title + Authors + Summary`, dùng để nhúng vector | Dựng lại tự động nếu bất kỳ trường gốc nào đổi (áp dụng khi corrupt) |
| `abs_url`, `pdf_url` | string | Không | Liên kết bài báo | Rỗng nếu Crossref không cung cấp |

### Quy tắc cleaning

| Quy tắc                                 | Quality dimension liên quan | Số record bị tác động | Cách xác minh      |
| ---------------------------------------- | ---------------------------- | -------------------------: | -------------------- |
| Loại record thiếu DOI/title/abstract | Completeness | 0 (24 raw → 24 clean, không có record nào bị loại trong lần chạy này) | So `raw_records` (24) với `clean_records` (24) trong `phase1_report.md` |
| Loại record có `summary` < 100 ký tự | Validity | 0 | `data/quality/baseline_quality.json` → `summary_min_length` PASS, actual=0 |
| Dedupe theo `paper_id`, giữ bản ghi đầu tiên | Uniqueness | 0 | `paper_id_unique` PASS, actual=0 duplicate |
| `fillna` toàn bộ cột chuỗi → `""`, `age_days` → `-1` | Completeness | Áp dụng cho mọi dòng còn NaN sau bước lọc | Kiểm tra `papers_clean.csv` không còn giá trị rỗng gây lỗi ChromaDB |

`text_for_embedding` được dựng bằng cách ghép `f"Title: {title}\nAuthors: {authors_joined}\nSummary: {summary}"` — đủ ngữ cảnh chủ đề (title), nội dung (summary) và tên người (authors) trong giới hạn ~256 token của MiniLM. `paper_id` là slug hoá từ DOI Crossref (khoá tự nhiên, ổn định qua các lần fetch). `age_days` được tính bằng `run_date.date() − published_ts.date()`, với `run_date` được **truyền vào** hàm thay vì gọi `datetime.now()` bên trong — đảm bảo tính tất định khi repair chạy lại cùng logic trên cùng raw snapshot.

## 6. Evaluation setup

| Thành phần                             | Cấu hình thực tế          |
| ---------------------------------------- | ----------------------------- |
| Số câu hỏi                            | 8 |
| Các `question_type`                    | `summary` (2), `authors` (2), `date` (2), `categories` (2) |
| Ground-truth document ID                 | Lấy trực tiếp từ `paper_id` của dòng dữ liệu sinh ra câu hỏi (không tự bịa) |
| Embedding model                          | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store/collection                  | ChromaDB, `papers-baseline` / `papers-corrupted` / `papers-repaired` (tách riêng, không đè nhau), không gian cosine |
| Retrieval `top_k`                       | 4 |
| LLM provider/model                       | Ollama / `llama3.1`, `temperature=0.0`, structured output (`JudgeVerdict`) |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` (đóng băng sau khi sinh ở baseline, `REFRESH_TEST_SET=false`) |

Test set được giữ nguyên khi đánh giá baseline, corrupted và repaired vì thí nghiệm chỉ hợp lệ khi **đúng một biến thay đổi giữa các lần đo** — ở đây là chất lượng dữ liệu. Nếu đổi bộ câu hỏi giữa các lần chạy, sự thay đổi của metric có thể do đề khác nhau chứ không chắc chắn do dữ liệu hỏng, khiến mọi kết luận về tác động của corruption/repair mất giá trị. Trong code, cả ba lần gọi `evaluate_pipeline()` (`phase1.py`, `corruption_flow.py`) đều trỏ tới cùng `paths.eval_testset`; thứ duy nhất thay đổi là index (`papers-baseline` / `-corrupted` / `-repaired`).

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế                | Trạng thái | Ghi chú   |
| ------------------------ | -------------------------------------- | ------------ | ---------- |
| Raw response/records     | `data/raw/crossref_response.json`, `crossref_records.json` | Có | Ghi trước khi parse, làm điểm phục hồi cho bước repair |
| Cleaned dataset          | `data/clean/papers_clean.csv`, `.json` | Có | 24 dòng, 10 cột, 0 giá trị null |
| Embedding manifest/index | `data/embeddings/papers_embeddings.json` | Có | Collection `papers-baseline`, 24 documents |
| Evaluation set           | `data/eval/test_set.json` | Có | 8 câu hỏi, đóng băng |
| Baseline metrics         | `data/results/baseline_metrics.json` | Có | — |
| Quality/freshness        | `data/quality/baseline_quality.json`, `freshness_report.json` | Có | Overall PASS, is_fresh=true |
| Baseline report          | `data/reports/phase1_report.md` | Có | — |

### Baseline metrics

| Metric                 |       Giá trị | Diễn giải                             |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate` |     1.0000 | Cả 8/8 câu đều tìm được tài liệu đúng trong top-4. Baseline sạch vì test set sinh từ chính dữ liệu (tiêu đề nhúng trong câu hỏi kích hoạt đường tra cứu chính xác) — đây là mốc chuẩn không nhiễu nền, không phải bằng chứng năng lực tổng quát |
| `mean_token_f1`      |     1.0000 | Rút trích tất định trong `qa.py` trả đúng trường ứng với từng loại câu hỏi, khớp 100% với ground truth lấy từ cùng trường đó |
| `judge_accuracy`     |     0.7500 | 6/8 câu được LLM judge (Ollama llama3.1) đánh giá `correct=True`; 2 câu (q2, q7) có F1=1.0 (trùng khớp tuyệt đối) nhưng vẫn bị chấm `correct=False` — cho thấy giám khảo LLM có tiêu chí riêng, không chỉ dựa trên trùng khớp từ ngữ |
| `mean_judge_score`   |     4.7500 | Trung bình điểm 1–5 trên 8 câu (điểm thấp nhất là 4/5, không có điểm dưới 4) |
| Ragas, nếu có        | N/A (skipped) | `RUN_RAGAS` không được bật (mặc định tắt vì tốn thời gian); metrics ghi rõ `"skipped": "Set RUN_RAGAS=1 to enable the slower Ragas pass."` |

## 8. Data quality và freshness

### Quality checks

| Check        | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline      | Bằng chứng |
| ------------ | ----------------- | ------------------ | ----------------------- | ------------ |
| `row_count` | Volume | ≥ 1 | PASS (actual=24) | `data/quality/baseline_quality.json` |
| `paper_id_not_null` | Completeness | 0 missing | PASS (actual=0) | `data/quality/baseline_quality.json` |
| `paper_id_unique` | Uniqueness | no duplicates | PASS (actual=0) | `data/quality/baseline_quality.json` |
| `title_not_null` | Completeness | 0 missing | PASS (actual=0) | `data/quality/baseline_quality.json` |
| `summary_min_length` | Validity | ≥ 100 chars | PASS (actual=0 dòng vi phạm) | `data/quality/baseline_quality.json` |
| `freshness_age_days` | Freshness | ≤ 180 ngày | PASS (actual=0 dòng stale) | `data/quality/baseline_quality.json` |

Ghi chú thiết kế: nhóm **chủ động không** kiểm tra `categories_joined` khác rỗng, vì trường `subject` của Crossref thường thiếu ngay cả sau 3 tầng dự phòng (`subject` → `container-title` → `type`) — thêm check này sẽ FAIL ngay từ baseline vì lý do không phải lỗi dữ liệu thật.

### Freshness

| Thuộc tính               | Giá trị                           |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại | `data/clean/papers_clean.csv` (bước cleaning, trước khi index) |
| Timestamp mới nhất       | 2026-08-01 |
| Timestamp cũ nhất         | 2026-02-12 |
| Ngưỡng freshness         | 180 ngày |
| Trạng thái baseline      | Fresh |
| Lý do                     | 0/24 dòng có `age_days < 0` hoặc `age_days > 180`; bài mới nhất cách thời điểm chạy 5 ngày, bài cũ nhất cách 175 ngày — nằm gọn trong cửa sổ lọc `from-pub-date` 180 ngày của Crossref query |

## 9. Corruption scenarios và repair

| Corruption         | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair   |
| ------------------ | ---------- | ---------------------: | ------------------------ | --------------------- | -------------- |
| `drop_latest_record` | Xoá hẳn 1 dòng thuộc ground truth (`10-2118-234689-pa`, câu q1) | 1 (24→23, trước khi duplicate bù lại) | `row_count` giảm | `retrieval_hit_rate` giảm: câu q1 hit=False, F1=0.140 | Chạy lại `build_clean_dataframe()` từ raw snapshot |
| `blank_summary` | Đặt `summary=""` cho 1 dòng ground truth (`10-1007-s10278-026-02086-9`, câu q2) | 1 | `summary_min_length` FAIL | Câu q2 vẫn hit=True nhưng F1=0.000; kéo `mean_token_f1` từ 1.000 → 0.767 | Chạy lại `build_clean_dataframe()` từ raw snapshot |
| `add_noise` | Nối chuỗi rác vào `summary` của 1 dòng **ngoài** ground truth (`10-2196-preprints-106157`) | 1 | Không có check cấu trúc nào bắt trực tiếp (mô phỏng nhiễu nền) | Không đổi metric nào (đúng thiết kế, vì nằm ngoài test set) | Chạy lại `build_clean_dataframe()` từ raw snapshot |
| `truncate_title` | Cắt `title` còn 12 ký tự cho 1 dòng ground truth (`10-21203-rs-3-rs-10178277-v1`, câu q3) | 1 | Không có check cấu trúc trực tiếp | Không đổi metric: câu q3 vẫn hit=True, F1=1.000 — tìm kiếm ngữ nghĩa (kiến trúc 2 đường trong `qa.py`) cứu được khi tra cứu chính xác thất bại | Chạy lại `build_clean_dataframe()` từ raw snapshot |
| `stale_date` | Đổi `published` thành `2000-01-01`, `age_days=9999` cho 1 dòng ground truth (`10-3390-buildings16132637`, câu q4) | 1 | `freshness_age_days` FAIL | **Không đổi metric nào** — q4 hỏi về tác giả, không đụng tới `published`; chỉ freshness/quality check bắt được | Chạy lại `build_clean_dataframe()` từ raw snapshot |
| `duplicate_row` | Nhân đôi 1 dòng **ngoài** ground truth (`10-1111-exsy-70341`) | 1 (23→24, bù lại số dòng đã mất ở `drop_latest_record`) | `paper_id_unique` FAIL | Không đổi metric nào (ngoài ground truth); `row_count` vẫn PASS vì tổng số dòng không đổi — chỉ `paper_id_unique` bắt được | Chạy lại `build_clean_dataframe()` từ raw snapshot |

Corruption log:

- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có
- Nhận xét: Log ghi đủ 6 entry, mỗi entry gồm `type`, `paper_id`, `param`, `before`, `after`, và cờ `in_ground_truth` — đủ để truy vết chính xác corruption nào gây ra thay đổi metric nào. Overall: `original_row_count=24`, `corrupted_row_count=24` (xoá 1, thêm 1).

Repair không sửa dữ liệu đã hỏng — nó **dựng lại toàn bộ** bằng cách đọc `data/raw/crossref_records.json` (raw snapshot bất biến, ghi từ trước khi có bất kỳ thao tác corrupt nào) và chạy lại đúng hàm `build_clean_dataframe()` đã tạo ra baseline, với cùng logic lọc/chuẩn hoá. Vì raw snapshot không bao giờ bị ghi đè và `run_date` được truyền vào tường minh (không phụ thuộc đồng hồ hệ thống tại thời điểm gọi), kết quả repair là tất định và tái tạo được — không phụ thuộc vào việc gọi lại Crossref API (vốn có cửa sổ lọc trượt theo thời gian thực, sẽ trả về bộ dữ liệu khác mỗi lần gọi).

## 10. So sánh baseline, corrupted và repaired

| Metric/signal            | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét   |
| ------------------------ | -------: | --------: | -------: | -----------------------: | --------------: | ------------ |
| `retrieval_hit_rate`   | 1.0000 | 0.8750 | 1.0000 | −0.1250 | 100% | Chỉ `drop_latest_record` làm giảm; các corruption còn lại nhắm GT (`truncate_title`, `stale_date`) không ảnh hưởng nhờ kiến trúc truy xuất 2 đường hoặc không liên quan tới câu hỏi bị hỏi |
| `mean_token_f1`        | 1.0000 | 0.7674 | 1.0000 | −0.2326 | 100% | `blank_summary` là nguyên nhân chính (F1 câu q2 = 0.000); `drop_latest_record` đóng góp phần còn lại (F1 câu q1 = 0.140) |
| `judge_accuracy`       | 0.7500 | 0.6250 | 0.7500 | −0.1250 | 100% | Giảm 1/8 câu do q1 mất tài liệu; 2 câu q2/q7 vốn đã `correct=False` từ baseline (do đặc thù LLM judge), không thay đổi thêm |
| `mean_judge_score`     | 4.7500 | 4.3750 | 4.7500 | −0.3750 | 100% | Nhất quán với `judge_accuracy`: điểm giảm ở đúng 2 câu bị corrupt trực tiếp (q1, q2) |
| Quality checks pass/fail | 6/6 PASS | 3/6 FAIL (`paper_id_unique`, `summary_min_length`, `freshness_age_days`) | 6/6 PASS | 3 check chuyển FAIL | 100% | Đúng 3 kịch bản có tác động cấu trúc trực tiếp (duplicate, blank, stale) bị bắt; `add_noise` và `truncate_title` không có check cấu trúc tương ứng nên không đổi |
| Freshness status         | Fresh (0/24 stale) | Stale (1/24 stale, oldest=2000-01-01) | Fresh (0/24 stale) | 1 dòng chuyển stale | 100% | Trực tiếp từ `stale_date`; đây là kịch bản duy nhất **không** ảnh hưởng metrics nhưng **có** ảnh hưởng quality/freshness — minh chứng rõ nhất cho lý do cần cả hai lớp giám sát |

Hai kết luận nhân quả được hỗ trợ bởi artifact:

1. `blank_summary` (xoá trống `summary` của tài liệu GT `10-1007-s10278-026-02086-9`) → `summary_min_length` chuyển FAIL trong `corrupted_quality.json` → `mean_token_f1` giảm từ 1.000 xuống 0.767 trong `corrupted_metrics.json` (do câu q2 rơi từ F1=1.000 xuống 0.000 trong `corrupted_answers.json`, dù vẫn `retrieval_hit=True`).
2. Repair (chạy lại `build_clean_dataframe()` từ `data/raw/crossref_records.json`) → `freshness_age_days` và `paper_id_unique`, `summary_min_length` quay lại PASS trong `repaired_quality.json` → `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`, `mean_judge_score` đều quay về đúng giá trị baseline trong `repaired_metrics.json`, đồng thời `set(paper_id)` của `baseline_df` và `repaired_df` bằng nhau (lineage check `True`, in trong log của `script/run_corruption_flow.py`).

Không phải mọi corruption đều có tác động lên metrics: `add_noise` và `truncate_title` không làm thay đổi bất kỳ chỉ số đánh giá nào — điều này khớp với thiết kế thí nghiệm (một nhắm ngoài ground truth, một bị kiến trúc truy xuất 2 đường của `qa.py` che chắn) nên nhóm không kết luận các corruption này "vô hại", mà kết luận đúng phạm vi: chúng nằm ngoài khả năng phát hiện của bộ metric hiện tại, không phải ngoài khả năng gây hại trong thực tế.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** `LocalEmbeddingIndex.build()` (ChromaDB `collection.add()`) văng lỗi khi metadata chứa giá trị `NaN` từ các cột chưa được xử lý đầy đủ trong DataFrame sạch.
- **Nguyên nhân:** ChromaDB chỉ chấp nhận metadata kiểu `str`, `int`, `float`, `bool`; các dòng có `published` không parse được hoặc trường tuỳ chọn rỗng bị pandas gán `NaN`, vi phạm hợp đồng ngầm giữa bước cleaning và bước embedding.
- **Cách xử lý:** Thêm bước `fillna("")` cho toàn bộ cột chuỗi và `fillna(-1).astype(int)` cho `age_days` ở cuối `build_clean_dataframe()`, biến hợp đồng ngầm thành cam kết tường minh: mọi output của cleaning phải không còn giá trị null trước khi sang bước index.
- **Cách xác minh:** `uv run python script/run_phase1.py` chạy hết pipeline không lỗi; đối chiếu `data/clean/papers_clean.csv` không còn ô rỗng gây lỗi kiểu dữ liệu, và `data/quality/baseline_quality.json` báo `paper_id_not_null` / `title_not_null` đều PASS với actual=0.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng   | Hướng cải thiện có thể kiểm chứng |
| --------------------- | -------------- | ----------------------------------------- |
| Test set sinh từ chính dữ liệu clean (tiêu đề nhúng nguyên văn trong câu hỏi) | Baseline đạt hit_rate/F1 = 1.0 tuyệt đối, không phản ánh năng lực tổng quát của hệ truy xuất | Viết tay thêm 15–20 câu hỏi diễn đạt lại (không chứa tiêu đề nguyên văn), bao gồm câu không có đáp án trong kho, để đo tỉ lệ từ chối trả lời đúng cách |
| Corruption nhắm mục tiêu (luôn chọn tài liệu ground truth) | Đo được độ nhạy của hệ giám sát nhưng không ước lượng được xác suất/mức độ ảnh hưởng khi lỗi rơi ngẫu nhiên trong thực tế | Chạy Monte Carlo: phá ngẫu nhiên có seed cố định, lặp nhiều lần với các tỉ lệ hỏng khác nhau (1%, 5%, 20%), báo cáo phân phối mức sụt giảm |
| Quality gate chỉ ghi log, không chặn pipeline khi FAIL | Dữ liệu hỏng vẫn có thể đi tiếp tới bước index/serve nếu không có người kiểm tra thủ công | Cho `run_data_quality_checks()` ném ngoại lệ khi `overall_status=FAIL` (có cờ bỏ qua tường minh khi cần), biến quan sát thụ động thành cổng chặn chủ động |
| Lineage check chỉ so `set(paper_id)`, chưa băm nội dung từng dòng | Chứng minh danh tính tài liệu khớp nhưng chưa chứng minh tuyệt đối nội dung từng dòng khớp | Bổ sung băm SHA-256 nội dung mỗi dòng (các cột đã sắp thứ tự) và so hai tập băm baseline/repaired |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set (`data/eval/test_set.json`).
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng (`report/<MSSV>_HoTen.md`, theo quy ước trong `report/README.md`).
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.
