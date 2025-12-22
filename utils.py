import pandas as pd
import numpy as np
from datetime import datetime


def custom_round(row):
    """Compute combined rushing+receiving yard points with special rounding.

    Intent:
    - Combine `rush_yds` and `rec_yds` to count how many whole "10-yard"
      units a player has across both categories, allowing small contributions
      from both to combine into a full 10 (e.g., 5 rush + 5 rec -> 1 point).
    - Special-case: if one category is zero and the other is < 10, return 0.
      This prevents small single-category values (or negative values) from
      producing non-zero or negative floor results.

    Examples:
    - rush=5, rec=5  -> (0.5 + 0.5) = 1.0 -> returns 1
    - rush=10, rec=0 -> (1.0 + 0) = 1.0 -> returns 1
    - rush=0, rec=9  -> special-case -> returns 0
    - rush=0, rec=-5 -> special-case -> returns 0 (avoids floor(-0.5) => -1)
    - rush=12, rec=8 -> (1.2 + 0.8) = 2.0 -> returns 2

    The function expects `row` to be a mapping-like object (e.g. a pandas
    Series) with keys `rush_yds` and `rec_yds`. Missing keys default to 0.
    """
    a, b = row.get('rush_yds', 0), row.get('rec_yds', 0)
    if (a == 0 and b < 10) or (b == 0 and a < 10):
        return 0
    else:
        combined_value = a / 10 + b / 10
        return np.floor(combined_value)


def handle_duplicate_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Resolve duplicate columns from DataFrame merges by filling missing values.

    When merging multiple DataFrames (e.g., offensive, defensive, kicking stats)
    with suffixes like '_df2' or '_df3', this function checks for suffixed columns
    and fills missing values in the original column with data from the suffixed one.
    The suffixed column is then dropped to avoid duplication.

    Need: Merging stats from different sources often creates overlapping columns;
    this ensures we don't lose data and maintain a clean DataFrame.

    Intention: Preserve as much complete data as possible after merges, prioritizing
    non-null values from the primary (original) column while supplementing with
    secondary sources.

    Args:
        df: DataFrame with potential duplicate columns from merges.

    Returns:
        Modified DataFrame with duplicates resolved and suffixed columns removed.
    """
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
    """Calculate fantasy football points from player stats using standard scoring rules.

    This function takes a DataFrame of raw player statistics and computes point
    totals for offensive, defensive, and kicking categories based on common
    fantasy football scoring (e.g., 1 pt per 10 rush/rec yards, 6 pts per TD).
    It handles missing columns gracefully and preserves legacy behaviors for
    compatibility.

    Need: Essential for converting raw NFL stats into fantasy points; used in
    the fantasy scoring pipeline to generate point totals for players.

    Intention: Provide accurate, consistent point calculations that match
    historical outputs, including special rounding for combined yards and
    double-counting of special teams TDs to maintain parity with prior systems.

    Args:
        df: DataFrame with player stats (e.g., pass_yds, rush_yds, etc.).

    Returns:
        DataFrame with added point columns (e.g., Total_Offensive_PTS) and
        cleaned stats.
    """
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
    # restore explicit recovered count (floor) to match legacy Lambda behavior
    df['FumblesRecovered'] = S('fum_recovered').apply(np.floor)
    df['FumblesRecovered_PTS'] = (S('fum_recovered').apply(np.floor) * 2).apply(np.floor)

    # Legacy parity: original Lambda added `SpecialTeamsTouchdowns_PTS` twice
    # (counting a special-teams touchdown double). Preserve that behavior
    # here to match historical outputs exactly.
    df['Total_defensive_PTS'] = (
        df['AssistedTackles_PTS'] + df['SoloTackles_PTS'] + df['PassesDefended_PTS'] +
        df['Sacks_PTS + Assisted Sacks_PTS'] + df['Safeties_PTS'] + df['SpecialTeamsTouchdowns_PTS'] +
        df['Interception_Defensive_PTS'] + df['SpecialTeamsTouchdowns_PTS'] + df['FumblesForced_PTS'] + df['FumblesRecovered_PTS']
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
    """Orchestrate merging of stats DataFrames and compute fantasy points.

    Merges three input DataFrames (typically offensive, defensive, kicking stats)
    on 'id', resolves duplicate columns by filling missing values, and applies
    point calculations using standard fantasy scoring rules.

    Need: Central function in the Streamlit app for processing user-uploaded
    CSV files into a single DataFrame with computed points, enabling download
    of results.

    Intention: Provide a clean, side-effect-free pipeline for fantasy football
    scoring, ensuring data integrity through merges and accurate point totals
    for league management.

    Args:
        df1, df2, df3: DataFrames with player stats, each containing an 'id' column.

    Returns:
        DataFrame with merged stats, resolved duplicates, and added point columns.
    """
    # Merge DataFrames on 'id' (outer join) and let handle_duplicate_columns resolve conflicts
    merged_df = df1.copy()
    merged_df = pd.merge(merged_df, df2, on='id', how='outer', suffixes=('', '_df2'))
    merged_df = pd.merge(merged_df, df3, on='id', how='outer', suffixes=('', '_df3'))

    final_df = handle_duplicate_columns(merged_df)
    result_df = CalculatePoints(final_df)
    return result_df


def aggregate_team_scores(final_df: pd.DataFrame, teams: list) -> dict:
    """Aggregate fantasy points into per-team and combined scores with transparency.

    Matches team rosters (from CSV or DataFrame) to computed player points,
    calculates per-player and team totals, and generates downloadable CSVs
    with calculation strings for auditability.

    Need: Essential for fantasy league scoring; takes individual player points
    and groups them by user-defined teams for league standings and reporting.

    Intention: Provide clear, verifiable team scores by enforcing ID-based
    matching, filling missing data, and including detailed calculation strings
    to build trust in the scoring process.

    Args:
        final_df: DataFrame with player points ('Total_Kicking_PTS', etc.) and 'id'.
        teams: List of team dicts/DataFrames with rosters and names.

    Returns:
        Dict with 'per_team' (DataFrames), 'per_team_csv' (bytes), 'combined_df',
        and 'combined_csv' for app downloads.
    """
    from io import BytesIO

    # Ensure final_df has the needed columns
    needed = ['id', 'Total_Kicking_PTS', 'Total_defensive_PTS', 'Total_Offensive_PTS']
    for c in needed:
        if c not in final_df.columns:
            raise ValueError(f"final_df missing required column: {c}")

    per_team = {}
    per_team_csv = {}
    combined_rows = []

    def load_team_df(team):
        if isinstance(team, dict) and 'df' in team and isinstance(team['df'], pd.DataFrame):
            return team['df'].copy()
        if isinstance(team, dict) and 'csv' in team:
            bio = BytesIO(team['csv'])
            return pd.read_csv(bio)
        # if team is a DataFrame itself
        if isinstance(team, pd.DataFrame):
            return team.copy()
        raise ValueError('team must be dict with csv or df, or a DataFrame')

    def find_id_col(df):
        lower = {c.lower(): c for c in df.columns}
        for candidate in ('id', 'player id', 'player_id', 'playerid'):
            if candidate in lower:
                return lower[candidate]
        # fallback to first numeric-looking column
        for c in df.columns:
            if df[c].dtype.kind in ('i', 'u', 'f'):
                return c
        # last fallback
        return df.columns[0]

    for team in teams:
        name = team.get('name') if isinstance(team, dict) else None
        if not name:
            name = getattr(team, 'name', None) or 'unnamed'
        try:
            team_df = load_team_df(team)
        except Exception:
            per_team[name] = pd.DataFrame()
            per_team_csv[name] = b''
            continue

        # Enforce that team CSVs MUST provide an id column (or accepted variants).
        lower_cols = {c.lower(): c for c in team_df.columns}
        id_candidates = ('id', 'player id', 'player_id', 'playerid')
        found_id = None
        for cand in id_candidates:
            if cand in lower_cols:
                found_id = lower_cols[cand]
                break

        if not found_id:
            # Do not attempt name-based matching — id is mandatory.
            per_team[name] = pd.DataFrame()
            per_team_csv[name] = b''
            continue

        # normalize id column name to 'id' for merging
        team_df = team_df.rename(columns={found_id: 'id'})
        merged = pd.merge(team_df, final_df, on='id', how='left', suffixes=('', '_final'))

        # Fill missing numeric columns with 0
        for c in ['Total_Kicking_PTS', 'Total_defensive_PTS', 'Total_Offensive_PTS']:
            if c not in merged.columns:
                merged[c] = 0
            merged[c] = pd.to_numeric(merged[c], errors='coerce').fillna(0)

        # Per-player total and calculation string
        merged['Total_Points'] = merged['Total_Kicking_PTS'] + merged['Total_defensive_PTS'] + merged['Total_Offensive_PTS']
        def make_calc(row):
            a = float(row['Total_Kicking_PTS'])
            b = float(row['Total_defensive_PTS'])
            c = float(row['Total_Offensive_PTS'])
            s = f"{a:.2f} + {b:.2f} + {c:.2f} = {a+b+c:.2f}"
            return s
        merged['calculation_str'] = merged.apply(make_calc, axis=1)

        # Team level transparency
        totals = merged['Total_Points'].fillna(0).tolist()
        if totals:
            parts = [f"{v:.2f}" for v in totals]
            team_total = sum(totals)
            team_calc = " + ".join(parts) + f" = {team_total:.2f}"
        else:
            team_calc = ""
            team_total = 0.0

        # Select columns to present
        present_cols = [c for c in merged.columns if c in ('id', 'first', 'last', 'position')]
        # ensure some name columns exist
        if 'first' not in merged.columns and 'player' in merged.columns:
            merged['first'] = merged['player']
        if 'last' not in merged.columns:
            merged['last'] = ''

        out_df = merged.copy()
        # keep useful columns plus calculation
        keep_cols = []
        for c in ('id', 'first', 'last', 'position'):
            if c in out_df.columns:
                keep_cols.append(c)
        keep_cols += ['Total_Kicking_PTS', 'Total_defensive_PTS', 'Total_Offensive_PTS', 'Total_Points', 'calculation_str']
        out_df = out_df.reindex(columns=[c for c in keep_cols if c in out_df.columns])

        # add team summary row metadata as attributes
        out_df.attrs['team_total'] = team_total
        out_df.attrs['team_calc'] = team_calc

        per_team[name] = out_df
        csv_bytes = out_df.to_csv(index=False).encode('utf-8')
        per_team_csv[name] = csv_bytes

        # prepare per-team DataFrame for combined output (preserve order, add team metadata)
        out_for_combined = out_df.copy()
        out_for_combined['team'] = name
        out_for_combined['team_calc'] = team_calc
        out_for_combined['team_total'] = team_total
        combined_rows.append(out_for_combined)

    # Build combined_df by concatenating per-team DataFrames (no all-NA separator frames)
    if combined_rows:
        combined_df = pd.concat(combined_rows, ignore_index=True)
        # Normalize dtypes to pandas nullable types to avoid future concat dtype inference changes
        try:
            combined_df = combined_df.convert_dtypes()
        except Exception:
            pass
    else:
        combined_df = pd.DataFrame()

    # For the downloadable combined CSV, join each per-team CSV string with a blank line between teams
    if combined_rows:
        csv_parts = []
        for part in combined_rows:
            csv_parts.append(part.to_csv(index=False))
        combined_csv_str = "\n".join(csv_parts)
        combined_csv = combined_csv_str.encode('utf-8')
    else:
        combined_csv = b''

    return {
        'per_team': per_team,
        'per_team_csv': per_team_csv,
        'combined_df': combined_df,
        'combined_csv': combined_csv,
    }
