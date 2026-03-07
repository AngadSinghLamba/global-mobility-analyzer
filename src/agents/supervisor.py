"""
Global Mobility Analyzer — Supervisor Agent

LangGraph router that dispatches user input to the correct
visa-specific subgraph based on target_country.

Architecture: Multi-Agent Supervisor with Agentic RAG (Option B)
"""

from __future__ import annotations

import logging

from src.shared.state import GraphState, TargetCountry

logger = logging.getLogger(__name__)


def route_to_workflow(state: GraphState) -> str:
    """
    Conditional edge function for the LangGraph Supervisor.

    Routes to the correct visa subgraph based on target_country.

    Returns:
        Node name string for the next subgraph.
    """
    country = state.get("target_country")

    routing_map = {
        TargetCountry.UK: "uk_skilled_worker",
        TargetCountry.DE: "de_opportunity_card",
        TargetCountry.CA: "ca_express_entry",
    }

    if country not in routing_map:
        logger.error("Unsupported target country: %s", country)
        raise ValueError(f"Unsupported target country: {country}")

    destination = routing_map[country]
    logger.info("Supervisor routing to: %s", destination)
    return destination


# TODO (Sprint 1): Build the full StateGraph with compiled subgraphs
# from langgraph.graph import StateGraph, END
# graph = StateGraph(GraphState)
# graph.add_conditional_edges("supervisor", route_to_workflow, {...})
