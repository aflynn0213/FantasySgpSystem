"""PointsHitters — points-league value engine for batters.

Mirrors SgpHitters but uses a simple weighted-sum instead of z-scores.

Key derived stat:
    1B = H - 2B - 3B - HR  (singles, computed here so the config can weight them)
"""
from typing import Dict
import pandas as pd

from Points.PointsCalculator import PointsCalculator
from utils.common_utils import parse_hitter_points_config


class PointsHitters:
    """Compute per-player fantasy-points totals for hitters.

    Args:
        data:        Same data dict produced by ExcelProjectionLoader:
                     keys 'stats', 'proj_read', 'auc_calc', 'weeks',
                     'period', 'projection'.
        sb_included: When False, SB is forced to weight=0 so stolen bases
                     do not contribute to Total_PTS.  Mirrors the SGP flag.
    """

    def __init__(self, data: Dict, sb_included: bool = False) -> None:
        print("Initializing PointsHitters...")

        # Mirror SgpBase attribute setup (without params / sgp_calculator)
        self.stats: pd.DataFrame = data["stats"].copy()
        self.proj_read: pd.DataFrame = data["proj_read"].copy()
        self.auc_calc: pd.DataFrame = data["auc_calc"].copy()
        self.weeks: int = data["weeks"]
        self.period: str = data.get("period", "pre")
        self.proj: str = data.get("projection", "unknown")
        self.sb_included: bool = sb_included

        self.points_df: pd.DataFrame = pd.DataFrame()

        # Derive 1B (singles) before handing off to the calculator
        self.stats["1B"] = (
            self.stats["H"]
            - self.stats["2B"]
            - self.stats["3B"]
            - self.stats["HR"]
        ).clip(lower=0)  # guard against negative values on bad projection rows

        # Also expose PA (after SH adjustment) for downstream display
        self.stats["PA_SH"] = self.stats["PA"] - self.stats["SH"]

        self._calc = PointsCalculator(self.stats)

        print("Processing hitters points scoring...")
        self._process_points()

        # Attach display-only PA column (without SH)
        self.points_df["PA"] = self.stats["PA"].values

        self._finalize()
        print("***PointsHitters initialized***")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _process_points(self) -> None:
        weights = parse_hitter_points_config()

        # Honour the SB flag — zero out the weight rather than removing the column
        if not self.sb_included:
            weights["SB"] = 0.0

        # 1B is a derived stat; pass it explicitly so the calculator finds it
        derived = {"1B": self.stats["1B"]}

        raw_pts = self._calc.calc_points(weights, derived=derived)
        raw_pts["Total_PTS"] = raw_pts.filter(like="PTS_").sum(axis=1)

        # Optionally store SB points separately even when excluded from total
        if not self.sb_included and "SB" in weights:
            sb_weight_orig = parse_hitter_points_config().get("SB", 0.0)
            raw_pts["PTS_SB"] = self.stats["SB"] * sb_weight_orig  # kept for reference
            raw_pts["Total_PTS_wSB"] = raw_pts["Total_PTS"] + raw_pts["PTS_SB"]
        else:
            raw_pts["Total_PTS_wSB"] = raw_pts["Total_PTS"]

        self.points_df = raw_pts

    def _finalize(self) -> None:
        """Attach Name/PlayerId (and ADP when available), then set MultiIndex."""
        self.points_df[["Name", "PlayerId"]] = self.stats[["Name", "PlayerId"]].values
        if "ADP" in self.proj_read.columns:
            adp_map = self.proj_read.drop_duplicates("PlayerId").set_index("PlayerId")["ADP"]
            self.points_df["ADP"] = self.stats["PlayerId"].map(adp_map).values
        self.points_df.set_index(["Name", "PlayerId"], inplace=True)
