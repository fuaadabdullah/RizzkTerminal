"""AI placeholder page."""

from __future__ import annotations

import os

from dash import html


def register():
    """Return an AI page renderer."""

    def render(_: str) -> html.Div:
        if not os.getenv("OPENAI_API_KEY"):
            return html.Div(
                [
                    html.H3("AI Assistant"),
                    html.P(
                        "OpenAI API key not configured. Add OPENAI_API_KEY to the environment to enable AI features.",
                    ),
                ]
            )
        return html.Div([html.P("AI integrations coming soon.")])

    return render
