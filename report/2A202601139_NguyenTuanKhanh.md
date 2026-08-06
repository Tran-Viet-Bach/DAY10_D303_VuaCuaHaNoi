# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --------- | -------- |
| Họ và tên | Nguyễn Tuấn Khanh |
| MSSV | 2A202601139 |
| Khóa/Lớp | K3 |
| Tên nhóm | Vua của Hà Nội |
| Vai trò chính | Cleaning & Corruption owner |
| Repository | https://github.com/Tran-Viet-Bach/DAY10_D303_VuaCuaHaNoi |
| Ngày hoàn thành | 2026-08-07 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | ------------------ | -------------- | --------------- | ---------- |
| Clean schema & data modeling | `src/ingestion/cleaning.py` (`build_clean_dataframe`) | `list[PaperRecord]` từ `crossref.py` | `data/clean/papers_clean.{csv,json}`, cột `text_for_embedding` | Hoàn thành |
| Cleaning log & audit | Bản `cleaning.py` mở rộng (`df.attrs["cleaning_log"]`) | Bản ghi bị loại/dedupe trong lúc clean | `data/clean/cleaning_log.json` | **Chưa merge vào `main`** — bản `cleaning.py` được chọn khi giải quyết conflict không ghi log này |
| 6 kịch bản corruption | `src/ingestion/corruption.py` (`corrupt_clean_dataframe`) | Baseline DataFrame + `ground_truth_doc_ids` | `data/results/corruption_log.json`, `data/clean/papers_clean_corrupted.{csv,json}` | Hoàn thành |
| Repair dataset | Chạy lại `build_clean_dataframe()` từ `data/raw/crossref_records.json` | Raw snapshot chưa bị corrupt | `data/clean/papers_clean_repaired.{csv,json}` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --------- | ----------------------------- | ------- |
| Sửa lỗi metadata `NaN` làm ChromaDB từ chối ghi document | Nguyễn Chính Nghĩa (`retrieval/index.py`) | Nguyên nhân nằm ở tầng cleaning của tôi (cột chuỗi để trống thành `NaN`); tôi thêm `fillna("")` cho toàn bộ cột chuỗi và `fillna(-1)` cho `age_days` ngay trong `build_clean_dataframe()` thay vì vá ở tầng index |
| Cung cấp `paper_id` ổn định làm khoá lineage | Trần Việt Bách (`evaluation/testset.py`) | `ground_truth_doc_ids` trong `data/eval/test_set.json` dùng đúng `paper_id` mà cleaning sinh ra, nên so khớp được xuyên suốt raw → clean → index |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------- | --------------------------- | ---------------- | ------------- |
| Viết `build_clean_dataframe()`: strip thẻ JATS XML trong abstract, loại record thiếu title hoặc summary < 100 ký tự, chuẩn hoá authors/categories, tính `age_days`, dedupe theo `paper_id`, sort ổn định theo `published` giảm dần | `src/ingestion/cleaning.py` | `data/clean/papers_clean.csv` / `.json` — 24 record, 10 cột, dùng cho toàn bộ 3 trạng thái | Đếm trực tiếp trong `papers_clean.json` (24 record); `data/quality/baseline_quality.json` cho `row_count = 24`, 6/6 check PASS |
| Định nghĩa `text_for_embedding` theo contract `Title: ...\\nAuthors: ...\\nSummary: ...` | `src/ingestion/cleaning.py` | Cột `text_for_embedding` là input duy nhất cho `LocalEmbeddingIndex.build()` | Kiểm tra trực tiếp cột trong `papers_clean.json`: 24/24 record không rỗng |
| Viết `corrupt_clean_dataframe()`: 6 kịch bản corruption, mỗi kịch bản ghi log before/after và cờ `in_ground_truth` | `src/ingestion/corruption.py` | `data/results/corruption_log.json` (6 entry), `papers_clean_corrupted.*` | Đối chiếu từng `paper_id` trong log với dòng tương ứng trong `papers_clean_corrupted.csv` |
| Repair bằng cách chạy lại cleaning từ raw snapshot (không sửa tay CSV/JSON) | `src/pipelines/corruption_flow.py` gọi lại `build_clean_dataframe()` | `papers_clean_repaired.*` khôi phục đủ 24 dòng | `data/quality/repaired_quality.json`: 6/6 PASS, `overall_status = "PASS"` |

Output cụ thể: `data/clean/papers_clean.json` — 24 record, 10 cột (`paper_id`, `title`, `summary`, `published`, `authors_joined`, `categories_joined`, `age_days`, `text_for_embedding`, `abs_url`, `pdf_url`), mỗi record có `paper_id` là DOI đã chuẩn hoá (bỏ prefix resolver, lowercase), `summary` đã bóc hết thẻ JATS, `text_for_embedding` không rỗng. Đây là input trực tiếp của `retrieval/index.py` và là điểm khôi phục cho bước repair.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Crossref trả về dữ liệu bẩn theo nhiều kiểu cùng lúc: `abstract` là JATS XML (`<jats:p>`, `<jats:title>Abstract</jats:title>`), nhiều record thiếu hẳn abstract hoặc abstract chỉ vài chục ký tự, có record trùng DOI, có trường bị thiếu hoàn toàn (8/24 record không có `pdf_url`). Nếu đẩy thẳng vào embedding thì index sẽ chứa document rác và mọi metric phía sau đều mất ý nghĩa. Đồng thời phải tạo ra một tập corrupted **có chủ đích** — corruption ngẫu nhiên sẽ không chắc chạm được vào tài liệu ground truth, và khi đó metric không đổi thì không chứng minh được gì.

### Cách triển khai

**Cleaning.** `build_clean_dataframe()` duyệt từng `PaperRecord`: `_strip_html()` bóc thẻ JATS khỏi `summary` rồi `normalize_whitespace`, sau đó bỏ qua record nếu `title` rỗng hoặc `summary` ngắn hơn ngưỡng `_MIN_SUMMARY_CHARS = 100`. `published` parse bằng `pd.to_datetime(..., errors="coerce")` để ngày hỏng không làm crash cả pipeline mà chỉ rơi về chuỗi rỗng và `age_days = -1`. Sau khi dựng DataFrame: `drop_duplicates(subset="paper_id", keep="first")` — giữ bản gặp đầu tiên vì Crossref trả theo độ liên quan giảm dần; `fillna("")` + `.astype(str)` cho toàn bộ cột chuỗi và `fillna(-1).astype(int)` cho `age_days`; cuối cùng `sort_values("published", ascending=False, kind="stable")` để ba trạng thái luôn có cùng thứ tự dòng, phép so sánh mới công bằng.

**Corruption.** `corrupt_clean_dataframe()` nhận thêm `ground_truth_doc_ids` và duy trì một hàng đợi `gt_pool`. Bốn kịch bản có khả năng ảnh hưởng metric (`drop_latest_record`, `blank_summary`, `truncate_title`, `stale_date`) lần lượt `pop` một `paper_id` khác nhau từ hàng đợi này, nên chắc chắn mỗi kịch bản chạm đúng một tài liệu ground truth khác nhau. Hai kịch bản còn lại (`add_noise`, `duplicate_row`) cố tình nhắm vào tài liệu **ngoài** ground truth để mô phỏng nhiễu chung của kho dữ liệu. Sau khi sửa `title`/`summary`, các dòng bị đổi được dựng lại `text_for_embedding` — nếu bỏ bước này thì vector vẫn được nhúng từ nội dung cũ và corruption sẽ không có tác dụng lên retrieval.

**Repair.** Repair không phải là "khôi phục từ bản backup của corrupted" mà là chạy lại đúng `build_clean_dataframe()` trên `data/raw/crossref_records.json`. Raw snapshot được giữ nguyên, không fetch đè trong lúc so sánh.

### Input, output và contract

| Thành phần | Mô tả |
| ---------- | ----- |
| Input | `list[PaperRecord]` (cleaning); baseline DataFrame + `ground_truth_doc_ids` (corruption) |
| Output | DataFrame sạch với schema cố định gồm `paper_id`, `title`, `summary`, `published`, `authors_joined`, `categories_joined`, `age_days`, `text_for_embedding`, `abs_url`, `pdf_url`; DataFrame corrupted cùng schema |
| Module phụ thuộc | `ingestion.crossref.PaperRecord`, `core.utils.compact_join/normalize_whitespace/write_json` |
| Module sử dụng output | `retrieval/index.py` (nhúng `text_for_embedding`), `evaluation/testset.py` (lấy `paper_id` làm ground truth), `observability/quality.py` (chạy check trên DataFrame), `pipelines/corruption_flow.py` |
| Điều kiện lỗi cần xử lý | Abstract rỗng/quá ngắn → bỏ record; DOI trùng → `drop_duplicates` giữ bản đầu; `published` không parse được → `errors="coerce"` rồi rơi về `""` và `age_days = -1` thay vì crash; giá trị thiếu → `fillna` để ChromaDB không nhận `NaN`; `ground_truth_doc_ids` rỗng → corruption rơi về `fallback_id` thay vì crash |

### Cách xác minh

```powershell
.\.venv\Scripts\python.exe script\run_phase1.py
.\.venv\Scripts\python.exe script\run_corruption_flow.py
```

- **Kết quả mong đợi:** `papers_clean.json` có đủ record và không cột nào rỗng ngoài dự kiến; `corruption_log.json` có đúng 6 entry, trong đó 4 entry có `in_ground_truth = true`; `repaired_quality.json` quay về PASS toàn bộ.
- **Kết quả thực tế:** Đúng như mong đợi. `papers_clean.json` có 24 record. `corruption_log.json` ghi 6 entry, 4 entry `in_ground_truth = true` (`drop_latest_record`, `blank_summary`, `truncate_title`, `stale_date`) và 2 entry `false` (`add_noise`, `duplicate_row`). `repaired_quality.json` cho `overall_status = "PASS"`, 6/6 check PASS.
- **Artifact/log:** `data/results/corruption_log.json`, `data/quality/baseline_quality.json`, `corrupted_quality.json`, `repaired_quality.json`.
- **Lưu ý:** trước khi giải quyết conflict, `src/ingestion/cleaning.py` trên `main` còn dấu merge nên hai lệnh này không chạy được; số liệu ở đây lấy từ artifact đã commit chứ không phải từ một lần chạy lại sau khi sửa conflict.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Kịch bản corruption phải chọn tài liệu nào để phá. Nếu chọn ngẫu nhiên, rất có thể cả 6 kịch bản đều rơi vào tài liệu không nằm trong ground truth của test set — khi đó `retrieval_hit_rate` và `mean_token_f1` sẽ không đổi, và bài lab không chứng minh được gì về tác động của lỗi dữ liệu.
- **Các phương án đã cân nhắc:** (1) Chọn ngẫu nhiên có `seed` — tái lập được nhưng không đảm bảo chạm ground truth; (2) Hard-code danh sách `paper_id` cụ thể — chắc chắn chạm nhưng vỡ ngay khi Crossref trả về kho dữ liệu khác (Crossref là nguồn sống); (3) Truyền `ground_truth_doc_ids` vào hàm corruption và dùng hàng đợi để mỗi kịch bản "ảnh hưởng metric" lấy một tài liệu ground truth khác nhau, có `fallback_id` khi hàng đợi cạn.
- **Phương án đã chọn:** Phương án (3).
- **Lý do:** Vừa đảm bảo corruption chắc chắn tác động lên phép đo, vừa không hard-code dữ liệu nên vẫn chạy được khi kho tài liệu thay đổi. Đổi lại, `corruption.py` phải biết tới khái niệm ground truth — một phụ thuộc ngược lên tầng evaluation mà tôi chấp nhận, và đã cô lập bằng cách để tham số này `Optional` (mặc định `None` thì hàm vẫn chạy, chỉ mất tính "nhắm đích").
- **Bằng chứng quyết định phù hợp:** `corruption_log.json` cho thấy 4 `paper_id` ground truth **khác nhau** bị chạm: `10-2118-234689-pa` (drop), `10-1007-s10278-026-02086-9` (blank summary), `10-21203-rs-3-rs-10178277-v1` (truncate title), `10-3390-buildings16132637` (stale date). Kết quả: `retrieval_hit_rate` giảm 1.0 → 0.875 và `mean_token_f1` giảm 1.0 → 0.767. Nếu corruption chọn ngẫu nhiên, xác suất cả 4 kịch bản đều trúng ground truth trên kho 24 tài liệu là rất thấp.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** ChromaDB từ chối ghi document khi build index, báo lỗi metadata không hợp lệ — giá trị `NaN` (kiểu `float`) xuất hiện ở các cột lẽ ra là chuỗi (`pdf_url`, `categories_joined`).
- **Lệnh hoặc bước tái hiện:** Chạy `script/run_phase1.py` với DataFrame sạch chưa `fillna`, ở bước `LocalEmbeddingIndex.build()` truyền metadata lấy trực tiếp từ các cột của DataFrame.
- **Nguyên nhân gốc:** Lỗi nằm ở tầng cleaning của tôi, không phải tầng index. `pd.DataFrame(rows, columns=...)` tự điền `NaN` cho ô thiếu giá trị; 8/24 record Crossref không có `pdf_url` nên cột này chứa `NaN`. ChromaDB chỉ chấp nhận metadata kiểu `str`/`int`/`float`/`bool` hợp lệ và `NaN` không qua được validation.
- **Cách xử lý:** Ép kiểu ngay trong `build_clean_dataframe()`: `fillna("")` + `.astype(str)` cho toàn bộ cột chuỗi, `fillna(-1).astype(int)` cho `age_days`. Sửa tại nguồn thay vì vá ở `index.py` — vì `quality.py` và `testset.py` cũng đọc cùng DataFrame này và sẽ gặp đúng vấn đề đó.
- **Cách xác minh sau khi sửa:** Sau khi sửa, `run_phase1.py` build được collection `papers-baseline` đầy đủ, và `baseline_quality.json` cho `overall_status = "PASS"` với check `paper_id_not_null` / `title_not_null` đều 0 giá trị thiếu. Đếm trực tiếp trong `papers_clean.json`: 8/24 record có `pdf_url` là chuỗi rỗng — tức chúng vẫn tồn tại trong dataset ở dạng `""` chứ không còn `NaN`, và không record nào bị loại vì lý do này.
- **Điều học được:** Lỗi hiện ra ở module nào không có nghĩa là lỗi thuộc về module đó. Sửa ở tầng dữ liệu gần nguồn nhất thì mọi consumer phía sau được hưởng, còn vá ở consumer thì mỗi consumer mới lại phải vá lại một lần.

## 7. Hiểu biết về luồng end-to-end

1. `crossref.py` (Trần Vương Hưng) fetch và parse thành `PaperRecord`, ghi `data/raw/crossref_records.json`. Module của tôi nhận danh sách đó, loại record không dùng được, chuẩn hoá và dựng `text_for_embedding` — đây là cột duy nhất được đưa đi nhúng, nên chất lượng cleaning quyết định trực tiếp chất lượng vector.
2. `paper_id` (DOI đã chuẩn hoá) do cleaning sinh ra là khoá lineage xuyên suốt: `testset.py` dùng nó làm `ground_truth_doc_ids`, `index.py` dùng nó làm document ID trong ChromaDB, `metrics.py` so `retrieved_doc_ids` với `ground_truth_doc_ids` cũng bằng khoá này. Nếu cleaning đổi cách sinh `paper_id` giữa chừng thì toàn bộ chuỗi đo lường mất chuẩn.
3. Quality và freshness (Trần Việt Bách) chạy trên DataFrame ở tầng của tôi, **trước** khi nhúng. Vì vậy hai tín hiệu này độc lập hoàn toàn với retrieval — chúng bắt được lỗi cấu trúc (trùng `paper_id`, summary quá ngắn, ngày quá cũ) mà retrieval không thấy, và ngược lại có lỗi làm hỏng câu trả lời mà quality check hoàn toàn không bắt.
4. Test set giữ nguyên xuyên suốt ba trạng thái, nên biến duy nhất giữa baseline và corrupted chính là DataFrame mà `corruption.py` tạo ra. Đây là điều làm phép so sánh có nghĩa: mọi thay đổi metric đều truy được về đúng một entry trong `corruption_log.json`.
5. Repair thành công khi chạy lại `build_clean_dataframe()` từ raw snapshot cho ra dataset khôi phục đủ số dòng và mọi metric quay về đúng mức baseline — chứng tỏ hàm cleaning của tôi là tất định theo input, không giữ trạng thái ẩn nào giữa các lần chạy.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ------------- | -------: | --------: | -------: | -------------------- |
| `retrieval_hit_rate` | 1.0000 | 0.8750 | 1.0000 | Giảm đúng 1/8 câu — do `drop_latest_record` xoá hẳn `10-2118-234689-pa` khỏi DataFrame nên tài liệu không tồn tại trong index để mà tìm |
| `mean_token_f1` | 1.0000 | 0.7674 | 1.0000 | Giảm chủ yếu do `blank_summary` trên `10-1007-s10278-026-02086-9`: retrieval vẫn trúng nhưng không còn nội dung để rút trích |
| `judge_accuracy` | 0.7500 | 0.6250 | 0.7500 | Giảm 1 câu, khớp với hướng của hai metric trên |
| `mean_judge_score` | 4.7500 | 4.3750 | 4.7500 | — |
| Quality checks | 6/6 PASS | 3/6 FAIL | 6/6 PASS | Ba check FAIL đều truy được về đúng kịch bản corruption của tôi (xem dưới) |
| Freshness status | Fresh (0 stale/24) | Stale (1 stale/24) | Fresh (0 stale/24) | `stale_date` đẩy `10-3390-buildings16132637` từ `2026-07-02` về `2000-01-01` |

Số liệu lấy từ `data/results/{baseline,corrupted,repaired}_metrics.json` (8 mẫu, `judge_backend = "ollama"`) và `data/quality/*_quality.json`.

### Kết luận từ số liệu

1. **Mỗi check FAIL ở corrupted map 1–1 với một kịch bản tôi viết.** `paper_id_unique` FAIL (1 trùng) ← `duplicate_row` nhân đôi `10-1111-exsy-70341`; `summary_min_length` FAIL (1 dòng) ← `blank_summary`; `freshness_age_days` FAIL (1 dòng) ← `stale_date`. Không có FAIL nào không giải thích được, tức là corruption đúng như thiết kế chứ không gây tác dụng phụ ngoài ý muốn.
2. **Repair đưa cả 6 check về PASS và cả 4 metric về đúng giá trị baseline**, xác nhận `build_clean_dataframe()` là tất định: cùng raw snapshot cho ra cùng dataset, không cần bất kỳ thao tác sửa tay nào lên CSV hay JSON kết quả.
3. **Corruption tác động mạnh nhất là `drop_latest_record`**, vì đây là kịch bản duy nhất làm tài liệu biến mất hoàn toàn — mọi kịch bản khác chỉ làm hỏng nội dung, hệ thống vẫn còn cơ hội tìm đúng tài liệu.

Kết quả khác kỳ vọng: tôi nghĩ `truncate_title` (cắt tiêu đề còn 12 ký tự) sẽ làm hỏng ít nhất một câu hỏi, vì test set nhúng nguyên văn tiêu đề vào câu hỏi. Thực tế câu tương ứng vẫn `retrieval_hit = true`. Nguyên nhân: `qa.py` (Nguyễn Chính Nghĩa) luôn chạy tìm kiếm ngữ nghĩa song song với tra cứu chính xác, và vector vẫn được dựng từ `summary` còn nguyên nên vẫn khớp. Đây là bài học ngược: một kịch bản corruption "trông có vẻ nặng" có thể bị kiến trúc phía sau hấp thụ hoàn toàn, nên không được suy ra mức độ nghiêm trọng từ hình thức của lỗi mà phải đo.

Tương tự, `add_noise` không làm đổi bất kỳ metric nào — đúng như thiết kế, vì kịch bản này cố tình nhắm vào tài liệu ngoài ground truth. Nó chỉ có ý nghĩa mô phỏng nhiễu chung của kho, và test set hiện tại không có câu hỏi nào đo được tác động này.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Cleaning là nơi rẻ nhất để sửa lỗi dữ liệu.** Lỗi `NaN` hiện ra ở ChromaDB nhưng sinh ra ở cleaning; sửa ở nguồn thì index, quality check và test set cùng được hưởng, còn vá ở consumer thì mỗi consumer mới lại phải vá lại.
2. **Loại bản ghi mà không log là mất dữ liệu âm thầm.** Bản `build_clean_dataframe()` hiện trên `main` chỉ `continue` khi record không đạt ngưỡng, nên không ai trả lời được câu "bao nhiêu record vào, bao nhiêu ra, và vì sao". Tôi đã viết một bản mở rộng ghi `df.attrs["cleaning_log"]` kèm lý do từng bản ghi bị loại, nhưng bản đó chưa được merge — đây là khoản nợ kỹ thuật tôi nhận là của mình.
3. **Corruption phải nhắm đích thì phép đo mới có nghĩa.** Corruption ngẫu nhiên rất dễ tạo ra kết quả "metric không đổi", mà đó không phải bằng chứng hệ thống bền — chỉ là bằng chứng ta chưa chạm đúng chỗ.

### Nếu có thêm thời gian

Tôi sẽ đưa ngưỡng `_MIN_SUMMARY_CHARS` (hiện hard-code trong `cleaning.py`) ra thành cấu hình trong `src/core/config.py`, rồi chạy pipeline nhiều lần với các mức ngưỡng khác nhau để đo đường cong đánh đổi giữa **số tài liệu giữ lại** và **`mean_token_f1` của baseline**. Hiện tại 100 ký tự là con số chọn theo đề bài chứ tôi chưa có bằng chứng nó tối ưu. Cách đo cải thiện: vẽ `retrieval_hit_rate` và `mean_token_f1` theo `min_summary_chars` ∈ {50, 100, 200, 400} trên cùng test set, tìm điểm mà nới ngưỡng bắt đầu làm giảm chất lượng.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng — mọi số liệu trong báo cáo lấy từ artifact đã commit, và phần `cleaning.py` mở rộng chưa merge được ghi rõ là chưa merge.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Tuấn Khanh
**Ngày xác nhận:** 2026-08-07
