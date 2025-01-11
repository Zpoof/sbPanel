import streamlit as st
from supabase import create_client, Client
import pandas as pd

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

    # Input form for logging a bet
    sportsbooks = supabase.table("sportsbooks").select("id, name").execute().data
    sports = supabase.table("sports").select("id, name").execute().data

    if sportsbooks and sports:
        sportsbook = st.selectbox("Sportsbook", [s["name"] for s in sportsbooks])
        sport = st.selectbox("Sport", [s["name"] for s in sports])
        bet_type = st.selectbox("Bet Type", ["Regular", "Matched", "Dutching"])
        stake = st.number_input("Stake", min_value=0.0, format="%.2f")
        odds = st.number_input("Odds", min_value=1.0, format="%.3f")
        outcome = st.selectbox("Outcome", ["Pending", "Won", "Lost", "Void"])
        profit_loss = st.number_input("Profit/Loss", format="%.2f")

        if st.button("Submit"):
            sportsbook_id = next(s["id"] for s in sportsbooks if s["name"] == sportsbook)
            sport_id = next(s["id"] for s in sports if s["name"] == sport)
            
            # Insert data into Supabase
            supabase.table("bets").insert({
                "sportsbook_id": sportsbook_id,
                "sport_id": sport_id,
                "bet_type": bet_type,
                "stake": stake,
                "odds": odds,
                "outcome": outcome,
                "profit_loss": profit_loss
            }).execute()
            st.success("Bet logged successfully!")
    else:
        st.error("Please add sportsbooks and sports in the Settings menu first!")

elif menu == "Settings":
    st.title("Settings")

    # Add a new sportsbook
    st.subheader("Add a Sportsbook")
    new_sportsbook = st.text_input("Sportsbook Name")
    if st.button("Add Sportsbook"):
        supabase.table("sportsbooks").insert({"name": new_sportsbook}).execute()
        st.success(f"{new_sportsbook} added!")

    # Add a new sport
    st.subheader("Add a Sport")
    new_sport = st.text_input("Sport Name")
    if st.button("Add Sport"):
        supabase.table("sports").insert({"name": new_sport}).execute()
        st.success(f"{new_sport} added!")
