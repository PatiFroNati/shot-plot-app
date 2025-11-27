import json
import math
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_plotly_events import plotly_events

# ---------------------------------------------------------------------
# Helpers & cached resources
# ---------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
TARGET_SPECS_PATH = BASE_DIR / "target_specs.json"


@st.cache_data
def load_target_specs():
    with open(TARGET_SPECS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["targets"]


def get_target_config(targets, target_name: str):
    return next(target for target in targets if target["type"] == target_name)


targets = load_target_specs()
target_options = [t["type"] for t in targets]

st.title("🎯 Shot Plotter (Display Test)")
selected_target = st.sidebar.selectbox(
    "Target type",
    target_options,
    index=target_options.index("ISSF 10m Air Rifle Target"),
)

target_config = get_target_config(targets, selected_target)
rings = target_config["rings"]
canvas_width = 800
max_diameter_mm = max(r["diameter"] for r in rings)
pixels_per_mm = canvas_width / max_diameter_mm
canvas_height = canvas_width  # square canvas
canvas_center = canvas_width / 2

if "shots" not in st.session_state:
    st.session_state.shots = []
if "active_target" not in st.session_state:
    st.session_state.active_target = selected_target
if "last_click_signature" not in st.session_state:
    st.session_state.last_click_signature = None

if selected_target != st.session_state.active_target:
    st.session_state.shots = []
    st.session_state.active_target = selected_target
    st.session_state.last_click_signature = None
    st.info("Target changed — shot log cleared.")


def compute_score(distance_mm: float) -> int:
    for ring in sorted(rings, key=lambda r: r["diameter"]):
        if distance_mm <= ring["diameter"] / 2:
            return ring["points"]
    return 0

def build_specs_fig():
    fig = go.Figure()
    for ring in sorted(rings, key=lambda r: r["diameter"], reverse=True):
        radius_px = (ring["diameter"] / 2) * pixels_per_mm
        fill_rgba = ring["color"]
        if len(fill_rgba) == 7:  # hex color e.g. #FFFFFF
            fill_rgba = f"{fill_rgba}"  # add alpha (~60%)
        fig.add_shape(
            type="circle",
            xref="x",
            yref="y",
            x0=canvas_width / 2 - radius_px,
            y0=canvas_height / 2 - radius_px,
            x1=canvas_width / 2 + radius_px,
            y1=canvas_height / 2 + radius_px,
            line=dict(color="#000000", width=1),
            fillcolor=fill_rgba,
            opacity=1.0,
        )

        if ring["ring"] not in ("10", "9"):
            fig.add_annotation(
                x=canvas_width / 2 + radius_px,
                y=canvas_height / 2,
                text=ring["ring"],
                showarrow=False,
                font=dict(color="#000000", size=12, family="Arial"),
                xanchor="right",
                yanchor="middle"
            )
            fig.add_annotation(
                x=canvas_width / 2,
                y=canvas_height / 2 - radius_px,
                text=ring["ring"],
                showarrow=False,
                font=dict(color="#000000", size=12, family="Arial"),
                xanchor="center",
                yanchor="top"
            )

    fig.update_xaxes(visible=False, range=[0, canvas_width], scaleanchor="y", scaleratio=1)
    fig.update_yaxes(visible=False, range=[canvas_height, 0])
    fig.update_layout(
        margin=dict(l=0, r=0, t=40, b=0),
        height=canvas_height + 40,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    if st.session_state.shots:
        fig.add_trace(
            go.Scatter(
                x=[shot["pixel_x"] for shot in st.session_state.shots],
                y=[shot["pixel_y"] for shot in st.session_state.shots],
                mode="markers",
                marker=dict(color="red", size=10, line=dict(color="white", width=1)),
                name="Shots",
                hovertemplate="Shot %{customdata[0]}<br>x=%{customdata[1]} mm<br>y=%{customdata[2]} mm<br>Score=%{customdata[3]}<extra></extra>",
                customdata=[
                    (
                        shot["shot"],
                        round(shot["x_mm"], 2),
                        round(shot["y_mm"], 2),
                        shot["score"],
                    )
                    for shot in st.session_state.shots
                ],
            )
        )
    return fig


st.subheader("Tap the target to log a shot")
fig = build_specs_fig()
clicked_points = plotly_events(
    fig,
    click_event=True,
    select_event=False,
    hover_event=False,
    key="shot-plot",
)

if clicked_points:
    point = clicked_points[0]
    px = point["x"]
    py = point["y"]

    click_signature = (point.get("curveNumber"), point.get("pointIndex"), px, py)
    if click_signature == st.session_state.last_click_signature:
        point = None
    else:
        st.session_state.last_click_signature = click_signature

if clicked_points and point:
    px = point["x"]
    py = point["y"]
    dx_px = px - canvas_center
    dy_px = canvas_center - py  # invert Y
    dx_mm = dx_px / pixels_per_mm
    dy_mm = dy_px / pixels_per_mm
    distance_mm = math.hypot(dx_mm, dy_mm)
    score = compute_score(distance_mm)

    shot_number = len(st.session_state.shots) + 1
    st.session_state.shots.append(
        {
            "shot": shot_number,
            "score": score,
            "x_mm": dx_mm,
            "y_mm": dy_mm,
            "pixel_x": px,
            "pixel_y": py,
        }
    )
    st.experimental_rerun()

st.subheader("📋 Shot Log")
if st.session_state.shots:
    df = pd.DataFrame(
        [
            {
                "Shot": shot["shot"],
                "Score": shot["score"],
                "X (mm)": round(shot["x_mm"], 2),
                "Y (mm)": round(shot["y_mm"], 2),
            }
            for shot in st.session_state.shots
        ]
    )
    st.dataframe(df, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save as CSV"):
            df.to_csv("shot_log.csv", index=False)
            st.success("Saved to shot_log.csv")
    with col2:
        if st.button("🧹 Clear shots"):
            st.session_state.shots = []
            st.experimental_rerun()
else:
    st.info("No shots logged yet — click the plot above to start.")