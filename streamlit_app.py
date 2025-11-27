import base64
import json
from io import BytesIO
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st
from PIL import Image

# ---------------------------------------------------------------------
# Helpers & cached resources
# ---------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
ASSETS_DIR = BASE_DIR / "assets"
TARGET_IMG_PATH = ASSETS_DIR / "target.png"
TARGET_SPECS_PATH = BASE_DIR / "target_specs.json"


@st.cache_data
def load_target_specs():
    with open(TARGET_SPECS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["targets"]


@st.cache_resource
def load_target_image(path: Path):
    return Image.open(path).convert("RGBA")


@st.cache_data
def image_to_data_url(image: Image.Image) -> str:
    """Convert PIL image to base64 data URL to avoid flicker on rerender."""
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def get_target_config(targets, target_name: str):
    return next(target for target in targets if target["type"] == target_name)


if not TARGET_IMG_PATH.exists():
    st.error(f"Target image not found at {TARGET_IMG_PATH}")
    st.stop()

targets = load_target_specs()
target_options = [t["type"] for t in targets]

target_img = load_target_image(TARGET_IMG_PATH)
canvas_width, canvas_height = target_img.size
target_data_url = image_to_data_url(target_img)

st.title("🎯 Shot Plotter (Display Test)")
selected_target = st.sidebar.selectbox(
    "Target type",
    target_options,
    index=target_options.index("ISSF 10m Air Rifle Target"),
)

display_mode = st.sidebar.radio(
    "Display mode",
    ["Background image", "Draw rings from specs"],
    index=0,
)

target_config = get_target_config(targets, selected_target)
rings = target_config["rings"]
max_diameter_mm = max(r["diameter"] for r in rings)
pixels_per_mm = canvas_width / max_diameter_mm


def build_image_fig():
    fig = go.Figure()
    fig.add_layout_image(
        dict(
            source=target_data_url,
            xref="x",
            yref="y",
            x=0,
            y=canvas_height,
            sizex=canvas_width,
            sizey=canvas_height,
            sizing="stretch",
            layer="below",
        )
    )
    fig.update_xaxes(visible=False, range=[0, canvas_width], scaleanchor="y", scaleratio=1)
    fig.update_yaxes(visible=False, range=[canvas_height, 0])
    fig.update_layout(margin=dict(l=0, r=0, t=40, b=0), height=canvas_height + 40)
    return fig


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
if display_mode == "Background image":
    st.info("Showing the raw target image via Plotly layout image.")
    st.plotly_chart(build_image_fig(), use_container_width=True)
else:
    st.info("Rendering rings directly from target_specs.json.")
    st.plotly_chart(build_specs_fig(), use_container_width=True)

st.caption("Click handling is temporarily disabled while we verify rendering.")