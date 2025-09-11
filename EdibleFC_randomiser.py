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

# --- Player Database Upload ---
st.sidebar.header("📂 Player Database")

uploaded_file = st.sidebar.file_uploader("Upload Excel file with players", type=["xlsx"])

if uploaded_file:
    try:
        df_db = pd.read_excel(uploaded_file)

        if "Name" in df_db.columns and "Position" in df_db.columns:
            st.sidebar.success("✅ Player database loaded!")

            # Multi-select to pick players from the database
            selected_names = st.sidebar.multiselect(
                "Select Players",
                options=df_db["Name"].tolist()
            )

            if st.sidebar.button("🕹️ Add Selected Players"):
                for name in selected_names:
                    pos = df_db.loc[df_db["Name"] == name, "Position"].values[0]
                    st.session_state["players"].append((name, pos))
                st.success(f"Added {len(selected_names)} players from database")
        else:
            st.sidebar.error("Excel must have 'Name' and 'Position' columns")

    except Exception as e:
        st.sidebar.error(f"Error reading Excel file: {e}")

# --- Sidebar form for manually adding players ---
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

    # Shuffle all players for randomness
    random.shuffle(players)

    # Group by position
    positions = {"GK": [], "DEF": [], "MID": [], "ST": []}
    for name, pos in players:
        positions[pos].append((name, pos))

    # Shuffle inside each position group
    for pos_group in positions.values():
        random.shuffle(pos_group)

    # Combine back in position order
    combined = []
    for pos in ["GK", "DEF", "MID", "ST"]:
        combined.extend(positions[pos])

    # --- Distribute players fairly ---
    total_players = len(players)
    base_size = total_players // num_teams
    remainder = total_players % num_teams

    # Target team sizes (e.g. 11 players, 2 teams → [6, 5])
    target_sizes = [base_size + (1 if i < remainder else 0) for i in range(num_teams)]

    team_sizes = [0] * num_teams
    for player in combined:
        # pick a team that is not yet "full"
        available_teams = [i for i in range(num_teams) if team_sizes[i] < target_sizes[i]]

        # among available, pick the one with fewest players so far
        min_team = min(available_teams, key=lambda x: team_sizes[x])

        teams[min_team + 1].append(player)
        team_sizes[min_team] += 1

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

        # Show player list
        for p, pos in players:
            st.write(f"- {p} ({pos})")

        # --- Show balance stats ---
        pos_counts = {"GK": 0, "DEF": 0, "MID": 0, "ST": 0}
        for _, pos in players:
            pos_counts[pos] += 1

        st.caption(
            f"⚖️ Balance → GK: {pos_counts['GK']}, DEF: {pos_counts['DEF']}, "
            f"MID: {pos_counts['MID']}, ST: {pos_counts['ST']} "
            f"(Total: {len(players)})"
        )

    # --- Excel Export ---
    def export_excel(teams):
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            for t_num, players in teams.items():
                team_data = [{"Player": p, "Position": pos} for p, pos in players]

                # Balance stats
                pos_counts = {"GK": 0, "DEF": 0, "MID": 0, "ST": 0}
                for _, pos in players:
                    pos_counts[pos] += 1

                team_data.append({
                    "Player": "⚖️ Balance",
                    "Position": f"GK:{pos_counts['GK']}, DEF:{pos_counts['DEF']}, "
                                f"MID:{pos_counts['MID']}, ST:{pos_counts['ST']}, "
                                f"Total:{len(players)}"
                })

                df_team = pd.DataFrame(team_data)
                df_team.to_excel(writer, index=False, sheet_name=f"Team {t_num}")
        return output.getvalue()

    excel_data = export_excel(st.session_state["teams"])
    st.download_button(
        label="📊 Download as Excel",
        data=excel_data,
        file_name="EdibleFC_Teams.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # --- PDF Export ---
    def export_pdf(teams):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer)
        styles = getSampleStyleSheet()
        elements = [Paragraph("EdibleFC Randomiser - Teams", styles['Title']), Spacer(1, 12)]

        for t_num, players in teams.items():
            elements.append(Paragraph(f"Team {t_num}", styles['Heading2']))

            for p, pos in players:
                elements.append(Paragraph(f"{p} ({pos})", styles['Normal']))

            # Balance stats
            pos_counts = {"GK": 0, "DEF": 0, "MID": 0, "ST": 0}
            for _, pos in players:
                pos_counts[pos] += 1

            elements.append(Paragraph(
                f"⚖️ Balance → GK:{pos_counts['GK']}, DEF:{pos_counts['DEF']}, "
                f"MID:{pos_counts['MID']}, ST:{pos_counts['ST']}, Total:{len(players)}",
                styles['Italic']
            ))
            elements.append(Spacer(1, 12))

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()

    pdf_data = export_pdf(st.session_state["teams"])
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
