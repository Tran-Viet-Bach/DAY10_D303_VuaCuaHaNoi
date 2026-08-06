# CP2 — Test set, RAG index & agent smoke test

> Mốc: 01:05–01:35 · Lệnh kiểm chứng: `find data -maxdepth 2 -type f | sort`

## 1. Pass criteria — trạng thái

| Tiêu chí | Trạng thái | Bằng chứng |
|---|---|---|
| `test_set.json` tồn tại | ĐẠT | 12 câu hỏi, schema 5 key khớp chính xác |
| Embedding manifest tồn tại | ĐẠT | `data/embeddings/papers_embeddings.json`, 23 documents |
| Collection baseline tồn tại | ĐẠT | `papers-baseline`, `collection.count()` = 23 |
| Semantic search trả kết quả có nguồn | ĐẠT | 3/3 query, mọi hit đều có `paper_id` + `title` |
| Exact lookup trả kết quả có nguồn | ĐẠT | HIT theo `paper_id` và theo `title`; ID không tồn tại → MISS |
| Agent trả kết quả có nguồn | ĐẠT | 3/3 case gọi tool, tool output chứa `paper_id` thật |

Minh chứng CHECKPOINT C2 của đề bài:

| Thư mục | File |
|---|---|
| `data/raw/` | `crossref_response.json`, `crossref_records.json` |
| `data/clean/` | `papers_clean.csv`, `papers_clean.json` (+ `cleaning_log.json`) |
| `data/eval/` | `test_set.json` |

## 2. Test set (vai trò 2)

12 câu hỏi (đề yêu cầu tối thiểu 5–10), phân bố `summary` 4 / `authors` 3 / `date` 3 / `categories` 2.

Schema từng sample đúng 5 key: `id`, `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids`.

> Đề bài ví dụ `"question_type": "factual"`. Tôi dùng 4 giá trị `summary`/`authors`/`date`/`categories` vì Guide.md bước 5 và mốc CP2 đều yêu cầu nhiều loại câu hỏi. Các **key** vẫn khớp schema tuyệt đối.

### Hai ràng buộc thiết kế

**Câu hỏi và ground_truth phải sinh cùng một chỗ.** `qa.py::_extract_answer` chọn field trả về dựa trên từ khoá trong câu hỏi:

| Từ khoá trong câu hỏi | Field trả về |
|---|---|
| `who authored` / `list the authors` | `metadata["authors_joined"]` |
| `when was` / `publication date` / `published on` | `metadata["published"]` |
| `what categories` | `metadata["categories_joined"]` |
| còn lại | `first_sentence(metadata["summary"])` |

Nếu câu hỏi và ground truth sinh rời nhau, metric sẽ đo độ lệch của chính test set chứ không đo chất lượng retrieval. `_build_question` sinh cả hai cùng lúc nên chúng luôn khớp.

**Chọn paper trải đều theo trục thời gian, không lấy `head(n)`.** Kịch bản corruption ở CP5 sẽ xoá *latest records*; nếu test set lệch về một phía thì việc xoá đó sẽ không làm metric giảm và ta kết luận sai rằng dữ liệu hỏng không ảnh hưởng gì.

**Loại câu hỏi `summary` cố ý không đặt title trong nháy đơn** — để bắt buộc đi qua semantic search thật. Ba loại còn lại đặt title trong nháy đơn để kích hoạt nhánh exact lookup của `answer_question`. Cả 23 title đều không chứa `'` nên regex `r"'([^']+)'"` an toàn (đã kiểm tra).

### Kiểm chứng

- `ground_truth_doc_ids` đều tồn tại trong clean data **và** trong index: True
- `ground_truth` không rỗng: 12/12
- Chạy `qa.answer_question` trên toàn bộ test set: **retrieval_hit 12/12, answer == ground_truth 12/12**

Con số 12/12 này là *baseline lành mạnh*, đúng như mong đợi khi dữ liệu còn sạch — nó tạo dư địa để CP5 quan sát mức sụt.

## 3. Index & manifest (vai trò 2 + 3)

| Hạng mục | Giá trị |
|---|---|
| Collection | `papers-baseline` |
| `collection.count()` | 23 (khớp 23 hàng clean) |
| Manifest | `data/embeddings/papers_embeddings.json` |
| Manifest keys | `backend`, `collection_name`, `documents`, `embedding_model`, `persist_path` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Số chiều vector | **384** |
| Chroma dir | `data/chroma/` |

> Đề bài nhắc thư mục `chroma_db/`. Code thực tế dùng `settings.paths.chroma_dir` = `data/chroma/`. Tôi giữ theo config vì `index.py` đã hard-wire vào đó và đổi sẽ phá `LocalEmbeddingIndex.load`.

Ba trạng thái đã tách sẵn, không có nguy cơ ghi đè: 3 tên collection khác nhau, 3 manifest path khác nhau (đã assert).

## 4. Smoke test

**Semantic search** — 3 query, mỗi hit đều có `paper_id` + `title` + score:

| Query | Top-1 | Score |
|---|---|---|
| agentic RAG for jawbone lesion diagnosis | `10.1007/s10278-026-02086-9` JADE-Plus | 0.6400 |
| roof design compliance with computer vision | `10.3390/buildings16132637` | 0.5997 |
| speculative decoding to reduce RAG cost | `10.70121/001c.158711` | 0.4241 |

Query thứ ba xếp đúng paper (`10.55041/isjem07213` Speculative RAG) ở hạng 2 với 0.4179 — sát nút. Đây là hành vi bình thường của MiniLM trên corpus 23 tài liệu cùng chủ đề RAG, không phải lỗi.

**Exact lookup** — theo `paper_id`: HIT; theo `title`: HIT cùng một paper; ID không tồn tại: MISS (đúng).

**Agent** — chạy bằng đúng `openrouter` / `google/gemini-2.5-flash` trong `.env`, 3/3 case gọi tool trước khi trả lời:

| Case | Tool được gọi | Kết quả |
|---|---|---|
| Semantic | `semantic_search_papers` | Trả đúng `10.3390/buildings16132637` |
| Lookup | `lookup_paper` | Trả đúng title của `10.2118/234689-pa` |
| Ngoài corpus | `semantic_search_papers` | **Từ chối đúng**: "The indexed corpus does not contain information about quantum error correction thresholds." |

Case thứ ba là quan trọng nhất: agent gọi tool, thấy không có kết quả phù hợp, và nói thẳng là không biết thay vì bịa. Log đầy đủ ở `data/results/agent_demo_answers.json`.

**Judge LLM** — `_judge_answer` (đường mã CP3 sẽ dùng) đã chạy bằng LLM thật, **không rơi vào fallback heuristic**: `score=5`, `correct=True`, reasoning "The model answer perfectly matches the reference answer."

## 5. Baseline signals (vai trò 3)

`data/quality/baseline_quality.json` — **9/9 PASS**:

| Check | Observed | Expected |
|---|---|---|
| `row_count_positive` | 23 | > 0 |
| `paper_id_not_null` | 0 | 0 rỗng/null |
| `paper_id_unique` | 0 | 0 trùng |
| `title_not_null` | 0 | 0 rỗng |
| `summary_not_null` | 0 | 0 rỗng |
| `summary_min_length` | 0 | 0 row < 100 ký tự |
| `text_for_embedding_not_empty` | 0 | 0 rỗng |
| `no_duplicate_titles` | 0 | 0 trùng |
| `freshness_within_threshold` | 0 | 0 row > 180 ngày |

`data/quality/freshness_report.json`:

| Field | Giá trị |
|---|---|
| `latest_published` | 2026-08-01 |
| `oldest_published` | 2026-02-12 |
| `newest_age_days` | 5 |
| `oldest_age_days` | 175 |
| `stale_rows` | 0 / 23 |
| `is_fresh` | true |

`is_fresh` bám vào tuổi của document **mới nhất**, không phải trung bình — vì cả hai kịch bản corruption ("xoá latest records" và "làm stale publication date") đều đẩy `latest_published` lùi lại, nên tín hiệu này chắc chắn đổi khi dữ liệu hỏng.

Khuôn `generate_phase1_report` đã viết xong, mọi số liệu đọc từ payload truyền vào — **không có giá trị nào hard-code trong template**. CP3 chỉ việc gọi.

## 6. Lineage (vai trò 1)

Một `paper_id` xuyên suốt, kiểm chứng thật:

```text
10.2118/234689-pa
  raw   : CÓ  (crossref_records.json)
  clean : CÓ  published=2026-08-01
  index : CÓ  metadata.paper_id=10.2118/234689-pa
```

- `text_for_embedding` rỗng: **0**
- `paper_id` trùng: **0**
- Toàn bộ `ground_truth_doc_ids` của test set có trong index: **True**
- Không refresh nguồn giữa chừng: `REFRESH_SOURCE` tắt, `crossref_response.json` giữ nguyên từ CP0

## 7. Giải thích (yêu cầu của đề)

### Tại sao phải chốt và đóng băng bộ câu hỏi trước khi chạy đánh giá RAG?

Vì phép so sánh chỉ có nghĩa khi **thước đo không đổi**. Ta muốn đo tác động của *chất lượng dữ liệu*, nên chất lượng dữ liệu phải là biến duy nhất thay đổi; test set, ground truth, evaluator và `top_k` phải đứng yên.

Nếu sinh lại test set từ dữ liệu đã hỏng, hậu quả rất cụ thể trong lab này:

- Corruption xoá *latest records*. Sinh lại test set sau đó thì những paper vừa bị xoá **không còn được hỏi nữa** → `retrieval_hit_rate` không giảm → ta kết luận sai rằng "dữ liệu xấu chẳng ảnh hưởng gì".
- Corruption blank summary. Sinh lại thì `ground_truth` cũng lấy từ summary rỗng → đáp án hỏng khớp với câu trả lời hỏng → mọi thứ vẫn "đúng".

Nói ngắn: test set sinh từ dữ liệu sạch chính là bản ghi *sự thật*. Đo cả ba trạng thái bằng đúng bản ghi đó mới cô lập được biến số. Kèm theo đó là tính tái lập — cùng code + cùng test set thì cùng số liệu, ai chạy lại cũng ra như nhau.

### Xử lý thế nào nếu một bài báo trong `ground_truth_doc_ids` bị thiếu ở pha sau?

Đây chính là tình huống sẽ xảy ra ở CP5, và **đó là tín hiệu, không phải lỗi cần vá**.

**Không được** sửa test set, không bỏ câu hỏi đó, không thay `ground_truth_doc_ids` sang paper khác. Làm vậy là xoá đúng cái mình đang cần đo.

Chuỗi phản ứng đúng khi paper biến mất:

1. `retrieval_hit` của câu đó thành `False` → `retrieval_hit_rate` giảm.
2. `answer_question` trả về document sai hoặc `"I don't know from the indexed corpus."` → `token_f1` và `judge_score` giảm.
3. Quality check `row_count` và freshness `latest_published` đồng thời báo động.

Ba tín hiệu đó nối được **nguyên nhân** (record bị mất) với **hậu quả** (metric tụt) — đúng mục tiêu của bài lab.

Ở pha repair: chạy lại cleaning từ `data/raw/` → paper quay lại index → metric hồi phục. **Nếu không hồi phục thì repair chưa đúng**, chứ không phải test set sai.

Chỉ có một trường hợp được sửa test set: khi phát hiện chính test set sai từ đầu (ví dụ ground truth ghi nhầm). Khi đó phải chạy lại **cả ba** trạng thái với test set mới, không được chỉ chạy lại trạng thái đang lỗi — nếu không thì lại so sánh trên hai thước đo khác nhau.

## 8. Blocker đã xử lý — HTTP 402 và nguyên nhân thật

**Triệu chứng:** mọi lời gọi LLM đều fail bằng HTTP 402, kể cả sau khi đổi API key.

```text
Error code: 402 - This request requires more credits, or fewer max_tokens.
You requested up to 65535 tokens, but can only afford 2945.
```

**Nguyên nhân không phải hết tiền.** Bằng chứng: gọi thẳng REST API cùng key đó thì **thành công**, chi phí thật chỉ 4e-06 USD.

Vấn đề nằm ở chỗ `build_llm` dựng `ChatOpenAI` mà **không đặt `max_tokens`**. Khi trường này để trống, OpenRouter ước lượng chi phí theo `max_completion_tokens` của model — với `google/gemini-2.5-flash` là **65,535 token** — rồi chặn request vì số dư không đủ trả cho trường hợp xấu nhất đó. Nó chặn theo *chi phí tối đa có thể*, không theo độ dài thật của câu trả lời.

**Cách sửa:** đặt `max_tokens` tường minh cho mọi provider trong `src/retrieval/llm.py`, lấy từ `settings.max_output_tokens` (env `LLM_MAX_TOKENS`, mặc định 1024). Tên tham số khác nhau giữa các SDK nên phải truyền riêng:

| Provider | Tham số |
|---|---|
| OpenAI / OpenRouter / custom | `max_tokens` |
| Anthropic | `max_tokens` |
| Gemini (native) | `max_output_tokens` |
| Ollama | `num_predict` |

Đo thực tế: `max_tokens=4096` → vẫn 402; `max_tokens=1024` → **200 OK**, và tool-calling hoạt động.

**Kết quả:** giữ nguyên `google/gemini-2.5-flash` như cấu hình ban đầu, không phải đổi model — nên evaluator vẫn đóng băng đúng Rule 2 từ đầu tới cuối.

> Nếu số dư tụt thêm và 402 quay lại, hạ `LLM_MAX_TOKENS` trong `.env` (ví dụ 512) thay vì đổi model. Đổi model giữa chừng sẽ phá phép so sánh 3 trạng thái.

### Tại sao checkpoint này bắt buộc phải kiểm tra model có gọi được không

Bốn lý do, xếp theo mức thiệt hại nếu bỏ qua:

**1. CP2 là điểm cuối còn sửa được mà không phải làm lại.** Từ CP3 trở đi evaluator bị đóng băng (Rule 2). Phát hiện model không gọi được ở CP3 thì hoặc bỏ dở, hoặc đổi model rồi phải chạy lại **cả ba** trạng thái. Ở CP2 thì đổi gì cũng còn miễn phí — chưa có metric nào được ghi.

**2. Lỗi này im lặng chứ không nổ.** `_judge_answer` trong `metrics.py` bắt mọi exception và rơi về heuristic dựa trên `token_f1`:

```python
except Exception:
    score = 5 if _token_f1(...) >= 0.95 else 3 if ... else 1
    reasoning = "Fallback heuristic judge used because the LLM evaluator was unavailable."
```

Pipeline vẫn chạy, vẫn sinh ra `baseline_metrics.json`, `judge_accuracy` vẫn có số. Không có traceback, không có exit code khác 0. Nếu không chủ động test, ta sẽ nộp một bản báo cáo mà `judge_accuracy` thực chất là *so khớp từ*, không phải LLM đánh giá — và không ai biết. Đúng cái mà mốc CP3 cảnh báo: "evaluator không silently fallback thành success giả".

**3. Đây là thành phần duy nhất phụ thuộc bên ngoài.** Crossref đã có snapshot lưu sẵn, MiniLM và Chroma chạy local — chúng không thể hỏng giữa chừng. Chỉ LLM là gọi mạng mỗi lần, phụ thuộc credit, rate limit và trạng thái upstream. Rủi ro tập trung ở đúng một chỗ thì phải kiểm tra đúng chỗ đó.

**4. Rubric mục 5 chấm 10 điểm cho "Agent chạy tốt, provider abstraction rõ ràng".** Không có bằng chứng agent gọi được LLM thật thì mục này bằng 0, bất kể code viết đẹp thế nào.

Cụ thể trong lần này, việc kiểm tra đã trả lại giá trị ngay: nó phát hiện một **bug trong `llm.py`** (thiếu `max_tokens`) mà nếu chỉ đọc code thì không thấy — lỗi chỉ lộ ra khi gọi thật qua gateway có kiểm tra số dư.
