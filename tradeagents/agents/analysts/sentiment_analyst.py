"""Sentiment analyst: one read from three pre-fetched sources.

The node fetches its sources before calling the model and puts them in the
prompt, so the model reports on data it was given rather than inventing posts:

  1. News headlines (Yahoo Finance)
  2. StockTwits messages (cashtag stream, with Bullish/Bearish tags)
  3. Reddit posts (r/wallstreetbets, r/stocks, r/investing)

The report is a ``SentimentReport`` through structured output where the
provider supports it, and free text otherwise, so the band/score/confidence
header reads the same across providers.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tradeagents.agents.context import get_language_instruction
from tradeagents.agents.schemas import SentimentReport, render_sentiment_report
from tradeagents.agents.structured import (
    bind_structured,
    invoke_structured_or_freetext,
)
from tradeagents.dataflows.vendors.reddit import fetch_reddit_posts
from tradeagents.dataflows.vendors.stocktwits import fetch_stocktwits_messages
from tradeagents.dataflows.vendors.yahoo.news import get_news


def _seven_days_back(trade_date: str) -> str:
    return (datetime.strptime(trade_date, "%Y-%m-%d") - timedelta(days=7)).strftime(
        "%Y-%m-%d"
    )


def create_sentiment_analyst(llm):
    structured_llm = bind_structured(llm, SentimentReport, "Sentiment Analyst")

    def sentiment_analyst_node(state):
        ticker = state["company_of_interest"]
        end_date = state["trade_date"]
        start_date = _seven_days_back(end_date)
        instrument_context = state.get("instrument_context", "")

        # Pre-fetch all three sources. Each fetcher degrades gracefully and
        # returns a string, so the model always sees either real data or a
        # clear placeholder; it can never invent a post.
        news_block = get_news(ticker, start_date, end_date)
        stocktwits_block = fetch_stocktwits_messages(
            ticker, limit=30, start_date=start_date, end_date=end_date
        )
        reddit_block = fetch_reddit_posts(
            ticker, start_date=start_date, end_date=end_date
        )

        system = _build_system_message(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            instrument_context=instrument_context,
            news_block=news_block,
            stocktwits_block=stocktwits_block,
            reddit_block=reddit_block,
        )
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )
        formatted = prompt.format_messages(messages=state["messages"])

        report_text = invoke_structured_or_freetext(
            structured_llm, llm, formatted, render_sentiment_report, "Sentiment Analyst"
        )

        return {
            "messages": [AIMessage(content=report_text)],
            "sentiment_report": report_text,
            "sender": "sentiment_analyst",
        }

    return sentiment_analyst_node


def _build_system_message(
    *,
    ticker: str,
    start_date: str,
    end_date: str,
    instrument_context: str,
    news_block: str,
    stocktwits_block: str,
    reddit_block: str,
) -> str:
    """Assemble the sentiment system message with the three structured data blocks."""
    return f"""You are a financial sentiment analyst. Produce a sentiment report on {ticker} covering {start_date} to {end_date}.

{instrument_context}

The data sources below have been pre-fetched for you. Analyze them. Do not invent posts or headlines that are not present.

### News headlines (Yahoo Finance)

<start_of_news>
{news_block}
<end_of_news>

### StockTwits messages

Each message carries a user-labeled sentiment tag (Bullish / Bearish / no-label).

<start_of_stocktwits>
{stocktwits_block}
<end_of_stocktwits>

### Reddit posts

<start_of_reddit>
{reddit_block}
<end_of_reddit>

## Analysis guidance

1. Read the StockTwits Bullish/Bearish ratio as a leading retail-sentiment
   signal. A 70/30 split is moderately bullish; ≥90/10 may indicate
   over-extension and contrarian risk; 50/50 is uncertainty. Sample size
   matters — base the read on the actual message count, not percentages alone.
2. Look for cross-source divergence. If news framing is bearish but retail is
   overwhelmingly bullish, that mismatch is itself a signal.
3. Judge Reddit posts by body content, not title alone.
4. Distinguish event from opinion. A news headline is an event; a social post
   is opinion. Weight them differently.
5. Identify recurring narrative themes — the topic that keeps coming up across
   sources is the dominant narrative.
6. Be honest about data limits. If a source returned an <unavailable> or
   placeholder block, say so explicitly in the confidence field and the
   narrative.
7. Past sentiment is not predictive. Frame the read as signal, not a price call.

## Output

Fill the structured output fields:
- **overall_band**: exactly one of Bullish / Mildly Bullish / Neutral / Mixed
  / Mildly Bearish / Bearish.
- **overall_score**: 0-10; 5 is neutral.
- **confidence**: low / medium / high.
- **narrative**: source-by-source breakdown, divergences, dominant themes,
  catalysts and risks, and a markdown summary table of key sentiment signals.
{get_language_instruction()}"""
