import streamlit as st
import pandas as pd
import math
import json
from streamlit_drawable_canvas import st_canvas
from PIL import Image

# --- Load target image ---
target_img = Image.open("assets/target.png")  # replace with your target image file

# --- Initialize shot log ---
if "shots" not in st.session_state:
    st.session_state.shots = []

st.title("🔫 10m Air Rifle Shot Tracker")

# --- Canvas with target as background ---
canvas_result = st_canvas(
    fill_color="rgba(255, 0, 0, 0.3)",  # red marker
    stroke_width=2,
    background_image=target_img,        # ✅ target overlay
    background_color="rgba(0,0,0,0)",
    height=50,
    width=50,
    drawing_mode="point",               # click = point
    key="canvas",
)

# --- Process clicks ---
if canvas_result.json_data is not None:
    for obj in canvas_result.json_data["objects"]:
        # Convert canvas coordinates to center-based coordinates
        x = obj["left"] - 300
        y = 300 - obj["top"]

        # Example scoring logic (using your JSON specs)
        with open("target_specs.json", "r") as f:
            specs = json.load(f)
        target = next(t for t in specs["targets"] if t["type"] == "ISSF 10m Air Rifle Target")
        rings = target["rings"]

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