"""PointsCalculator — straightforward weighted-sum scoring engine.

No replacement levels, no z-scores.  Each stat is multiplied by its
configured point value and the per-player total is summed across all
active (non-zero weight) stats.
"""
from typing import Dict, Optional
import pandas as pd


class PointsCalculator:
    """Compute fantasy-points totals from a projection DataFrame.

    Args:
        stats: Player projection DataFrame (one row per player).
               Must share the same index as the objects that consume results.
    """

    def __init__(self, stats: pd.DataFrame) -> None:
        self._stats = stats.copy()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_stats(self, stats: pd.DataFrame) -> None:
        """Replace internal stats — call after ip_adj re-projection."""
        self._stats = stats.copy()

    def calc_points(
        self,
        stat_weights: Dict[str, float],
        derived: Optional[Dict[str, pd.Series]] = None,
    ) -> pd.DataFrame:
        """Multiply each stat by its weight and return a PTS_<stat> DataFrame.

        Stats with a weight of exactly 0 are skipped so their column never
        appears in the output, keeping the results tidy.

        Args:
            stat_weights: Mapping of {stat_name: point_value}.  Values may
                          be negative (e.g. ER → -1) or fractional (SO → 0.5).
            derived:      Optional pre-computed Series that override (or
                          supplement) what is present in the stats DataFrame.
                          Keyed by the same stat names used in stat_weights.

        Returns:
            DataFrame indexed like self._stats with columns ``PTS_<stat>``
            for every stat whose weight is non-zero.
        """
        derived = derived or {}
        result: Dict[str, pd.Series] = {}

        for stat, weight in stat_weights.items():
            if weight == 0:
                continue  # skip zero-weighted stats — no output column

            if stat in derived:
                series = derived[stat]
            elif stat in self._stats.columns:
                series = self._stats[stat]
            else:
                print(f"[WARN] Points: stat '{stat}' not found in projections — skipping")
                continue

            result[f"PTS_{stat}"] = series * weight

        return pd.DataFrame(result, index=self._stats.index)
