# PartSelect Chat Agent — Backend

FastAPI + LangGraph backend that scrapes PartSelect.com in real time to answer refrigerator and dishwasher parts questions.

## Overview

The backend is a stateless FastAPI service — conversation history is sent by the client on every request, so no session state is stored server-side. Each request invokes a two-node LangGraph graph: an agent node backed by Gemini 2.5 Flash decides which tool to call, and a tool node executes it. Tools scrape PartSelect.com live via Playwright (chromium) to return real-time part data. Repair guide lookup uses ChromaDB semantic search first, falling back to live scraping if no close match is found.

## Tech Stack

| Component  | Technology |
|------------|------------|
| Framework  | FastAPI + uvicorn |
| Agent      | LangGraph + Gemini 2.5 Flash |
| Scraping   | Playwright (chromium) + playwright-stealth |
| Vector DB  | ChromaDB PersistentClient |
| LLM client | langchain-google-genai |

## Project Structure

```
backend/
  main.py                 — FastAPI app, /health, /chat, /chat/stream
  agent/
    graph.py              — LangGraph StateGraph, tool wrappers (@tool)
    state.py              — AgentState TypedDict
    prompts.py            — system prompt
    tools/
      search.py           — search_parts
      part_details.py     — get_part_details
      compatibility.py    — check_compatibility
      repair_guide.py     — get_repair_guide
      model_parts.py      — get_model_parts
  data/
    vector_store.py       — ChromaDB init, add_repair_guide, search_repair_guides
    seed.py               — scrapes and seeds repair guides into ChromaDB
  requirements.txt
  chromadb_data/          — persisted ChromaDB files (gitignored)
```

## API Endpoints

### GET /health

Returns `{"status": "ok"}`. Used to verify the server is up.

### POST /chat

Synchronous endpoint. Runs the full LangGraph graph in a dedicated thread (required on Windows — see note below) and waits for completion.

**Request:**
```json
{ "message": "string", "history": [{"role": "user"|"assistant", "content": "string"}] }
```

**Response:**
```json
{ "response": "string", "history": [...] }
```

### POST /chat/stream

SSE streaming endpoint. Runs the graph in a background thread and feeds chunks into a `queue.Queue`. The `generate()` generator reads from the queue and yields SSE events:

| Event | Payload | When |
|-------|---------|------|
| `data: {"token": "..."}` | One LLM output token | Per `AIMessageChunk` |
| `data: {"metadata": {...}}` | Structured tool result for card rendering | After stream ends |
| `data: {"done": true, "history": [...]}` | Updated conversation history | Final event |

Metadata shape depends on the tool result: `type: "part"` for part details, `type: "repair"` for repair guides, `type: "compatibility"` for compatibility checks.

## The 5 Tools

### search_parts

```python
async def search_parts(query: str, appliance_filter: str) -> dict
```

Navigates to `https://www.partselect.com/{Refrigerator|Dishwasher}-Parts.htm?SearchTerm={query}` and scrapes up to 8 result cards. Key selectors: `div.nf__part.mb-3` (cards), `a.nf__part__detail__title` (name + href), `div.mt-sm-2.price` (price). Part numbers are extracted from the href via `re.search(r'PS\d+', href)`. Returns `results`, `count`, `query`, `appliance`.

### get_part_details

```python
async def get_part_details(part_number: str) -> dict
```

Navigates to `https://www.partselect.com/api/search/?searchterm={part_number}` which redirects to the canonical product page. Scrapes: `span[itemprop='productID']` (part ID), `span.js-partPrice` (price), `span[itemprop='availability']` (availability), `div[itemprop="description"]` (description), `div.d-flex p` nth 0/1 (install difficulty/time), `li.mb-1` within symptoms and product-type sections, `img[itemprop=image]` (image), `div[data-yt-init]` (YouTube video ID). Returns the full part dict including `video_url` and `video_thumbnail_url` derived from the video ID.

### check_compatibility

```python
async def check_compatibility(part_number: str, model_number: str) -> dict
```

Navigates to `https://www.partselect.com/Models/{model_number}/Parts/`, confirms the model exists by reading the `h1`, then checks `part_number in page.content()`. String search is used because the PartSelect compatibility API returns 403 for unauthenticated requests. Returns `compatible` (bool), `message`, `model_name`, `model_url`.

### get_repair_guide

```python
async def get_repair_guide(symptom: str, appliance_type: str) -> dict
```

Two-phase lookup. **Phase 1:** queries ChromaDB (`search_repair_guides`) for the closest pre-seeded guide; uses it if `distance < 1.3`. **Phase 2 (fallback):** navigates to `https://www.partselect.com/Repair/{Refrigerator|Dishwasher}/`, scrapes `.symptom-list a` entries, and substring-matches the symptom string. Once a guide URL is resolved, scrapes the guide page for parts (`div.repair__intro a.js-scrollTrigger`) and a YouTube video ID (`div[data-yt-init]`). Returns `symptom_matched`, `parts`, `video_url`, `video_thumbnail_url`, `guide_url`, `source` (`"vector_db"` or `"live"`).

### get_model_parts

```python
async def get_model_parts(model_number: str, search_term: str = "") -> dict
```

Navigates to `https://www.partselect.com/Models/{model_number}/Parts/` — or `?SearchTerm={search_term}` when a search term is provided — and scrapes up to 12 part cards (`div.mega-m__part`). Key selectors: `a.mega-m__part__name` (title), `a.mega-m__part__img` (href → URL + PS number), `div.mega-m__part__price` (price), `div.mega-m__part__avlbl span` (availability). Returns `model_number`, `model_name`, `parts`, `count`, `model_url`.

## ChromaDB

- **Collection:** `repair_guides`
- **Documents:** 21 total — 12 refrigerator symptoms + 9 dishwasher symptoms
- **Seeded from:** `partselect.com/Repair/Refrigerator/` and `partselect.com/Repair/Dishwasher/`
- **Semantic matching:** maps colloquial input (e.g. "ice maker not working") to stored guide titles (e.g. "Ice maker not making ice")
- **Distance threshold:** 1.3 — hits above this score fall through to live scraping
- **Reseed:** `python -m data.seed` from the `backend/` directory

## Windows-Specific Notes

`main.py` sets `asyncio.WindowsProactorEventLoopPolicy()` at module level before any other imports:

```python
import sys, asyncio
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
```

Without this, Playwright cannot create subprocess handles from worker threads on Windows and raises a `NotImplementedError` at runtime. This line is harmless on Mac/Linux where the standard policy already supports subprocesses; it can be left in place for cross-platform deployments.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GOOGLE_API_KEY` | Google AI Studio key — used by `langchain-google-genai` to call Gemini 2.5 Flash |
| `ENVIRONMENT` | `development` or `production` (optional, not currently gated) |

Create `backend/.env`:
```
GOOGLE_API_KEY=your_key_here
```

## Setup

```bash
pip install -r requirements.txt
playwright install chromium
python -m data.seed
uvicorn main:app --reload --port 8000
```
