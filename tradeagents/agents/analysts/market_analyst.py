"""Market analyst: technical read of the instrument.

The node is a single step in a ReAct loop. It either emits tool calls (and
LangGraph routes to the tool node, which routes back here) or emits the final
report. The analyst factory binds the tools once so every call reuses the same
bound model.
"""

from __future__ import annotations

from pathlib import Path
from string import Template

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tradeagents.agents.context import get_language_instruction
from tradeagents.agents.tools import get_indicators, get_stock_data

# The tools this analyst is offered. Its graph tool-node is built from the same
# tuple (see graph/setup.py), so the two never drift.
TOOLS = (get_stock_data, get_indicators)

_PROMPT = Template(
    (Path(__file__).parent / "prompts" / "market_analyst.txt").read_text(
        encoding="utf-8"
    )
)


def create_market_analyst(llm):
    """Return a market-analyst node bound to ``llm``."""
    bound_llm = llm.bind_tools(TOOLS)

    def market_analyst_node(state):
        system = _PROMPT.substitute(
            ticker=state["company_of_interest"],
            trade_date=state["trade_date"],
            instrument_context=state.get("instrument_context", ""),
            language_instruction=get_language_instruction(),
        )
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )
        messages = prompt.format_messages(messages=state["messages"])
        response = bound_llm.invoke(messages)

        # A tool-calling response is a work-in-progress turn: the graph routes
        # to the tool node and back. Only a no-tool-call response is the report.
        report = "" if response.tool_calls else response.content

        return {
            "messages": [response],
            "market_report": report,
            "sender": "market_analyst",
        }

    return market_analyst_node
