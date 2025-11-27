import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_drawable_canvas import st_canvas
import math
import json

# --- Load target specs ---
with open("target_specs.json", "r") as f:
    specs = json.load(f)

target = next(t for t in specs["targets"] if t["type"] == "ISSF 10m Air Rifle Target")
rings = target["rings"]

# --- Initialize shot log ---
if "shots" not in st.session_state:
    st.session_state.shots = []

st.title("🔫 10m Air Rifle Shot Tracker")

# --- Draw target with Plotly ---
fig = go.Figure()

for ring in sorted(rings, key=lambda r: r["diameter"], reverse=True):
    fig.add_shape(
        type="circle",
        xref="x", yref="y",
        x0=-ring["diameter"]/2, y0=-ring["diameter"]/2,
        x1=ring["diameter"]/2, y1=ring["diameter"]/2,
        line=dict(color="black"),
        fillcolor=ring["color"],
        layer="below"
    )

# Add existing shots
for shot in st.session_state.shots:
    fig.add_trace(go.Scatter(
        x=[shot["x"]], y=[shot["y"]],
        mode="markers+text",
        marker=dict(size=8, color="red"),
        text=[f'{shot["shot"]}'],
        textposition="top center"
    ))

fig.update_layout(
    width=600, height=600,
    xaxis=dict(range=[-25, 25], zeroline=False),
    yaxis=dict(range=[-25, 25], scaleanchor="x", zeroline=False),
    title="Target"
)

st.plotly_chart(fig, use_container_width=True)

# --- Click capture via drawable canvas ---
canvas_result = st_canvas(
    fill_color="rgba(255, 0, 0, 0.3)",  # red marker
    stroke_width=2,
    background_color="white",
    update_streamlit=True,
    height=600,
    width=600,
    drawing_mode="point",  # click = point
    key="canvas",
)

if canvas_result.json_data is not None:
    for obj in canvas_result.json_data["objects"]:
        # Convert canvas coordinates to target coordinates
        # Canvas origin is top-left, so we center it
        x = obj["left"] - 300
        y = 300 - obj["top"]

        distance = math.hypot(x, y)
        score = next(
            (r["points"] for r in sorted(rings, key=lambda r: r["diameter"]) if distance <= r["diameter"]/2),
            0
        )

        shot_number = len(st.session_state.shots) + 1
        st.session_state.shots.append({"shot": shot_number, "score": score, "x": x, "y": y})

# --- Display shot log ---
df = pd.DataFrame(st.session_state.shots)
st.subheader("📋 Shot Log")
st.dataframe(df)

# --- Save to CSV ---
if st.button("💾 Save as CSV"):
    df.to_csv("shot_log.csv", index=False)
    st.success("Saved to shot_log.csv")