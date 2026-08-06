# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Chính Nghĩa |
| MSSV               | 2A202601815 |
| Khóa/Lớp         | K3 |
| Tên nhóm         | Vua của Hà Nội |
| Vai trò chính    | RAG & Agent owner |
| Repository         | https://github.com/Tran-Viet-Bach/DAY10_D303_VuaCuaHaNoi |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Embedding backend | `src/retrieval/embeddings.py` (`MiniLMEmbeddings`) | Chuỗi văn bản (`text_for_embedding`) | Vector 384 chiều | Hoàn thành |
| Vector index & search | `src/retrieval/index.py` (`LocalEmbeddingIndex`) | DataFrame sạch | ChromaDB collection (baseline/corrupted/repaired), `search()`, `lookup()` | Hoàn thành |
| QA rút trích tất định | `src/retrieval/qa.py` (`answer_question`, `_extract_answer`) | Câu hỏi + index | `AnswerResult` (đáp án, doc IDs, contexts) dùng cho evaluation | Hoàn thành |
| Agent demo | `src/retrieval/agent.py` (`build_agent`, `run_agent_question`) | Index + LLM | Agent dùng tool-calling để trả lời câu hỏi tự do | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Xây dựng demo Streamlit 5 trang trực quan hoá toàn bộ pipeline | Cả nhóm (dùng cho thuyết trình) | `demo/app.py` + 5 trang (Overview, Baseline, Corruption, Repair, Comparison) đọc trực tiếp từ artifact JSON thật, không dữ liệu giả |
| Debug lỗi metadata NaN khi build ChromaDB | Nguyễn Tuấn Khanh | Xác định nguyên nhân ở tầng cleaning, phối hợp thêm `fillna` đúng chỗ |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Viết `LocalEmbeddingIndex.build()`: nhúng bằng MiniLM-L6-v2, ghi ChromaDB collection tách riêng cho từng trạng thái | `src/retrieval/index.py` | Collection `papers-baseline`/`-corrupted`/`-repaired`, không đè lên nhau | `data/embeddings/papers_embeddings*.json`; đếm document trong mỗi collection |
| Viết `answer_question()`: kết hợp tra cứu chính xác theo tiêu đề (regex) và tìm kiếm ngữ nghĩa (luôn chạy song song) | `src/retrieval/qa.py` | Câu trả lời chính xác cho 4 loại câu hỏi (`summary`/`authors`/`date`/`categories`) | `baseline_answers.json`: `retrieval_hit_rate=1.0`, `mean_token_f1=1.0` |
| Viết `build_agent()`: agent dùng LangChain `create_agent` với 2 tool (`semantic_search_papers`, `lookup_paper`) | `src/retrieval/agent.py` | Demo trả lời tự do dựa trên tool-calling, không bịa ngoài corpus | `data/results/agent_demo_answers.json` |

Output cụ thể: collection ChromaDB `papers-baseline` — 24 document, mỗi document có metadata đầy đủ (`paper_id`, `title`, `published`, `authors_joined`, `categories_joined`, `summary`, `abs_url`, `pdf_url`), là nền tảng cho cả đường đánh giá tất định (`qa.py`) lẫn đường agent tự do (`agent.py`).

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Cần biến 24 tài liệu văn bản thành một cấu trúc có thể tìm kiếm theo ngữ nghĩa (không chỉ khớp từ khoá), đồng thời đảm bảo baseline/corrupted/repaired không lẫn lộn dữ liệu với nhau khi so sánh. Đồng thời, việc rút trích câu trả lời phải đủ tất định để dùng làm đường đánh giá (evaluation), nhưng vẫn cần một đường "tự nhiên" hơn (agent) để demo khả năng trả lời câu hỏi tự do.

### Cách triển khai

`MiniLMEmbeddings` bọc model `sentence-transformers/all-MiniLM-L6-v2`, sinh vector 384 chiều cho mỗi `text_for_embedding`. `LocalEmbeddingIndex.build()` xác định tên collection bằng cách ánh xạ đường dẫn file embedding manifest sang tên cố định (`_derive_collection_name()`), xoá collection cũ nếu tồn tại (`delete_collection` trước `create_collection`) để đảm bảo mỗi lần build là build sạch, rồi ghi toàn bộ document + metadata + embedding vào ChromaDB với `configuration={"hnsw": {"space": "cosine"}}`.

`answer_question()` trong `qa.py` triển khai kiến trúc 2 đường: regex `r"'([^']+)'"` bóc tiêu đề trong dấu nháy đơn (nếu câu hỏi chứa), gọi `index.lookup()` để tra cứu chính xác theo `paper_id`/`title`; đồng thời `index.search()` **luôn luôn chạy** bất kể tra cứu chính xác có thành công hay không. Nếu tra cứu chính xác trúng, kết quả đó được gán điểm `1.0` và đẩy lên đầu danh sách, khử trùng lặp với kết quả tìm kiếm ngữ nghĩa. Đây là thiết kế suy giảm êm (graceful degradation): khi đường nhanh (tra cứu chính xác) bị phá — ví dụ do `truncate_title` — đường chậm (tìm kiếm ngữ nghĩa) vẫn có thể cứu được câu trả lời vì vector vẫn được dựng từ `summary` còn nguyên.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | DataFrame sạch (từ cleaning), câu hỏi dạng chữ |
| Output                         | `SearchResult` (paper_id, title, score, content, metadata), `AnswerResult` (answer, retrieved_doc_ids, retrieved_contexts) |
| Module phụ thuộc             | `core.config.Settings`, `ingestion.cleaning` (qua DataFrame), ChromaDB, sentence-transformers |
| Module sử dụng output        | `evaluation.metrics.evaluate_pipeline()` (dùng `answer_question`), `demo/` Streamlit |
| Điều kiện lỗi cần xử lý | `search()` trả về rỗng → `answer = "I don't know from the indexed corpus."` thay vì lỗi hoặc bịa câu trả lời |

### Cách xác minh

```bash
uv run python script/run_phase1.py
```

- **Kết quả mong đợi:** Collection `papers-baseline` có 24 document; toàn bộ 8 câu hỏi test set truy xuất đúng tài liệu (`retrieval_hit_rate=1.0`).
- **Kết quả thực tế:** Đúng như mong đợi, xác nhận qua `data/results/baseline_metrics.json` và `baseline_answers.json` (8/8 `retrieval_hit=true`).
- **Artifact/log:** `data/embeddings/papers_embeddings.json`, `data/results/baseline_answers.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Câu hỏi trong test set nhúng nguyên văn tiêu đề bài báo (để có ground truth rõ ràng), nhưng cần đảm bảo hệ thống vẫn hoạt động đúng khi tiêu đề bị hỏng (corruption) hoặc khi câu hỏi không chứa tiêu đề chính xác.
- **Các phương án đã cân nhắc:** (1) Chỉ dùng tra cứu chính xác theo tiêu đề (nhanh, chính xác tuyệt đối khi tiêu đề còn nguyên, nhưng giòn — vỡ hoàn toàn khi tiêu đề bị sửa); (2) Chỉ dùng tìm kiếm ngữ nghĩa (linh hoạt hơn nhưng có thể trả sai tài liệu khi nhiều bài cùng chủ đề); (3) Kết hợp cả hai, tra cứu chính xác chạy trước và được ưu tiên, tìm kiếm ngữ nghĩa luôn chạy song song làm lớp dự phòng.
- **Phương án đã chọn:** Phương án (3).
- **Lý do:** Đánh đổi thêm một lần gọi `search()` (chi phí tính toán nhỏ với kho 24 tài liệu) để lấy khả năng chịu lỗi — nếu chỉ dùng (1), kịch bản `truncate_title` sẽ làm câu hỏi tương ứng thất bại hoàn toàn thay vì được cứu.
- **Bằng chứng quyết định phù hợp:** Trong `corrupted_answers.json`, câu q3 (tài liệu bị `truncate_title` — tiêu đề bị cắt còn 12 ký tự) vẫn có `retrieval_hit=True` và `token_f1=1.000`, dù đường tra cứu chính xác chắc chắn thất bại (tiêu đề trong câu hỏi không còn khớp với tiêu đề đã bị cắt trong index) — chứng minh đường tìm kiếm ngữ nghĩa đã cứu được câu trả lời.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `ModuleNotFoundError` cho `datasets` và một số submodule `langchain` khi cố gắng import và test `retrieval/agent.py`, `evaluation/metrics.py` trong lúc các dependency nặng (torch, chromadb, langchain đầy đủ) vẫn đang cài đặt nền qua `pip install -e .`.
- **Lệnh hoặc bước tái hiện:** Import trực tiếp `from retrieval.agent import build_agent` khi môi trường ảo chưa cài xong toàn bộ `pyproject.toml`.
- **Nguyên nhân gốc:** Các module Zone B (retrieval, evaluation) phụ thuộc dependency nặng (torch, sentence-transformers, langchain, chromadb) cần thời gian cài đặt lâu; việc phát triển và viết code cho các module không phụ thuộc dependency nặng (Zone A: cleaning, corruption logic thuần pandas) bị chặn oan nếu chờ toàn bộ môi trường cài xong mới bắt đầu.
- **Cách xử lý:** Tách công việc theo "zone": viết và verify các hàm Zone A (không cần torch/langchain) bằng cách load module độc lập qua `importlib.util`, bỏ qua chuỗi import `__init__.py` kéo theo toàn bộ package nặng; chỉ chạy full integration test (bao gồm `agent.py`, `metrics.py`) sau khi xác nhận `pip install -e .` hoàn tất.
- **Cách xác minh sau khi sửa:** Sau khi cài đặt hoàn tất, `uv run python script/run_phase1.py` chạy hết pipeline bao gồm cả agent demo, không còn `ModuleNotFoundError`.
- **Điều học được:** Trong một dự án có dependency nặng, tách rõ phần code phụ thuộc ít (có thể phát triển/test sớm) khỏi phần phụ thuộc nhiều giúp không lãng phí thời gian chờ cài đặt — nhưng phải cẩn thận không commit code chưa test được với dependency thật.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. DataFrame sạch (do Nguyễn Tuấn Khanh cung cấp) đi vào `LocalEmbeddingIndex.build()`: mỗi dòng trở thành 1 document với `content = text_for_embedding`, được nhúng bằng MiniLM-L6-v2 thành vector 384 chiều, ghi vào ChromaDB kèm đầy đủ metadata. Từ vector index đó, `qa.py` và `agent.py` mới truy xuất được.
2. Evaluation set (Trần Việt Bách) cung cấp `question` và `ground_truth_doc_ids`; tôi dùng `answer_question()` để lấy `retrieved_doc_ids` thực tế, sau đó `evaluate_pipeline()` so hai tập này để tính `retrieval_hit_rate` — retrieval là bước đầu tiên trong chuỗi đo lường, quyết định liệu hệ thống có cơ hội trả lời đúng hay không trước cả khi tính đến chất lượng rút trích.
3. Quality checks kiểm tra dữ liệu ở tầng DataFrame/CSV (trước khi tôi nhúng); freshness cũng vậy. Cả hai không "nhìn thấy" được ChromaDB — chúng độc lập hoàn toàn với retrieval, đó là lý do một lỗi như `stale_date` có thể bị quality/freshness bắt được trong khi retrieval hoàn toàn không bị ảnh hưởng (vì câu hỏi liên quan không hỏi về ngày).
4. Test set phải giữ nguyên để `retrieved_doc_ids` tôi trả về luôn được so với đúng một `ground_truth_doc_ids` cố định — nếu đổi câu hỏi, không còn cơ sở để nói retrieval "tốt hơn" hay "tệ hơn" giữa hai lần chạy.
5. Repair thành công khi index mới (`papers-repaired`, do tôi build lại từ DataFrame đã repair) cho ra `retrieved_doc_ids` giống hệt baseline cho toàn bộ 8 câu hỏi — thể hiện qua `retrieval_hit_rate` quay về 1.0 và `mean_token_f1` quay về 1.0 trong `repaired_metrics.json`.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` | 1.0000 | 0.8750 | 1.0000 | Chỉ `drop_latest_record` (xoá hẳn tài liệu khỏi index) làm giảm; `truncate_title` không ảnh hưởng nhờ kiến trúc 2 đường tôi thiết kế |
| `mean_token_f1`      | 1.0000 | 0.7674 | 1.0000 | Không phải lỗi retrieval — retrieval vẫn đúng ở câu q2 (`blank_summary`), chỉ nội dung rút trích rỗng |
| `judge_accuracy`     | 0.7500 | 0.6250 | 0.7500 | — |
| `mean_judge_score`   | 4.7500 | 4.3750 | 4.7500 | — |
| Quality checks         | 6/6 PASS | 3/6 FAIL | 6/6 PASS | Không liên quan trực tiếp retrieval, nhưng xác nhận dữ liệu tôi nhúng vào corrupted index đúng là dữ liệu đã bị corrupt |
| Freshness status       | Fresh | Stale (1/24) | Fresh | Không ảnh hưởng retrieval — đúng như phân tích ở mục 7.3 |

### Kết luận từ số liệu

1. `drop_latest_record` (xoá 1 tài liệu ground truth khỏi DataFrame trước khi tôi build index) → tài liệu đó không tồn tại trong `papers-corrupted` collection → câu q1 `retrieval_hit=False`, F1=0.140 (trùng từ ngẫu nhiên với tài liệu khác được trả về thay thế).
2. Repair (tôi build lại `papers-repaired` từ DataFrame đã phục hồi đầy đủ 24 tài liệu) → `retrieval_hit_rate` quay về 1.0000, chứng minh index tôi xây tất định theo đúng nội dung DataFrame đầu vào, không giữ trạng thái ẩn nào từ lần build corrupted trước đó (nhờ `delete_collection()` trước mỗi `create_collection()`).

Corruption ảnh hưởng rõ nhất đến retrieval là `drop_latest_record`, vì đây là kịch bản duy nhất làm tài liệu biến mất hoàn toàn khỏi không gian tìm kiếm — mọi kịch bản khác chỉ sửa nội dung tài liệu (vẫn còn trong index) nên retrieval vẫn có cơ hội tìm đúng.

Kết quả khác kỳ vọng: tôi kỳ vọng `add_noise` (tiêm chuỗi rác vào summary) sẽ làm giảm điểm tương đồng và có thể đẩy tài liệu đó ra khỏi top-4 cho một số câu hỏi liên quan, nhưng vì `add_noise` nhắm vào tài liệu ngoài ground truth nên không có câu hỏi nào trong test set kiểm tra được tác động này — đã xác nhận bằng cách tính thử cosine similarity thủ công giữa vector trước/sau khi thêm nhiễu, thấy có dịch chuyển nhưng không đủ lớn để đổi thứ hạng trong top-4 của các câu hỏi hiện có.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Kiến trúc truy xuất có lớp dự phòng (suy giảm êm) làm hệ thống chịu lỗi tốt hơn nhiều so với một đường duy nhất, nhưng cũng có thể "che" mất một lỗi dữ liệu thật đang tồn tại — cần quality check độc lập để không bị đánh lừa bởi khả năng phục hồi ngầm của retrieval.
2. Tách collection theo trạng thái (baseline/corrupted/repaired) là cách rẻ và an toàn để giữ khả năng so sánh mà không cần build lại từ đầu mỗi lần.
3. Một agent dùng LLM (không tất định hoàn toàn) không thể thay thế đường rút trích tất định trong việc đo lường — hai đường này phục vụ hai mục đích khác nhau: `qa.py` để đo, `agent.py` để demo.

### Nếu có thêm thời gian

Tôi sẽ thêm một chỉ số theo dõi độ trôi dạt embedding (embedding drift): tính vector trung tâm của toàn kho ở mỗi trạng thái (baseline/corrupted/repaired) và đo khoảng cách cosine giữa các tâm này — nếu `add_noise` hoặc corruption khác đủ lớn để dịch chuyển tâm đáng kể, đây sẽ là tín hiệu sớm phát hiện lỗi ngữ nghĩa mà quality check cấu trúc hiện tại hoàn toàn không thấy được. Đo cải thiện: so sánh khoảng cách tâm giữa baseline-corrupted trước và sau khi tăng cường độ nhiễu của `add_noise`.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Chính Nghĩa
**Ngày xác nhận:** 2026-08-06
