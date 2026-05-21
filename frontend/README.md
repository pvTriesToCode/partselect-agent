# PartSelect Chat Agent — Frontend

React chat interface for the PartSelect AI assistant, with SSE streaming and rich part/repair cards.

## Overview

This is a Create React App frontend that streams responses token-by-token from the FastAPI backend via Server-Sent Events. It renders assistant messages as markdown and attaches rich UI cards — PartCards and VideoCards — alongside relevant messages based on metadata returned in the SSE stream. The UI uses PartSelect's teal and amber brand colors throughout.

## Tech Stack

- React 18 (Create React App)
- react-markdown + remark-gfm for markdown rendering
- SSE via native `fetch` ReadableStream (no external SSE library)

## Project Structure

```
frontend/
  src/
    api/api.js          — SSE fetch, conversation history management
    components/
      ChatWindow.js     — main chat UI, streaming, loading state
      ChatWindow.css    — styles and responsive breakpoints
      PartCard.js       — part image, price, buy button, video thumbnail
      PartCard.css
      VideoCard.js      — YouTube thumbnail, repair guide link
      VideoCard.css
  public/
    partselect-logo.png — PartSelect logo used in header and as favicon
```

## Key Components

### ChatWindow.js

Manages the full chat lifecycle. Messages are stored as a list alongside a parallel `cardMetadata` array keyed by message index — when metadata arrives for message N, the card for that index is set and rendered below the message bubble. Streaming is handled via `onToken` and `onMetadata` callbacks passed into `getAIMessage`. While a tool call is running, `isLoading` is true and a cycling array of loading messages rotates every 1.5 seconds via `setInterval` to give feedback during the 8–30s tool execution window. The input and send button are disabled during loading.

### api.js

Holds a module-level `conversationHistory` array that persists across calls within a session. On each send, the user message is appended to history and the full list is POSTed to `/chat/stream`. The response body is read as a `ReadableStream`, decoded line by line. Each `data: {"token": "..."}` event calls `onToken` with the accumulated partial content so far. A `data: {"metadata": {...}}` event calls `onMetadata` to attach card data. A `data: {"done": [...]}` event replaces `conversationHistory` with the updated list returned by the backend.

### PartCard.js

Renders when `metadata.type === "part"`. Displays the part image, name, and part number, followed by price and an availability badge (green for in-stock, grey otherwise). A buy button links directly to the part's PartSelect product page. If `metadata.video_url` is set, a YouTube thumbnail is shown below the part details with a play icon overlay.

### VideoCard.js

Renders when `metadata.type === "repair"`. Shows a YouTube thumbnail generated from the video ID with a play button overlay, a symptom label, and a link to the full PartSelect repair guide page.

## Streaming Architecture

1. `ChatWindow` calls `getAIMessage(input, onToken, onMetadata)`
2. `api.js` POSTs to `/chat/stream` and opens the response as a `ReadableStream`
3. Each `data: {"token": "..."}` event fires `onToken` with the cumulative partial string → the last message in state is updated in place, rendering tokens as they arrive
4. A `data: {"metadata": {...}}` event fires `onMetadata` → stored in `cardMetadata[assistantIndex]`, which triggers the appropriate card to appear below the message
5. A `data: {"done": [...]}` event writes the completed conversation back to `conversationHistory` for the next request

## Branding

- **Primary:** `#337778` (teal) — header border, user bubble, send button, assistant message accent
- **Accent:** `#F5A623` (amber) — box shadows, hover states
- **Layout:** centered at 70% width, capped at 900px max-width
- **Responsive breakpoints:** 1024px (85% width), 768px (95% width), 480px (100% width with padding)

## Running

```bash
npm install
npm start
```

Opens at [http://localhost:3000](http://localhost:3000). Requires the backend running at `http://localhost:8000`.
