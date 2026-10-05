"""News analyst: ticker-specific events and macro context."""

from __future__ import annotations

from pathlib import Path
from string import Template

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tradeagents.agents.context import get_language_instruction
from tradeagents.agents.tools import get_global_news, get_news

TOOLS = (get_news, get_global_news)

_PROMPT = Template(
    (Path(__file__).parent / "prompts" / "news_analyst.txt").read_text(encoding="utf-8")
)


def create_news_analyst(llm):
    bound_llm = llm.bind_tools(TOOLS)

    def news_analyst_node(state):
        asset_type = state.get("asset_type", "stock")
        asset_label = "company" if asset_type == "stock" else "asset"
        system = _PROMPT.substitute(
            ticker=state["company_of_interest"],
            trade_date=state["trade_date"],
            asset_label=asset_label,
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
            "news_report": report,
            "sender": "news_analyst",
        }

    return news_analyst_node
