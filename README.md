# DeepCites

> **An AI-powered research agent that investigates questions, retrieves evidence from the web and your documents, and generates answers with source-backed citations.**

**Status:** 🚧 In active development

DeepCites is a portfolio project exploring practical AI engineering: agent orchestration, retrieval-augmented generation (RAG), tool calling, citation integrity, evaluation, and observability. The goal is to build a research workflow that can explain what it found, where the evidence came from, and when the available evidence is insufficient.

---

## Contents

- [Vision](#vision)
- [Planned Features](#planned-features)
- [Technology Stack](#technology-stack)
- [How It Will Work](#how-it-will-work)
- [Architecture](#architecture)
- [RAG Pipeline](#rag-pipeline)
- [Security and Reliability](#security-and-reliability)
- [Development Roadmap](#development-roadmap)
- [Planned Project Structure](#planned-project-structure)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Testing and Evaluation](#testing-and-evaluation)
- [Current Status](#current-status)
- [Future Improvements](#future-improvements)

---

## Vision

Research often involves searching across multiple websites and documents, comparing claims, and checking whether sources actually support a conclusion. DeepCites aims to make this workflow easier by coordinating research tools and document retrieval through a controlled AI workflow.

Rather than treating an LLM response as automatically correct, DeepCites is being designed to:

1. Break a research question into manageable subquestions.
2. Retrieve relevant information from permitted web sources and user-uploaded documents.
3. organize evidence and identify gaps or conflicting information.
4. Check citation and evidence references before producing the final answer.
5. Clearly communicate uncertainty when the available evidence is insufficient.

> **Design principle:** A fluent answer is not necessarily a well-supported answer. DeepCites aims to make evidence traceable and limitations visible.

## Planned Features

- **Research planning:** Decompose a broad question into focused research queries.
- **Web research:** Search the web using Tavily and extract page content with HTTPX and Beautiful Soup.
- **Document research:** Upload supported files and ask questions grounded in their content.
- **Semantic retrieval:** Find relevant document chunks using embeddings and PostgreSQL `pgvector`.
- **Evidence analysis:** Compare sources, surface disagreements, and identify missing evidence.
- **Citation checks:** Validate source references and check whether claims are linked to relevant evidence.
- **Grounded responses:** Generate answers with links to sources and document page references where available.
- **Authentication:** Use Supabase Auth for user identity.
- **User-scoped data:** Keep document retrieval and research data isolated between users.
- **Progress updates:** Provide useful research progress and, where practical, stream responses to the frontend.
- **Feedback and evaluation:** Collect feedback and run repeatable checks on retrieval and answer quality.
- **Observability:** Trace graph nodes and tools with OpenTelemetry.

*These are project goals; features are not considered complete until implemented and tested.*

## Technology Stack

| Layer | Planned technology | Purpose |
|---|---|---|
| Frontend | Next.js, TypeScript, shadcn/ui | Research interface and results |
| Backend | Python, FastAPI | API, authentication verification, ingestion, and orchestration |
| Agent workflow | LangGraph | State-driven research workflow and bounded routing |
| Database | Supabase PostgreSQL | Sessions, metadata, evidence, feedback, and related records |
| Vector search | PostgreSQL `pgvector` | Semantic search over document chunks |
| Authentication | Supabase Auth | Sign-up, sign-in, and user identity |
| File storage | Supabase Storage | Uploaded research documents |
| Embeddings | FastEmbed + `BAAI/bge-small-en-v1.5` | 384-dimensional document and query embeddings |
| Web search | Tavily | Find candidate web sources |
| Page extraction | HTTPX + Beautiful Soup | Fetch and extract readable page content |
| Validation | Pydantic | Validate inputs and structured outputs |
| Testing | pytest | Unit and integration tests |
| Observability | OpenTelemetry | Tracing and basic operational measurements |
| Deployment target | Vercel + a suitable Python host | Host the frontend and backend |

### LLM provider

The initial model provider is being evaluated. Gemini is the current starting candidate, with NVIDIA Nemotron 3 Super as a possible comparison model. The final choice will depend on tool-calling reliability, structured output support, answer quality, latency, API availability, and free-tier limits.

Model IDs and provider settings should be configurable rather than hard-coded throughout the application.

## How It Will Work

A typical research request is intended to follow this flow:

1. **Validate the request** — check input limits and confirm the user's access.
2. **Plan research** — produce a small set of focused research questions.
3. **Gather evidence** — search the web, read relevant pages, and retrieve authorized document chunks.
4. **Analyze evidence** — summarize findings, compare sources, and flag gaps or conflicts.
5. **Check citations** — validate source IDs and evidence links; assess support where practical.
6. **Write the answer** — produce a readable response grounded in the collected evidence.
7. **Return results** — show the answer, source links, limitations, and progress information.

The workflow will use bounded retries and iteration limits. If it cannot find enough evidence, it should say so rather than inventing sources or unsupported claims.

## Architecture

```text
Next.js + TypeScript + shadcn/ui
                 |
                 v
         Supabase Auth session
                 |
                 v
          FastAPI backend
                 |
       Request validation and
       token verification
                 |
                 v
       LangGraph research flow
                 |
     +-----------+------------+
     |           |            |
     v           v            v
   Planner   Researcher    Analyst
                 |
       +---------+----------+
       |                    |
       v                    v
 Tavily + page reader   Document retrieval
       |                    |
       v                    v
 Web evidence        Supabase pgvector
       |                    |
       +---------+----------+
                 |
                 v
       Citation / evidence checks
                 |
                 v
          Answer generation
                 |
                 v
       Response / progress stream
```

The exact node boundaries and API contracts may change as implementation and testing progress.

## RAG Pipeline

The planned document question-answering pipeline is:

```text
Upload document
      |
      v
Validate file and ownership
      |
      v
Store original in Supabase Storage
      |
      v
Extract text and page metadata
      |
      v
Split text into chunks
      |
      v
Generate embeddings with FastEmbed
      |
      v
Store chunks + 384-dimensional vectors
in PostgreSQL with pgvector
      |
      v
Embed the user's question
      |
      v
Retrieve relevant, authorized chunks
      |
      v
Pass evidence to the research workflow
      |
      v
Generate an answer with document references
```

The embedding model must remain consistent between ingestion and query time. Retrieval should be scoped to documents the requesting user is authorized to access. Where possible, evidence should retain document ID, page number, and chunk metadata so the final answer can reference its origin.

## Security and Reliability

Security and reliability are part of the design, not optional finishing touches.

- Verify Supabase access tokens on the backend.
- Enforce ownership checks and appropriate Row Level Security (RLS) policies.
- Never expose the Supabase service-role key in browser code or public frontend environment variables.
- Validate upload types, sizes, and request lengths.
- Treat web pages and uploaded documents as untrusted content, not as instructions to the agent.
- Restrict outbound URL fetching and protect against SSRF, private/internal IPs, unsafe redirects, and oversized responses.
- Set timeouts and limits for model calls, searches, page extraction, retrieval, and graph iterations.
- Validate generated output and ensure cited source IDs belong to the current research run.
- Avoid logging secrets, access tokens, or private document contents.
- Use graceful error handling when external providers, the database, or the model are unavailable.

Citation validation can establish that a source exists and is connected to a claim; it does **not**, by itself, prove that the claim is true.

## Development Roadmap

The roadmap is intentionally prioritized for a small working demo.

### Phase 1 — Core research flow

- [ ] Inspect and organize the existing repository.
- [ ] Set up FastAPI and configuration.
- [ ] Build a minimal LangGraph workflow.
- [ ] Integrate Tavily search.
- [ ] Extract readable web page content.
- [ ] Return a useful answer with source links.
- [ ] Add basic error handling and tests.

### Phase 2 — Supabase and document RAG

- [ ] Configure Supabase Auth.
- [ ] Verify user tokens in FastAPI.
- [ ] Create database schema and RLS policies.
- [ ] Configure Supabase Storage for uploads.
- [ ] Implement document parsing and chunking.
- [ ] Generate embeddings with FastEmbed.
- [ ] Store vectors in `pgvector`.
- [ ] Implement user-scoped semantic retrieval.
- [ ] Test retrieval using known questions and evidence.

### Phase 3 — Evidence quality and UI integration

- [ ] Add analysis and citation-checking steps.
- [ ] Define structured schemas for sources, evidence, claims, and answers.
- [ ] Connect the Next.js interface to FastAPI.
- [ ] Add research progress updates or SSE if practical.
- [ ] Test missing evidence, invalid citations, and provider failures.
- [ ] Test user-data isolation.

### Phase 4 — Evaluation and deployment

- [ ] Create a small, repeatable evaluation dataset.
- [ ] Measure retrieval quality and citation coverage.
- [ ] Add user feedback collection.
- [ ] Add basic OpenTelemetry tracing.
- [ ] Deploy frontend and backend.
- [ ] Verify environment variables, CORS, storage, and persistence.
- [ ] Document known limitations and demo instructions.

## Planned Project Structure

The structure below is a target, not a claim that every file already exists. Keep the repository simpler if the current implementation does not need all these modules yet.

```text
deepcites/
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── package.json
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/
│   │   ├── auth/
│   │   ├── graph/
│   │   │   ├── state.py
│   │   │   ├── workflow.py
│   │   │   └── nodes/
│   │   ├── tools/
│   │   ├── retrieval/
│   │   ├── guardrails/
│   │   ├── db/
│   │   └── schemas/
│   ├── tests/
│   ├── evals/
│   └── requirements.txt
├── supabase/
│   └── migrations/
├── .env.example
├── .gitignore
└── README.md
```

## Getting Started

DeepCites is currently in development, so setup commands may need adjustment as the repository and dependencies are finalized.

### Prerequisites

- Python compatible with the selected backend dependencies.
- Node.js compatible with the selected Next.js version.
- A Supabase project.
- A Gemini API key or another supported LLM provider key.
- A Tavily API key if using Tavily web search.

### Setup outline

1. Clone the repository.
2. Install the frontend and backend dependencies using the manifests in each directory.
3. Create a Supabase project and configure Auth, Storage, PostgreSQL, and `pgvector`.
4. Copy `.env.example` to the appropriate local environment file and add your own credentials.
5. Apply the database migrations.
6. Start FastAPI and the Next.js development server.
7. Run the tests and verify the configured research workflow.

Do not commit `.env` files, service-role keys, API keys, access tokens, uploaded private documents, or other sensitive data.

## Configuration

The following is an illustrative configuration checklist. Use the exact variable names defined by the implementation once they are created.

| Setting | Used by | Notes |
|---|---|---|
| LLM API key | Backend | Keep private; never expose in the frontend |
| LLM model ID | Backend | Choose a model supported by the configured provider |
| Tavily API key | Backend | Needed for Tavily search |
| Supabase project URL | Frontend/backend as required | Public URL, but not an authorization mechanism |
| Supabase publishable/anon key | Frontend | Use with appropriate Auth and RLS policies |
| Supabase secret/service-role key | Backend only, if needed | Highly privileged; never expose to the browser |
| Supabase database connection settings | Backend/migrations | Store securely and use the appropriate connection method |
| Frontend origin / CORS allowlist | Backend | Restrict to expected deployment origins |

Use placeholders in `.env.example`; never include real credentials in source control.

## Testing and Evaluation

The planned tests will cover both correctness and security.

- **Unit tests:** chunking, metadata, schemas, graph routing, iteration limits, and citation IDs.
- **Retrieval tests:** known queries against known evidence, with Recall@K or MRR where labels are available.
- **Integration tests:** Supabase access, upload and ingestion, vector retrieval, and API behavior.
- **Security tests:** invalid tokens, cross-user document access, invalid file types, unsafe URLs, and oversized requests.
- **Failure tests:** model errors, search timeouts, empty retrieval, and malformed outputs.
- **End-to-end tests:** sign in, research a web question, upload a document, ask a document question, and inspect citations.

Evaluation should distinguish deterministic checks from human judgments about answer quality. An LLM judge may help with review, but it should not be treated as ground truth.

## Current Status

DeepCites is **under active development**. The technology choices and intended architecture are being established. Features listed as planned above should not be considered implemented until they have been built and verified.

The immediate priority is to deliver a small end-to-end research flow, then add authenticated document RAG, evidence checks, and testing.

## Future Improvements

Potential extensions after the core demo is stable:

- Better source ranking and source-diversity strategies.
- Stronger claim-level evidence verification.
- Improved PDF parsing and page-aware citations.
- Research history and exportable reports.
- More comprehensive evaluation datasets.
- Provider comparisons using the same benchmark questions.
- More detailed tracing and performance analysis.
- Additional document formats and retrieval filters.

---

## Project Philosophy

**Build the smallest reliable research loop first. Measure it. Then make it smarter.**

DeepCites is a learning project focused on making AI research workflows more useful, traceable, and testable—not on adding complexity for its own sake.
