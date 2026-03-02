from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agent.nodes import (
    analyze_round_node,
    finalize_node,
    generate_initial_questions_node,
    generate_next_questions_node,
    route_after_analyze,
)
from app.agent.state import AgentState


class ChecklistGraphService:
    def __init__(self, llm_service, portrait_service):
        self.llm_service = llm_service
        self.portrait_service = portrait_service
        self._start_graph = self._build_start_graph()
        self._round_graph = self._build_round_graph()

    def _build_start_graph(self):
        graph = StateGraph(AgentState)

        async def _initial(state):
            return await generate_initial_questions_node(state, self.llm_service)

        graph.add_node("generate_initial_questions", _initial)
        graph.add_edge(START, "generate_initial_questions")
        graph.add_edge("generate_initial_questions", END)
        return graph.compile()

    def _build_round_graph(self):
        graph = StateGraph(AgentState)

        async def _analyze(state):
            return await analyze_round_node(state, self.llm_service)

        async def _next(state):
            return await generate_next_questions_node(state, self.llm_service)

        async def _finalize(state):
            return await finalize_node(state, self.llm_service, self.portrait_service)

        graph.add_node("analyze_round", _analyze)
        graph.add_node("generate_next_questions", _next)
        graph.add_node("finalize", _finalize)

        graph.add_edge(START, "analyze_round")
        graph.add_conditional_edges(
            "analyze_round",
            route_after_analyze,
            {
                "next_round": "generate_next_questions",
                "finalize": "finalize",
            },
        )
        graph.add_edge("generate_next_questions", END)
        graph.add_edge("finalize", END)
        return graph.compile()

    async def start(self, state: AgentState) -> AgentState:
        return await self._start_graph.ainvoke(state)

    async def advance(self, state: AgentState) -> AgentState:
        return await self._round_graph.ainvoke(state)
