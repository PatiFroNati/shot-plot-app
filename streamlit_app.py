import base64
import json
import math
from io import BytesIO
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from PIL import Image
from streamlit_plotly_events import plotly_events

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


def compute_score(rings, distance_mm: float) -> int:
    for ring in sorted(rings, key=lambda r: r["diameter"]):
        if distance_mm <= ring["diameter"] / 2:
            return ring["points"]
    return 0


if not TARGET_IMG_PATH.exists():
    st.error(f"Target image not found at {TARGET_IMG_PATH}")
    st.stop()

targets = load_target_specs()
target_options = [t["type"] for t in targets]

target_img = load_target_image(TARGET_IMG_PATH)
canvas_width, canvas_height = target_img.size
target_data_url = image_to_data_url(target_img)

st.title("🎯 Shot Plotter")
selected_target = st.sidebar.selectbox("Target type", target_options, index=target_options.index("ISSF 10m Air Rifle Target"))

if "shots" not in st.session_state:
    st.session_state.shots = []
if "active_target" not in st.session_state:
    st.session_state.active_target = selected_target
if "last_click_signature" not in st.session_state:
    st.session_state.last_click_signature = None

if selected_target != st.session_state.active_target:
    st.session_state.shots = []
    st.session_state.active_target = selected_target
    st.info("Target changed — shot log cleared.")

target_config = get_target_config(targets, selected_target)
rings = target_config["rings"]
max_diameter_mm = max(r["diameter"] for r in rings)
pixels_per_mm = canvas_width / max_diameter_mm

# ---------------------------------------------------------------------
# Build Plotly figure (background image + current shots)
# ---------------------------------------------------------------------
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

fig.update_xaxes(
    visible=False,
    range=[0, canvas_width],
    scaleanchor="y",
    scaleratio=1,
)
fig.update_yaxes(
    visible=False,
    range=[canvas_height, 0],
)
fig.update_layout(
    margin=dict(l=0, r=0, t=40, b=0),
    height=canvas_height + 40,
    dragmode="pan",
)

st.subheader("Tap the target to log a shot")
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

    # Convert to a center-origin coordinate system in millimeters
    dx_px = px - canvas_width / 2
    dy_px = canvas_height / 2 - py  # invert Y (Plotly origin is top-left)
    dx_mm = dx_px / pixels_per_mm
    dy_mm = dy_px / pixels_per_mm
    distance_mm = math.hypot(dx_mm, dy_mm)
    score = compute_score(rings, distance_mm)

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

# ---------------------------------------------------------------------
# Shot log + export
# ---------------------------------------------------------------------
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
    st.info("No shots logged yet — click the target above to start.")