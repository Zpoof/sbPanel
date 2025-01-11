import streamlit as st
from supabase import create_client, Client
import pandas as pd
import math

# Initialize Supabase
SUPABASE_URL = "https://xhjaflbwngmsslorehrk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhoamFmbGJ3bmdtc3Nsb3JlaHJrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzY1NTU2MDEsImV4cCI6MjA1MjEzMTYwMX0.I_jsQ5GG650iPag2dFOgSFn1a-rx3vHu3CLx_JlfM7Q"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# Page Config
st.set_page_config(
    page_title="Sports Betting Tracker",
    layout="wide"
)

# Sidebar navigation
st.sidebar.title("Sports Betting Tracker")
menu = st.sidebar.selectbox("Menu", ["Dashboard", "Log a Bet", "Settings"])

if menu == "Dashboard":
    st.title("Dashboard Overview")

    # Fetch data
    bets_response = supabase.table("bets").select("*").execute()
    if bets_response.data:
        df = pd.DataFrame(bets_response.data)

        # Fetch related data for sportsbook and sport names
        sportsbooks = supabase.table("sportsbooks").select("*").execute().data
        sports = supabase.table("sports").select("*").execute().data
        sportsbook_map = {s['id']: s['name'] for s in sportsbooks}
        sport_map = {s['id']: s['name'] for s in sports}

        # Add readable names for sportsbooks and sports
        df['sportsbook'] = df['sportsbook_id'].map(sportsbook_map)
        df['sport'] = df['sport_id'].map(sport_map)

        # Filter options
        sportsbook_filter = st.selectbox("Filter by Sportsbook", ["All"] + list(sportsbook_map.values()))
        sport_filter = st.selectbox("Filter by Sport", ["All"] + list(sport_map.values()))
        bet_type_filter = st.selectbox("Filter by Bet Type", ["All", "Regular", "Matched", "Dutching"])

        # Apply filters
        if sportsbook_filter != "All":
            df = df[df['sportsbook'] == sportsbook_filter]
        if sport_filter != "All":
            df = df[df['sport'] == sport_filter]
        if bet_type_filter != "All":
            df = df[df['bet_type'] == bet_type_filter]

        # Display filtered data
        st.write("Filtered Bets")
        st.dataframe(df)

        # Net performance calculation
        net_performance = df['profit_loss'].sum()
        st.metric(label="Net Performance", value=f"${net_performance:.2f}")

        # Monthly trends chart
        df['month'] = pd.to_datetime(df['created_at']).dt.to_period("M")
        monthly_performance = df.groupby("month")["profit_loss"].sum()
        st.line_chart(monthly_performance)
    else:
        st.warning("No bets logged yet!")

elif menu == "Log a Bet":
    st.title("Log a Bet")

    # Input form for matched betting
    bet_type = st.selectbox("Bet Type", ["Regular", "Matched", "Dutching"])

    if bet_type == "Matched":
        # Back Bet (Bookie) section
        st.subheader("Back Bet (Bookie)")
        back_stake = st.number_input("Back stake", min_value=0.0, step=0.01, format="%.2f")
        back_odds = st.number_input("Back odds (decimal)", min_value=1.0, step=0.01, format="%.2f")
        back_commission = st.number_input("Back commission (%)", min_value=0.0, max_value=100.0, step=0.1, format="%.1f")
        stake_returned = st.checkbox("Stake returned", value=False)

        # Lay Bet (Betting Exchange) section
        st.subheader("Lay Bet (Betting Exchange)")
        lay_odds = st.number_input("Lay odds (decimal)", min_value=1.0, step=0.01, format="%.2f")
        lay_commission = st.number_input("Lay commission (%)", min_value=0.0, max_value=100.0, step=0.1, format="%.1f")
        lay_stake = st.number_input("Lay stake (auto-calculated below)", min_value=0.0, step=0.01, format="%.2f", disabled=True)

        # Button to calculate lay stake
        if st.button("Calculate Lay Stake"):
            # Formula to calculate lay stake
            lay_stake = back_stake * (back_odds - (1 if stake_returned else 0)) / (lay_odds - 1)
            st.write(f"Calculated Lay Stake: **${lay_stake:.2f}**")

            # Calculate the net profit/loss
            back_profit = (back_stake * back_odds - back_stake) * (1 - back_commission / 100)
            lay_liability = lay_stake * (lay_odds - 1)
            lay_profit = lay_stake * (1 - lay_commission / 100)
            net_profit = back_profit - lay_liability if lay_stake > 0 else 0.0

            # Display calculated profit/loss
            st.write(f"Net Profit: **${net_profit:.2f}**")

        # Allow submission of the matched bet
        if st.button("Submit Matched Bet"):
            # Save matched bet details to the database
            supabase.table("bets").insert({
                "bet_type": "Matched",
                "stake": back_stake,
                "odds": back_odds,
                "outcome": "Pending",
                "profit_loss": net_profit
            }).execute()
            st.success("Matched Bet logged successfully!")
    else:
        st.error("Please add sportsbooks and sports in the Settings menu first!")

elif menu == "Settings":
    st.title("Settings")

    # Fetch existing sportsbooks and sports
    existing_sportsbooks = supabase.table("sportsbooks").select("name").execute().data
    existing_sports = supabase.table("sports").select("name").execute().data

    existing_sportsbooks_names = [s["name"].lower() for s in existing_sportsbooks] if existing_sportsbooks else []
    existing_sports_names = [s["name"].lower() for s in existing_sports] if existing_sports else []

    # Add a new sportsbook
    st.subheader("Add a Sportsbook")
    new_sportsbook = st.text_input("Sportsbook Name")
    if st.button("Add Sportsbook"):
        if new_sportsbook.strip().lower() in existing_sportsbooks_names:
            st.error(f"{new_sportsbook} already exists!")
        else:
            supabase.table("sportsbooks").insert({"name": new_sportsbook.strip()}).execute()
            st.success(f"{new_sportsbook} added!")
            # Refresh the list
            existing_sportsbooks_names.append(new_sportsbook.strip().lower())

    # Add a new sport
    st.subheader("Add a Sport")
    new_sport = st.text_input("Sport Name")
    if st.button("Add Sport"):
        if new_sport.strip().lower() in existing_sports_names:
            st.error(f"{new_sport} already exists!")
        else:
            supabase.table("sports").insert({"name": new_sport.strip()}).execute()
            st.success(f"{new_sport} added!")
            # Refresh the list
            existing_sports_names.append(new_sport.strip().lower())

