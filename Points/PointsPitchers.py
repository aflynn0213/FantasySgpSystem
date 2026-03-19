"""PointsPitchers — points-league value engine for pitchers.

Mirrors SgpPitchers structure.  The ip_adj playing-time re-projection extends
the existing category logic (QS/SO/H/BB/ER/SV/HLD) to also scale the
additional stats that appear in a points scoring system (W, L, HR, R, HBP).

ip_adj stat scaling rules (consistent with SgpPitchers):
    QS, SV, HLD, W, L,  -> new_IP  / old_IP  × stat  (game-count based)
    SO                  -> new_TBF × K%
    H                   -> WHIP × new_IP − BB% × new_TBF
    BB                  -> new_TBF × BB%
    ER                  -> new_IP  × ERA / 9
    HR, R, HBP          -> new_TBF / old_TBF × stat  (user-specified simple scale)
    IP, TBF             -> replaced directly with new values
"""
from typing import Dict, Optional
import os
import pandas as pd

from Points.PointsCalculator import PointsCalculator
from utils.common_utils import parse_pitcher_points_config, get_repo_root


class PointsPitchers:
    """Compute per-player fantasy-points totals for pitchers.

    Args:
        data:   Same data dict produced by ExcelProjectionLoader:
                keys 'stats', 'proj_read', 'auc_calc', 'weeks',
                'period', 'projection', and optionally 'ip_adj'.
        ip_adj: Optional projection-system name to use for IP/TBF
                playing-time adjustment (e.g. ``"steamer"``).
                Mirrors the SGP ip_adj parameter exactly.
    """

    def __init__(self, data: Dict, ip_adj: Optional[str] = None) -> None:
        print("Initializing PointsPitchers...")

        # Mirror SgpBase attribute setup (without params / sgp_calculator)
        self.stats: pd.DataFrame = data["stats"].copy()
        self.proj_read: pd.DataFrame = data["proj_read"].copy()
        self.auc_calc: pd.DataFrame = data["auc_calc"].copy()
        self.weeks: int = data["weeks"]
        self.period: str = data.get("period", "pre")
        self.proj: str = data.get("projection", "unknown")
        self.ip_adj = ip_adj

        self.points_df: pd.DataFrame = pd.DataFrame()

        if ip_adj:
            print(f"Adjusting pitcher playing time via '{ip_adj}'...")
            self.__adjust_playing_time(ip_adj)

        self._calc = PointsCalculator(self.stats)

        print("Processing pitchers points scoring...")
        self._process_points()

        # Preserve IP and GS for display / downstream use
        self.points_df["IP"] = self.stats["IP"]
        self.points_df["GS"] = self.stats["GS"]

        self._finalize()
        print("***PointsPitchers initialized***")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _process_points(self) -> None:
        weights = parse_pitcher_points_config()
        self.points_df = self._calc.calc_points(weights)
        self.points_df["Total_PTS"] = self.points_df.filter(like="PTS_").sum(axis=1)

    def _finalize(self) -> None:
        """Attach Name/PlayerId (and ADP when available), then set MultiIndex."""
        self.points_df[["Name", "PlayerId"]] = self.stats[["Name", "PlayerId"]].values
        if "ADP" in self.proj_read.columns:
            adp_map = self.proj_read.drop_duplicates("PlayerId").set_index("PlayerId")["ADP"]
            self.points_df["ADP"] = self.stats["PlayerId"].map(adp_map).values
        self.points_df.set_index(["Name", "PlayerId"], inplace=True)

    def __adjust_playing_time(self, ip_adj: str) -> None:
        """Re-project pitcher counting stats to the ip_adj projection's IP/TBF.

        Extends SgpPitchers.__adjust_playing_time with the additional stats
        used by a points scoring system (W, L, HR, R, HBP).

        Scaling rules
        -------------
        Game-count  stats (QS, SV, HLD, W, L)   -> new_IP / old_IP  × stat
        K-rate      stat  (SO)                  -> new_TBF × K%
        Hit formula       (H)                   -> WHIP × new_IP − BB% × new_TBF
        Walk-rate   stat  (BB)                  -> new_TBF × BB%
        ER formula        (ER)                  -> new_IP × ERA / 9
        Simple TBF-scale  (HR, R,HBP)           -> new_TBF / old_TBF × stat
        """
        play_time_df = pd.read_excel(
            f'projections/fangraphs_pitching_{ip_adj}.xlsx', sheet_name=0
        )
        play_time_df["PlayerId"] = play_time_df["PlayerId"].astype(str)
        play_time_df = play_time_df.rename(columns={"IP": "new_IP", "TBF": "new_TBF"})

        self.stats = self.stats.merge(
            play_time_df[["PlayerId", "new_IP", "new_TBF"]],
            on="PlayerId",
            how="left",
        )

        # Pitchers absent from the ip_adj projection keep their original figures
        self.stats["new_IP"] = self.stats["new_IP"].fillna(self.stats["IP"])
        self.stats["new_TBF"] = self.stats["new_TBF"].fillna(self.stats["TBF"])

        new_ip_multiple = self.stats["new_IP"] / self.stats["IP"]
        new_tbf_multiple = self.stats["new_TBF"] / self.stats["TBF"]

        new_ip = self.stats["new_IP"]
        new_tbf = self.stats["new_TBF"]

        # ---- Stats shared with the categories engine (same formulas) ------
        for cat in ["QS", "SO", "H", "BB", "ER", "SV", "HLD"]:
            if cat not in self.stats.columns:
                continue
            if cat in ("QS", "SV", "HLD"):
                self.stats[cat] = new_ip_multiple * self.stats[cat]
            elif cat == "SO":
                self.stats[cat] = new_tbf * self.stats["K%"]
            elif cat == "H":
                self.stats[cat] = (
                    self.stats["WHIP"] * new_ip - self.stats["BB%"] * new_tbf
                )
            elif cat == "BB":
                self.stats[cat] = new_tbf * self.stats["BB%"]
            elif cat == "ER":
                self.stats[cat] = new_ip * self.stats["ERA"] / 9

        # ---- Additional stats used in points scoring ----------------------
        # Simple proportional scale by TBF ratio (per user spec)
        for cat in ["W", "L", "HR", "R", "HBP"]:
            if cat in self.stats.columns:
                self.stats[cat] = new_tbf_multiple * self.stats[cat]

        # Replace IP and TBF with the adjusted values
        self.stats["IP"] = new_ip
        self.stats["TBF"] = new_tbf
