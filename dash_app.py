import json
import math
from pathlib import Path

import dash
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, callback_context, dash_table, dcc, html

BASE_DIR = Path(__file__).parent
TARGET_SPECS = json.loads((BASE_DIR / "target_specs.json").read_text(encoding="utf-8"))["targets"]


def get_target_config(target_name: str):
    return next(target for target in TARGET_SPECS if target["type"] == target_name)


def compute_score(target_name: str, distance_mm: float) -> int:
    rings = get_target_config(target_name)["rings"]
    for ring in sorted(rings, key=lambda r: r["diameter"]):
        if distance_mm <= ring["diameter"] / 2:
            return ring["points"]
    return 0


def build_target_figure(target_name: str, shots: list[dict]) -> go.Figure:
    target = get_target_config(target_name)
    rings = target["rings"]
    canvas_size = 800
    max_diameter = max(r["diameter"] for r in rings)
    pixels_per_mm = canvas_size / max_diameter
    center = canvas_size / 2

    fig = go.Figure()
    for ring in sorted(rings, key=lambda r: r["diameter"], reverse=True):
        radius_px = (ring["diameter"] / 2) * pixels_per_mm
        color = ring["color"]
        fig.add_shape(
            type="circle",
            xref="x",
            yref="y",
            x0=center - radius_px,
            y0=center - radius_px,
            x1=center + radius_px,
            y1=center + radius_px,
            line=dict(color="#000000", width=1),
            fillcolor=color,
            opacity=1.0,
        )

        if ring["ring"] not in ("10", "9"):
            fig.add_annotation(
                x=center + radius_px,
                y=center,
                text=ring["ring"],
                showarrow=False,
                font=dict(color="#000000", size=12),
                xanchor="left",
                yanchor="middle",
            )
            fig.add_annotation(
                x=center,
                y=center - radius_px,
                text=ring["ring"],
                showarrow=False,
                font=dict(color="#000000", size=12),
                xanchor="center",
                yanchor="bottom",
            )

    if shots:
        fig.add_trace(
            go.Scatter(
                x=[shot["pixel_x"] for shot in shots],
                y=[shot["pixel_y"] for shot in shots],
                mode="markers",
                marker=dict(color="red", size=10, line=dict(color="white", width=1)),
                name="Shots",
                customdata=[
                    (
                        shot["shot"],
                        round(shot["x_mm"], 2),
                        round(shot["y_mm"], 2),
                        shot["score"],
                    )
                    for shot in shots
                ],
                hovertemplate="Shot %{customdata[0]}<br>x=%{customdata[1]} mm"
                "<br>y=%{customdata[2]} mm<br>Score %{customdata[3]}<extra></extra>",
            )
        )

    fig.update_xaxes(visible=False, range=[0, canvas_size], scaleanchor="y", scaleratio=1)
    fig.update_yaxes(visible=False, range=[canvas_size, 0])
    fig.update_layout(
        margin=dict(l=0, r=0, t=40, b=0),
        height=canvas_size + 40,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        dragmode="pan",
        clickmode="event+select",
    )
    return fig


app = Dash(__name__)
target_options = [t["type"] for t in TARGET_SPECS]

app.layout = html.Div(
    [
        html.H1("🎯 Shot Plotter (Dash)"),
        html.P("Select a target, then click anywhere on the chart to log a shot."),
        dcc.Dropdown(
            options=[{"label": option, "value": option} for option in target_options],
            value="ISSF 10m Air Rifle Target",
            id="target-select",
            clearable=False,
        ),
        dcc.Graph(id="target-graph", config={"displayModeBar": False}),
        html.Div(
            [
                html.Button("Clear shots", id="clear-btn", n_clicks=0),
                html.Button("Download CSV", id="download-btn", n_clicks=0),
            ],
            style={"display": "flex", "gap": "1rem", "margin": "1rem 0"},
        ),
        dash_table.DataTable(
            id="shot-table",
            columns=[
                {"name": "Shot", "id": "shot"},
                {"name": "Score", "id": "score"},
                {"name": "X (mm)", "id": "x_mm"},
                {"name": "Y (mm)", "id": "y_mm"},
            ],
            data=[],
            style_table={"maxWidth": 400},
            style_cell={"padding": "4px", "textAlign": "center"},
        ),
        dcc.Store(id="shots-store", data=[]),
        dcc.Download(id="download-shots"),
    ],
    style={"maxWidth": "900px", "margin": "0 auto"},
)


@app.callback(
    Output("shots-store", "data"),
    Input("target-graph", "clickData"),
    Input("clear-btn", "n_clicks"),
    Input("target-select", "value"),
    State("shots-store", "data"),
    prevent_initial_call=True,
)
def update_shots(click_data, clear_clicks, target_name, shots):
    shots = shots or []
    triggered = callback_context.triggered_id

    if triggered in {"clear-btn", "target-select"}:
        return []

    if triggered == "target-graph" and click_data:
        point = click_data["points"][0]
        canvas_size = 800
        center = canvas_size / 2
        max_diameter = max(r["diameter"] for r in get_target_config(target_name)["rings"])
        pixels_per_mm = canvas_size / max_diameter

        px = point["x"]
        py = point["y"]
        dx_mm = (px - center) / pixels_per_mm
        dy_mm = (center - py) / pixels_per_mm
        distance_mm = math.hypot(dx_mm, dy_mm)
        score = compute_score(target_name, distance_mm)

        shots.append(
            {
                "shot": len(shots) + 1,
                "score": score,
                "x_mm": dx_mm,
                "y_mm": dy_mm,
                "pixel_x": px,
                "pixel_y": py,
            }
        )

    return shots


@app.callback(
    Output("target-graph", "figure"),
    Output("shot-table", "data"),
    Input("target-select", "value"),
    Input("shots-store", "data"),
)
def update_outputs(target_name, shots):
    figure = build_target_figure(target_name, shots or [])
    table_data = [
        {
            "shot": shot["shot"],
            "score": shot["score"],
            "x_mm": round(shot["x_mm"], 2),
            "y_mm": round(shot["y_mm"], 2),
        }
        for shot in shots or []
    ]
    return figure, table_data


@app.callback(
    Output("download-shots", "data"),
    Input("download-btn", "n_clicks"),
    State("shots-store", "data"),
    prevent_initial_call=True,
)
def trigger_download(n_clicks, shots):
    if not shots:
        return dash.no_update
    df = pd.DataFrame(shots)
    return dcc.send_data_frame(df.to_csv, "shot_log.csv", index=False)


if __name__ == "__main__":
    app.run_server(debug=True)

