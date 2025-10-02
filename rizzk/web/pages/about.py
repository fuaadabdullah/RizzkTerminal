"""About page content."""

from __future__ import annotations

from dash import html


def register():
    """Return an about page renderer."""

    def render(_: str) -> html.Div:
        return html.Div(
            [
                html.H3("About"),
                html.P("Rizzk Terminal is an experimental research tool for traders."),
                html.P("Built with Dash, Flask, and a lightweight data layer."),
            ]
        )

    return render
