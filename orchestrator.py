from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END

from sanitization import sanitization_agent
from agents.claim_agent import claim_agent
from agents.search_agent import search_agent
from agents.verification_agent import verification_agent


class GraphState(TypedDict):
    claim:             str
    claims:            List[str]
    evidence:          List[dict]
    results:           List[dict]
    sentence_analysis: List[dict]
    triplets:          List[dict]
    timeline:          List[dict]
    error:             Optional[str]


def build_graph():
    workflow = StateGraph(GraphState)

    workflow.add_node("sanitize", sanitization_agent)
    workflow.add_node("claim",    claim_agent)
    workflow.add_node("search",   search_agent)
    workflow.add_node("verify",   verification_agent)

    workflow.set_entry_point("sanitize")
    workflow.add_edge("sanitize", "claim")
    workflow.add_edge("claim",    "search")
    workflow.add_edge("search",   "verify")
    workflow.add_edge("verify",   END)

    return workflow.compile()


graph = build_graph()