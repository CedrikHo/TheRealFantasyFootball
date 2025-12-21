#!/usr/bin/env python3
import streamlit as st
import pandas as pd
from datetime import datetime
from utils import compute

st.set_page_config(page_title="Fantasy Football Calculator", layout="wide")

if 'results' not in st.session_state:
    st.session_state['results'] = []

st.title("Fantasy Calculator")

tabs = st.tabs(["Home", "Compute", "Results"])

with tabs[0]:
    st.header("Welcome")
    st.write("Welcome to the Fantasy Page Calculation")

with tabs[1]:
    st.header("Compute")
    st.write("Upload three CSV files (all three are required).")
    col1, col2, col3 = st.columns(3)
    with col1:
        f1 = st.file_uploader("ALLPLAYERSTATS.CSV", type=['csv'], key='f1')
        if f1 is not None and getattr(f1, 'name', '').upper() != 'ALLPLAYERSTATS.CSV':
            st.warning("Uploaded file name does not match ALLPLAYERSTATS.CSV — that's okay, but make sure this file contains all-player stats.")
    with col2:
        f2 = st.file_uploader("DEFENSIVESTATS.CSV", type=['csv'], key='f2')
        if f2 is not None and getattr(f2, 'name', '').upper() != 'DEFENSIVESTATS.CSV':
            st.warning("Uploaded file name does not match DEFENSIVESTATS.CSV — that's okay, but make sure this file contains defensive stats.")
    with col3:
        f3 = st.file_uploader("KICKERSTATS.CSV", type=['csv'], key='f3')
        if f3 is not None and getattr(f3, 'name', '').upper() != 'KICKERSTATS.CSV':
            st.warning("Uploaded file name does not match KICKERSTATS.CSV — that's okay, but make sure this file contains kicker stats.")

    all_present = (f1 is not None and f2 is not None and f3 is not None)
    if st.button("Submit", disabled=not all_present):
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
    st.header("Results")
    results = st.session_state.get('results', [])
    if not results:
        st.info("No results yet.")
    else:
        rows = []
        for i, r in enumerate(results):
            rows.append({'index': i, 'timestamp': r['timestamp'], 'file': f"result_{i}.csv"})
        df_table = pd.DataFrame(rows)
        st.dataframe(df_table)
        for i, r in enumerate(results):
            fn = f"result_{i}_{r['timestamp'].replace(':','-')}.csv"
            st.download_button(label=f"Download result {i} ({r['timestamp']})",
                               data=r['csv'],
                               file_name=fn,
                               mime="text/csv")
