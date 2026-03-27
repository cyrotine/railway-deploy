from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END

from sanitization import sanitization_agent
from agents.claim_agent import claim_agent
from agents.search_agent import search_agent
from agents.verification_agent import verification_agent
from agents.linguistic_agent import linguistic_agent
from agents.triplet_agent import triplet_agent


class GraphState(TypedDict):
    claim:    str
    claims:   List[str]
    evidence: List[dict]
    results:  List[dict]
    linguistic: dict
    triplets: List[dict]
    error:    Optional[str]


def build_graph():
    workflow = StateGraph(GraphState)
    workflow.add_node("sanitize",   sanitization_agent)
    workflow.add_node("linguistic", linguistic_agent)
    workflow.add_node("claim",      claim_agent)
    workflow.add_node("search",     search_agent)
    workflow.add_node("triplet",    triplet_agent)
    workflow.add_node("verify",     verification_agent)

    workflow.set_entry_point("sanitize")
    workflow.add_edge("sanitize",   "linguistic")
    workflow.add_edge("linguistic", "claim")
    workflow.add_edge("claim",      "search")
    workflow.add_edge("search",     "triplet")
    workflow.add_edge("triplet",    "verify")
    workflow.add_edge("verify",     END)
    return workflow.compile()


graph = build_graph()