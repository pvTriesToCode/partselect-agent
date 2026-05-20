import sys
import asyncio
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import asyncio
import threading
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from langchain_core.messages import HumanMessage, AIMessage
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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
