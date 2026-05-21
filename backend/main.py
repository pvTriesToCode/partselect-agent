import sys
import asyncio
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import asyncio
import json
import queue
import threading
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk, ToolMessage
from agent.graph import compiled_graph

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    history: Optional[list] = []


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        messages = []
        for item in request.history:
            role = item.get("role", "")
            content = item.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))

        messages.append(HumanMessage(content=request.message))

        result_container = {}

        def run_graph():
            import sys
            if sys.platform == "win32":
                loop = asyncio.ProactorEventLoop()
            else:
                loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result_container["result"] = compiled_graph.invoke({"messages": messages})
            except Exception as e:
                result_container["error"] = str(e)
            finally:
                loop.close()

        thread = threading.Thread(target=run_graph)
        thread.start()
        thread.join()

        if "error" in result_container:
            return {"error": result_container["error"]}

        result = result_container["result"]

        last_message = result["messages"][-1]
        response_text = last_message.content if hasattr(last_message, "content") else str(last_message)

        updated_history = list(request.history) + [
            {"role": "user", "content": request.message},
            {"role": "assistant", "content": response_text},
        ]

        return {"response": response_text, "history": updated_history}
    except Exception as e:
        return {"error": str(e)}


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    messages = []
    for item in request.history:
        role = item.get("role", "")
        content = item.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))

    messages.append(HumanMessage(content=request.message))

    chunk_queue = queue.Queue()

    def run_stream():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            for chunk in compiled_graph.stream({"messages": messages}, stream_mode="messages"):
                chunk_queue.put(chunk)
        except Exception as e:
            chunk_queue.put(e)
        finally:
            chunk_queue.put(None)
            loop.close()

    thread = threading.Thread(target=run_stream)
    thread.start()

    def generate():
        full_response = []
        tool_results = []
        while True:
            chunk = chunk_queue.get()
            if chunk is None:
                break
            if isinstance(chunk, Exception):
                yield f"data: {json.dumps({'error': str(chunk)})}\n\n"
                return
            if isinstance(chunk[0], AIMessageChunk) and chunk[0].content:
                full_response.append(chunk[0].content)
                yield f"data: {json.dumps({'token': chunk[0].content})}\n\n"
            if isinstance(chunk[0], ToolMessage):
                try:
                    data = json.loads(chunk[0].content)
                    tool_results.append(data)
                except Exception:
                    pass

        metadata = {"type": None}
        for result in tool_results:
            if "part_id" in result and "price" in result:
                metadata = {
                    "type": "part",
                    "part_number": result.get("part_id", ""),
                    "part_name": result.get("part_name", ""),
                    "price": result.get("price", ""),
                    "availability": result.get("availability", ""),
                    "image_url": result.get("image_url", ""),
                    "video_url": result.get("video_url", ""),
                    "video_thumbnail_url": result.get("video_thumbnail_url", ""),
                    "product_url": result.get("product_url", ""),
                }
                break
            if "compatible" in result and "model_number" in result:
                metadata = {
                    "type": "compatibility",
                    "compatible": result.get("compatible", False),
                    "part_number": result.get("part_number", ""),
                    "model_number": result.get("model_number", ""),
                    "model_name": result.get("model_name", ""),
                    "message": result.get("message", ""),
                }
                break
            if "video_thumbnail_url" in result and result.get("video_thumbnail_url"):
                metadata = {
                    "type": "repair",
                    "video_url": result.get("video_url", ""),
                    "video_thumbnail_url": result.get("video_thumbnail_url", ""),
                    "guide_url": result.get("guide_url", ""),
                    "symptom_matched": result.get("symptom_matched", ""),
                }
                break

        updated_history = list(request.history) + [
            {"role": "user", "content": request.message},
            {"role": "assistant", "content": "".join(full_response)},
        ]
        yield f"data: {json.dumps({'metadata': metadata})}\n\n"
        yield f"data: {json.dumps({'done': True, 'history': updated_history})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
