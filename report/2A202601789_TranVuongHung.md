# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Trần Vương Hưng |
| MSSV               | 2A202601789 |
| Khóa/Lớp         | K3 |
| Tên nhóm         | Vua của Hà Nội |
| Vai trò chính    | Lead / Pipeline Integrator |
| Repository         | https://github.com/Tran-Viet-Bach/DAY10_D303_VuaCuaHaNoi |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | ------------ |
| Cấu hình tập trung | `src/core/config.py` (`Settings`, `Paths`, `load_settings`) | Biến môi trường từ `.env` | Một object `Settings` bất biến chứa 30 đường dẫn artifact tuyệt đối + tham số pipeline, dùng chung cho cả 5 module | Hoàn thành |
| Provider abstraction & credential gate | `src/core/config.py` (`normalized_provider`, `require_llm_credentials`) | `LLM_PROVIDER`, `LLM_MODEL`, các key | Tên provider đã chuẩn hoá; lỗi sớm có thông điệp rõ khi thiếu đúng key của provider đang bật | Hoàn thành |
| Utility I/O dùng chung | `src/core/utils.py` (`write_json`, `read_json`, `write_csv`, `write_text`, `ensure_parent`, `now_utc`) | Payload từ mọi module | Mọi artifact ghi ra cùng một định dạng, thư mục cha tự tạo | Hoàn thành |
| Baseline orchestration | `src/pipelines/phase1.py` (`main`, `_detect_judge_backend`) | 5 module của 4 thành viên còn lại | 8 bước end-to-end + toàn bộ artifact pha 1 (`data/raw/`, `clean/`, `embeddings/`, `eval/`, `results/`, `quality/`, `reports/`) | Hoàn thành |
| Corruption/repair orchestration | `src/pipelines/corruption_flow.py` (`main`) | Baseline artifacts + `corrupt_clean_dataframe` | Corrupted/repaired dataset, 3 collection tách biệt, 2 bộ metrics, comparison report, lineage check | Hoàn thành |
| Reproducibility gates | `settings.refresh_source`, `settings.refresh_test_set` và 2 nhánh điều kiện trong `phase1.py` | Cờ `REFRESH_SOURCE`, `REFRESH_TEST_SET` | Raw snapshot và test set được đóng băng mặc định; chỉ ghi đè khi bật cờ tường minh | Hoàn thành |
| Entrypoint | `script/run_phase1.py`, `script/run_corruption_flow.py` | — | Hai lệnh chạy được từ repo gốc | Hoàn thành (starter, không sửa) |

Tôi **không** nhận ownership cho `crossref.py` (Đoàn Quốc Việt), `cleaning.py`/`corruption.py` (Nguyễn Tuấn Khanh), `src/retrieval/` (Nguyễn Chính Nghĩa), `src/evaluation/` và `src/observability/` (Trần Việt Bách). Vai trò của tôi là chốt contract giữa các module đó và ghép chúng thành hai flow chạy được, chứ không viết nội dung bên trong chúng.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ------------ | ------------------------------------ | ---------- |
| Chốt contract "cleaning không được để null lọt sang bước index", sau đó tự chịu trách nhiệm nửa còn lại của contract ở phía đọc CSV ngược trong `corruption_flow.py` | Nguyễn Tuấn Khanh (`cleaning.py`), Nguyễn Chính Nghĩa (`index.py`) | `LocalEmbeddingIndex.build()` chạy được trên cả 3 trạng thái; chi tiết ở mục 6 |
| Bổ sung trường `judge_backend` vào metrics JSON để phân biệt judge thật với fallback heuristic | Trần Việt Bách (`metrics.py`) | Cả 3 file `*_metrics.json` đều ghi `"judge_backend": "ollama"`, xác nhận 24/24 lượt chấm đi qua LLM thật |
| Truyền `ground_truth_doc_ids` từ test set sang hàm corruption để 4/6 kịch bản nhắm đúng tài liệu đang được đo | Nguyễn Tuấn Khanh (`corruption.py`), Trần Việt Bách (`testset.py`) | `corruption_log.json` có cờ `in_ground_truth` cho từng entry; 4 entry `true`, 2 entry `false` |
| Cấu hình `LLM_PROVIDER=ollama` chạy cục bộ cho cả nhóm | Toàn nhóm | Không thành viên nào phải dùng API key trả phí; repo không có secret nào cần che |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------- | ----------------- |
| Gom toàn bộ đường dẫn artifact vào một `Paths` dataclass đóng băng, không module nào tự ghép path | `src/core/config.py` | 30 trường path tuyệt đối; `grep` toàn `src/` không còn chuỗi `"data/"` nào viết tay | Mọi artifact rơi đúng thư mục mà `README.md` mục 6 yêu cầu |
| Viết `phase1.py` 8 bước, mỗi bước ghi artifact ngay khi xong thay vì gom ghi ở cuối | `src/pipelines/phase1.py` | Pipeline chạy hết một lượt sinh đủ 10 artifact pha 1 | `data/reports/phase1_report.md` — `raw_records=24`, `clean_records=24`, `test_set_size=8` |
| Viết `corruption_flow.py` với fail-fast guard, 3 index tách biệt và lineage check | `src/pipelines/corruption_flow.py` | Corrupted + repaired chạy trên cùng test set đóng băng, không đè lên index baseline | `Lineage check (repaired paper_id set == baseline paper_id set): True` in ra ở stdout |
| Đặt hai cổng reproducibility (`REFRESH_SOURCE`, `REFRESH_TEST_SET`), mặc định TẮT | `src/core/config.py` dòng 132-133, `phase1.py` bước 1 và 4 | Chạy lại pipeline không gọi lại Crossref, không sinh lại test set | `data/raw/crossref_response.json` và `data/eval/test_set.json` giữ nguyên qua các lần chạy |
| Ghi `judge_backend` vào cả 3 metrics file | `phase1.py` (`_detect_judge_backend`), `corruption_flow.py` | Phân biệt được số liệu do LLM chấm và số liệu do heuristic chấm | `baseline/corrupted/repaired_metrics.json` đều có `"judge_backend": "ollama"` |
| Chạy và ghi lại hai flow trên cùng một máy, cùng một cấu hình | `script/run_phase1.py`, `script/run_corruption_flow.py` | Dấu thời gian liên tục: 03:15:32Z (baseline) → 03:21:50Z (corrupt) → 03:23:18Z (quality corrupted) → 03:24:40Z (comparison report) | Trường `generated_at` trong `baseline_quality.json`, `corruption_log.json`, `corrupted_quality.json`, `corruption_report.md` |

Output cụ thể mà phần việc của tôi tạo ra: **`data/reports/corruption_report.md`** — file duy nhất trong bài đặt cạnh nhau đủ ba trạng thái trên cùng một thước đo, kèm hai cột `Δ Corruption` và `Δ Recovery`. Nó tồn tại được không phải nhờ logic tính toán nào phức tạp, mà nhờ ba ràng buộc orchestration mà tôi phải giữ đúng trong `corruption_flow.py`: cùng một `paths.eval_testset` cho cả ba lần đo, ba `embeddings_output_path` khác nhau để ba collection không đè nhau, và repair đọc từ raw snapshot chứ không từ bản clean đã có. Hỏng bất kỳ ràng buộc nào trong ba ràng buộc đó thì bảng so sánh vẫn in ra số, nhưng số đó không so sánh được với nhau.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Bài lab này không phải là năm bài toán độc lập ghép lại. Nó là **một thí nghiệm có đối chứng**: đo cùng một hệ thống ở ba trạng thái dữ liệu và quy sự khác biệt về đúng một nguyên nhân là chất lượng dữ liệu. Vấn đề của vai trò tích hợp vì thế không phải "làm cho pipeline chạy" — mà là **giữ cho mọi biến ngoài dữ liệu đứng yên** giữa ba lần đo. Có bốn biến có thể trôi mà không báo lỗi gì cả: corpus nguồn (Crossref là nguồn sống), bộ câu hỏi, index đang được truy vấn, và backend chấm điểm. Nếu bất kỳ biến nào trong bốn biến đó thay đổi giữa các lần chạy, pipeline vẫn chạy trót lọt, vẫn in ra bốn con số đẹp, và kết luận rút ra sẽ sai mà không có dấu hiệu nào để phát hiện. Toàn bộ phần việc của tôi là dựng bốn cái chốt cho bốn biến đó.

### Cách triển khai

**Chốt 1 — corpus nguồn.** `phase1.py` bước 1 không gọi API vô điều kiện:

```python
if settings.refresh_source or not paths.raw_records_json.exists():
    records = fetch_source_records(settings)
else:
    records = load_raw_records(paths.raw_records_json)
```

Lý do nằm ở `config.py` dòng 74: `source_filter` được dựng từ `datetime.now(UTC).date() - timedelta(days=180)`, tức **cửa sổ lọc trượt theo ngày chạy**. Gọi lại Crossref hôm sau sẽ trả về một corpus khác — có bài mới lọt vào, có bài cũ rơi ra. Với một nguồn sống như vậy, "chạy lại pipeline" và "chạy lại cùng một thí nghiệm" là hai việc khác nhau, và mặc định phải là việc thứ hai.

**Chốt 2 — bộ câu hỏi.** Cùng dạng điều kiện ở bước 4, với cờ riêng `REFRESH_TEST_SET`. Test set chỉ được sinh khi file chưa tồn tại. Cả ba lần gọi `evaluate_pipeline()` trong hai file pipeline đều nhận đúng `paths.eval_testset`, không có tham số nào cho phép trỏ đi chỗ khác.

**Chốt 3 — index.** Đây là chốt dễ hỏng nhất vì `LocalEmbeddingIndex.build()` **xoá collection cũ trước khi tạo lại** (`index.py` dòng 97-104). Nếu ba trạng thái cùng ghi vào một collection thì mỗi lần build sau sẽ phá index của lần trước, và tệ hơn: baseline vẫn có metrics đúng (vì đã đo xong trước khi bị phá) nên không có triệu chứng nào. Vì vậy `corruption_flow.py` truyền ba `embeddings_output_path` khác nhau, và `_derive_collection_name()` map chúng sang `papers-baseline` / `papers-corrupted` / `papers-repaired`. Ba collection tồn tại song song trong cùng một ChromaDB, có thể mở lại và kiểm tra chéo sau khi flow kết thúc.

**Chốt 4 — backend chấm điểm.** `_judge_answer()` trong `metrics.py` bọc lời gọi LLM trong `try/except Exception` và khi lỗi thì rơi về một heuristic dựa trên token F1 — **vẫn trả về một `JudgeVerdict` hợp lệ**. Nghĩa là một máy không bật Ollama vẫn cho ra `judge_accuracy` và `mean_judge_score` trông bình thường, nhưng đó là hai chỉ số hoàn toàn khác về bản chất. Tôi thêm `_detect_judge_backend()` gọi thử `build_llm()` một lần và ghi kết quả vào metrics JSON dưới khoá `judge_backend`, để artifact tự khai backend của chính nó thay vì để người đọc phải tin.

**Fail-fast ở đầu corruption flow.** `corruption_flow.py` dòng 30-33 kiểm tra `baseline_metrics.json` và `papers_clean.csv` tồn tại, không có thì `raise RuntimeError` với hướng dẫn chạy `run_phase1.py` trước. Không có guard này, flow vẫn chạy được tới bước đọc `baseline_metrics` rồi chết bằng `FileNotFoundError` trần trụi sau khi đã kịp ghi đè `papers_clean_corrupted.csv` — hỏng nửa vời khó gỡ hơn là không chạy.

**Lineage check.** Sau khi repair, tôi so `set(paper_id)` của baseline và repaired rồi in kết quả, kèm hai tập hiệu nếu lệch. Đây là kiểm tra ở tầng danh tính tài liệu, độc lập hoàn toàn với metrics: metrics có thể khớp do may mắn (câu hỏi không chạm tới tài liệu bị mất), còn tập `paper_id` thì không.

### Input, output và contract

| Thành phần | Mô tả |
| ------------ | -------- |
| Input | `.env` (provider + model); artifact của 4 module còn lại theo contract đã chốt: `list[PaperRecord]`, DataFrame 10 cột không null, `LocalEmbeddingIndex`, `EvaluationBundle`, dict quality/freshness |
| Output | `Settings`/`Paths` cho mọi module; toàn bộ artifact của hai flow; hai dòng log kiểm chứng (`Lineage check ...`, dòng tổng kết ba `retrieval_hit_rate`) |
| Module phụ thuộc | Cả 5 module còn lại — pipeline là nơi duy nhất trong repo import chéo tất cả |
| Module sử dụng output | `demo/` (Streamlit đọc trực tiếp các JSON theo đúng path trong `Paths`); người chấm chạy hai script |
| Điều kiện lỗi cần xử lý | Thiếu baseline artifact khi chạy pha 2 → `RuntimeError` có hướng dẫn; agent demo lỗi → nuốt exception và ghi `{"error": ...}` vào `agent_demo_answers.json`, không được phép làm hỏng baseline đã đo xong; LLM không dựng được → `judge_backend="heuristic"` ghi thẳng vào metrics; thiếu key của provider đang bật → `require_llm_credentials` ném lỗi nêu đúng tên biến còn thiếu |

### Cách xác minh

```bash
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Lần chạy thứ nhất sinh đủ artifact pha 1. Lần chạy thứ hai sinh corrupted + repaired, in `Lineage check ... True`, và repaired phải trùng baseline ở cả 4 metric — vì repair chạy đúng hàm cleaning đã tạo ra baseline trên đúng raw snapshot đã tạo ra baseline.
- **Kết quả thực tế:** Đúng như mong đợi. `Lineage check (repaired paper_id set == baseline paper_id set): True`. Baseline `1.0000 / 1.0000 / 0.7500 / 4.7500`; repaired trùng khớp tuyệt đối cả bốn giá trị. Dấu thời gian trong artifact liên tục từ 03:15:32Z đến 03:24:40Z, xác nhận hai flow chạy nối tiếp trên cùng một cấu hình.
- **Artifact/log:** `data/results/*_metrics.json`, `data/results/corruption_log.json`, `data/quality/*_quality.json`, `data/quality/*freshness_report.json`, `data/reports/phase1_report.md`, `data/reports/corruption_report.md`. Không file nào chứa key hay `.env`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Bước repair phải khôi phục dataset đã hỏng. Cần chọn nguồn để khôi phục từ đó — và lựa chọn này quyết định repair *chứng minh* được điều gì.
- **Các phương án đã cân nhắc:** (1) Gọi lại Crossref API để lấy dữ liệu mới — trực quan nhất, "lấy lại từ nguồn thật"; (2) Sao lưu `papers_clean.csv` thành `papers_clean_backup.csv` trước khi corrupt rồi copy ngược lại — nhanh nhất, chắc chắn khớp 100%; (3) Đọc `data/raw/crossref_records.json` (snapshot bất biến, ghi từ trước mọi thao tác corrupt) và chạy lại đúng hàm `build_clean_dataframe()` đã tạo ra baseline.
- **Phương án đã chọn:** Phương án (3).
- **Lý do:** Phương án (1) phá chính thí nghiệm. `source_filter` trong `config.py` dùng cửa sổ `from-pub-date` trượt theo ngày chạy, nên corpus fetch lại **không phải** corpus của baseline; "repaired" sẽ được đo trên một tập tài liệu khác và mọi so sánh với baseline mất nghĩa — đúng thứ mà chốt 1 ở mục 4 sinh ra để ngăn. Phương án (2) chạy được nhưng chỉ chứng minh được rằng ta biết copy file: nó không đi qua một dòng nào của logic cleaning, nên nếu dữ liệu hỏng vì bản thân cleaning có bug thì bản backup mang nguyên bug đó và vẫn "repair thành công". Phương án (3) là phương án duy nhất chứng minh được điều mà bài lab thực sự hỏi: **pipeline có tái tạo lại được trạng thái sạch từ nguồn bất biến hay không**. Nó cũng đặt điều kiện ngược lên các module khác — `build_clean_dataframe` phải tất định, nên `run_date` được truyền vào như tham số thay vì gọi `datetime.now()` bên trong hàm; đây là contract tôi chốt với Nguyễn Tuấn Khanh chính vì bước repair này.
- **Bằng chứng quyết định phù hợp:** `repaired_metrics.json` trùng `baseline_metrics.json` ở cả 4 metric tới từng chữ số (`1.0 / 1.0 / 0.75 / 4.75`), `repaired_quality.json` trở lại 6/6 PASS, `repaired_freshness_report.json` trở lại `is_fresh=true` với `latest_published=2026-08-01` và `oldest_published=2026-02-12` — trùng đúng cặp ngày của baseline, trong khi bản corrupted là `2026-07-13` / `2000-01-01`. Và lineage check `True`. Bốn tín hiệu độc lập cùng khớp; nếu dùng phương án (2) thì cả bốn cũng khớp nhưng không tín hiệu nào chứng minh được logic cleaning còn chạy đúng.

## 6. Một lỗi hoặc blocker đã xử lý

### 6.1 Đã xử lý — dữ liệu chết trên đường CSV roundtrip giữa hai flow

- **Triệu chứng/lỗi nguyên văn:** `corruption_flow.py` đọc lại `papers_clean.csv` bằng `pd.read_csv()` mặc định, và `LocalEmbeddingIndex.build()` cho collection `papers-corrupted` văng lỗi vì ChromaDB từ chối metadata kiểu `float NaN` — trong khi đúng DataFrame đó vừa được index thành công ở `phase1.py` vài phút trước.
- **Lệnh hoặc bước tái hiện:** `uv run python script/run_phase1.py` (thành công) rồi `uv run python script/run_corruption_flow.py` với dòng đọc CSV để mặc định.
- **Nguyên nhân gốc:** Không phải lỗi của cleaning và cũng không phải lỗi của index. Trong `phase1.py`, DataFrame đi thẳng từ `build_clean_dataframe()` sang `LocalEmbeddingIndex.build()` **trong cùng một tiến trình**, nên chuỗi rỗng `""` mà cleaning gán cho các trường tuỳ chọn vẫn là chuỗi rỗng. Nhưng pha 2 chạy ở tiến trình khác và phải đọc lại qua CSV — mà `pd.read_csv()` mặc định coi ô rỗng là `NaN`. Dữ liệu chết trên đường đi giữa hai flow, tại một chỗ không thuộc module nào cả. Đây đúng là loại lỗi chỉ vai trò tích hợp nhìn thấy: mỗi module đều đúng theo contract của nó, nhưng contract chỉ được phát biểu cho *dữ liệu trong bộ nhớ*, không cho *dữ liệu đã qua serialize*.
- **Cách xử lý:** Sửa ở phía đọc trong `corruption_flow.py`, không sửa ở phía ghi (vì CSV phải giữ nguyên định dạng cho `demo/` và cho người chấm mở bằng Excel):

  ```python
  baseline_df = pd.read_csv(paths.clean_csv, dtype=str, keep_default_na=False)
  baseline_df["age_days"] = baseline_df["age_days"].astype(int)
  ```

  `keep_default_na=False` giữ ô rỗng là `""`; `dtype=str` chặn pandas tự suy kiểu (nếu không, `paper_id` dạng số sẽ thành float và lệch khỏi `paper_id` gốc); dòng thứ hai trả `age_days` về `int` vì quality check so sánh số học trên cột này.
- **Cách xác minh sau khi sửa:** `uv run python script/run_corruption_flow.py` chạy hết không lỗi; ba collection `papers-baseline` / `papers-corrupted` / `papers-repaired` cùng tồn tại; `corrupted_quality.json` báo `row_count=24` đúng bằng baseline, xác nhận không dòng nào bị rơi trong quá trình roundtrip.
- **Điều học được:** Contract giữa hai module phải được phát biểu cho dạng dữ liệu **đã tuần tự hoá**, không chỉ cho object trong bộ nhớ. Ranh giới nguy hiểm nhất trong một pipeline nhiều tiến trình không nằm trong module nào — nó nằm ở định dạng file giữa các module, và đó chính xác là chỗ không ai được giao sở hữu nếu không có vai trò tích hợp.

### 6.2 Chưa xử lý xong — nhánh `main` đang chứa một merge chưa giải quyết xung đột

- **Triệu chứng/lỗi nguyên văn:** Commit `aa6a311` ("individualreport") là merge của `e437061` và `78ad189` nhưng được commit **kèm nguyên conflict marker**. `git grep -c "^<<<<<<< "` trên `main` trả về 18 file: 6 file source (`phase1.py`, `crossref.py`, `cleaning.py`, `testset.py`, `quality.py`, `reporting.py`) và 12 file artifact trong `data/`. Clone `main` về chạy `run_phase1.py` sẽ chết ngay ở bước import với `SyntaxError`, và các file `*_metrics.json` không parse được bằng `json.loads`.
- **Phạm vi bị ảnh hưởng:** Toàn bộ khả năng tái hiện của bài nộp. Số liệu trong báo cáo này và trong `group_report.md` lấy từ lần chạy trên nhánh `78ad189` (03:15:32Z–03:24:40Z), lần chạy đó là thật và artifact còn nguyên trong lịch sử git, **nhưng chúng không đọc được ở trạng thái `main` hiện tại**.
- **Những gì đã loại trừ:** Không phải merge đang dở dang trên máy tôi — `git status` sạch, không có `MERGE_HEAD`; conflict marker đã nằm trong lịch sử ở phía remote. Không phải lỗi checkout hay line-ending — `git show aa6a311:src/pipelines/phase1.py` cho ra đúng nội dung có marker. Không phải xung đột ngẫu nhiên do format: hai nhánh là hai bản implement độc lập với contract khác nhau (23 dòng/12 câu hỏi/9 quality check ở `e437061` so với 24 dòng/8 câu hỏi/6 quality check ở `78ad189`), nên không thể merge bằng cách lấy máy móc một bên cho từng hunk.
- **Bước tiếp theo:** Chọn `78ad189` làm bản gốc cho toàn bộ 18 file (đây là bản đã chạy hết cả hai flow và là bản mà `group_report.md` mô tả), commit lại thành một merge sạch, rồi chạy lại tuần tự `run_phase1.py` và `run_corruption_flow.py` trên bản đã gộp để xác nhận bốn metric tái hiện đúng `1.0000 / 1.0000 / 0.7500 / 4.7500`. Kiểm chứng cuối: `git grep -c "^<<<<<<< "` phải trả về rỗng.
- **Điều học được:** Cổng chặn duy nhất mà tôi quên dựng lại là cổng ở tầng version control, chứ không phải ở tầng dữ liệu. Nhóm đã có quality gate cho dữ liệu vào pipeline nhưng không có gate nào cho code vào `main` — trong khi cả hai đều là "dữ liệu hỏng đi tiếp mà không ai chặn". Một pre-push hook `git grep -q "^<<<<<<< " && exit 1` là bốn dòng và sẽ chặn được đúng sự cố này.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. **Từ Crossref đến vector index.** `fetch_source_records()` gọi `https://api.crossref.org/works` với query và filter dựng trong `config.py`, ghi nguyên văn response xuống `data/raw/crossref_response.json` **trước khi parse** — thứ tự này quan trọng: nếu parse lỗi, dữ liệu vẫn còn để gỡ. Payload được parse thành 24 `PaperRecord` và lưu tiếp thành `crossref_records.json`. `build_clean_dataframe()` nhận list đó cùng một `run_date` truyền vào, bóc thẻ JATS, chuẩn hoá, tính `age_days`, dựng `text_for_embedding`, cho ra DataFrame 24×10. `LocalEmbeddingIndex.build()` nhúng cột `text_for_embedding` bằng MiniLM-L6-v2 thành vector 384 chiều, ghi vào ChromaDB không gian cosine cùng metadata của từng dòng, và xuất một manifest JSON để lần sau `load()` lại được mà không phải nhúng lại. Ở góc nhìn của tôi, luồng này có đúng **một** điểm không thể tạo lại được là `data/raw/` — mọi thứ sau đó đều là hàm thuần của nó cộng với `run_date`.

2. **Test set và ground-truth doc IDs.** Mỗi câu hỏi mang hai loại đáp án cho hai tầng khác nhau. `ground_truth_doc_ids` được so với `retrieved_doc_ids` để tính `retrieval_hit_rate` — đo tầng *tìm*. `ground_truth` (chuỗi) được so với câu trả lời bằng token F1 và bằng LLM judge — đo tầng *nói*. Hai tầng này phải tách vì chúng hỏng độc lập, và bài chạy này chứng minh điều đó bằng số: q1 hỏng tầng tìm (hit `True`→`False`), q2 hỏng tầng nói trong khi tầng tìm nguyên vẹn (hit vẫn `True`, F1 `1.000`→`0.000`). Nếu chỉ có một chỉ số tổng hợp, hai lỗi khác bản chất này sẽ trông giống hệt nhau.

3. **Quality check khác freshness ở đâu.** Cả hai đều chạy trên DataFrame *trước khi index*, nên cả hai đều không nhìn thấy ChromaDB — đó là lý do chúng dùng được làm đối chứng độc lập với metrics. Khác nhau ở chỗ: quality check là **cổng nhị phân** trên tính toàn vẹn cấu trúc (thiếu, trùng, quá ngắn) và kết luận PASS/FAIL cho cả dataset; freshness là **tín hiệu theo trục thời gian**, báo cả những trường mô tả không có ngưỡng như `latest_published`/`oldest_published`. Bài chạy này cho thấy vì sao cần cả hai dạng: `duplicate_row` chỉ bị cổng nhị phân bắt, còn việc mất bài mới nhất thì chỉ trường mô tả `latest_published` giữ được dấu vết.

4. **Vì sao cùng một test set.** Vì đây là thí nghiệm có đối chứng và chỉ được phép có một biến thay đổi. Đổi bộ câu hỏi giữa các lần đo thì không còn cách nào tách phần metric thay đổi do dữ liệu hỏng khỏi phần thay đổi do đề khác nhau. Tệ hơn, sinh lại test set trên dữ liệu đã hỏng còn tạo ra một lỗi im lặng: câu hỏi sẽ được sinh từ chính tài liệu đã bị corrupt và ground truth sẽ lấy đúng giá trị đã hỏng làm đáp án đúng — metric đẹp trong khi dữ liệu sai hoàn toàn. Đây là lý do tôi đặt cổng `REFRESH_TEST_SET` mặc định TẮT thay vì để `build_test_set()` chạy vô điều kiện.

5. **Repair thành công dựa trên gì.** Không dựa trên một chỉ số nào cả, mà trên bốn tín hiệu ở bốn tầng khác nhau cùng phục hồi: (a) tầng danh tính — lineage check `set(paper_id)` baseline == repaired trả `True`; (b) tầng cấu trúc — `repaired_quality.json` trở lại 6/6 PASS; (c) tầng thời gian — `repaired_freshness_report.json` trở lại `is_fresh=true`, `latest_published=2026-08-01`; (d) tầng hệ thống — 4/4 metric trong `repaired_metrics.json` trùng khớp baseline. Nếu chỉ (d) phục hồi mà (b) vẫn FAIL thì kết luận đúng phải là "dữ liệu vẫn hỏng nhưng bộ metric không đủ nhạy để thấy", hoàn toàn khác với "repair thành công".

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` | 1.0000 | 0.8750 | 1.0000 | Chỉ q1 mất hit. Đây là chỉ số duy nhất phản ứng với việc tài liệu *biến mất*; sửa nội dung tài liệu thì nó mù hoàn toàn |
| `mean_token_f1` | 1.0000 | 0.7674 | 1.0000 | Nhạy nhất trong bốn chỉ số. Phân rã đúng bằng `(0.1395 + 0.000 + 6×1.000)/8 = 0.7674` — q1 và q2 gánh toàn bộ mức sụt |
| `judge_accuracy` | 0.7500 | 0.6250 | 0.7500 | Chỉ đổi ở q1 (`correct` True→False). Baseline đã sẵn 0.75 vì q2 và q7 bị chấm sai từ đầu dù F1 = 1.000 |
| `mean_judge_score` | 4.7500 | 4.3750 | 4.7500 | Toàn bộ mức giảm 0.375 đến từ một mình q1 (5→2). q2 vẫn giữ 4/5 dù câu trả lời đã rỗng nội dung |
| Quality checks | 6/6 PASS | 3/6 FAIL | 6/6 PASS | `paper_id_unique`, `summary_min_length`, `freshness_age_days` cùng FAIL với `actual=1`; bắt được 2 kịch bản mà cả 4 metric đều không thấy |
| Freshness status | Fresh, 0/24 stale, latest 2026-08-01 | Stale, 1/24, latest 2026-07-13, oldest 2000-01-01 | Fresh, 0/24, latest 2026-08-01 | `latest_published` lùi 19 ngày là dấu vết duy nhất của `drop_latest_record` ở tầng dữ liệu |

Bảng theo từng câu hỏi (đọc từ `baseline_answers.json` và `corrupted_answers.json`), cho thấy corruption chạm được đúng 2/8 câu:

| Câu | Loại | `paper_id` ground truth | Baseline hit/F1 | Corrupted hit/F1 | Kịch bản chạm vào |
| --- | ---- | ---- | ---- | ---- | ---- |
| q1 | summary | `10-2118-234689-pa` | 1 / 1.000 | **0 / 0.140** | `drop_latest_record` |
| q2 | summary | `10-1007-s10278-026-02086-9` | 1 / 1.000 | **1 / 0.000** | `blank_summary` |
| q3 | authors | `10-21203-rs-3-rs-10178277-v1` | 1 / 1.000 | 1 / 1.000 | `truncate_title` (không đổi metric) |
| q4 | authors | `10-3390-buildings16132637` | 1 / 1.000 | 1 / 1.000 | `stale_date` (không đổi metric) |
| q5–q8 | date, categories | — | 1 / 1.000 | 1 / 1.000 | không bị nhắm |

### Kết luận từ số liệu

1. `blank_summary` xoá trống `summary` của `10-1007-s10278-026-02086-9` → `summary_min_length` chuyển FAIL với `actual=1` trong `corrupted_quality.json` → q2 giữ `retrieval_hit=True` nhưng `token_f1` rơi từ 1.000 xuống 0.000, kéo `mean_token_f1` toàn cục từ 1.0000 xuống 0.7674. Chuỗi này sạch vì tín hiệu quality và tín hiệu metric cùng trỏ về đúng một `paper_id`.
2. Repair chạy lại `build_clean_dataframe()` từ `data/raw/crossref_records.json` → `paper_id_unique`, `summary_min_length`, `freshness_age_days` cùng quay lại PASS và `is_fresh` quay lại `true` → cả 4 metric trong `repaired_metrics.json` khớp `baseline_metrics.json` tới từng chữ số, kèm lineage check `True`. Cả bốn tầng cùng phục hồi nên kết luận "repair thành công" đứng được.

**Corruption nào ảnh hưởng rõ nhất?** `drop_latest_record`. Xét biên độ trên một chỉ số đơn lẻ thì `blank_summary` lớn hơn (−0.2326 trên `mean_token_f1` so với −0.1395 phần của q1). Nhưng `drop_latest_record` là kịch bản duy nhất làm giảm **cả bốn** metric cùng lúc (hit 1→0, F1 1.000→0.140, judge `correct` True→False, score 5→2), vì nó phá ở tầng sâu nhất: tài liệu không còn tồn tại thì không tầng nào phía sau cứu được. Xoá trống nội dung vẫn để lại một tài liệu đúng để truy xuất; xoá hẳn tài liệu thì không.

**Kết quả nào khác với kỳ vọng ban đầu?** Hai điểm, và cả hai đều thuộc phần orchestration của tôi.

Thứ nhất, tôi kỳ vọng `drop_latest_record` sẽ kéo `row_count` xuống 23 và bị check Volume bắt ngay. Thực tế `corrupted_quality.json` báo `row_count=24`, PASS. Nguyên nhân là `duplicate_row` nhân đôi một dòng khác và **bù lại đúng dòng đã mất** — hai lỗi triệt tiêu nhau ở đúng chỉ số đang đếm chúng. Tôi đã kiểm tra lại `corruption_log.json` để xác nhận: `original_row_count=24`, `corrupted_row_count=24`, trong khi phần `entries` ghi rõ một entry `REMOVED` và một entry `1 occurrence → 2 occurrences`. Bài học cho vai trò tích hợp: một chỉ số **tổng hợp** có thể bị hai lỗi bù trừ qua mặt, nên cổng chất lượng cần ít nhất một chỉ số nói về *danh tính* chứ không chỉ về *số lượng* — ở đây `paper_id_unique` là thứ duy nhất cứu được tình huống, và nó bắt được là nhờ đếm bản trùng chứ không đếm tổng số dòng.

Thứ hai, tôi kỳ vọng `truncate_title` (cắt tiêu đề còn 12 ký tự, `"Retrieval-Au"`) sẽ phá q3, vì câu hỏi trong test set nhúng nguyên văn tiêu đề trong dấu nháy đơn và `qa.py` dùng regex bóc tiêu đề đó ra để tra cứu chính xác — tiêu đề đã cắt thì `index.lookup()` chắc chắn miss. Thực tế q3 giữ nguyên `hit=True, F1=1.000`. Đọc lại `qa.py` mới thấy `answer_question()` **luôn** chạy `index.search()` song song với `lookup()` và chỉ dùng kết quả exact để đẩy lên đầu danh sách nếu có; khi lookup miss, đường semantic vẫn tìm ra tài liệu vì `text_for_embedding` chứa cả summary lẫn authors, không chỉ title. Kiến trúc hai đường của Nguyễn Chính Nghĩa đã che được lỗi này. Đây là kết quả tốt cho hệ thống nhưng là cảnh báo cho phép đo: bộ metric hiện tại **không** phân biệt được "dữ liệu còn nguyên" với "dữ liệu hỏng nhưng có đường dự phòng che", nên tôi không kết luận `truncate_title` vô hại — chỉ kết luận nó nằm ngoài tầm phát hiện của bộ đo hiện tại.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về data pipeline:** Tính tái hiện không đến từ việc pipeline chạy được, mà từ việc mặc định của nó là *không* làm mới thứ gì. Hai dòng điều kiện quanh `fetch_source_records()` và `build_test_set()` là phần code có ảnh hưởng lớn nhất mà tôi viết trong bài này, và cả hai đều là code *không làm gì cả* trong trường hợp thường gặp. Với một nguồn sống như Crossref, "chạy lại pipeline" và "chạy lại thí nghiệm" là hai việc khác nhau, và mặc định phải nghiêng về việc thứ hai.
2. **Về data quality/observability:** Thứ nguy hiểm nhất không phải lỗi làm pipeline dừng, mà lỗi khiến pipeline vẫn cho ra số hợp lệ nhưng vô nghĩa. Cả ba trường hợp tôi gặp đều thuộc loại này: judge im lặng rơi về heuristic mà vẫn trả về `JudgeVerdict` hợp lệ; ba collection đè lên nhau mà baseline vẫn có metrics đúng; `row_count` vẫn PASS vì hai lỗi bù trừ. Không cái nào tự báo lỗi — mỗi cái cần một tín hiệu được dựng riêng để phát hiện (`judge_backend`, tách collection, `paper_id_unique`).
3. **Về ảnh hưởng của data tới RAG agent:** Quan hệ giữa chất lượng dữ liệu và chất lượng câu trả lời không phải một-một theo cả hai chiều. `stale_date` và `duplicate_row` làm hỏng dữ liệu mà không đụng một metric nào; ngược lại `blank_summary` để `retrieval_hit_rate` nguyên vẹn nhưng làm câu trả lời rỗng nội dung; và `truncate_title` hỏng dữ liệu nhưng bị kiến trúc truy xuất che mất. Chỉ dùng một lớp giám sát là chắc chắn có điểm mù, và điểm mù của hai lớp không trùng nhau — đó chính là lý do phải chạy song song.

### Nếu có thêm thời gian

Tôi sẽ biến quality gate từ quan sát thụ động thành **cổng chặn thật** trong `phase1.py`: sau bước 6, nếu `quality["overall_status"] == "FAIL"` thì dừng pipeline trước khi ghi report, trừ khi có cờ `ALLOW_DIRTY=1` tường minh. Hiện tại dữ liệu hỏng vẫn đi hết pipeline và sinh ra một `phase1_report.md` trông bình thường; chỉ có người mở đúng file JSON mới biết. Cách đo cải thiện rất rõ: cố tình chạy `run_phase1.py` trên bản corrupted, kỳ vọng pipeline dừng ở bước 6 với mã thoát khác 0 và **không** sinh ra `phase1_report.md` mới; đồng thời chạy lại trên bản sạch phải vẫn qua được 8/8 bước — nếu bản sạch cũng bị chặn thì cổng đặt sai ngưỡng.

Song song đó tôi sẽ thêm cổng ở tầng version control mà mục 6.2 đã chỉ ra là còn thiếu: một pre-push hook chạy `git grep -q "^<<<<<<< "` và chặn push nếu có, cộng thêm một bước CI tối thiểu `python -c "import json,glob; [json.load(open(f)) for f in glob.glob('data/**/*.json', recursive=True)]"` để một artifact JSON hỏng không bao giờ vào được `main`. Cả hai đều rẻ và đều chặn được đúng sự cố đã thực sự xảy ra với nhóm.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng — mục 6.2 ghi rõ nhánh `main` hiện chưa chạy được và số liệu trong báo cáo lấy từ lần chạy trên `78ad189` lúc 03:15:32Z–03:24:40Z.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret (nhóm dùng Ollama cục bộ, không có key nào cần che).
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Trần Vương Hưng
**Ngày xác nhận:** 2026-08-06
