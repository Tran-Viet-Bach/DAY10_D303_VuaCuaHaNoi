# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Trần Việt Bách |
| MSSV               | 2A202601773 |
| Khóa/Lớp         | K3 |
| Tên nhóm         | Vua của Hà Nội |
| Vai trò chính    | Evaluation & Observability owner |
| Repository         | https://github.com/Tran-Viet-Bach/DAY10_D303_VuaCuaHaNoi |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | ------------ |
| Frozen test set | `src/evaluation/testset.py` (`build_test_set`, `_select_candidates`, `_pick_rows`) | DataFrame sạch 24 dòng (từ Nguyễn Tuấn Khanh) | `data/eval/test_set.json` — 8 câu hỏi, 4 loại × 2 | Hoàn thành |
| Metrics & LLM judge | `src/evaluation/metrics.py` (`evaluate_pipeline`, `_token_f1`, `_judge_answer`, `JudgeVerdict`) | Test set + index của một trạng thái | `baseline/corrupted/repaired_metrics.json` + `*_answers.json` | Hoàn thành |
| Data quality checks | `src/observability/quality.py` (`run_data_quality_checks`) | DataFrame của 3 trạng thái | `data/quality/{baseline,corrupted,repaired}_quality.json` | Hoàn thành |
| Freshness monitoring | `src/observability/quality.py` (`build_freshness_report`) | Cột `published` và `age_days` | `freshness_report.json`, `corrupted_freshness_report.json`, `repaired_freshness_report.json` | Hoàn thành |
| Markdown reporting | `src/observability/reporting.py` (`generate_phase1_report`, `generate_corruption_report`, `_quality_table`, `_metrics_table`) | Payload metrics/quality/freshness thật | `data/reports/phase1_report.md`, `corruption_report.md` | Hoàn thành |
| Ragas pass (tuỳ chọn) | `src/evaluation/metrics.py` (`_run_ragas` + shim `langchain_community.chat_models.vertexai`) | Danh sách answers | Trường `"ragas"` trong metrics JSON | Một phần — code và shim đã hoạt động, nhưng lần nộp này chạy với `RUN_RAGAS` tắt nên artifact ghi `"skipped"` |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ------------ | ------------------------------------ | ---------- |
| Cung cấp danh sách `ground_truth_doc_ids` rút từ test set để corruption nhắm đúng tài liệu đang được đo | Nguyễn Tuấn Khanh (`corruption.py`) | `corruption_flow.py` truyền `ground_truth_doc_ids` vào `corrupt_clean_dataframe`; log ghi cờ `in_ground_truth` cho từng entry, 4/6 kịch bản nhắm đúng tài liệu GT |
| Kiểm tra judge có thật sự gọi LLM hay đã rơi về fallback heuristic | Trần Vương Hưng (`phase1.py`, `corruption_flow.py`) | Metrics JSON của cả 3 trạng thái có `"judge_backend": "ollama"`; đối chiếu thêm 24/24 trường `judge.reasoning` không chứa chuỗi `"Fallback heuristic judge used"` |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------- | ----------------- |
| Sinh test set 8 câu hỏi, mỗi câu gắn với một tài liệu khác nhau, ground truth lấy đúng trường mà `_extract_answer` trả về | `src/evaluation/testset.py` | `data/eval/test_set.json` (đóng băng sau baseline) | 8 `ground_truth_doc_ids` phân biệt; toàn bộ tồn tại trong `papers_clean.csv` |
| Viết `evaluate_pipeline()`: chạy tuần tự test set qua `answer_question`, tính `retrieval_hit`, `token_f1`, chấm LLM judge, ghi cả summary lẫn chi tiết từng câu | `src/evaluation/metrics.py` | 4 metrics × 3 trạng thái + `*_answers.json` truy vết được từng câu | `data/results/baseline_metrics.json`: `retrieval_hit_rate=1.0`, `mean_token_f1=1.0`, `judge_accuracy=0.75`, `mean_judge_score=4.75` |
| Viết 6 quality check phủ 5 quality dimension, dùng chung một hàm cho cả 3 trạng thái | `src/observability/quality.py` | `overall_status` PASS/FAIL + chi tiết `threshold`/`actual` từng check | `baseline_quality.json` PASS 6/6; `corrupted_quality.json` FAIL 3/6 |
| Viết freshness report tách rời khỏi quality gate, báo cáo `latest_published`/`oldest_published`/`stale_rows`/`is_fresh` | `src/observability/quality.py` | 3 freshness report | `freshness_report.json`: `is_fresh=true`, 0/24 stale; `corrupted_freshness_report.json`: `is_fresh=false`, 1/24 stale |
| Viết 2 generator Markdown đọc payload thật, không hard-code số | `src/observability/reporting.py` | `phase1_report.md`, `corruption_report.md` (có cột Δ Corruption / Δ Recovery) | So bảng trong report với JSON tương ứng, khớp từng con số |

Output cụ thể mà phần việc của tôi tạo ra: `data/quality/corrupted_quality.json` — báo cáo duy nhất trong bài chứng minh dữ liệu đã thật sự hỏng ở tầng cấu trúc, độc lập hoàn toàn với retrieval. Ba check `paper_id_unique`, `summary_min_length`, `freshness_age_days` cùng chuyển sang `FAIL` với `actual=1`, kéo `overall_status` từ `PASS` xuống `FAIL`. Nếu chỉ nhìn metrics, hai kịch bản `stale_date` và `duplicate_row` sẽ hoàn toàn vô hình.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Toàn bộ lab dựa trên một phép so sánh 3 trạng thái, nên phần việc của tôi phải cung cấp hai thứ mà mọi kết luận khác dựa vào: (1) một **thước đo cố định** để baseline / corrupted / repaired được chấm trên đúng một bộ câu hỏi và đúng một cách tính, và (2) một **lớp giám sát độc lập với retrieval** để bắt được những lỗi dữ liệu mà metrics không nhìn thấy. Hai thứ này phải tách nhau: nếu quality check cũng đi qua index thì khi index hỏng, cả hai tín hiệu cùng chết và không còn gì để đối chứng.

### Cách triển khai

**Test set.** `_select_candidates()` lọc trước hai loại title không dùng được: title không thuần ASCII và title có chứa dấu nháy đơn — dấu nháy đơn sẽ phá regex `r"'([^']+)'"` mà `qa.py` dùng để bóc tiêu đề, khiến câu hỏi thất bại vì lỗi cú pháp của chính test set chứ không phải vì retrieval kém. Sau đó `_pick_rows()` chọn tài liệu cho từng loại câu hỏi kèm predicate riêng: loại `authors` chỉ chọn dòng có `authors_joined` khác rỗng, loại `date` yêu cầu `age_days != -1` **và** `published` khác rỗng, loại `categories` yêu cầu `categories_joined` khác rỗng. Ground truth của mỗi loại được lấy đúng trường mà `_extract_answer` sẽ trả về (`summary` → `first_sentence`, `authors` → `authors_joined`, `date` → `published`, `categories` → `categories_joined`), nên nếu metric thấp thì đó là lỗi hệ thống, không phải lỗi lệch đề.

**Metrics.** `_token_f1` chuẩn hoá khoảng trắng, hạ chữ thường rồi tính F1 trên **tập** token (bag of unique tokens) — không nhạy với thứ tự từ và token lặp; đây là điểm yếu tôi ghi rõ ở mục 9. `_judge_answer` gọi LLM với `temperature=0.0` và `with_structured_output(JudgeVerdict)`; `JudgeVerdict` là model Pydantic ràng buộc `score` trong khoảng 1–5 (`ge=1, le=5`), nên một verdict sai định dạng bị chặn ngay tại tầng schema thay vì lọt vào phép tính trung bình.

**Quality checks.** 6 check phủ 5 dimension: `row_count` (Volume), `paper_id_not_null` + `title_not_null` (Completeness), `paper_id_unique` (Uniqueness), `summary_min_length` ≥ 100 ký tự (Validity), `freshness_age_days` (Freshness). Chi tiết đáng chú ý: check freshness đếm `(age_days < 0) | (age_days > threshold)` — nhánh `< 0` bắt sentinel `-1` mà cleaning gán cho ngày không parse được. Một ngày **không đọc được** không phải là "fresh", nó là "không biết"; nếu chỉ kiểm tra `> 180` thì corrupt trường `published` thành chuỗi rác sẽ lọt qua cổng freshness một cách im lặng.

**Freshness report** cố ý tách khỏi quality gate và báo cáo thêm `latest_published` / `oldest_published` — đây là hai trường mô tả, không có ngưỡng pass/fail, dùng để đọc *hình dạng* của dữ liệu chứ không chỉ đọc kết luận nhị phân. Quyết định này về sau tự chứng minh giá trị (mục 8).

### Input, output và contract

| Thành phần | Mô tả |
| ------------ | -------- |
| Input | DataFrame sạch (10 cột, không NaN), `LocalEmbeddingIndex` của trạng thái đang đo, đường dẫn test set đã đóng băng |
| Output | `test_set.json` (5 key: `id`, `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids`); `*_metrics.json` (4 metric + `samples` + `ragas`); `*_answers.json` (chi tiết từng câu); `*_quality.json`; `*_freshness_report.json`; 2 report Markdown |
| Module phụ thuộc | `ingestion.cleaning` (schema DataFrame), `retrieval.qa.answer_question`, `retrieval.llm.build_llm`, `core.config.Settings` (`top_k`, `freshness_threshold_days`, `paths`) |
| Module sử dụng output | `pipelines.phase1`, `pipelines.corruption_flow` (gọi cả 5 hàm của tôi), `demo/` Streamlit (đọc trực tiếp các JSON này) |
| Điều kiện lỗi cần xử lý | DataFrame rỗng → quality/freshness trả payload hợp lệ với `is_fresh=false` thay vì ném lỗi; không đủ candidate title hợp lệ hoặc < 5 câu hỏi → `build_test_set` ném `ValueError` có thông điệp rõ (thà dừng còn hơn tạo test set không đo được gì); LLM judge lỗi → rơi về heuristic **nhưng** ghi dấu vào `reasoning` để phát hiện được |

### Cách xác minh

```bash
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Baseline có đủ 4 metric và 6/6 quality check PASS; sau corruption đúng 3 check chuyển FAIL và metrics giảm; sau repair cả hai lớp quay về giá trị baseline.
- **Kết quả thực tế:** Đúng như mong đợi. Baseline `1.0 / 1.0 / 0.75 / 4.75`, quality 6/6 PASS, `is_fresh=true`. Corrupted `0.875 / 0.7674 / 0.625 / 4.375`, quality 3/6 FAIL, `is_fresh=false`. Repaired trùng khớp baseline tới từng chữ số ở cả 4 metric.
- **Artifact/log:** `data/results/*_metrics.json`, `data/results/*_answers.json`, `data/quality/*_quality.json`, `data/quality/*freshness_report.json`, `data/reports/corruption_report.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Với 8 câu hỏi trên 24 tài liệu, tôi phải quyết định phân bổ ground truth như thế nào — có nên để nhiều câu hỏi cùng trỏ về một tài liệu hay không.
- **Các phương án đã cân nhắc:** (1) Lấy 2 tài liệu "đẹp" nhất và hỏi cả 4 loại câu hỏi trên mỗi tài liệu — đơn giản, chắc chắn mọi trường metadata đều đầy đủ; (2) Lấy `head(8)` theo thứ tự dataset — đơn giản nhất, nhưng test set dồn về một phía trục thời gian; (3) Mỗi câu hỏi gắn với một tài liệu khác nhau, dùng `used_ids` để một `paper_id` đã dùng không bao giờ được chọn lại cho loại câu hỏi sau.
- **Phương án đã chọn:** Phương án (3) — 8 câu hỏi trên 8 `paper_id` phân biệt.
- **Lý do:** Test set không chỉ để đo chất lượng, nó còn quyết định **diện tích mà corruption có thể chạm tới**. Với phương án (1), một lần `blank_summary` vào đúng tài liệu đó sẽ hạ 4 câu cùng lúc và mọi kịch bản còn lại rơi ra ngoài ground truth — bộ metric sẽ chỉ có hai trạng thái "sập" hoặc "không thấy gì", không phân giải được kịch bản nào gây ra gì. Phương án (2) tệ hơn nữa: nếu test set lệch về phía tài liệu cũ thì `drop_latest_record` sẽ không chạm vào câu nào và nhóm sẽ kết luận sai rằng xoá bản ghi mới nhất không ảnh hưởng gì.
- **Bằng chứng quyết định phù hợp:** Corruption flow nhắm được 4 kịch bản khác nhau vào 4 tài liệu ground truth khác nhau (q1 `drop_latest_record`, q2 `blank_summary`, q3 `truncate_title`, q4 `stale_date`) và thu được 4 kết cục **phân biệt được** trong `corrupted_answers.json`: q1 `hit=False, F1=0.140`; q2 `hit=True, F1=0.000`; q3 và q4 giữ nguyên `hit=True, F1=1.000`. Chính sự khác nhau này mới cho phép quy trách nhiệm từng mức sụt metric về đúng một kịch bản.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `ModuleNotFoundError: No module named 'langchain_community.chat_models.vertexai'` phát sinh khi `ragas` được import ở top-level của `src/evaluation/metrics.py`. Hậu quả nghiêm trọng hơn triệu chứng: lỗi xảy ra lúc *import module*, nên `evaluate_pipeline` không nạp được và cả hai script pipeline chết trước khi chạy tới bước đo — một dependency **tuỳ chọn** làm hỏng đường đo **bắt buộc**.
- **Lệnh hoặc bước tái hiện:** `uv run python script/run_phase1.py` với `metrics.py` còn dòng `from ragas import evaluate` ở đầu file.
- **Nguyên nhân gốc:** `ragas` import chuỗi phụ thuộc chạm tới `langchain_community.chat_models.vertexai`, module này đã bị gỡ khỏi `langchain-community` 0.4.x. Đây không phải lỗi cấu hình máy mà là xung đột phiên bản giữa hai thư viện bên thứ ba, không thể sửa bằng cách cài lại.
- **Cách xử lý:** Ba thay đổi trong `_run_ragas`: (a) đưa toàn bộ `from ragas import ...` xuống trong thân hàm để chuỗi import chỉ chạy khi thật sự cần; (b) đăng ký một `types.ModuleType` shim vào `sys.modules["langchain_community.chat_models.vertexai"]` với thuộc tính `ChatVertexAI` giả trước khi import ragas, thoả mãn tham chiếu đã chết mà không đụng vào package đã cài; (c) đặt toàn bộ pass sau cổng biến môi trường `RUN_RAGAS`, mặc định tắt, trả về `{"skipped": ...}` — và bọc phần còn lại trong `try/except` trả về `{"error": ...}` để nếu Ragas hỏng thì 4 metric chính vẫn ra số.
- **Cách xác minh sau khi sửa:** `uv run python script/run_phase1.py` chạy hết 8 bước không lỗi; `data/results/baseline_metrics.json` chứa `"ragas": {"skipped": "Set RUN_RAGAS=1 to enable the slower Ragas pass."}` cùng đầy đủ 4 metric chính.
- **Điều học được:** Một phép đo tuỳ chọn không bao giờ được phép nằm trên đường phụ thuộc bắt buộc của phép đo chính. Lazy import cộng với cổng biến môi trường biến "toàn bộ pipeline chết" thành "một chỉ số phụ bị bỏ qua, có ghi lý do trong artifact" — và dòng `"skipped"` trong JSON quan trọng không kém con số, vì nó nói rõ chỉ số đó *không được chạy* chứ không phải *chạy ra 0*.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. Crossref trả JSON thô, `crossref.py` (Đoàn Quốc Việt) ghi nguyên văn xuống `data/raw/` trước khi parse — đây là điểm khôi phục bất biến của cả bài. `cleaning.py` (Nguyễn Tuấn Khanh) bóc thẻ JATS, lọc, chuẩn hoá thành 24 dòng × 10 cột và dựng `text_for_embedding`. `index.py` (Nguyễn Chính Nghĩa) nhúng cột đó bằng MiniLM-L6-v2 thành vector 384 chiều và ghi vào ChromaDB. Tôi nhận DataFrame sạch ở đúng khúc giữa: dùng nó để sinh test set và để chạy quality/freshness, còn phần đo hệ thống thì đi qua index.
2. Mỗi sample trong test set mang `ground_truth` (chuỗi đáp án) và `ground_truth_doc_ids` (danh tính tài liệu). Hai thứ này đo hai tầng khác nhau: `retrieval_hit_rate` so `retrieved_doc_ids` với `ground_truth_doc_ids` — trả lời câu hỏi "hệ thống có *tìm đúng* tài liệu không"; `mean_token_f1` và LLM judge so nội dung câu trả lời với `ground_truth` — trả lời "sau khi tìm đúng, nó có *nói đúng* không". Tách hai tầng là bắt buộc, vì q2 sau corruption cho thấy tìm đúng vẫn có thể trả lời rỗng.
3. Quality check và freshness đều chạy trên DataFrame trước khi index, nhưng khác nhau về mục đích: quality check là **cổng nhị phân** trên tính toàn vẹn cấu trúc (thiếu, trùng, quá ngắn) và kết luận PASS/FAIL; freshness là **tín hiệu theo thời gian** trên `published`/`age_days`, báo cả những trường mô tả không có ngưỡng như `latest_published`. Cả hai đều không nhìn thấy ChromaDB — đó chính là lý do chúng dùng được làm đối chứng độc lập khi metrics im lặng.
4. Vì thí nghiệm chỉ hợp lệ khi đúng một biến thay đổi. Nếu sinh lại test set trên dữ liệu đã hỏng, câu hỏi sẽ được sinh từ chính tài liệu đã bị corrupt và ground truth sẽ tự "hợp thức hoá" dữ liệu hỏng — metric có thể vẫn đẹp trong khi dữ liệu đã sai. Trong code, cả ba lần gọi `evaluate_pipeline()` đều nhận cùng `paths.eval_testset`; `phase1.py` chỉ sinh test set khi file chưa tồn tại hoặc `REFRESH_TEST_SET` được bật tường minh.
5. Repair thành công khi **cả hai lớp** cùng phục hồi, không phải một lớp: 4/4 metric trong `repaired_metrics.json` trùng khớp `baseline_metrics.json`; 6/6 check trong `repaired_quality.json` trở lại PASS; `repaired_freshness_report.json` trở lại `is_fresh=true` với `latest_published=2026-08-01`; và lineage check `set(paper_id)` baseline == repaired trả về `True`. Nếu metrics về nhưng quality vẫn FAIL thì đó là dữ liệu vẫn hỏng mà bộ đo không đủ nhạy — kết luận hoàn toàn khác.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` | 1.0000 | 0.8750 | 1.0000 | Đúng 1/8 câu mất hit (q1). Chỉ kịch bản làm tài liệu **biến mất** mới hạ được chỉ số này; sửa nội dung tài liệu thì không |
| `mean_token_f1` | 1.0000 | 0.7674 | 1.0000 | Sụt mạnh nhất trong 4 metric. Phân rã: q2 rơi từ 1.000 → 0.000 (`blank_summary`), q1 rơi 1.000 → 0.140 (`drop_latest_record`), 6 câu còn lại giữ 1.000 → `(0.140 + 0 + 6)/8 = 0.7674` |
| `judge_accuracy` | 0.7500 | 0.6250 | 0.7500 | Chỉ giảm đúng 1/8 (q1: `correct` True→False). q2 tuy F1 rơi về 0 nhưng judge đã chấm `correct=False` ngay từ baseline nên không giảm thêm — judge "mù" với phần sụt này |
| `mean_judge_score` | 4.7500 | 4.3750 | 4.7500 | Toàn bộ mức giảm 0.375 đến từ một mình q1 (5 → 2 điểm); q2 vẫn được chấm 4/5 dù câu trả lời đã rỗng nội dung tóm tắt |
| Quality checks | 6/6 PASS | 3/6 FAIL | 6/6 PASS | Bắt được `duplicate_row` và `stale_date` — hai kịch bản mà cả 4 metric đều không thấy |
| Freshness status | Fresh (0/24 stale, latest 2026-08-01) | Stale (1/24 stale, latest 2026-07-13, oldest 2000-01-01) | Fresh (0/24 stale, latest 2026-08-01) | Xem phân tích bên dưới: trường `latest_published` bắt được cả một lỗi thứ hai mà không check nào bắt |

### Kết luận từ số liệu

1. `blank_summary` xoá trống `summary` của tài liệu GT `10-1007-s10278-026-02086-9` → `summary_min_length` chuyển FAIL với `actual=1` trong `corrupted_quality.json` → câu q2 trong `corrupted_answers.json` giữ `retrieval_hit=True` nhưng `token_f1=0.000`, kéo `mean_token_f1` toàn cục từ 1.0000 xuống 0.7674. Đây là chuỗi nhân quả sạch nhất trong bài: tín hiệu quality và tín hiệu metric cùng trỏ về đúng một `paper_id`.
2. Repair chạy lại `build_clean_dataframe()` từ `data/raw/crossref_records.json` → `paper_id_unique`, `summary_min_length`, `freshness_age_days` cùng quay lại PASS trong `repaired_quality.json`, `is_fresh` quay lại `true` → cả 4 metric trong `repaired_metrics.json` khớp `baseline_metrics.json` tới từng chữ số, kèm lineage check `set(paper_id)` bằng nhau. Cả hai lớp cùng phục hồi nên kết luận "repair thành công" đứng được.

**Corruption nào ảnh hưởng rõ nhất?** Xét theo biên độ trên một metric đơn lẻ thì là `blank_summary` (−0.2326 trên `mean_token_f1`). Nhưng xét theo *số lớp giám sát bị chạm*, đáng chú ý nhất là `drop_latest_record`: nó là kịch bản duy nhất làm giảm cả `retrieval_hit_rate`, `judge_accuracy` lẫn `mean_judge_score` cùng lúc, vì nó phá ở tầng sâu nhất — tài liệu không còn tồn tại thì không có tầng nào phía sau cứu được.

**Kết quả khác kỳ vọng ban đầu.** Có hai điểm, và cả hai đều nằm trong phần việc của tôi.

Thứ nhất, tôi kỳ vọng `judge_accuracy` bằng 1.0 ở baseline vì cả 8 câu đều có `token_f1=1.000`, tức câu trả lời trùng khớp tuyệt đối với ground truth. Thực tế chỉ đạt 0.7500. Kiểm tra `baseline_answers.json` thấy hai câu bị chấm `correct=False`: q2 được judge nhận xét "almost identical to the reference answer, but it lacks any mention of the JADE-Plus framework" — tức judge đang chấm theo tiêu chí "tóm tắt đầy đủ bài báo" trong khi ground truth chỉ là câu đầu của abstract; và q7 có `ground_truth` và `answer` **giống hệt nhau từng ký tự** (`posted-content`) nhưng vẫn bị chấm sai với lý do "'posted-content' is too broad". Đây là bằng chứng trực tiếp rằng LLM judge không đo cùng thứ với token F1: nó chấm theo kỳ vọng riêng về một câu trả lời "tốt", nên `judge_accuracy` có một sàn dưới 1.0 không liên quan gì tới chất lượng hệ thống. Vì vậy tôi chỉ dùng judge để đọc **mức thay đổi** giữa ba trạng thái, không dùng giá trị tuyệt đối của nó làm kết luận.

Thứ hai, và là phát hiện tôi thấy giá trị nhất từ vai trò observability: **`row_count` hoàn toàn mù trước việc mất bản ghi mới nhất**. Corruption xoá 1 dòng rồi nhân đôi 1 dòng khác, nên `row_count` vẫn là 24 và check Volume vẫn PASS — nhìn vào quality gate sẽ không biết có tài liệu nào đã biến mất. Thứ duy nhất phản ánh được là trường `latest_published` trong freshness report: tụt từ `2026-08-01` xuống `2026-07-13`, đúng bằng ngày xuất bản của tài liệu kế tiếp sau tài liệu bị xoá (`10-2118-234689-pa`, published 2026-08-01, `age_days=5` — bài mới nhất kho). Một trường **mô tả, không có ngưỡng** lại là thứ duy nhất giữ được dấu vết của lỗi này. Bài học: quality gate nhị phân dễ bị "bù trừ" qua mặt, còn các trường mô tả thì không.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về data pipeline:** Test set là một artifact của pipeline chứ không phải tài liệu đi kèm — nó phải được đóng băng và version hoá như dữ liệu, vì mọi kết luận so sánh đều treo trên giả định "đề không đổi". Việc `phase1.py` chỉ sinh lại test set khi được yêu cầu tường minh quan trọng ngang với việc `data/raw/` không bị fetch đè.
2. **Về data quality/observability:** Một cổng PASS/FAIL có thể bị vô hiệu bởi hai lỗi bù trừ nhau (xoá 1 dòng + thêm 1 dòng ⇒ `row_count` vẫn PASS). Bộ giám sát cần cả tín hiệu nhị phân lẫn trường mô tả, và tốt nhất là cả tín hiệu **so với lần chạy trước** chứ không chỉ so với một hằng số ngưỡng.
3. **Về ảnh hưởng của data tới RAG agent:** Chất lượng dữ liệu và chất lượng câu trả lời không tương ứng một-một. `stale_date` và `duplicate_row` làm hỏng dữ liệu mà không đụng tới một metric nào; ngược lại `blank_summary` để `retrieval_hit_rate` nguyên vẹn nhưng làm câu trả lời rỗng nội dung. Chỉ dùng một trong hai lớp là chắc chắn có điểm mù.

### Nếu có thêm thời gian

Tôi sẽ thêm một check dạng **regression theo thời gian** vào `run_data_quality_checks()`: đọc `latest_published` của lần chạy PASS gần nhất và FAIL nếu giá trị mới lùi lại so với giá trị cũ. Lý do đã nêu ở mục 8 — đây đúng là lỗ hổng mà `drop_latest_record` chui lọt trong lần chạy này. Cách đo cải thiện rất rõ: chạy lại `run_corruption_flow.py` không đổi gì khác, kỳ vọng `corrupted_quality.json` chuyển từ 3 FAIL lên 4 FAIL với check mới bắt được `latest_published` lùi từ 2026-08-01 về 2026-07-13, trong khi `repaired_quality.json` vẫn phải PASS 100% — nếu repaired cũng FAIL thì check bị quá nhạy và phải chỉnh lại. Song song đó tôi sẽ thay `_token_f1` thuần tập hợp bằng biến thể có tính tới số lần lặp token, và đo độ ổn định của LLM judge bằng cách chấm lại cùng một bộ answers 5 lần để báo cáo độ lệch chuẩn của `judge_accuracy` — hiện tại con số 0.7500 đang được trình bày như thể nó tất định, trong khi thực tế chưa có bằng chứng nào về độ lặp lại của nó.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng (Ragas pass được ghi rõ là `skipped`, không phải đã chạy).
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Trần Việt Bách
**Ngày xác nhận:** 2026-08-06
