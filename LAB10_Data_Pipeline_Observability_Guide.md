# Lab 10 — Data Pipeline & Data Observability

## 1. Bức tranh toàn cảnh & Thuật ngữ

### Thông tin chung

* Thời lượng: **210 phút (3.5 giờ)**
* Mức độ: **Trung cấp**

Trong lab này, nhóm sẽ xây dựng một pipeline RAG hoàn chỉnh từ dữ liệu khoa học lấy từ Crossref API, sau đó áp dụng Data Observability để giám sát chất lượng dữ liệu, mô phỏng các sự cố dữ liệu (Data Corruption), đánh giá tác động của chúng lên hệ thống RAG, và cuối cùng khôi phục dữ liệu từ các bản sao lưu thô (Raw Snapshot).

---

## Mục tiêu của Lab

Chứng minh được mối quan hệ:

```text
Crossref API (Source)
        ↓
Raw Artifacts
        ↓
Clean Dataset
        ↓
Embedding + ChromaDB
        ↓
Evaluation Set + Answers
        ↓
Quality + Freshness Checks
        ↓
Baseline Evidence
        ↓
Controlled Corruption
        ↓
Corrupted Evidence
        ↓
Repair from Saved Raw
        ↓
Repaired Evidence
        ↓
Fair Comparison
```

### Kết luận cần chứng minh

> Data Corruption làm thay đổi các tín hiệu chất lượng dữ liệu (Quality/Freshness Signals), từ đó ảnh hưởng trực tiếp tới chất lượng Retrieval và Answering của hệ thống RAG.

> Repair từ Raw Snapshot giúp phục hồi hệ thống và cho phép đo lường sự phục hồi một cách công bằng.

---

# Timeline Buổi Lab

| Thời gian | Thành phần     | Nội dung                                 |
| --------- | -------------- | ---------------------------------------- |
| 0:00–0:20 | Cả nhóm        | Setup môi trường, đọc starter code       |
| 0:20–0:40 | Cả nhóm        | Phân vai và thống nhất Data Contract     |
| 0:40–1:45 | Mỗi người      | Ingestion, Cleaning, Test Set, Retrieval |
| 1:45–2:25 | Mỗi người      | Chạy Baseline và đánh giá                |
| 2:25–3:10 | Nhóm / Cá nhân | Corruption và Repair                     |
| 3:10–3:30 | Cả nhóm        | Hoàn thiện báo cáo và nộp bài            |

---

# Deliverables

| # | Sản phẩm                 | Người nộp | Vị trí                         |
| - | ------------------------ | --------- | ------------------------------ |
| 1 | Source Code hoàn chỉnh   | Nhóm      | `src/`                         |
| 2 | Dataset sạch / lỗi / sửa | Nhóm      | `data/raw`, `data/clean`       |
| 3 | Frozen Evaluation Set    | Nhóm      | `data/eval/test_set.json`      |
| 4 | Metrics & Answers        | Nhóm      | `data/results/`                |
| 5 | Quality Reports          | Nhóm      | `data/quality`, `data/reports` |
| 6 | Group Report             | Nhóm      | `report/group_report.md`       |
| 7 | Individual Report        | Cá nhân   | `report/individual_[MSSV].md`  |

---

# Rubric

| Hạng mục                   | Điểm |
| -------------------------- | ---- |
| Code Structure             | 10   |
| Raw Data Ingestion         | 15   |
| Cleaning & Data Modeling   | 15   |
| Embedding & Vector Store   | 10   |
| Agent & Multi-provider LLM | 10   |
| Evaluation & Scoring       | 10   |
| Data Observability         | 10   |
| Corruption & Comparison    | 10   |
| Bonus                      | 10   |

Tổng: **90 điểm + 10 bonus**

---

# Thuật ngữ quan trọng

| Thuật ngữ          | Ý nghĩa                     |
| ------------------ | --------------------------- |
| Data Pipeline      | Luồng xử lý dữ liệu tự động |
| Data Observability | Giám sát trạng thái dữ liệu |
| Raw Artifacts      | Dữ liệu gốc lưu từ API      |
| Evaluation Set     | Bộ câu hỏi đánh giá         |
| Data Corruption    | Cố ý làm hỏng dữ liệu       |
| Data Repair        | Khôi phục dữ liệu           |
| Baseline           | Trạng thái chuẩn            |
| Retrieval Hit Rate | Tỷ lệ tìm đúng tài liệu     |

---

# 2. Setup, Phân Vai & Data Contract

## Yêu cầu Python

```bash
python --version
```

Hỗ trợ:

```text
Python 3.11 - 3.13
```

---

## Cách A - UV (Khuyến nghị)

```bash
uv sync
```

Tự động:

* Tạo `.venv`
* Cài dependencies
* Đồng bộ lock file

---

## Cách B - Pip

### Windows

```powershell
python -m venv .venv

.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip

python -m pip install -e .
```

### macOS/Linux

```bash
python3 -m venv .venv

source .venv/bin/activate

python -m pip install --upgrade pip

python -m pip install -e .
```

---

## Cấu hình .env

```bash
cp .env.example .env
```

Ví dụ Gemini:

```env
LLM_PROVIDER=gemini

LLM_MODEL=gemini-2.5-flash

GOOGLE_API_KEY=your_key_here
```

---

## Tìm TODO

### Linux/macOS

```bash
grep -RInE 'TODO\(student\)|NotImplementedError' src
```

### Windows

```powershell
Get-ChildItem src -Recurse -Filter *.py |
Select-String -Pattern 'TODO\(student\)|NotImplementedError'
```

---

# CHECKPOINT C0

### Minh chứng

* Environment cài đặt thành công
* Tạo được `.env`
* Liệt kê được toàn bộ TODO

---

# Phân vai

## Nhóm 4 người (khuyến nghị)

### Thành viên 1

Source Ingestion Owner

```text
crossref.py
```

### Thành viên 2

Data Model & Eval Set Owner

```text
cleaning.py
testset.py
```

### Thành viên 3

Data Observability Owner

```text
quality.py
reporting.py
```

### Thành viên 4

Corruption & Integration Owner

```text
corruption.py
phase1.py
corruption_flow.py
```

---

## Data Contract

### Raw Schema

```json
[
  {
    "paper_id": "...",
    "title": "...",
    "summary": "..."
  }
]
```

---

### Clean Schema

```text
paper_id
title
summary
published
authors_joined
categories_joined
age_days
text_for_embedding
abs_url
pdf_url
```

---

### Evaluation Schema

```json
{
  "id": "q1",
  "question_type": "factual",
  "question": "...",
  "ground_truth": "...",
  "ground_truth_doc_ids": ["paper_123"]
}
```

---

# CHECKPOINT C1

Mục tiêu:

* Tránh xung đột interface.
* Điền phân công vào `group_report.md`.

---

# 3. Thu thập & Làm sạch dữ liệu

## Crossref Ingestion

File:

```text
src/ingestion/crossref.py
```

API:

```text
https://api.crossref.org/works
```

### Yêu cầu

#### 1. Query dữ liệu

Ví dụ:

```text
machine learning
```

Chỉ giữ record có:

* title
* abstract/description

---

#### 2. Retry & Backoff

Xử lý:

```text
429
503
```

---

#### 3. Lưu Raw Artifacts

### HTTP Response gốc

```text
data/raw/crossref_response.json
```

### Parsed Records

```text
data/raw/crossref_records.json
```

---

## Cleaning

File:

```text
src/ingestion/cleaning.py
```

### Quy tắc

#### Drop dữ liệu rác

Loại bỏ:

* title rỗng
* summary < 100 ký tự

---

#### Xóa HTML/XML

Ví dụ:

```html
<jats:p>
<b>
```

---

#### Gộp Authors

```text
authors_joined
```

---

#### Gộp Categories

```text
categories_joined
```

---

#### Freshness

Chuẩn hóa:

```text
YYYY-MM-DD
```

Tính:

```text
age_days
```

---

#### Text for Embedding

```text
Title: ...
Authors: ...
Summary: ...
```

---

## Output

```text
data/clean/papers_clean.csv
data/clean/papers_clean.json
```

---

# 4. Frozen Evaluation Set

File:

```text
src/evaluation/testset.py
```

---

## Yêu cầu

Sinh 5-10 câu hỏi factual.

Ví dụ:

```text
Tác giả của bài báo về Machine Learning là ai?
```

Schema:

```json
{
  "id": "q1",
  "question_type": "factual",
  "question": "...",
  "ground_truth": "...",
  "ground_truth_doc_ids": ["paper_id"]
}
```

Output:

```text
data/eval/test_set.json
```

---

## Retrieval Stack

### embeddings.py

```text
all-MiniLM-L6-v2
384 dimensions
```

### index.py

```text
ChromaDB
```

### llm.py

```text
Gemini/OpenAI/Ollama Wrapper
```

### agent.py + qa.py

```text
Retrieve → Prompt → LLM → Answer
```

---

# CHECKPOINT C2

Phải có:

```text
data/raw/
├── crossref_response.json
└── crossref_records.json

data/clean/
├── papers_clean.csv
└── papers_clean.json

data/eval/
└── test_set.json
```

---

# 5. Baseline Pipeline

File:

```text
src/pipelines/phase1.py
```

Pipeline:

```text
Crossref
 ↓
Raw
 ↓
Cleaning
 ↓
Chroma Index
 ↓
Test Set
 ↓
Agent QA
 ↓
Metrics
 ↓
Quality Checks
 ↓
Report
```

---

## Metrics

### Retrieval Hit Rate

```text
Top-k có chứa ground truth hay không
```

### Mean Token F1

```text
Độ khớp Answer vs Ground Truth
```

### LLM Judge

Đánh giá bằng Gemini/OpenAI nếu bật.

---

## Chạy

```bash
uv run python script/run_phase1.py
```

---

# CHECKPOINT C3

Output:

```text
data/results/baseline_metrics.json
data/results/baseline_answers.json

data/quality/*
data/reports/phase1_report.md
```

Tất cả quality checks phải:

```text
PASS
```

---

# 6. Corruption & Repair

File:

```text
src/ingestion/corruption.py
```

---

## Kịch bản Corruption

### 1. Blank Summary

```text
summary = ""
```

---

### 2. Stale Date

```text
published -> year 2000
```

---

### 3. Duplicate

Nhân đôi record.

---

### 4. Add Noise

Chèn nội dung rác.

---

⚠️ Phải làm hỏng ít nhất một tài liệu nằm trong:

```text
ground_truth_doc_ids
```

---

Output:

```text
data/clean/papers_corrupted.csv
data/results/corruption_log.json
```

---

## Repair Flow

File:

```text
src/pipelines/corruption_flow.py
```

### Corrupted

```text
Corrupted CSV
 ↓
Build Chroma
 ↓
Evaluate
 ↓
Corrupted Metrics
```

### Repair

```text
crossref_records.json
 ↓
Cleaning
 ↓
Clean Data
 ↓
Build Chroma
 ↓
Evaluate
 ↓
Repaired Metrics
```

---

## Chạy

```bash
uv run python script/run_corruption_flow.py
```

---

# CHECKPOINT C4

Phải có:

```text
data/clean/papers_corrupted.csv

data/results/corruption_log.json

data/reports/corruption_report.md
```

Report phải so sánh:

| Metric | Baseline | Corrupted | Repaired |
| ------ | -------- | --------- | -------- |

---

# 7. Báo cáo & Nộp bài

## Cấu trúc repo

```text
K3-DAY10-[MSSV]-[HoVaTen]
│
├── src
├── data
├── report
├── pyproject.toml
└── script
```

---

## Definition of Done

* Baseline chạy thành công
* Corruption chạy thành công
* Repair chạy thành công
* Dùng cùng một frozen test set
* Group report hoàn chỉnh
* Individual report đầy đủ
* Không commit API Key

---

# CHECKPOINT C5

Minh chứng:

```text
report/group_report.md

report/individual_[MSSV].md
```

Đã hoàn thiện và commit sạch sẽ.

---

# Troubleshooting

| Lỗi                        | Nguyên nhân             | Cách xử lý           |
| -------------------------- | ----------------------- | -------------------- |
| ModuleNotFoundError        | Chưa `pip install -e .` | Cài package editable |
| GOOGLE_API_KEY is required | Thiếu API key           | Kiểm tra `.env`      |
| NotImplementedError        | TODO chưa làm           | Hoàn thiện code      |
| Crossref 429/503           | Rate limit              | Retry + Backoff      |
| Metrics không đổi          | Corruption sai dữ liệu  | Đụng vào frozen docs |
| RRF Score lỗi              | So sánh sai score       | Dùng Cosine Score    |

```
```
