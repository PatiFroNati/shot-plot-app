import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_plotly_events import plotly_events
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

# --- Create target plot ---
fig = go.Figure()

# Draw concentric rings (largest first)
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
    title="Click to record a shot"
)

# --- Capture click (this both renders and listens) ---
click_data = plotly_events(fig, click_event=True, hover_event=False)

if click_data:
    x = click_data[0]["x"]
    y = click_data[0]["y"]
    distance = math.hypot(x, y)

    # Determine score
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