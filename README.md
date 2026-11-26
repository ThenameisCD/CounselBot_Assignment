
# CounselBot — Advanced RAG with Role-Based Access and Ethical Walls

An internal legal document assistant built for the fictional Veridian Legal Hub. CounselBot combines document retrieval, hybrid search, cross-encoder reranking and SQL-based question answering with role-based access control and matter-level ethical walls.

> **Disclaimer:** This is an educational demonstration using fictional legal data. It is not legal advice and is not intended for production use.

## 1. Project Overview

CounselBot allows legal and compliance staff to ask questions about internal documents and structured legal records.

The system supports:

- PDF and Markdown document ingestion.
- Structure-aware hierarchical chunking.
- Document metadata and manifest-based permissions.
- Dense vector retrieval and BM25 keyword retrieval.
- Reciprocal Rank Fusion (RRF) for hybrid retrieval.
- Cross-encoder reranking.
- SQL-based question answering over scoped database views.
- JWT authentication.
- Role-based and matter-based access restrictions.
- A Next.js chat interface with user identity and source citations.

## 2. Architecture

```text
                    Next.js Frontend
                           |
                           | HTTP + JWT
                           v
                     FastAPI Backend
                           |
                    Authenticate User
                           |
                 Derive Role and Matters
                    from Signed JWT
                           |
                 Access Control Checks
                           |
              +------------+------------+
              |                         |
        Document RAG                 SQL RAG
              |                         |
       Qdrant Retrieval           SQL Generation
              |                         |
       Dense Search               SQL Validation
              |                         |
       BM25 Search                Read-only Execution
              |                         |
       RRF Fusion                 Matter-scoped Views
              |                         |
       Cross-Encoder              Database Results
         Reranking                       |
              |                         |
       Answer Generation         Answer Generation
              |                         |
              +------------+------------+
                           |
                  Answer + Citations
                           |
                     Next.js UI
```

## 3. Technology Stack

| Component | Technology |
|---|---|
| Backend API | Python, FastAPI |
| Authentication | JWT |
| Document parsing | Docling |
| Chunking | Hierarchical chunking |
| Embeddings | Sentence Transformers |
| Vector database | Qdrant |
| Keyword retrieval | BM25 |
| Hybrid ranking | Reciprocal Rank Fusion |
| Reranking | Cross-Encoder |
| LLM integration | LangChain, Groq |
| Structured data | SQLite |
| Frontend | Next.js, React, TypeScript |
| Styling | Tailwind CSS |

## 4. Project Structure

```text
CounselBot_Assignment/
|
|-- backend/
|   |-- app/
|   |   |-- main.py
|   |   |-- auth.py
|   |   |-- config.py
|   |   |-- models.py
|   |   |
|   |   |-- security/
|   |   |   |-- access_control.py
|   |   |   |-- document_access.py
|   |   |   |-- manifest_loader.py
|   |   |   |-- sql_scoping.py
|   |   |
|   |   |-- rag/
|   |       |-- ingestion.py
|   |       |-- embeddings.py
|   |       |-- vector_store.py
|   |       |-- dense_retrieval.py
|   |       |-- bm25_retrieval.py
|   |       |-- hybrid_retrieval.py
|   |       |-- reranking.py
|   |       |-- document_rag.py
|   |       |-- sql_rag.py
|   |       |-- answer_generation.py
|   |       |-- index_documents.py
|   |       |-- retrieval_comparison.py
|   |
|   |-- requirements.txt
|
|-- frontend/
|   |-- app/
|   |   |-- page.tsx
|   |   |-- layout.tsx
|   |   |-- globals.css
|   |-- package.json
|
|-- veridian_legal_dataset/
|   |-- documents/
|   |-- manifest.json
|   |-- users_seed.json
|   |-- veridian_legal.db
|
|-- screenshots/
|-- retrieval_comparison.txt
|-- .env.example
|-- .gitignore
|-- README.md
```

## 5. Setup Instructions

### Prerequisites

- Python 3.10 or compatible version.
- Node.js and npm.
- Git.
- A Groq API key.

### Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd CounselBot_Assignment
```

### Backend setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install Python dependencies:

```powershell
python -m pip install -r backend/requirements.txt
```

Create a `.env` file in the project root.

Add:

```env
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-120b
JWT_SECRET_KEY=your_long_random_secret
```

Use your own API key and a strong random JWT secret. Never commit `.env` to GitHub.

### Build the vector database

From the project root, with the virtual environment activated:

```powershell
python -m backend.app.rag.index_documents
```

This processes the dataset and indexes document chunks into the five Qdrant collections.

### Start the backend

```powershell
uvicorn backend.app.main:app --reload
```

Backend address:

```text
http://127.0.0.1:8000
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

### Frontend setup

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Frontend address:

```text
http://localhost:3000
```

Keep the backend and frontend running in separate terminals.

## 6. API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/login` | Authenticate a demo user and issue JWT |
| POST | `/chat` | Ask a document or SQL question |
| GET | `/me` | Retrieve authenticated user details |
| GET | `/collections/{role}` | Retrieve permitted collections |
| GET | `/health` | Check API health |

The backend derives the user's identity, role and matter assignments from the authenticated token. The frontend cannot grant itself additional permissions by changing request fields.

## 7. Access Control and Ethical Walls

Document access requires all three checks to pass:

1. The user's role can access the document collection.
2. The user's role is included in the document's permitted access roles.
3. The document matter is either unrestricted, assigned to the user, or the user has General Counsel wildcard access.

The manifest is the source of truth for document permissions.

### Collection permissions

| Role | Permitted collections |
|---|---|
| General Counsel | General, Contracts, Litigation, Compliance, IP |
| Corporate Counsel | General, Contracts, IP |
| Litigation Counsel | General, Litigation, IP |
| Compliance Officer | General, Compliance |
| Paralegal | General, Contracts |

Matter restrictions apply in addition to collection and role restrictions.

### SQL permissions

| Role | Permitted SQL data |
|---|---|
| General Counsel | Contracts and litigation |
| Corporate Counsel | Contracts only |
| Litigation Counsel | No SQL access |
| Compliance Officer | No SQL access |
| Paralegal | No SQL access |

SQL queries use scoped views, read-only connections and execution restrictions. Matter filtering is applied before results are returned.

## 8. Retrieval Pipeline

The document retrieval process follows these stages:

1. Parse source documents using Docling.
2. Create hierarchical chunks with section headings and metadata.
3. Generate embeddings using Sentence Transformers.
4. Store chunks in Qdrant collections.
5. Retrieve candidates using dense vector search.
6. Retrieve candidates using BM25 keyword search.
7. Combine rankings using Reciprocal Rank Fusion.
8. Rerank candidates using a cross-encoder.
9. Send the selected accessible passages to the LLM.
10. Return the answer with application-generated citations.

Security filters are applied during retrieval, not merely after the LLM generates an answer.

## 9. SQL RAG Pipeline

The SQL RAG pipeline:

1. Receives the user's question.
2. Checks whether the user's role may access the requested data.
3. Provides only the permitted database schema to the SQL generation model.
4. Generates a read-only SQL query.
5. Executes it against matter-scoped views.
6. Converts the results into a natural-language answer.

Only authorised, scoped results are supplied for answer generation.

## 10. Security and Adversarial Testing

Testing covers:

- Role-restricted collection access.
- Matter-level isolation.
- Paralegal access restrictions.
- Corporate Counsel SQL restrictions.
- Litigation data restrictions.
- Prompt injection attempts.
- Attempts to impersonate General Counsel.
- SQL modification attempts.
- General Counsel access to authorised sensitive documents.

Screenshots documenting the tests are stored in the `screenshots/` directory.

## 11. Retrieval Comparison

The project includes a retrieval comparison script:

```powershell
python -m backend.app.rag.retrieval_comparison
```

It compares:

- Dense-only retrieval.
- Hybrid retrieval using dense search and BM25.
- Hybrid retrieval followed by cross-encoder reranking.

The comparison output is saved in:

```text
retrieval_comparison.txt
```

The demonstration shows that reranking can improve the position of relevant results for the tested query. Results from one query should not be treated as a universal performance benchmark.

## 12. Demo Users

The fictional dataset includes eight demo users:

| Username | Role |
|---|---|
| gc.sharma | General Counsel |
| adv.rao | Corporate Counsel |
| adv.nair | Corporate Counsel |
| adv.khan | Litigation Counsel |
| adv.iyer | Litigation Counsel |
| comp.deshpande | Compliance Officer |
| comp.bose | Compliance Officer |
| para.sneha | Paralegal |

Use the corresponding demo passwords supplied in `veridian_legal_dataset/users_seed.json`.

These are demonstration credentials only. Do not use this authentication design for a production legal system.

## 13. Limitations and Future Improvements

This project is an educational prototype. Further work would be required before production deployment, including:

- Password hashing and secure user management.
- Stronger SQL parsing and query validation.
- More comprehensive automated security tests.
- Production-grade secrets management.
- Audit logging and monitoring.
- Evaluation across a larger set of retrieval questions.
- Improved document parsing and retrieval evaluation.
- Deployment hardening and infrastructure security.

## 14. Tool Choices and Substitutions

The implementation uses the following components:

- **Qdrant:** local vector storage and metadata filtering.
- **Sentence Transformers:** local embedding generation.
- **BM25:** sparse keyword retrieval.
- **Cross-Encoder:** relevance-based reranking.
- **SQLite:** structured legal records and scoped views.
- **FastAPI:** backend API.
- **Next.js:** frontend application.
- **Groq:** LLM inference.

These choices provide a practical implementation of the assignment requirements without requiring a hosted vector database or a separate managed SQL service.

## 15. Disclaimer

CounselBot uses fictional Veridian Legal Hub documents and data for educational purposes. It does not provide legal advice, and its outputs must not be relied upon for real legal decisions.
