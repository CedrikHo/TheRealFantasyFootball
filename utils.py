import pandas as pd
import numpy as np
from datetime import datetime


def custom_round(row):
    a, b = row.get('rush_yds', 0), row.get('rec_yds', 0)
    if (a == 0 and b < 10) or (b == 0 and a < 10):
        return 0
    else:
        combined_value = a / 10 + b / 10
        return np.floor(combined_value)


def handle_duplicate_columns(df: pd.DataFrame) -> pd.DataFrame:
    for col in list(df.columns):
        if col.endswith('_df2'):
            original_col = col.replace('_df2', '')
            if original_col in df.columns:
                df[original_col] = df.apply(
                    lambda row: row[original_col] if pd.notna(row[original_col]) else row[col],
                    axis=1
                )
                df.drop(columns=[col], inplace=True)
        elif col.endswith('_df3'):
            original_col = col.replace('_df3', '')
            if original_col in df.columns:
                df[original_col] = df.apply(
                    lambda row: row[original_col] if pd.notna(row[original_col]) else row[col],
                    axis=1
                )
                df.drop(columns=[col], inplace=True)
    return df


def CalculatePoints(df: pd.DataFrame) -> pd.DataFrame:
    # Defensive copy
    df = df.copy()

    # helper to return a Series for a column, or a zero Series if missing
    def S(col):
        if col in df.columns:
            try:
                return df[col].astype(float)
            except Exception:
                return df[col]
        return pd.Series(0, index=df.index, dtype=float)

    # Offensive
    df['PassingYards_PTS'] = (S('pass_yds') / 25).apply(np.floor)
    df['RushingYards_PTS'] = (S('rush_yds') / 10).apply(np.floor)
    df['ReceivingYards_PTS'] = (S('rec_yds').apply(np.floor) / 10).apply(np.floor)

    df['ReceivingYards_and_Rushing_Yards_SpecialRoundingCase'] = df.apply(custom_round, axis=1)

    df['ReceivingTouchdowns_PTS'] = (S('rec_td').apply(np.floor) * 6).apply(np.floor)
    df['PassingTouchdowns_PTS'] = (S('pass_td').apply(np.floor) * 4).apply(np.floor)
    df['RushingTouchdowns_PTS'] = (S('rush_td').apply(np.floor) * 6).apply(np.floor)
    df['Fumbles_Lost_PTS'] = 0
    df['Interception_Offensive_PTS'] = (S('pass_int').apply(np.floor) * -2).apply(np.floor)

    df.loc[df['PassingYards_PTS'] < 0, 'PassingYards_PTS'] = 0

    df['Total_Offensive_PTS'] = (
        df['PassingYards_PTS'] +
        df['ReceivingYards_and_Rushing_Yards_SpecialRoundingCase'] +
        df['ReceivingTouchdowns_PTS'] +
        df['PassingTouchdowns_PTS'] +
        df['RushingTouchdowns_PTS'] +
        df['Fumbles_Lost_PTS'] +
        df['Interception_Offensive_PTS']
    )

    # Defensive
    df['AssistedTackles_PTS'] = (S('tkl_astd').apply(np.floor) * 1).apply(np.floor)
    df['SoloTackles_PTS'] = (S('tkl_solo').apply(np.floor) * 1).apply(np.floor)
    df['PassesDefended_PTS'] = (S('pass_def').apply(np.floor) * 1).apply(np.floor)
    df['Sacks_PTS + Assisted Sacks_PTS'] = (S('def_sck') * 4)
    df['Safeties_PTS'] = 0
    df['Interception_Defensive_PTS'] = (S('def_int').apply(np.floor) * 6).apply(np.floor)
    df['SpecialTeamsTouchdowns_PTS'] = (S('def_td').apply(np.floor) * 6).apply(np.floor)
    df['FumblesForced_PTS'] = (S('fum_forced').apply(np.floor) * 4).apply(np.floor)
    df['FumblesRecovered_PTS'] = (S('fum_recovered').apply(np.floor) * 2).apply(np.floor)

    df['Total_defensive_PTS'] = (
        df['AssistedTackles_PTS'] + df['SoloTackles_PTS'] + df['PassesDefended_PTS'] +
        df['Sacks_PTS + Assisted Sacks_PTS'] + df['Safeties_PTS'] + df['SpecialTeamsTouchdowns_PTS'] +
        df['Interception_Defensive_PTS'] + df['FumblesForced_PTS'] + df['FumblesRecovered_PTS']
    )

    # Kicking
    df['ExtraPointsMade_PTS'] = (S('xp').apply(np.floor) * 1).apply(np.floor)
    df['FieldGoalsMade_PTS'] = S('fg').apply(np.floor) * 3
    df['Total_Kicking_PTS'] = df['FieldGoalsMade_PTS'] + df['ExtraPointsMade_PTS']

    # Force integer-like rounding on some base stats
    for c in ['pass_yds', 'rush_yds', 'rec_yds', 'rec_td', 'pass_td', 'rush_td', 'pass_int',
              'tkl_astd', 'tkl_solo', 'pass_def', 'def_td', 'def_int', 'fum_forced', 'fg_long', 'xp']:
        if c in df.columns:
            try:
                df[c] = df[c].apply(np.floor)
            except Exception:
                pass

    # Try to set some columns for readability if present
    for col in ['player', 'pos', 'Total_Offensive_PTS', 'Total_defensive_PTS', 'Total_Kicking_PTS']:
        if col in df.columns:
            try:
                df.set_index(df.pop(col), inplace=True)
                df.reset_index(inplace=True)
            except Exception:
                pass

    return df


def compute(df1: pd.DataFrame, df2: pd.DataFrame, df3: pd.DataFrame) -> pd.DataFrame:
    """Merge the three input DataFrames, handle duplicate columns, and calculate points.

    This function is adapted for Streamlit usage: it returns the resulting DataFrame
    so the caller can convert it to CSV and present a download link. It does not
    perform any AWS or side-effecting I/O.
    """
    # Merge DataFrames on 'id' (outer join) and let handle_duplicate_columns resolve conflicts
    merged_df = df1.copy()
    merged_df = pd.merge(merged_df, df2, on='id', how='outer', suffixes=('', '_df2'))
    merged_df = pd.merge(merged_df, df3, on='id', how='outer', suffixes=('', '_df3'))

    final_df = handle_duplicate_columns(merged_df)
    result_df = CalculatePoints(final_df)
    return result_df
