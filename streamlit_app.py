import streamlit as st
import pandas as pd
import math
import json
from pathlib import Path
from streamlit_drawable_canvas import st_canvas
from PIL import Image

# --- Load target image ---
ASSETS_DIR = Path(__file__).parent / "assets"
TARGET_PATH = ASSETS_DIR / "target.png"

if not TARGET_PATH.exists():
    st.error(f"Target image not found at {TARGET_PATH}")
    st.stop()

target_img = Image.open(TARGET_PATH).convert("RGBA")
canvas_width, canvas_height = target_img.size

# --- Initialize shot log ---
if "shots" not in st.session_state:
    st.session_state.shots = []

st.title("🔫 10m Air Rifle Shot Tracker")

# --- Canvas with target as background ---
canvas_result = st_canvas(
    fill_color="rgba(255, 0, 0, 0.3)",  # red marker
    stroke_width=2,
    background_image=target_img,        # ✅ target overlay
    background_color="rgba(0, 0, 0, 0)",# transparent canvas so image shows
    height=canvas_height,
    width=canvas_width,
    drawing_mode="point",               # click = point
    point_display_radius=6,
    update_streamlit=True,
    key="canvas",
)

# --- Process clicks ---
if canvas_result.json_data is not None:
    objects = canvas_result.json_data.get("objects", [])
    center_x = canvas_width / 2
    center_y = canvas_height / 2

    for obj in objects:
        # Convert canvas coordinates to center-based coordinates
        x = obj["left"] - center_x
        y = center_y - obj["top"]

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