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
    st.header("Custom Fantasy Football Calculator")
    # show a local image if present (non-fatal)
    try:
        from pathlib import Path
        base = Path(__file__).parent
        img_path = base / "SylvainFootBallMeme.png"
        # Prefer image in Images/ folder, fall back to repo root for compatibility
        base = Path(__file__).resolve().parent
        candidates = [base / 'Images' / 'SylvainFootBallMeme.png', base / 'SylvainFootBallMeme.png']
        found = None
        for p in candidates:
            if p.exists():
                found = p
                break
        if found:
            st.image(str(found), width='stretch')
        else:
            st.info('SylvainFootBallMeme.png not found. Place it in `Images/` or the repo root to display.')
    except Exception:
        st.info("Unable to load Home image.")

    # Instructions and team template download
    st.markdown("**How to use this app**")
    st.markdown(
        "1. Download the team template CSV and use it to prepare one CSV per team.\n"
        "2. Go to the **Teams** tab: for each team add a name, upload that team's CSV, then click **Add team**.\n"
        "3. When all teams are uploaded, go to the **Compute** tab and upload the three required files: `ALLPLAYERSTATS.CSV`, `DEFENSIVESTATS.CSV`, and `KICKERSTATS.CSV`.\n"
        "4. Click **Submit** to run the calculator.\n"
        "5. Open the **Results** tab to download each team's calculated CSV, or download all teams combined.\n"
        "\nNotes: each team must have its own CSV file containing an `id` column that matches the computed results `id` values."
    )

    # provide a downloadable template (kept in repo under test/sample_csvs)
    try:
        template_path = base / 'test' / 'sample_csvs' / 'TEAMEXAMPLE.csv'
        if template_path.exists():
            with open(template_path, 'rb') as _tf:
                tpl_bytes = _tf.read()
            st.download_button('Download Team Template CSV', data=tpl_bytes, file_name='TEAMEXAMPLE.csv', mime='text/csv')
        else:
            st.info('Team template not found in repo (test/sample_csvs/TEAMEXAMPLE.csv)')
    except Exception:
        st.info('Unable to load team template for download')

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
        # Use the session_state-backed uploader values (more stable across reruns)
        f1_obj = st.session_state.get('compute_f1', f1)
        f2_obj = st.session_state.get('compute_f2', f2)
        f3_obj = st.session_state.get('compute_f3', f3)
        if not (f1_obj and f2_obj and f3_obj):
            st.error("Please upload all three CSVs before submitting.")
        else:
            try:
                df1 = pd.read_csv(f1_obj)
                df2 = pd.read_csv(f2_obj)
                df3 = pd.read_csv(f3_obj)
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

            # Validate presence of an id column and that every row has a non-empty id
            lower = {c.lower(): c for c in df_team.columns}
            id_candidates = ('id', 'player id', 'player_id', 'playerid')
            found_id = None
            for cand in id_candidates:
                if cand in lower:
                    found_id = lower[cand]
                    break
            if not found_id:
                st.session_state['_team_add_error'] = "Malformed team CSV: missing required 'id' column. Every row must include an id."
                return

            ids = df_team[found_id]
            missing_mask = ids.isnull() | (ids.astype(str).str.strip() == '')
            if missing_mask.any():
                st.session_state['_team_add_error'] = f"Malformed team CSV: {missing_mask.sum()} row(s) missing id. Every row must include an id."
                return

            csv_bytes = df_team.to_csv(index=False).encode('utf-8')
            timestamp = datetime.utcnow().isoformat(timespec='seconds') + 'Z'
            st.session_state['teams'].append({'name': team_name_cb, 'csv': csv_bytes, 'timestamp': timestamp, 'rows': len(df_team)})
            # record success for display
            st.session_state['_last_team_added'] = team_name_cb
            # set a hint that a refresh may be needed
            st.session_state['_need_refresh'] = True
        except Exception as e:
            st.session_state['_team_add_error'] = str(e)

    # callback to remove a team by index (use on_click so Streamlit reruns reliably)
    def _remove_team_cb(idx: int):
        teams = st.session_state.get('teams', [])
        if 0 <= idx < len(teams):
            removed = teams.pop(idx)
            st.session_state['teams'] = teams
            st.session_state['_last_team_removed'] = removed.get('name', f"team_{idx}")
            # set refresh hint so UI shows the updated state; do not call experimental_rerun()
            st.session_state['_need_refresh'] = True

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
                st.button("Remove team", key=f"remove_team_{i}", on_click=_remove_team_cb, args=(i,))

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
                # show a compact team totals table for quick scanning
                try:
                    totals_rows = []
                    for nm, df_t in per_team.items():
                        totals_rows.append({'team': nm, 'team_total': df_t.attrs.get('team_total', 0.0)})
                    if totals_rows:
                        import pandas as _pd
                        totals_df = _pd.DataFrame(totals_rows)
                        st.markdown("**Team totals**")
                        st.dataframe(totals_df.sort_values('team').reset_index(drop=True))
                except Exception:
                    pass
                for idx, (team_name, df_team) in enumerate(per_team.items()):
                    with st.expander(f"{team_name} — {df_team.attrs.get('team_total', 0):.2f}"):
                        st.write(df_team)
                        # bar chart of player points
                        if 'Total_Points' in df_team.columns and not df_team.empty:
                            chart = df_team.set_index('id')['Total_Points']
                            st.bar_chart(chart)

                        # display team total and calculation string explicitly
                        team_total = df_team.attrs.get('team_total', 0.0)
                        team_calc = df_team.attrs.get('team_calc', '')
                        st.markdown(f"**Team total:** {team_total:.2f}")
                        if team_calc:
                            st.write("Team calculation:", team_calc)
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
