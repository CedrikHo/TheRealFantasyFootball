#!/usr/bin/env python3
import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
from utils import compute, aggregate_team_scores

st.set_page_config(page_title="Fantasy Football Point Calculator", layout="wide")

if 'results' not in st.session_state:
    st.session_state['results'] = []
if 'teams' not in st.session_state:
    st.session_state['teams'] = []

st.title("Fantasy Football Point Calculator")

tabs = st.tabs(["Home", "Compute", "Teams", "Results"])

with tabs[0]:
    st.header("Welcome")
    st.write("Welcome to the Fantasy Page Calculation")

with tabs[1]:
    st.header("Compute")
    st.write("Upload three CSV files (all three are required).")
    col1, col2, col3 = st.columns(3)
    with col1:
        f1 = st.file_uploader("ALLPLAYERSTATS.CSV", type=['csv'], key='compute_f1')
        if f1 is not None and getattr(f1, 'name', '').upper() != 'ALLPLAYERSTATS.CSV':
            st.warning("Uploaded file name does not match ALLPLAYERSTATS.CSV — that's okay, but make sure this file contains all-player stats.")
    with col2:
        f2 = st.file_uploader("DEFENSIVESTATS.CSV", type=['csv'], key='compute_f2')
        if f2 is not None and getattr(f2, 'name', '').upper() != 'DEFENSIVESTATS.CSV':
            st.warning("Uploaded file name does not match DEFENSIVESTATS.CSV — that's okay, but make sure this file contains defensive stats.")
    with col3:
        f3 = st.file_uploader("KICKERSTATS.CSV", type=['csv'], key='compute_f3')
        if f3 is not None and getattr(f3, 'name', '').upper() != 'KICKERSTATS.CSV':
            st.warning("Uploaded file name does not match KICKERSTATS.CSV — that's okay, but make sure this file contains kicker stats.")

    all_present = (f1 is not None and f2 is not None and f3 is not None)
    if st.button("Submit", disabled=not all_present, key='submit_compute'):
        try:
            df1 = pd.read_csv(f1)
            df2 = pd.read_csv(f2)
            df3 = pd.read_csv(f3)
            result_df = compute(df1, df2, df3)
            csv_bytes = result_df.to_csv(index=False).encode('utf-8')
            timestamp = datetime.utcnow().isoformat(timespec='seconds') + 'Z'
            st.session_state['results'].append({'timestamp': timestamp, 'csv': csv_bytes})
            st.success("Computation finished and saved to Results.")
        except Exception as e:
            st.error(f"Error during computation: {e}")

with tabs[2]:
    st.header("Teams")
    st.write("Manage teams: upload one CSV per team (columns: first,last,player ID,position).")
    # callback to add a team (defined before widgets so it can safely mutate session_state)
    def _add_team_cb():
        team_name_cb = st.session_state.get('team_name')
        team_file_cb = st.session_state.get('team_file_upload')
        if not (team_name_cb and team_file_cb):
            return
        try:
            df_team = pd.read_csv(team_file_cb)
            csv_bytes = df_team.to_csv(index=False).encode('utf-8')
            timestamp = datetime.utcnow().isoformat(timespec='seconds') + 'Z'
            st.session_state['teams'].append({'name': team_name_cb, 'csv': csv_bytes, 'timestamp': timestamp, 'rows': len(df_team)})
            # note: do NOT assign to widget-backed keys like 'team_file_upload' — Streamlit forbids this
            # record success for display
            st.session_state['_last_team_added'] = team_name_cb
            # Note: some Streamlit installs don't expose `experimental_rerun()`.
            # Instead set a flag so UI can show a refresh hint to the user.
            st.session_state['_need_refresh'] = True
        except Exception as e:
            st.session_state['_team_add_error'] = str(e)

    col_name, col_file, col_action = st.columns([2, 3, 1])
    with col_name:
        team_name = st.text_input("Team name (e.g. Jake's team)", key='team_name')
    with col_file:
        team_file = st.file_uploader("Team CSV", type=['csv'], key='team_file_upload')
    with col_action:
        add_disabled = not (team_name and team_file)
        st.button("Add team", disabled=add_disabled, key='add_team', on_click=_add_team_cb)

    # show success / error from callback (if any)
    if st.session_state.get('_last_team_added'):
        st.success(f"Team '{st.session_state.pop('_last_team_added')}' added.")
    if st.session_state.get('_team_add_error'):
        st.error(f"Error reading team CSV: {st.session_state.pop('_team_add_error')}")

    st.markdown("---")
    st.subheader("Existing teams")
    if not st.session_state['teams']:
        st.info("No teams added yet.")
    else:
        for i, t in enumerate(list(st.session_state['teams'])):
            with st.expander(f"{t['name']} — {t['rows']} players — {t['timestamp']}"):
                st.download_button(label="Download CSV", data=t['csv'], file_name=f"{t['name'].replace(' ','_')}.csv", mime="text/csv", key=f"download_team_{i}")
                if st.button("Remove team", key=f"remove_team_{i}"):
                    st.session_state['teams'].pop(i)
                    st.experimental_rerun()

with tabs[3]:
    st.header("Results")
    results = st.session_state.get('results', [])

    # Only show a FINAL results DataFrame if the user has run the Compute (Submit) flow.
    if not results:
        st.info("No computed FINAL results available. Use the Compute tab and submit three files to generate results.")
        # If we asked the app to refresh after adding a team but couldn't programmatically rerun,
        # show a gentle hint to the user.
        if st.session_state.get('_need_refresh'):
            st.info("Team added — please refresh the page or switch tabs to see updated state.")
    else:
        final_df = None
        try:
            latest = results[-1]
            final_df = pd.read_csv(BytesIO(latest['csv']))
        except Exception as e:
            st.error(f"Unable to load computed result: {e}")

        if final_df is None:
            st.info("No FINAL results available. Run Compute to create a result CSV.")
        else:
            # show raw final_df download (only for compute-produced CSVs)
            st.subheader("Final Results (computed)")
            st.dataframe(final_df.head(20))
            st.download_button(label="Download FINALRESULTS.csv", data=final_df.to_csv(index=False).encode('utf-8'), file_name='FINALRESULTS.csv', mime='text/csv', key='download_final_csv')

        # Aggregate per team
        teams = st.session_state.get('teams', [])
        if not teams:
            st.info("No teams defined. Add teams in the Teams tab to see team aggregations.")
        else:
            try:
                agg = aggregate_team_scores(final_df, teams)
                per_team = agg['per_team']
                per_team_csv = agg['per_team_csv']
                combined_df = agg['combined_df']
                combined_csv = agg['combined_csv']

                st.markdown("---")
                st.subheader("Team Summaries")
                for idx, (team_name, df_team) in enumerate(per_team.items()):
                    with st.expander(f"{team_name} — {df_team.attrs.get('team_total', 0):.2f}"):
                        st.write(df_team)
                        # bar chart of player points
                        if 'Total_Points' in df_team.columns and not df_team.empty:
                            chart = df_team.set_index('id')['Total_Points']
                            st.bar_chart(chart)

                        st.write("Team calculation:", df_team.attrs.get('team_calc', ''))
                        st.download_button(label=f"Download {team_name} CSV", data=per_team_csv.get(team_name, b''), file_name=f"{team_name.replace(' ','_')}_calc.csv", mime='text/csv', key=f"download_team_result_{idx}")

                st.markdown("---")
                st.subheader("All Teams Combined")
                if not combined_df.empty:
                    st.dataframe(combined_df.head(50))
                    st.download_button(label="Download combined teams CSV", data=combined_csv, file_name='all_teams_calculations.csv', mime='text/csv', key='download_combined_teams')
                else:
                    st.info("Combined results are empty.")
            except Exception as e:
                st.error(f"Error aggregating team scores: {e}")
