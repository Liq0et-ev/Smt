"""Task 5: interactive Dash/Plotly dashboard. Talks only to the FastAPI
backend (Task 4) over HTTP -- never touches Snowflake or MongoDB
directly, matching the architecture diagram in the README.

Run locally (API must already be running, e.g. `uvicorn api.main:app --reload`
in another terminal):
    python -m dashboard.app
Then open http://localhost:8050.

Or via Docker Compose (starts Mongo + API + dashboard together):
    docker compose up -d --build
"""
import logging

import dash
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, dcc, html

from dashboard import api_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = Dash(__name__, title="COVID-19 Data Platform")
server = app.server  # WSGI entrypoint if ever deployed behind gunicorn

try:
    COUNTRIES = api_client.get_countries()
except Exception as e:
    logger.error("Could not reach the API at startup (%s) -- is it running? "
                 "Country list will be empty until the page is reloaded.", e)
    COUNTRIES = []

COUNTRY_OPTIONS = [
    {"label": f"{c['country_name']} ({c['iso_code']})", "value": c["iso_code"]}
    for c in COUNTRIES
    if c.get("country_name")
]
DEFAULT_COUNTRY = (
    "US" if any(opt["value"] == "US" for opt in COUNTRY_OPTIONS)
    else (COUNTRY_OPTIONS[0]["value"] if COUNTRY_OPTIONS else None)
)

METRIC_OPTIONS = [
    {"label": "Confirmed cases", "value": "confirmed_cases"},
    {"label": "Confirmed deaths", "value": "confirmed_deaths"},
    {"label": "Vaccinations", "value": "vaccinations"},
    {"label": "Other", "value": "other"},
]


def stat_card(label: str, value: str) -> html.Div:
    return html.Div(
        [
            html.Div(label, style={"fontSize": "13px", "color": "#666"}),
            html.Div(value, style={"fontSize": "22px", "fontWeight": "bold"}),
        ],
        style={
            "padding": "12px 16px",
            "border": "1px solid #ddd",
            "borderRadius": "8px",
            "minWidth": "150px",
            "background": "#fafafa",
        },
    )


app.layout = html.Div(
    [
        html.H1("COVID-19 Data Integration & Analysis Platform"),
        html.P(
            "Snowflake (Marketplace data + augmented indicators, transformed with dbt) "
            "-> FastAPI -> this dashboard."
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.Label("Country"),
                        dcc.Dropdown(
                            id="country-dropdown",
                            options=COUNTRY_OPTIONS,
                            value=DEFAULT_COUNTRY,
                            clearable=False,
                        ),
                    ],
                    style={"minWidth": "260px"},
                ),
                html.Div(
                    [
                        html.Label("Date range (time series charts only)"),
                        dcc.DatePickerRange(id="date-range", display_format="YYYY-MM-DD"),
                    ]
                ),
            ],
            style={"display": "flex", "gap": "24px", "alignItems": "flex-end", "marginBottom": "20px"},
        ),
        dcc.Loading(
            html.Div(
                id="summary-cards",
                style={"display": "flex", "gap": "12px", "flexWrap": "wrap", "marginBottom": "24px"},
            )
        ),
        dcc.Loading(dcc.Graph(id="cases-deaths-graph")),
        dcc.Loading(dcc.Graph(id="forecast-graph")),
        dcc.Loading(dcc.Graph(id="vaccination-graph")),
        dcc.Loading(dcc.Graph(id="crosscheck-graph")),
        html.Hr(),
        html.H2("Annotations"),
        html.P(
            "Bonus feature: comments stored in MongoDB (Task 3), scoped to the "
            "selected country, added and read live through the API (Task 4)."
        ),
        html.Div(
            [
                dcc.Dropdown(
                    id="annotation-metric",
                    options=METRIC_OPTIONS,
                    value="confirmed_cases",
                    clearable=False,
                    style={"width": "220px"},
                ),
                dcc.Textarea(
                    id="annotation-comment",
                    placeholder="Add a note about this country's data...",
                    style={"width": "400px", "height": "60px"},
                ),
                html.Button("Add annotation", id="annotation-submit", n_clicks=0),
            ],
            style={"display": "flex", "gap": "12px", "alignItems": "flex-start", "marginBottom": "12px"},
        ),
        html.Div(id="annotation-status", style={"color": "#a00", "marginBottom": "12px"}),
        html.Div(id="annotations-list"),
        dcc.Store(id="annotations-refresh"),
    ],
    style={"maxWidth": "1100px", "margin": "0 auto", "padding": "24px", "fontFamily": "sans-serif"},
)


def safe_fetch(fn, *args, default, **kwargs):
    """Every chart on this page comes from a separate API call. One
    country having odd/sparse data (e.g. a small country with a
    near-constant case count breaking the forecast model) shouldn't blank
    out the whole page -- just the one chart that couldn't load."""
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        logger.warning("Dashboard fetch failed (%s, %s): %s", getattr(fn, "__name__", fn), args, e)
        return default


@app.callback(
    Output("summary-cards", "children"),
    Output("cases-deaths-graph", "figure"),
    Output("forecast-graph", "figure"),
    Output("vaccination-graph", "figure"),
    Output("crosscheck-graph", "figure"),
    Input("country-dropdown", "value"),
    Input("date-range", "start_date"),
    Input("date-range", "end_date"),
)
def update_country_view(iso_code, start_date, end_date):
    if not iso_code:
        return [], go.Figure(), go.Figure(), go.Figure(), go.Figure()

    summary = safe_fetch(api_client.get_summary, iso_code, default=None)
    daily = safe_fetch(api_client.get_daily, iso_code, start_date, end_date, default=[])
    waves = safe_fetch(api_client.get_waves, iso_code, default=[])
    cross_check = safe_fetch(api_client.get_cross_check, iso_code, default=[])
    forecast = safe_fetch(api_client.get_forecast, iso_code, days=30, default=[])

    if summary:
        cfr = summary.get("latest_case_fatality_rate")
        vacc = summary.get("latest_people_fully_vaccinated_per_hundred")
        cards = [
            stat_card("Latest date", str(summary.get("latest_date") or "-")),
            stat_card("Confirmed cases", f"{summary.get('latest_confirmed_cases') or 0:,.0f}"),
            stat_card("Confirmed deaths", f"{summary.get('latest_confirmed_deaths') or 0:,.0f}"),
            stat_card("Case fatality rate", f"{cfr * 100:.2f}%" if cfr is not None else "-"),
            stat_card("Fully vaccinated", f"{vacc:.1f}%" if vacc is not None else "-"),
            stat_card("Median age", f"{summary['median_age']:.1f}" if summary.get("median_age") is not None else "-"),
            stat_card(
                "GDP per capita",
                f"${summary['gdp_per_capita']:,.0f}" if summary.get("gdp_per_capita") is not None else "-",
            ),
            stat_card(
                "Human Development Index",
                f"{summary['human_development_index']:.3f}"
                if summary.get("human_development_index") is not None
                else "-",
            ),
        ]
    else:
        cards = [html.P(f"No summary data available for {iso_code}.")]

    dates = [d["report_date"] for d in daily]

    cases_fig = go.Figure()
    cases_fig.add_trace(
        go.Scatter(x=dates, y=[d["confirmed_cases"] for d in daily], name="Confirmed cases", mode="lines")
    )
    cases_fig.add_trace(
        go.Scatter(
            x=dates, y=[d["confirmed_deaths"] for d in daily],
            name="Confirmed deaths", mode="lines", yaxis="y2",
        )
    )
    for w in waves:
        cases_fig.add_vrect(
            x0=w["wave_start"], x1=w["wave_end"],
            fillcolor="LightSalmon", opacity=0.25, line_width=0,
            annotation_text=f"Wave {w['wave_number']}", annotation_position="top left",
        )
    cases_fig.update_layout(
        title="Cumulative confirmed cases & deaths (shaded = detected waves, Task 9 MATCH_RECOGNIZE)",
        yaxis=dict(title="Confirmed cases"),
        yaxis2=dict(title="Confirmed deaths", overlaying="y", side="right"),
        legend=dict(orientation="h"),
    )

    forecast_fig = go.Figure()
    historical_new_cases = [None]
    for i in range(1, len(daily)):
        prev_cases, cur_cases = daily[i - 1]["confirmed_cases"], daily[i]["confirmed_cases"]
        historical_new_cases.append(
            max(cur_cases - prev_cases, 0) if prev_cases is not None and cur_cases is not None else None
        )
    forecast_fig.add_trace(
        go.Scatter(x=dates, y=historical_new_cases, name="Historical new cases", mode="lines")
    )
    forecast_fig.add_trace(
        go.Scatter(
            x=[f["date"] for f in forecast], y=[f["predicted_new_cases"] for f in forecast],
            name="Forecast (Holt-Winters)", mode="lines", line=dict(dash="dash"),
        )
    )
    forecast_fig.update_layout(
        title="Daily new cases: recent history + 30-day forecast (Task 6)",
        yaxis_title="New cases / day",
        legend=dict(orientation="h"),
    )

    vacc_fig = go.Figure()
    vacc_fig.add_trace(
        go.Scatter(
            x=dates, y=[d["people_fully_vaccinated_per_hundred"] for d in daily],
            name="Fully vaccinated (%)", mode="lines",
        )
    )
    vacc_fig.update_layout(title="Vaccination progress", yaxis_title="% of population fully vaccinated")

    cc_dates = [c["report_date"] for c in cross_check]
    cc_fig = go.Figure()
    cc_fig.add_trace(go.Scatter(x=cc_dates, y=[c["jhu_cases"] for c in cross_check], name="JHU cases", mode="lines"))
    cc_fig.add_trace(
        go.Scatter(x=cc_dates, y=[c["who_total_cases"] for c in cross_check], name="WHO cases", mode="lines")
    )
    cc_fig.update_layout(title="JHU vs. WHO reported cases (data-quality cross-check)", yaxis_title="Confirmed cases")

    return cards, cases_fig, forecast_fig, vacc_fig, cc_fig


def render_annotations(iso_code: str) -> list:
    docs = api_client.get_annotations(iso_code)
    if not docs:
        return [html.P("No annotations yet for this country.", style={"color": "#888"})]
    return [
        html.Div(
            [
                html.Div(f"{a['metric']} -- {a['created_at'][:10]}", style={"fontSize": "12px", "color": "#888"}),
                html.Div(a["comment"]),
            ],
            style={
                "padding": "8px 12px",
                "borderLeft": "3px solid #4a90d9",
                "marginBottom": "8px",
                "background": "#f7f9fc",
            },
        )
        for a in docs
    ]


@app.callback(
    Output("annotations-list", "children"),
    Input("country-dropdown", "value"),
    Input("annotations-refresh", "data"),
)
def update_annotations(iso_code, _refresh_token):
    if not iso_code:
        return []
    return render_annotations(iso_code)


@app.callback(
    Output("annotations-refresh", "data"),
    Output("annotation-comment", "value"),
    Output("annotation-status", "children"),
    Input("annotation-submit", "n_clicks"),
    State("country-dropdown", "value"),
    State("annotation-metric", "value"),
    State("annotation-comment", "value"),
    prevent_initial_call=True,
)
def submit_annotation(n_clicks, iso_code, metric, comment):
    if not comment or not comment.strip():
        return dash.no_update, comment, "Comment can't be empty."
    try:
        api_client.create_annotation(iso_code, metric, comment.strip())
    except Exception as e:
        logger.error("Failed to save annotation: %s", e)
        return dash.no_update, comment, f"Failed to save annotation: {e}"
    return n_clicks, "", ""


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)
