import sys
import argparse
from typing import Dict, Any, List

import pandas as pd
import numpy as np


def _find_id_column(df: pd.DataFrame) -> str:
    lower = {c.lower(): c for c in df.columns}
    for candidate in ('id', 'player id', 'player_id', 'playerid'):
        if candidate in lower:
            return lower[candidate]
    for c in df.columns:
        if df[c].dtype.kind in ('i', 'u', 'f'):
            return c
    return df.columns[0]


def compare_csvs(path_a: str, path_b: str, id_col: str = 'id', sort: bool = True,
                 float_tol: float = 1e-6, max_diffs: int = 200) -> Dict[str, Any]:
    """Compare two CSV files and return a structured diff report.

    The comparison is id-centric: both files are sorted/merged by the provided
    `id_col` (case-insensitive lookup). Numeric columns are compared with
    absolute tolerance `float_tol`. String columns compare after stripping
    whitespace.

    Returns a dict containing keys: `cols_only_in_a`, `cols_only_in_b`,
    `ids_only_in_a`, `ids_only_in_b`, `diffs` (list of difference records).
    """
    a = pd.read_csv(path_a, dtype=object)
    b = pd.read_csv(path_b, dtype=object)

    # Normalize column whitespace
    a.columns = [c.strip() for c in a.columns]
    b.columns = [c.strip() for c in b.columns]

    # Resolve id column name if not present exactly
    if id_col not in a.columns:
        id_col = _find_id_column(a) if id_col not in a.columns else id_col
    if id_col not in b.columns:
        id_col = _find_id_column(b) if id_col not in b.columns else id_col

    if sort:
        try:
            a = a.sort_values(by=id_col).reset_index(drop=True)
        except Exception:
            a = a.reset_index(drop=True)
        try:
            b = b.sort_values(by=id_col).reset_index(drop=True)
        except Exception:
            b = b.reset_index(drop=True)

    cols_a = set(a.columns)
    cols_b = set(b.columns)
    cols_only_in_a = sorted(list(cols_a - cols_b))
    cols_only_in_b = sorted(list(cols_b - cols_a))

    # Build merged frame on id to ease comparisons
    merged = a.merge(b, on=id_col, how='outer', suffixes=('_A', '_B'), indicator=True)

    ids_only_in_a = merged.loc[merged['_merge'] == 'left_only', id_col].dropna().astype(str).tolist()
    ids_only_in_b = merged.loc[merged['_merge'] == 'right_only', id_col].dropna().astype(str).tolist()

    common_cols = sorted(list((cols_a & cols_b) - {id_col}))

    diffs: List[Dict[str, Any]] = []

    for _, row in merged.iterrows():
        row_id = row.get(id_col)
        if pd.isna(row_id):
            row_id = ''
        row_id = str(row_id)
        if row_id in ids_only_in_a or row_id in ids_only_in_b:
            continue
        for col in common_cols:
            va = row.get(f"{col}_A") if f"{col}_A" in merged else row.get(col)
            vb = row.get(f"{col}_B") if f"{col}_B" in merged else row.get(col)

            # Normalize empty/NA
            if pd.isna(va):
                va_norm = None
            else:
                va_norm = str(va).strip()
            if pd.isna(vb):
                vb_norm = None
            else:
                vb_norm = str(vb).strip()

            if va_norm is None and vb_norm is None:
                continue

            # Try numeric comparison
            na = pd.to_numeric(va_norm, errors='coerce') if va_norm is not None else np.nan
            nb = pd.to_numeric(vb_norm, errors='coerce') if vb_norm is not None else np.nan

            both_numeric = not (np.isnan(na) and np.isnan(nb))
            equal = False
            diff_val = None
            if both_numeric:
                na_f = 0.0 if np.isnan(na) else float(na)
                nb_f = 0.0 if np.isnan(nb) else float(nb)
                if np.isclose(na_f, nb_f, atol=float_tol, rtol=1e-8):
                    equal = True
                else:
                    diff_val = na_f - nb_f
            else:
                # String compare (case-sensitive after strip)
                if va_norm == vb_norm:
                    equal = True
                else:
                    diff_val = (va_norm, vb_norm)

            if not equal:
                diffs.append({
                    'id': row_id,
                    'column': col,
                    'value_a': va_norm,
                    'value_b': vb_norm,
                    'difference': diff_val,
                })
                if len(diffs) >= max_diffs:
                    break
        if len(diffs) >= max_diffs:
            break

    result = {
        'cols_only_in_a': cols_only_in_a,
        'cols_only_in_b': cols_only_in_b,
        'ids_only_in_a': ids_only_in_a,
        'ids_only_in_b': ids_only_in_b,
        'diffs': diffs,
        'diff_count': len(diffs),
    }
    return result


def print_report(res: Dict[str, Any], limit: int = 200, out=sys.stdout) -> None:
    out.write(f"Columns only in A: {res['cols_only_in_a']}\n")
    out.write(f"Columns only in B: {res['cols_only_in_b']}\n")
    out.write(f"IDs only in A ({len(res['ids_only_in_a'])}): {res['ids_only_in_a'][:limit]}\n")
    out.write(f"IDs only in B ({len(res['ids_only_in_b'])}): {res['ids_only_in_b'][:limit]}\n")
    out.write(f"Differences found: {res['diff_count']}\n")
    if res['diff_count']:
        out.write('\nSample diffs (first {}):\n'.format(min(limit, res['diff_count'])))
        for d in res['diffs'][:limit]:
            out.write(f"id={d['id']} col={d['column']} A={d['value_a']} B={d['value_b']} diff={d['difference']}\n")


def _main(argv: List[str]) -> int:
    p = argparse.ArgumentParser(description='Compare two CSV files (id-centric)')
    p.add_argument('a', help='Path to CSV A (reference)')
    p.add_argument('b', help='Path to CSV B (new)')
    p.add_argument('--id-col', default='id', help='ID column name or candidate')
    p.add_argument('--tol', type=float, default=1e-6, help='Numeric absolute tolerance')
    p.add_argument('--max-diffs', type=int, default=200, help='Maximum diffs to collect')
    args = p.parse_args(argv)

    res = compare_csvs(args.a, args.b, id_col=args.id_col, float_tol=args.tol, max_diffs=args.max_diffs)
    print_report(res)
    return 0


if __name__ == '__main__':
    raise SystemExit(_main(sys.argv[1:]))
