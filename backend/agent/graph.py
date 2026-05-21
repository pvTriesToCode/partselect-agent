import os
import asyncio
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from agent.state import AgentState
from agent.prompts import SYSTEM_PROMPT
from agent.tools.search import search_parts
from agent.tools.part_details import get_part_details
from agent.tools.compatibility import check_compatibility
from agent.tools.repair_guide import get_repair_guide
from agent.tools.model_parts import get_model_parts

load_dotenv()


@tool
def search_parts_tool(query: str, appliance_filter: str) -> dict:
    """Search for refrigerator or dishwasher parts on PartSelect.

    Args:
        query: Search terms describing the part needed
        appliance_filter: Must be 'refrigerator' or 'dishwasher'

    Returns:
        dict with results list, count, query, and appliance fields
    """
    return asyncio.run(search_parts(query, appliance_filter))


@tool
def get_part_details_tool(part_number: str) -> dict:
    """Get detailed information about a specific part by its part number.

    Args:
        part_number: The PS part number (e.g. PS11752778)

    Returns:
        dict with part_name, price, availability, symptoms, and other details
    """
    return asyncio.run(get_part_details(part_number))


@tool
def check_compatibility_tool(part_number: str, model_number: str) -> dict:
    """Check if a part is compatible with a specific appliance model.

    Args:
        part_number: The PS part number (e.g. PS11752778)
        model_number: The appliance model number (e.g. WDT780SAEM1)

    Returns:
        dict with compatible bool, message, model_name, model_url
    """
    return asyncio.run(check_compatibility(part_number, model_number))


@tool
def get_repair_guide_tool(symptom: str, appliance_type: str) -> dict:
    """Get a repair guide for a refrigerator or dishwasher symptom.

    Args:
        symptom: Description of the problem (e.g. 'ice maker not working')
        appliance_type: Must be 'refrigerator' or 'dishwasher'

    Returns:
        dict with symptom_matched, parts, video_url, guide_url,
        ai_disclaimer and other repair guide details
    """
    return asyncio.run(get_repair_guide(symptom, appliance_type))


@tool
def get_model_parts_tool(model_number: str, search_term: str = "") -> dict:
    """Get all parts for a specific appliance model number, optionally filtered by search term.

    Args:
        model_number: The appliance model number (e.g. WDT780SAEM1)
        search_term: Optional part description to search within the model's parts (e.g. 'heating element', 'door seal')

    Returns:
        dict with model_name, parts list, count, and model_url
    """
    return asyncio.run(get_model_parts(model_number, search_term))


tools = [search_parts_tool, get_part_details_tool, check_compatibility_tool, get_repair_guide_tool, get_model_parts_tool]

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
)

llm_with_tools = llm.bind_tools(tools)


def agent_node(state: AgentState) -> dict:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


def should_continue(state: AgentState) -> str:
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tool_node"
    return END


tool_node = ToolNode(tools=tools)

graph = StateGraph(AgentState)
graph.add_node("agent_node", agent_node)
graph.add_node("tool_node", tool_node)

graph.add_edge(START, "agent_node")
graph.add_conditional_edges("agent_node", should_continue, {"tool_node": "tool_node", END: END})
graph.add_edge("tool_node", "agent_node")

compiled_graph = graph.compile()
