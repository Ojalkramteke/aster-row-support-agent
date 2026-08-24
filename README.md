# Aster & Row Support Agent

A reliable, grounded, and privacy-preserving customer support agent for Aster & Row, an ecommerce brand selling bags, drinkware, and travel accessories. Built for deterministic accuracy, multi-turn context retention, prompt-injection defense, and customer data privacy with zero external runtime dependencies.

---

## Demo

A 2–4 minute demonstration of the Aster & Row Support Agent:

[▶️ Watch the Aster & Row Support Agent Demo](https://drive.google.com/file/d/1ijXhlvLbgHGVatbJN1N-KshNni-5N-w8/view?usp=drive_link)

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [Environment Configuration](#environment-configuration)
- [Running the Agent](#running-the-agent)
  - [Terminal CLI Chat](#terminal-cli-chat)
  - [Local Web UI](#local-web-ui)
- [Running Tests](#running-tests)
- [Evaluation Suite](#evaluation-suite)
- [Baseline vs. Final Results](#baseline-vs-final-results)
- [Bug Diary](#bug-diary)
- [Safety, Privacy & Prompt Security](#safety-privacy--prompt-security)
- [Observability & Inspection](#observability--inspection)
- [Known Limitations](#known-limitations)
- [AI Coding Tools](#ai-coding-tools)
- [Demo](#demo)
- [Future Improvements](#future-improvements)
- [Submission Checklist](#submission-checklist)

---

## Overview

The Aster & Row Support Agent provides customer support by combining structured order data lookup with document-grounded policy retrieval:
1. **Authoritative Precedence**: Distinguishes current active policies (`01-returns-policy-current.md`) from legacy documents (`02-returns-policy-legacy.md`) and draft migration notes (`14-internal-content-migration-notes.md`).
2. **Conflict Awareness**: Detects genuine active source conflicts (e.g., product care guidance between `11-product-care.md` and `12-breeze-tumbler-product-card.md`) and recommends human review rather than silently picking a side.
3. **Safe Tool Execution**: Looks up orders via an isolated data tool (`data/orders.json`), normalizing diverse user phrasing (`ORD-1007`, `ord 1007`, `order 1006`, `ord    1000`) and suppressing stale delivery fields on cancelled or returned shipments.
4. **Data Privacy & Sanitization**: Enforces strict boundaries where internal warehouse notes, risk scores, and customer emails/addresses are never disclosed.
5. **Multi-Turn Memory**: Preserves session state for contextual follow-ups (*"When will it arrive?"*, *"What about Canada?"*) while prioritizing newly supplied order IDs over stale context.

> **System Approach**: The system implements **deterministic retrieval and response synthesis**. It relies on Python standard-library components, a custom TF-IDF retrieval indexer with metadata/authority weighting, and rule-grounded response synthesis. It does **not** call an external generative LLM API (such as OpenAI, Gemini, or Anthropic) at runtime and requires **no external API keys or vector databases**.

---

## Features

- **Grounded Policy Retrieval**: Retrieves relevant passages with document citations (file name and heading).
- **Multi-Source Grounding**: Correctly synthesizes policies across multiple documents (e.g., damaged-item 7-day exception on final-sale items).
- **Safe Abstention & Escalation**: Identifies uncertified product claims (e.g., vegan adhesives) and recommends human handoff without hallucinating facts.
- **Prompt Injection Defense**: Rejects instructions embedded inside retrieved migration notes or order warehouse fields attempting to override store policies or issue unapproved discounts.
- **Multi-Turn Session Retention**: Maintains conversational state across successive questions and safely resets upon user request (`exit`, `quit`, or "New Chat").
- **Minimal Local Web Interface**: Responsive WhatsApp-style UI served via Python's standard library with zero external frontend build dependencies.

---

## Architecture

The system follows a modular, deterministic pipeline:

```
                                  ┌────────────────────────┐
                                  │      User Message      │
                                  └───────────┬────────────┘
                                              │
                                              ▼
                                  ┌────────────────────────┐
                                  │     SupportAgent       │
                                  │    (src/app.py)        │
                                  └─────┬────────────┬─────┘
                                        │            │
             ┌──────────────────────────┘            └──────────────────────────┐
             ▼                                                                  ▼
┌─────────────────────────┐                                        ┌─────────────────────────┐
│     Order Pipeline      │                                        │      RAG Pipeline       │
│  (src/tools/order_      │                                        │  (src/retrieval/        │
│   lookup.py)            │                                        │   retriever.py)         │
├─────────────────────────┤                                        ├─────────────────────────┤
│ • Regex ID Normalizer   │                                        │ • Stopword Filtering    │
│ • Sanitization filter   │                                        │ • Synonym Expansion     │
│ • Status Precedence     │                                        │ • TF-IDF Ranked Scorer  │
│   (cancelled/shipped)   │                                        │ • Authority Boosting    │
└────────────┬────────────┘                                        └────────────┬────────────┘
             │                                                                  │
             └──────────────────────────┬───────────────────────────────────────┘
                                        │
                                        ▼
                          ┌───────────────────────────┐
                          │   Deterministic Synthesis │
                          │    (src/prompting.py)     │
                          ├───────────────────────────┤
                          │ • Source Citation Builder │
                          │ • Conflict Detection      │
                          │ • Safe Abstention Rules   │
                          │ • Prompt Security Filter  │
                          └─────────────┬─────────────┘
                                        │
                                        ▼
                          ┌───────────────────────────┐
                          │   Sanitized JSON Output   │
                          │  (response, handoff, src) │
                          └───────────────────────────┘
```

---

## Tech Stack

- **Core Language**: Python (Pure standard library)
- **External Dependencies**: None (Zero third-party packages required)
- **Retrieval Engine**: Custom TF-IDF indexer & ranked scorer with front-matter authority weighting and synonym expansion
- **Knowledge Base**: Markdown documents (`knowledge-base/*.md`) with YAML front matter
- **Order Store**: Mock JSON data store (`data/orders.json`)
- **Web Server**: Python standard library `http.server.ThreadingHTTPServer`
- **Web Frontend**: Vanilla HTML5, CSS3, JavaScript (no external build tools or frameworks)
- **Test & Evaluation Harness**: Deterministic Python test scripts (`run_app_tests.py`, `run_order_lookup_tests.py`, `run_retriever_tests.py`, `run_evaluation.py`)
- **Generative LLM / External APIs**: None (Fully deterministic local execution)

---

## Project Structure

```text
.
├── .env.example                       # Configuration example (PORT variable)
├── README.md                          # Project documentation and submission report
├── data/
│   ├── orders.json                    # Mock orders dataset
│   └── orders-data-dictionary.md      # Customer safety data dictionary
├── evaluation/
│   ├── visible-cases.json             # 15 supplied visible evaluation cases
│   ├── additional-cases.json          # 5 additional original evaluation cases
│   └── results.json                   # Automated evaluation run results
├── knowledge-base/                    # Active and legacy Markdown policies
│   ├── 01-returns-policy-current.md
│   ├── 02-returns-policy-legacy.md
│   ├── 03-final-sale-and-promotions.md
│   ├── 04-damaged-or-wrong-items.md
│   ├── 05-domestic-shipping.md
│   ├── 06-international-shipping.md
│   ├── 07-warranty.md
│   ├── 08-order-changes-and-cancellations.md
│   ├── 09-trailplus-membership.md
│   ├── 10-gift-cards-and-price-adjustments.md
│   ├── 11-product-care.md
│   ├── 12-breeze-tumbler-product-card.md
│   ├── 13-support-escalation.md
│   └── 14-internal-content-migration-notes.md
├── scripts/
│   ├── chat.py                        # Terminal CLI chat entry point
│   ├── run_ui.py                      # Local Web UI server launcher
│   ├── run_app_tests.py               # Application & multi-turn regression test runner
│   ├── run_order_lookup_tests.py      # Order lookup unit test runner
│   ├── run_retriever_tests.py         # Knowledge-base retriever test runner
│   ├── run_evaluation.py              # Behavioral evaluation suite runner
│   ├── debug_agent_outputs.py         # Utility script for inspecting raw agent outputs
│   └── inspect_kb.py                  # Utility script for inspecting indexed KB passages
├── src/
│   ├── app.py                         # SupportAgent orchestration and session management
│   ├── prompting.py                   # Response synthesis, citation formatting, and security
│   ├── session.py                     # Session state and conversation history container
│   ├── server.py                      # Threaded HTTP API server for Web UI
│   ├── eval/                          # Evaluation assertion engine and runner
│   │   ├── case_assertions.py
│   │   └── eval_runner.py
│   ├── retrieval/                     # Document chunking, indexing, and TF-IDF scoring
│   │   ├── indexer.py
│   │   └── retriever.py
│   ├── static/
│   │   └── index.html                 # Clean, responsive Web UI
│   └── tools/
│       └── order_lookup.py            # Sanitized order lookup tool
└── tests/
    ├── test_app.py                    # 19 application and multi-turn regression tests
    ├── test_order_lookup.py           # 11 order normalization and privacy unit tests
    └── test_retriever.py              # 11 retrieval ranking and metadata unit tests
```

---

## Setup & Installation

The project uses only the Python standard library and requires **no package installations** (no `pip install` or `requirements.txt`).

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Ojalkramteke/aster-row-support-agent.git
   cd aster-row-support-agent
   ```

2. **Verify Python**:
   ```bash
   python --version
   # Compatible with standard Python 3.9+
   ```

---

## Environment Configuration

- **No external API keys, tokens, or credentials are required.**
- The application optionally reads the `PORT` environment variable (defaults to `8000` if unset).
- Python's standard library does not automatically load `.env` files. You can configure `PORT` via your shell environment:

**PowerShell (Windows)**:
```powershell
$env:PORT=8080
python scripts/run_ui.py
```

**Bash / macOS / Linux**:
```bash
export PORT=8080
python scripts/run_ui.py
```

*(A [`.env.example`](.env.example) file is provided for reference).*

---

## Running the Agent

### Terminal CLI Chat
Start an interactive multi-turn terminal chat session:

```bash
python scripts/chat.py
```
- Accepts continuous user messages.
- Type `exit` or `quit` to exit the CLI application.

### Local Web UI
Launch the local web server:

```bash
python scripts/run_ui.py
```
Open **`http://localhost:8000`** in your browser.

- Features a WhatsApp-style interface with user and bot chat bubbles.
- Supports multi-turn conversations and typing indicators.
- Click **New Chat** to start a fresh conversation session with a new session ID.
- Typing `exit`, `quit`, or `end` returns a polite goodbye and resets the active conversation context while keeping the Python web server running.

---

## Running Tests

Execute the unit and regression test runners:

```bash
# Order lookup and field sanitization tests (11 tests)
python scripts/run_order_lookup_tests.py

# Knowledge-base indexing and retriever tests (11 tests)
python scripts/run_retriever_tests.py

# Core application and multi-turn regression tests (19 tests)
python scripts/run_app_tests.py
```

---

## Evaluation Suite

The evaluation harness evaluates agent behavior across 20 distinct scenarios (15 supplied visible cases + 5 original test cases in `evaluation/additional-cases.json`).

Run the evaluation suite:

```bash
python scripts/run_evaluation.py
```

Evaluation outputs are displayed in the terminal and written to [`evaluation/results.json`](evaluation/results.json), covering:
- **Retrieval & Precedence**: Required document citation matching (`01-returns-policy-current.md`, `09-trailplus-membership.md`).
- **Groundedness**: Substring assertions without hallucinations or policy fabrication.
- **Tool Use**: Order normalization across natural user phrasing and missing order ID handling.
- **Privacy**: Strict non-disclosure of internal notes and customer emails.
- **Handoff Recommendations**: Verifying `handoff: True` for active conflicts and unconfirmed materials.

---

## Baseline vs. Final Results

- **Baseline**: No formal numerical baseline score was recorded before the evaluation harness was implemented.
- **Development & Hardening**: During development, individual failures (e.g., stale ETAs, unhandled order variations, DOM manipulation issues) were systematically reproduced and fixed through regression testing.
- **Final Verified Evaluation**: **20 / 20 (100%)** passed across all 15 visible test cases and 5 additional test cases.

### Verified Results Breakdown
- **Visible Cases (15/15)**: All passed
- **Additional Cases (5/5)**: All passed
- **Total**: **20 / 20 (100%) passed**

---

## Bug Diary

### Bug 1: Order extraction failure causing stale session order leakage
- **Reproduction**: In a multi-turn conversation, look up `ORD-1005`, then ask: `"where is order 1006"`.
- **Root Cause**: The order ID extractor in `src/app.py` used `r"ord[-\s]?(\d{3,})"`, which only matched the literal letters `"ord"` followed directly by digits. In `"where is order 1006"`, the letter `'e'` in `"order"` caused extraction to return `None`. The fallback rule `if not order_id and re.search(r"\border\b", message): order_id = session.get_order_context()` then fetched the active session's previous order (`ORD-1005`) instead of extracting `1006`.
- **Fix**: Replaced regex with a multi-pattern extractor supporting `order 1006`, `order number 1006`, `status of 1006`, etc., ensuring explicit IDs in the current message always supersede previous session context.
- **Regression Test**: Added `test_order_whitespace_and_natural_variations()` in `tests/test_app.py`.

### Bug 2: Multiple whitespace in order prefix caused fallback to previous order
- **Reproduction**: Turn 1: `"where is ord 1004"`, Turn 2: `"where is ord    1000"`.
- **Root Cause**: The separator regex `[-\s_]?` matched at most one space. With multiple spaces (`"ord    1000"`), extraction failed and the follow-up rule `if not order_id and session.get_order_context() and re.search(r"where", message)` incorrectly returned the previous turn's `ORD-1004` instead of looking up `ORD-1000`.
- **Fix**: Updated prefix regex to `r"\b(?:ord(?:er)?)(?:[\s\-_#]+(?:number|no\.?|id|#)?)?[\s\-_#:]*(\d{3,})\b"` supporting arbitrary whitespace, and ensured explicit IDs update session context immediately (returning not-found if the ID is unknown rather than falling back to previous orders).
- **Regression Test**: Added `test_multiturn_order_override_vs_pronoun_reference()` in `tests/test_app.py`.

### Bug 3: "New Chat" button froze the web UI due to a detached DOM node
- **Reproduction**: In the localhost web UI, ask `"Where is order 1007?"`, click **New Chat**, then send `"Where is order 1006?"`.
- **Root Cause**: Clicking "New Chat" set `messagesArea.innerHTML = ...`, which recreated the HTML and deleted the original `typingIndicator` element. Subsequent messages called `messagesArea.insertBefore(row, typingIndicator)` referencing the detached DOM node, throwing an uncaught JavaScript `DOMException` and freezing message sending.
- **Fix**: Updated reset handler to selectively remove `.message-row` elements while preserving the `typingIndicator` DOM element, and upgraded the server to `ThreadingHTTPServer` for non-blocking concurrent connections.
- **Regression Test**: Verified via automated API test and manual UI reset flow.

### Bug 4: International shipping query for India returned generic unhelpful abstention
- **Reproduction**: Ask: `"Do you ship internationally to India?"`.
- **Root Cause**: The query keyword `"India"` was not mapped in `detect_topic` or `_expanded_terms`, causing retrieval to fall through to generic abstention rather than retrieving `06-international-shipping.md` (which explicitly states Aster & Row ships internationally only to Canada).
- **Fix**: Added `"india"` and `"internationally"` to topic detection and document ranking in `src/retrieval/retriever.py` and `src/prompting.py`. Synthesized a grounded response citing `06-international-shipping.md` stating Aster & Row ships only to Canada, shipping to India is not confirmed in the policy, and human confirmation is required (`handoff: True`).
- **Regression Test**: Verified via evaluation suite and live test queries.

---

## Safety, Privacy & Prompt Security

In this mock assignment implementation, safety and data privacy are enforced deterministically:

1. **Internal Notes & Private Fields**: `src/tools/order_lookup.py` explicitly strips `customer.name`, `customer.email`, `customer.shipping_address`, `internal.risk_score`, `internal.warehouse_note`, and `internal.support_tags` before returning order data.
2. **Cancelled/Returned Order Precedence**: Stale carrier, tracking, and estimated delivery dates are suppressed for cancelled or returned orders to prevent misleading customers.
3. **Prompt Injection Defense**: Explicit security filters in `src/prompting.py` prevent untrusted text in migration notes (`14-internal-content-migration-notes.md`) or internal warehouse instructions (`ORD-1005`) from overriding active policy or issuing unapproved discounts.
4. **System Prompt Protection**: Refuses requests to disclose hidden developer instructions, system prompts, or internal rules.

---

## Observability & Inspection

Rather than relying on a heavy external logging framework, the repository provides straightforward inspection mechanisms:
- **Session State Tracing**: View message history and active order context programmatically via `session.get_messages()` and `session.get_order_context()`.
- **Retrieval Scoring Inspection**: Inspect passage ranking scores, document metadata (`filename`, `heading`, `authoritative`), and extracted terms using `scripts/inspect_kb.py`.
- **Raw Agent Output Debugging**: Run `scripts/debug_agent_outputs.py` to inspect raw response payloads, tool execution flags, and handoff recommendations.
- **Evaluation Reporting**: `scripts/run_evaluation.py` outputs per-case results, pass/fail status, retrieved document citations, and tool call traces to `evaluation/results.json`.

---

## Known Limitations

- **Deterministic Keyword Retrieval**: TF-IDF retrieval with term expansion is highly predictable and lightweight, but lacks the generalized semantic flexibility of deep neural embeddings for complex paraphrased phrasing.
- **Static Knowledge Corpus**: Passages are indexed from local Markdown files at startup; dynamic real-time policy updates would require an incremental index manager.
- **Single-Node Local Web Server**: The Python standard library `ThreadingHTTPServer` is designed for local demonstration and testing rather than high-concurrency production deployments.
- **Mock Order Data Store**: Reads from a static JSON file (`data/orders.json`) with no write operations (cancellations or refunds are not executed live).
- **Authentication & Multi-Tenancy**: The application does not include user authentication, role-based access control, or live CRM ticketing integrations.

---

## AI Coding Tools

- **Tool Used**: Google Antigravity (Advanced Agentic AI Coding Assistant).
- **Tasks Performed**: Codebase navigation, test failure root-cause analysis, implementing deterministic scoring adjustments, developing regression tests, and documentation refinement.
- **Example of an Incomplete Suggestion**:
  During order-ID extraction refinement, an AI-generated suggestion proposed using `r"\bord[-\s_]?(\d{3,})\b"` with a single optional quantifier `?` for whitespace. While this handled single spaces (`"ord 1004"`), it failed on inputs with multiple spaces (`"ord    1000"`), which silently triggered the session fallback and returned the previous session's order. This was caught during manual edge-case testing and corrected with arbitrary whitespace handling `[\s\-_#:]*` and explicit session priority rules.

---

## Demo

A 2–4 minute demonstration of the Aster & Row Support Agent:

[▶️ Watch the Aster & Row Support Agent Demo](https://drive.google.com/file/d/1ijXhlvLbgHGVatbJN1N-KshNni-5N-w8/view?usp=drive_link)

### Demonstrated Scenarios:
- **Grounded Policy Retrieval**: Retrieves the standard return policy and cites the authoritative knowledge-base document (`01-returns-policy-current.md`).
- **International Shipping**: Correctly identifies that Aster & Row currently ships internationally only to Canada.
- **Shipping Information**: Retrieves the appropriate domestic shipping delivery timeframe without confusing it with TrailPlus membership benefits or return policies.
- **Multi-Turn Context**: Demonstrates contextual follow-up questions while maintaining the relevant conversation state.
- **Order Lookup**: Retrieves shipment and tracking information for `ORD-1007`.
- **Privacy Protection**: Refuses to disclose protected customer information such as email addresses.
- **Safe Conflict Handling**: Detects conflicting official Breeze Tumbler care information and escalates for human confirmation rather than inventing an answer.
- **Automated Evaluation**: Demonstrates the final evaluation suite with all 20 cases passing.

---

## Future Improvements

1. **Hybrid Semantic Retrieval**: Combine TF-IDF / BM25 with local sentence embeddings (e.g., MiniLM) for enhanced fuzzy question understanding.
2. **Helpdesk & Ticketing Integration**: Connect `handoff: True` escalations directly to customer support systems (e.g., Zendesk, Gorgias, Intercom).
3. **Transactional Order Actions**: Implement authenticated APIs allowing customers to initiate returns or cancel eligible unshipped orders.
4. **Multi-Language Support**: Expand topic extraction and date formatters to support multilingual customer queries.

---

## Submission Checklist

- [x] Complete source code in `src/` and `scripts/` (pure Python standard library)
- [x] 11 order lookup unit tests passing (`scripts/run_order_lookup_tests.py`)
- [x] 11 retriever unit tests passing (`scripts/run_retriever_tests.py`)
- [x] 19 core application regression tests passing (`scripts/run_app_tests.py`)
- [x] 20 / 20 evaluation cases passing (`scripts/run_evaluation.py`)
- [x] Comprehensive, truthful `README.md` and `.env.example`
- [x] Zero external credentials or API keys required
- [x] 2–4 minute demo video recorded and linked in Demo section
