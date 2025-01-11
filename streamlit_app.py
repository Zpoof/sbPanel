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
    bets_response = supabase.table("bets").select("*, sportsbooks(name), sports(name)").execute()
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

    # Fetch Sports and Sportsbooks from the database
    sportsbooks = supabase.table("sportsbooks").select("id, name").execute().data
    sports = supabase.table("sports").select("id, name").execute().data
    criteria_response = supabase.table("bets").select("criteria").execute()
    existing_criteria = list(set([item['criteria'] for item in criteria_response.data if item['criteria']]))

    if not sportsbooks or not sports:
        st.error("Please add sportsbooks and sports in the Settings menu before logging bets!")
    else:
        sportsbook_map = {s['id']: s['name'] for s in sportsbooks}
        sport_map = {s['id']: s['name'] for s in sports}

        # Dropdowns for selecting sportsbook, sport, and criteria
        selected_sportsbook = st.selectbox("Select Sportsbook", list(sportsbook_map.values()))
        selected_sport = st.selectbox("Select Sport", list(sport_map.values()))
        criteria = st.selectbox("Select or Enter Criteria", ["Enter New"] + existing_criteria)
        if criteria == "Enter New":
            criteria = st.text_input("Enter New Criteria")

        event_name = st.text_input("Event Name")

        sportsbook_id = next(key for key, value in sportsbook_map.items() if value == selected_sportsbook)
        sport_id = next(key for key, value in sport_map.items() if value == selected_sport)

        # Dropdown for selecting bet type
        bet_type = st.selectbox("Bet Type", ["Regular", "Matched", "Dutching"])

        # Regular Bet
        if bet_type == "Regular":
            st.subheader("Regular Bet")

            # Input fields for a regular bet
            stake = st.number_input("Stake", min_value=0.0, step=0.01, format="%.2f")
            odds = st.number_input("Odds (decimal)", min_value=1.0, step=0.01, format="%.2f")
            commission = st.number_input("Commission (%)", min_value=0.0, max_value=100.0, step=0.1, format="%.1f")
            outcome = st.selectbox("Outcome", ["Pending", "Won", "Lost", "Void"])

            # Calculate profit or loss
            if st.button("Submit Regular Bet"):
                profit_loss = 0.0
                if outcome == "Won":
                    profit_loss = (stake * odds - stake) * (1 - commission / 100)
                elif outcome == "Lost":
                    profit_loss = -stake
                elif outcome == "Void":
                    profit_loss = 0.0

                # Insert the regular bet into the database
                supabase.table("bets").insert({
                    "sportsbook_id": sportsbook_id,
                    "sport_id": sport_id,
                    "bet_type": "Regular",
                    "stake": stake,
                    "odds": odds,
                    "commission": commission,
                    "outcome": outcome,
                    "profit_loss": profit_loss,
                    "event_name": event_name,
                    "criteria": criteria
                }).execute()
                st.success(f"Regular Bet logged successfully! Profit/Loss: ${profit_loss:.2f}")

        # Matched Bet
        elif bet_type == "Matched":
            st.subheader("Matched Bet")

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

            # Calculate Lay Stake
            if st.button("Calculate Lay Stake"):
                lay_stake = back_stake * (back_odds - (1 if stake_returned else 0)) / (lay_odds - 1)
                st.write(f"Calculated Lay Stake: **${lay_stake:.2f}**")

                # Calculate Profit/Loss
                back_profit = (back_stake * back_odds - back_stake) * (1 - back_commission / 100)
                lay_liability = lay_stake * (lay_odds - 1)
                lay_profit = lay_stake * (1 - lay_commission / 100)
                net_profit = back_profit - lay_liability if lay_stake > 0 else 0.0
                st.write(f"Net Profit: **${net_profit:.2f}**")

            # Submit Matched Bet
            if st.button("Submit Matched Bet"):
                # Generate a unique ID for the matched bet
                matched_bet_id = supabase.table("bets").select("MAX(id)").execute().data[0]["max"] + 1

                # Insert Back Bet
                supabase.table("bets").insert({
                    "matched_bet_id": matched_bet_id,
                    "sportsbook_id": sportsbook_id,
                    "sport_id": sport_id,
                    "bet_type": "Back",
                    "stake": back_stake,
                    "odds": back_odds,
                    "commission": back_commission,
                    "outcome": "Pending",
                    "profit_loss": net_profit,  # Initially calculated here
                    "event_name": event_name,
                    "criteria": criteria
                }).execute()

                # Insert Lay Bet
                supabase.table("bets").insert({
                    "matched_bet_id": matched_bet_id,
                    "sportsbook_id": sportsbook_id,
                    "sport_id": sport_id,
                    "bet_type": "Lay",
                    "stake": lay_stake,
                    "odds": lay_odds,
                    "commission": lay_commission,
                    "outcome": "Pending",
                    "profit_loss": -lay_liability,  # Initially negative liability
                    "event_name": event_name,
                    "criteria": criteria
                }).execute()

                st.success("Matched Bet logged successfully!")

        # Dutching
        elif bet_type == "Dutching":
            st.subheader("Dutching Bet")

            # Input fields for multiple outcomes
            outcomes = st.number_input("Number of Outcomes", min_value=1, step=1, value=2)
            dutch_stakes = []
            for i in range(outcomes):
                st.write(f"Outcome {i + 1}")
                odds = st.number_input(f"Odds for Outcome {i + 1} (decimal)", min_value=1.0, step=0.01, format="%.2f", key=f"odds_{i}")
                stake = st.number_input(f"Stake for Outcome {i + 1}", min_value=0.0, step=0.01, format="%.2f", key=f"stake_{i}")
                dutch_stakes.append((odds, stake))

            # Calculate Dutching profit/loss
            if st.button("Submit Dutching Bet"):
                total_stake = sum(stake for _, stake in dutch_stakes)
                max_profit = max((odds * stake - total_stake) for odds, stake in dutch_stakes)
                profit_loss = max_profit

                # Insert each outcome into the database
                for i, (odds, stake) in enumerate(dutch_stakes):
                    supabase.table("bets").insert({
                        "sportsbook_id": sportsbook_id,
                        "sport_id": sport_id,
                        "bet_type": "Dutching",
                        "stake": stake,
                        "odds": odds,
                        "outcome": "Pending",
                        "profit_loss": profit_loss,
                        "event_name": event_name,
                        "criteria": criteria
                    }).execute()

                st.success(f"Dutching Bet logged successfully! Maximum Profit/Loss: ${profit_loss:.2f}")

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
