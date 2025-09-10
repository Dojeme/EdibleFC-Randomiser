import streamlit as st
import random
from collections import defaultdict
import pandas as pd
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

st.set_page_config(page_title="EdibleFC Randomiser", page_icon="⚽", layout="centered")

st.title("🍽️⚽ EdibleFC Randomiser")
st.write("Generate fair football teams with balanced positions (GK, DEF, MID, ST).")

# Persistent storage
if "players" not in st.session_state:
    st.session_state["players"] = []
if "teams" not in st.session_state:
    st.session_state["teams"] = {}
if "edit_index" not in st.session_state:
    st.session_state["edit_index"] = None  # track which player is being edited

# Sidebar form for adding players
st.sidebar.header("➕ Add Players")
with st.sidebar.form("add_player_form"):
    name = st.text_input("Player Name")
    position = st.selectbox("Position", ["GK", "DEF", "MID", "ST"])
    add_btn = st.form_submit_button("Add Player")

    if add_btn and name:
        st.session_state["players"].append((name, position))
        st.success(f"✅ Added {name} as {position}")

# --- Manage Players ---
st.subheader("📋 Player List")

if not st.session_state["players"]:
    st.info("No players added yet.")
else:
    # Shuffle players button
    if st.button("🔀 Shuffle Players"):
        random.shuffle(st.session_state["players"])
        st.success("🔀 Player list shuffled!")
        st.rerun()

    for i, (p, pos) in enumerate(st.session_state["players"]):
        cols = st.columns([3, 1, 1])
        
        # If this player is being edited
        if st.session_state["edit_index"] == i:
            with cols[0]:
                new_name = st.text_input("Name", value=p, key=f"edit_name_{i}")
                new_position = st.selectbox(
                    "Position", ["GK", "DEF", "MID", "ST"],
                    index=["GK", "DEF", "MID", "ST"].index(pos),
                    key=f"edit_pos_{i}"
                )
            with cols[1]:
                if st.button("💾 Save", key=f"save_{i}"):
                    st.session_state["players"][i] = (new_name, new_position)
                    st.session_state["edit_index"] = None
                    st.rerun()
            with cols[2]:
                if st.button("❌ Cancel", key=f"cancel_{i}"):
                    st.session_state["edit_index"] = None
                    st.rerun()
        else:
            with cols[0]:
                st.write(f"{p} ({pos})")
            with cols[1]:
                if st.button("✏️ Edit", key=f"edit_{i}"):
                    st.session_state["edit_index"] = i
                    st.rerun()
            with cols[2]:
                if st.button("🗑️ Remove", key=f"remove_{i}"):
                    removed = st.session_state["players"].pop(i)
                    st.success(f"🗑️ Removed {removed[0]} ({removed[1]})")
                    st.rerun()

# --- Team generator function ---
def generate_teams(players, num_teams):
    teams = defaultdict(list)
    positions = {"GK": [], "DEF": [], "MID": [], "ST": []}

    # Group players by position
    for name, pos in players:
        positions[pos].append(name)

    # Shuffle for randomness
    for pos in positions:
        random.shuffle(positions[pos])

    # Distribute evenly
    for pos, pos_players in positions.items():
        for i, player in enumerate(pos_players):
            team_num = (i % num_teams) + 1
            teams[team_num].append((player, pos))

    return teams

# --- Generate Teams ---
if st.session_state["players"]:
    num_teams = st.slider("Number of Teams", min_value=2, max_value=6, value=2, step=1)

    if st.button("🎲 Generate Teams"):
        st.session_state["teams"] = generate_teams(st.session_state["players"], num_teams)

# --- Show results ---
if st.session_state["teams"]:
    for t_num, players in st.session_state["teams"].items():
        st.markdown(f"### 🟢 Team {t_num}")
        for p, pos in players:
            st.write(f"- {p} ({pos})")

    # Convert to DataFrame for export
    all_data = []
    for t_num, players in st.session_state["teams"].items():
        for p, pos in players:
            all_data.append({"Team": f"Team {t_num}", "Player": p, "Position": pos})
    df = pd.DataFrame(all_data)

    # --- Excel Export ---
    def export_excel(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Teams")
        return output.getvalue()

    excel_data = export_excel(df)
    st.download_button(
        label="📊 Download as Excel",
        data=excel_data,
        file_name="EdibleFC_Teams.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # --- PDF Export ---
    def export_pdf(df):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer)
        styles = getSampleStyleSheet()
        elements = [Paragraph("EdibleFC Randomiser - Teams", styles['Title']), Spacer(1, 12)]

        grouped = df.groupby("Team")
        for team, group in grouped:
            elements.append(Paragraph(team, styles['Heading2']))
            for _, row in group.iterrows():
                elements.append(Paragraph(f"{row['Player']} ({row['Position']})", styles['Normal']))
            elements.append(Spacer(1, 12))

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()

    pdf_data = export_pdf(df)
    st.download_button(
        label="📄 Download as PDF",
        data=pdf_data,
        file_name="EdibleFC_Teams.pdf",
        mime="application/pdf"
    )

# --- Reset all players ---
if st.button("♻️ Reset Players"):
    st.session_state["players"] = []
    st.session_state["teams"] = {}
    st.session_state["edit_index"] = None
    st.success("Player list cleared.")
