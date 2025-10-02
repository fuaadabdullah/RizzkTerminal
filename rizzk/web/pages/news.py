"""News page rendering."""

from __future__ import annotations

from dash import html
from flask_caching import Cache

from rizzk.core.news import fetch_news


def register(cache: Cache):
    """Register news helpers."""

    @cache.memoize(timeout=600)
    def _load_news() -> list[dict[str, str]]:
        try:
            return fetch_news(limit=40)
        except Exception as exc:  # pragma: no cover - defensive for network issues
            return [{"source": "Error", "title": str(exc), "link": ""}]

    def render(_: str) -> html.Div:
        items = _load_news()
        if not items:
            return html.Div([html.P("No news available.")])
        return html.Div(
            [
                html.Ul(
                    [
                        html.Li(
                            html.A(
                                f"{item['source']}: {item['title']}",
                                href=item["link"] or "#",
                                target="_blank",
                                rel="noopener noreferrer",
                            )
                        )
                        for item in items
                    ],
                    className="news-list",
                )
            ]
        )

    return render
