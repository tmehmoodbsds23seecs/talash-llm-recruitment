"""
backend/modules/qs_ranking_matcher.py
Matches university names to QS World Rankings.
Reads from an Excel file if present; falls back to a built-in curated list.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import pandas as pd

QS_RANKING_PATH = Path(__file__).resolve().parents[2] / "qs_rankings" / "2026 QS World University Rankings 1.3 (For qs.com).xlsx"

# ── Built-in fallback rankings (Pakistan + common international) ──────────────
BUILTIN_RANKINGS: dict[str, tuple[str, int]] = {
    "quaid-i-azam university":              ("Quaid-i-Azam University",              551),
    "national university of sciences":      ("NUST",                                  334),
    "nust":                                 ("NUST",                                  334),
    "lahore university of management":      ("LUMS",                                  701),
    "lums":                                 ("LUMS",                                  701),
    "university of engineering":            ("UET Lahore",                             801),
    "uet":                                  ("UET Lahore",                             801),
    "university of karachi":                ("University of Karachi",                  801),
    "comsats":                              ("COMSATS University Islamabad",           751),
    "aga khan university":                  ("Aga Khan University",                    501),
    "fast":                                 ("FAST-NUCES",                             801),
    "nuces":                                ("FAST-NUCES",                             801),
    "mit":                                  ("Massachusetts Institute of Technology",    1),
    "stanford":                             ("Stanford University",                      5),
    "harvard":                              ("Harvard University",                       4),
    "oxford":                               ("University of Oxford",                     3),
    "cambridge":                            ("University of Cambridge",                  2),
    "imperial college":                     ("Imperial College London",                  6),
    "university of toronto":                ("University of Toronto",                   25),
    "university of melbourne":              ("University of Melbourne",                 33),
}

_QS_DF: pd.DataFrame | None = None


def _load_excel() -> pd.DataFrame | None:
    global _QS_DF
    if _QS_DF is not None:
        return _QS_DF
    if not QS_RANKING_PATH.exists():
        return None
    try:
        _QS_DF = pd.read_excel(QS_RANKING_PATH, header=2)
        return _QS_DF
    except Exception:
        return None


def _clean(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def get_qs_ranking(uni_name: str) -> tuple[str, int | None]:
    """
    Returns (matched_name, qs_rank_int_or_None).
    Tries Excel first, then built-in fallback, then None.
    """
    if not uni_name:
        return uni_name, None

    # 1. Try Excel file
    df = _load_excel()
    if df is not None and "Name" in df.columns and "Rank" in df.columns:
        search = _clean(uni_name)
        for _, row in df.iterrows():
            raw = row["Name"]
            if not isinstance(raw, str):
                continue
            c = _clean(raw)
            if search == c or (len(search) > 10 and search in c) or (len(c) > 10 and c in search):
                rank_val = row["Rank"]
                if isinstance(rank_val, (int, float)):
                    return raw, int(rank_val)
                if isinstance(rank_val, str):
                    nums = re.findall(r"\d+", rank_val)
                    if nums:
                        return raw, int(nums[0])

    # 2. Fallback built-in list
    search_lower = uni_name.lower()
    for key, (matched, rank) in BUILTIN_RANKINGS.items():
        if key in search_lower or search_lower in key:
            return matched, rank

    return uni_name, None
