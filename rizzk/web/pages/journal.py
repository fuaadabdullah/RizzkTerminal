"""Journal page callbacks and rendering."""

from __future__ import annotations

from dash import Dash, Input, Output, State, dash_table, dcc, html

from rizzk.core.journal import add_entry, list_entries
from rizzk.core.util import humanize_timestamp


def register(app: Dash):
    """Register journal callbacks and return a renderer."""

    def _format_rows(limit: int = 50) -> list[dict[str, str]]:
        entries = list_entries(limit=limit)
        return [
            {
                "id": str(entry["id"]),
                "timestamp": humanize_timestamp(entry["ts"]),
                "body": entry["body"],
            }
            for entry in entries
        ]

    def render(_: str) -> html.Div:
        return html.Div(
            [
                html.Div(id="journal-message", className="journal-message"),
                dcc.Textarea(id="journal-text", style={"width": "100%", "height": "120px"}),
                html.Button("Save Entry", id="journal-save", n_clicks=0),
                dash_table.DataTable(
                    id="journal-table",
                    columns=[
                        {"name": "ID", "id": "id"},
                        {"name": "Timestamp", "id": "timestamp"},
                        {"name": "Entry", "id": "body"},
                    ],
                    data=_format_rows(),
                    style_table={"overflowY": "auto", "maxHeight": "320px"},
                ),
            ]
        )

    @app.callback(  # type: ignore[misc]
        Output("journal-message", "children"),
        Output("journal-table", "data"),
        Input("journal-save", "n_clicks"),
        State("journal-text", "value"),
        prevent_initial_call=True,
    )
    def _save_entry(n_clicks: int, text: str):  # pragma: no cover - exercised via Dash
        if not text or not text.strip():
            return "Nothing to save.", _format_rows()
        try:
            add_entry(text)
        except ValueError as error:
            return str(error), _format_rows()
        return "Saved entry.", _format_rows()

    return render
