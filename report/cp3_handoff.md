# CP3 — Baseline end-to-end & báo cáo

> Mốc: 01:35–02:00 · Lệnh: `python script/run_phase1.py`

## 1. Pass criteria — trạng thái

| Tiêu chí | Trạng thái | Bằng chứng |
|---|---|---|
| `baseline_metrics.json` | ĐẠT | 217 B |
| `baseline_answers.json` | ĐẠT | 110,141 B, 12 records |
| Quality report (completeness/uniqueness/freshness) **tất cả PASS** | ĐẠT | `baseline_quality.json` 9/9 PASS |
| `freshness_report.json` | ĐẠT | `is_fresh: true`, 0/23 stale |
| `phase1_report.md` | ĐẠT | 2,008 ký tự, 75 dòng |
| Giải thích được ít nhất một hit/miss bằng artifact | ĐẠT | Mục 5 |

## 2. Metrics baseline

| Metric | Giá trị |
|---|---|
| `samples` | 12 |
| `retrieval_hit_rate` | 1.0000 |
| `mean_token_f1` | 1.0000 |
| `judge_accuracy` | 1.0000 |
| `mean_judge_score` | 5 |
| `judge_fallback_rows` | **0** — judge dùng LLM thật cho cả 12 câu |

`judge_fallback_rows` là cột do pipeline tự đếm: `_judge_answer` nuốt mọi exception rồi rơi về heuristic `token_f1` mà vẫn trả ra số. Nếu cột này khác 0 thì `judge_accuracy` không phải LLM chấm và report phải nói rõ. Ở lần chạy này bằng 0.

Provider: `openai` / `gpt-4.1-mini`, `top_k=4`, `max_output_tokens=2048`. Ragas bị skip (`RUN_RAGAS` chưa bật).

## 3. Vai trò 1 — nền tảng dữ liệu & pipeline

**Pipeline** `src/pipelines/phase1.py` chạy 7 bước: raw → clean → index → test set → evaluate → quality/freshness → report, cộng một demo agent không bắt buộc.

**Không fetch lại nguồn ngoài ý muốn.** `_load_or_fetch_raw` chỉ gọi Crossref khi `data/raw/crossref_records.json` chưa tồn tại hoặc `REFRESH_SOURCE=1`. Lần chạy này: `source_mode = reused_snapshot`, log in rõ `KHÔNG goi API`. Tương tự, test set đã đóng băng (`test_set_mode = frozen`), không sinh lại.

**Raw/clean count và lý do chênh lệch:**

```text
raw records : 24
clean rows  : 23
chênh lệch  : 1
  10.47576/2949-1894.2026.7.7.023  [non_english_summary]  non-ascii 40% > 30%
phương trình kiểm toán: 24 = 23 + 1 dropped + 0 deduped  ✓
```

**Quality check phản ánh dữ liệu thật, không hard-code pass.** Đã chứng minh bằng thí nghiệm ngược: chạy lại đúng bộ check trên một bản copy bị cố ý làm hỏng (xoá summary 1 dòng, xoá title 1 dòng, nhân bản `paper_id`, đặt `age_days=9999`, xoá `text_for_embedding`):

```text
kết quả: FAIL (3/9)
  [FAIL] paper_id_unique                observed=1
  [FAIL] title_not_null                 observed=1
  [FAIL] summary_not_null               observed=1
  [FAIL] summary_min_length             observed=1
  [FAIL] text_for_embedding_not_empty   observed=1
  [FAIL] freshness_within_threshold     observed=1
```

Sáu check chuyển sang FAIL đúng chỗ dữ liệu bị hỏng. Bộ check này đọc dữ liệu thật.

**Lineage và schema trong artifact đã ghi:** `text_for_embedding` rỗng = 0, `paper_id` trùng = 0, `age_days` 5–175, mọi `ground_truth_doc_id` đều có trong index.

## 4. Vai trò 3 — đối chiếu report với JSON/CSV thật

| Đối chiếu | Kết quả |
|---|---|
| `samples`: metrics 12 = answers 12 = test_set 12 | khớp |
| `clean_rows`: CSV 23 = quality 23 = freshness 23 | khớp |
| 4 metric trong `phase1_report.md` == `baseline_metrics.json` | khớp |
| Quality **PASS** trong report == `baseline_quality.json` | khớp |
| `latest_published` trong report == `freshness_report.json` | khớp |

Không có số nào trong report được viết cứng — `generate_phase1_report` chỉ format lại payload truyền vào.

**Baseline signals làm mốc đối chiếu sau corruption:**

| Signal | Baseline |
|---|---|
| `total_rows` | 23 |
| `latest_published` | 2026-08-01 |
| `oldest_published` | 2026-02-12 |
| `newest_age_days` | 5 |
| `stale_rows` | 0 |
| `is_fresh` | true |
| Quality | 9/9 PASS |

## 5. Vai trò 2 — đọc một hit bằng artifact

Ground truth nằm ở **rank 1 cho cả 12/12 câu** — không có câu nào ground truth rơi khỏi vị trí đầu.

Chi tiết q1, lấy nguyên từ `data/results/baseline_answers.json`:

```text
question : What problem does the paper titled SafeRAG: A Large-Language-Model-Based
           Multistage Retrieval-Augmented Framework... address?
GT doc   : ['10.2118/234689-pa']
retrieved: ['10.2118/234689-pa',            <- rank 1, trùng ground truth
            '10.21203/rs.3.rs-9770645/v1',
            '10.55041/isjem07213',
            '10.20944/preprints202604.0339.v1']
retrieval_hit : True
token_f1      : 1.0
judge         : score=5 correct=True
reasoning     : "The model answer exactly matches the reference answer..."
```

Đây là một **hit sạch**: retriever xếp đúng tài liệu ở đầu, và câu trả lời trích từ đúng tài liệu đó.

## 6. Điểm phải nói thẳng — vì sao mọi metric đều bằng 1.0

`mean_token_f1 = 1.0000` không phải trùng hợp, cũng không phải gian lận. Nguyên nhân nằm ở kiến trúc của starter code:

**`qa.py::_extract_answer` là extractive, không phải generative.** Nó trả về nguyên văn field metadata (`authors_joined`, `published`, `categories_joined`) hoặc `first_sentence(summary)` — không sinh văn bản mới. Test set lấy ground truth từ chính những field đó, nên khi retrieval đúng thì hai chuỗi **giống nhau từng ký tự**.

Kiểm chứng: **12/12 câu có `answer` giống hệt `ground_truth`**.

Điều này **không** làm metric mất tác dụng, vì `_token_f1` vẫn rất nhạy với sai lệch. Đo trên q5 (`ground_truth = "Audrey Rah, Sven Hahues"`):

| Nếu câu trả lời là… | token_f1 |
|---|---|
| giống hệt | 1.0000 |
| chỉ 1 tác giả đầu | 0.3333 |
| thêm tiền tố "The authors are …" | 0.7273 |
| tác giả của paper **khác** | 0.0000 |

Nên khi CP5 làm hỏng dữ liệu, `token_f1` sẽ tụt ngay. Baseline bằng 1.0 thực ra là **có lợi cho thí nghiệm**: nó cho biên độ quan sát tối đa, mọi mức sụt sau đó đều quy được về đúng một nguyên nhân là chất lượng dữ liệu.

Hạn chế cần thừa nhận: ở baseline, `token_f1` không phân biệt được chất lượng *giữa các câu trả lời đều đúng* — nó bão hoà ở 1.0.

## 7. Giải thích (yêu cầu của đề)

### `retrieval_hit_rate` phản ánh hiệu suất của cấu phần nào?

Chỉ của **retriever** — cụ thể là bộ ba: embedding model (`all-MiniLM-L6-v2`), vector store (Chroma, cosine distance), và tham số `top_k`. Nó **không** đo generator/LLM.

Nhìn thẳng vào code trong `metrics.py`:

```python
retrieval_hit = any(doc_id in item["ground_truth_doc_ids"]
                    for doc_id in result.retrieved_doc_ids)
```

Nó chỉ đọc `retrieved_doc_ids`, hoàn toàn không chạm vào `result.answer`. LLM có trả lời sai bét thì `retrieval_hit` vẫn `True` miễn là tài liệu đúng nằm trong top-k.

Ba hệ quả cần nhớ:

1. **Điều kiện cần, không đủ.** Retrieval trượt thì generator hết đường đúng (trừ khi bịa mà trúng). Retrieval đúng vẫn có thể trả lời sai. Vì vậy `retrieval_hit_rate` phải đọc kèm `token_f1`/`judge_score` — cặp số này tách được lỗi *tìm* khỏi lỗi *diễn đạt*.
2. **Nó là hit@k, không phải precision.** Chỉ cần tài liệu đúng nằm đâu đó trong 4 kết quả. Ba tài liệu sai còn lại không bị phạt.
3. **Tăng `top_k` thì chỉ số này chỉ có tăng hoặc giữ nguyên, không bao giờ giảm.** Nên so sánh baseline/corrupted/repaired chỉ có nghĩa khi `top_k` cố định — đúng Rule 2 trong `CLAUDE.md`.

### Tại sao Token F1 không bao giờ đạt 1.0 kể cả khi retrieval tìm đúng tài liệu?

**Với RAG sinh văn bản thì đúng như vậy, và đây là bằng chứng đo được.** Tôi chạy cùng một câu hỏi (q5), cùng một ground truth, qua hai đường trả lời khác nhau:

| Đường trả lời | Câu trả lời | token_f1 |
|---|---|---|
| Extractive (`qa.py`) | `Audrey Rah, Sven Hahues` | **1.0000** |
| Generative (agent + LLM) | `The paper titled "…Architecture" was authored by Audrey Rah and Sven Hahues.` | **0.1379** |

Câu trả lời của agent **hoàn toàn đúng về nghĩa** — nêu đủ cả hai tác giả — nhưng F1 chỉ 0.14. Phân tích token cho thấy chính xác vì sao:

```text
token ground_truth : ['audrey', 'hahues', 'rah,', 'sven']       -> 4 token
token của agent     : 25 token
overlap             : 2
token bị coi là thiếu: ['hahues', 'rah,']
```

Bốn nguyên nhân, xếp theo mức thiệt hại:

1. **Khung câu làm precision sụp.** LLM viết cả câu hoàn chỉnh: `The paper titled … was authored by …`. 21 token thừa (`paper`, `authored`, `by`, cả title được nhắc lại). Precision = 2/25.
2. **Dấu câu không được tách.** `_token_f1` chỉ `lower()` rồi `split()` theo khoảng trắng, **không** bỏ dấu câu. Nên `rah,` (có phẩy, trong ground truth) ≠ `rah` (agent viết), và `hahues` ≠ `hahues.`. Hai tác giả được nêu đúng tên nhưng bị tính là *thiếu* cả hai. Recall = 2/4.
3. **Ground truth chỉ là một cách diễn đạt trong vô số cách đúng.** Không có ràng buộc nào buộc LLM chọn đúng cách đó — nó có thể dùng "and" thay dấu phẩy, đảo thứ tự, thêm học hàm.
4. **F1 tính trên tập hợp.** `set(tokens)` gộp từ lặp và bỏ qua thứ tự, nên nó đo *độ chồng lấn từ vựng* chứ không đo *độ đúng ngữ nghĩa*.

Nói ngắn: Token F1 phạt **cách diễn đạt**, không chấm **tính đúng**. Retrieval đúng chỉ đảm bảo LLM có đủ dữ kiện; nó không đảm bảo LLM viết ra đúng bằng đúng những từ mà ground truth dùng.

**Vì sao trong lab này lại đạt 1.0:** `qa.py` là extractive — trả về nguyên văn giá trị field, không diễn đạt lại. Không có khung câu, không lệch dấu câu, không có từ đồng nghĩa. Bốn nguyên nhân trên đều biến mất. Nếu thay `answer_question` bằng agent LLM thì `mean_token_f1` sẽ tụt xuống quanh mức 0.1–0.3 dù mọi câu trả lời vẫn đúng — đúng như con số 0.1379 đo được ở trên.

Đây cũng là lý do thực tế người ta không dùng Token F1 một mình để chấm RAG sinh văn bản, mà kèm LLM-as-judge (chấm ngữ nghĩa) hoặc các metric của Ragas (`answer_relevancy`, `faithfulness`).

## 8. Bàn giao cho CP5

| Thứ | Trạng thái | Ràng buộc |
|---|---|---|
| Test set | Đóng băng, 12 câu | Không sinh lại |
| `top_k` | 4 | Không đổi |
| Evaluator | `openai` / `gpt-4.1-mini` | Không đổi |
| Embedding | `all-MiniLM-L6-v2` | Không đổi |
| Baseline artifacts | Đã ghi | **Không ghi đè** |

Corruption phải ghi sang path và collection riêng (`papers-corrupted`, `*_corrupted.*`). Bảng tách 3 trạng thái nằm ở `CLAUDE.md`.

Dự đoán tín hiệu sẽ đổi khi corruption chạy — dùng để đối chiếu ở CP5:

| Kịch bản corruption | Signal dự kiến đổi |
|---|---|
| Xoá latest records | `latest_published` lùi, `newest_age_days` tăng, `is_fresh` có thể thành false, `row_count` giảm, `retrieval_hit_rate` giảm ở các câu hỏi trỏ tới paper bị xoá |
| Blank summary | `summary_not_null` + `summary_min_length` FAIL, `token_f1` tụt ở câu loại `summary` |
| Thêm noise vào summary | `token_f1` tụt, quality có thể vẫn PASS (đây là loại lỗi quality check **không** bắt được — cần nói rõ trong report) |
| Truncate title | Exact lookup gãy → câu loại `authors`/`date`/`categories` rơi về semantic search |
| Làm stale published | `stale_rows` > 0, `freshness_within_threshold` FAIL |
| Thêm duplicate rows | `paper_id_unique` + `no_duplicate_titles` FAIL |
