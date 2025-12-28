"""Research orchestrator that manages different research providers."""

from __future__ import annotations

import asyncio

import forecasting_tools
import requests
from asknews_sdk import AskNewsSDK
from langfuse import observe

from castor.config.settings import settings
from castor.exceptions import ResearchError


class Researcher:
    """Researches a question using available providers."""

    def __init__(self):
        """Initialize the research orchestrator."""
        self.provider = self._select_provider()

    def _select_provider(self) -> str:
        """Select the best available research provider based on API keys."""
        if settings.asknews_client_id and settings.asknews_secret:
            return "asknews"
        elif settings.exa_api_key:
            return "exa"
        elif settings.perplexity_api_key:
            return "perplexity"
        else:
            return "none"

    @observe(as_type="span", name="research")
    def research(self, question: str) -> str:
        """Conduct research on a question.

        Args:
            question: The question to research.

        Returns:
            Research findings as a string.
        """
        if self.provider == "asknews":
            return self._call_asknews(question)
        elif self.provider == "exa":
            return self._call_exa_smart_searcher(question)
        elif self.provider == "perplexity":
            return self._call_perplexity(question)
        else:
            return "No research done"

    def _call_perplexity(self, question: str) -> str:
        """Use Perplexity to research a question.

        Args:
            question: The question to research.

        Returns:
            Research findings.

        Raises:
            ResearchError: If the API call fails.
        """
        url = "https://api.perplexity.ai/chat/completions"
        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {settings.perplexity_api_key}",
            "content-type": "application/json",
        }
        payload = {
            "model": "llama-3.1-sonar-huge-128k-online",
            "messages": [
                {
                    "role": "system",
                    "content": """
                You are an assistant to a superforecaster.
                The superforecaster will give you a question they intend to forecast on.
                To be a great assistant, you generate a concise but detailed rundown of the most relevant news, including if the question would resolve Yes or No based on current information.
                You do not produce forecasts yourself.
                """,
                },
                {
                    "role": "user",
                    "content": question,
                },
            ],
        }
        response = requests.post(url=url, json=payload, headers=headers)
        if not response.ok:
            raise ResearchError(
                f"Perplexity API call failed: {response.status_code} {response.text}"
            )
        content = response.json()["choices"][0]["message"]["content"]
        return content

    def _call_exa_smart_searcher(self, question: str) -> str:
        """Use Exa to research a question.

        Args:
            question: The question to research.

        Returns:
            Research findings.
        """
        if settings.openai_api_key is None:
            searcher = forecasting_tools.ExaSearcher(
                include_highlights=True,
                num_results=10,
            )
            highlights = asyncio.run(
                searcher.invoke_for_highlights_in_relevance_order(question)
            )
            prioritized_highlights = highlights[:10]
            combined_highlights = ""
            for i, highlight in enumerate(prioritized_highlights):
                combined_highlights += f'[Highlight {i+1}]:\nTitle: {highlight.source.title}\nURL: {highlight.source.url}\nText: "{highlight.highlight_text}"\n\n'
            response = combined_highlights
        else:
            searcher = forecasting_tools.SmartSearcher(
                temperature=0,
                num_searches_to_run=2,
                num_sites_per_search=10,
            )
            prompt = (
                "You are an assistant to a superforecaster. The superforecaster will give "
                "you a question they intend to forecast on. To be a great assistant, you generate "
                "a concise but detailed rundown of the most relevant news, including if the question "
                "would resolve Yes or No based on current information. You do not produce forecasts yourself."
                f"\n\nThe question is: {question}"
            )
            response = asyncio.run(searcher.invoke(prompt))
            assert response is not None

        return response

    def _call_asknews(self, question: str) -> str:
        """Use AskNews to research a question.

        Args:
            question: The question to research.

        Returns:
            Research findings formatted as a string.
        """
        ask = AskNewsSDK(
            client_id=settings.asknews_client_id,
            client_secret=settings.asknews_secret,
            scopes=set(["news"]),
        )

        # get the latest news related to the query (within the past 48 hours)
        hot_response = ask.news.search_news(
            query=question,
            n_articles=6,
            return_type="both",
            strategy="latest news",
        )

        # get context from the "historical" database
        historical_response = ask.news.search_news(
            query=question,
            n_articles=10,
            return_type="both",
            strategy="news knowledge",
        )

        hot_articles = hot_response.as_dicts
        historical_articles = historical_response.as_dicts
        formatted_articles = "Here are the relevant news articles:\n\n"

        if hot_articles:
            hot_articles = [article.__dict__ for article in hot_articles]
            hot_articles = sorted(hot_articles, key=lambda x: x["pub_date"], reverse=True)

            for article in hot_articles:
                pub_date = article["pub_date"].strftime("%B %d, %Y %I:%M %p")
                formatted_articles += f"**{article['eng_title']}**\n{article['summary']}\nOriginal language: {article['language']}\nPublish date: {pub_date}\nSource:[{article['source_id']}]({article['article_url']})\n\n"

        if historical_articles:
            historical_articles = [article.__dict__ for article in historical_articles]
            historical_articles = sorted(
                historical_articles, key=lambda x: x["pub_date"], reverse=True
            )

            for article in historical_articles:
                pub_date = article["pub_date"].strftime("%B %d, %Y %I:%M %p")
                formatted_articles += f"**{article['eng_title']}**\n{article['summary']}\nOriginal language: {article['language']}\nPublish date: {pub_date}\nSource:[{article['source_id']}]({article['article_url']})\n\n"

        if not hot_articles and not historical_articles:
            formatted_articles += "No articles were found.\n\n"
            return formatted_articles

        return formatted_articles
