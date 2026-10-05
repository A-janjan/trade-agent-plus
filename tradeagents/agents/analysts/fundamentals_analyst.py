"""Fundamentals analyst: balance sheet, income statement, cash flow."""

from __future__ import annotations

from pathlib import Path
from string import Template

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tradeagents.agents.context import get_language_instruction
from tradeagents.agents.tools import (
    get_balance_sheet,
    get_cashflow,
    get_fundamentals,
    get_income_statement,
)

TOOLS = (get_fundamentals, get_balance_sheet, get_cashflow, get_income_statement)

_PROMPT = Template(
    (Path(__file__).parent / "prompts" / "fundamentals_analyst.txt").read_text(
        encoding="utf-8"
    )
)


def create_fundamentals_analyst(llm):
    bound_llm = llm.bind_tools(TOOLS)

    def fundamentals_analyst_node(state):
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
        response = bound_llm.invoke(prompt.format_messages(messages=state["messages"]))

        report = "" if response.tool_calls else response.content
        return {
            "messages": [response],
            "fundamentals_report": report,
            "sender": "fundamentals_analyst",
        }

    return fundamentals_analyst_node
