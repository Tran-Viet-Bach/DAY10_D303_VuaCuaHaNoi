# CLAUDE.md

## Quy tắc xuyên suốt lab

Áp dụng cho mọi checkpoint, không có ngoại lệ.

1. **Chỉ chạy corruption sau khi baseline đã tạo đủ artifact.** Kiểm tra artifact thật tồn tại trước, không dựa vào việc script exit code 0.
2. **Giữ nguyên test set, ground truth, evaluator và `top_k` khi so sánh baseline / corrupted / repaired.** Ba trạng thái phải được đo trên cùng một thước đo, nếu không phép so sánh vô nghĩa.
3. **Dùng paths và collection riêng cho ba trạng thái; không ghi đè baseline.**
4. **Repair bằng cách chạy lại từ raw/source đáng tin, không sửa tay `answers` hoặc `metrics`.**
5. **Report phải trỏ tới artifact thật; không commit API key hoặc `.env`.**

### Rule 2 — hằng số phải giữ nguyên

| Thứ | Giá trị | Định nghĩa tại |
|---|---|---|
| Test set | `data/eval/test_set.json` | Khoá lại sau CP2, không sinh lại |
| `top_k` | 4 | `src/core/config.py` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` | `src/core/config.py` |
| Evaluator | cùng LLM provider/model cho cả 3 lần chạy | `.env` |

`REFRESH_TEST_SET=1` chỉ dùng khi cố ý tạo lại test set trước khi khoá — không bật giữa lúc so sánh.

### Rule 3 — bảng tách trạng thái

| | baseline | corrupted | repaired |
|---|---|---|---|
| Clean data | `data/clean/papers_clean.{csv,json}` | `papers_clean_corrupted.{csv,json}` | `papers_clean_repaired.{csv,json}` |
| Embeddings | `data/embeddings/papers_embeddings.json` | `papers_embeddings_corrupted.json` | `papers_embeddings_repaired.json` |
| Chroma collection | `papers-baseline` | `papers-corrupted` | `papers-repaired` |
| Metrics | `data/results/baseline_metrics.json` | `corrupted_metrics.json` | `repaired_metrics.json` |
| Answers | `data/results/baseline_answers.json` | `corrupted_answers.json` | `repaired_answers.json` |

Mọi path đã khai báo sẵn trong `Paths` (`src/core/config.py`) — dùng `settings.paths.*`, không hard-code chuỗi đường dẫn.

### Rule 4 — repair là chạy lại pipeline

Repair = `data/raw/crossref_records.json` → `build_clean_dataframe()` → rebuild index → evaluate lại. Không copy rồi sửa tay từ baseline, không vá JSON kết quả. Nếu số liệu xấu thì sửa data contract rồi chạy lại, đừng chỉnh output.

`data/raw/` là điểm khôi phục — không corrupt và không fetch đè lên nó trong lúc so sánh (`REFRESH_SOURCE` phải tắt), nếu không comparison mất tính công bằng.

### Rule 5 — trước khi commit

- `.env` đã nằm trong `.gitignore`; chỉ commit `.env.example` với giá trị rỗng.
- Mỗi con số trong report phải truy được về một file trong `data/`.
- Không hard-code path tuyệt đối.

## Môi trường

Python **3.12** (`pyproject.toml` yêu cầu `>=3.11,<3.14`; máy này mặc định `python` là 3.14 nên phải tạo venv bằng `py -3.12 -m venv .venv`).

```powershell
.\.venv\Scripts\python.exe script\run_phase1.py
.\.venv\Scripts\python.exe script\run_corruption_flow.py
```

## Ghi chú kỹ thuật đã xác minh

- `ragas` fail nếu `import` ở top-level (`langchain_community.chat_models.vertexai` đã bị bỏ ở langchain-community 0.4.x). `src/evaluation/metrics.py` đã cài shim trước khi import — giữ nguyên cơ chế đó. Ragas chỉ chạy khi `RUN_RAGAS=1`.
- Crossref: tham số `select` **không** nhận `language` (trả HTTP 400). `abstract` trả về là JATS XML, phải strip tag.
- `paper_id` = DOI đã chuẩn hoá (bỏ prefix resolver, lowercase) — là khoá lineage xuyên suốt raw → clean → index → `ground_truth_doc_ids`.
- **`max_tokens` phải luôn đặt tường minh khi gọi LLM.** Để trống thì OpenRouter tính chi phí theo `max_completion_tokens` của model (65,535 với gemini-2.5-flash) và chặn bằng HTTP 402 dù số dư đủ trả cho câu trả lời thật. Điều khiển qua `LLM_MAX_TOKENS` trong `.env` (mặc định 1024). Gặp 402 thì **hạ số này**, đừng đổi model — đổi model giữa chừng phá phép so sánh 3 trạng thái.
- `_judge_answer` nuốt mọi exception và rơi về heuristic `token_f1` với reasoning "Fallback heuristic judge used…". Pipeline vẫn chạy và vẫn ra số, nên **phải chủ động kiểm tra LLM gọi được** trước khi tin vào `judge_accuracy`.
