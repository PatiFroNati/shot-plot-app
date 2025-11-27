import json
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

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
    return fig


st.subheader("Plot preview")
st.info("Rendering rings directly from target_specs.json.")
st.plotly_chart(build_specs_fig(), use_container_width=True)
st.caption("Click handling is temporarily disabled while we verify rendering.")