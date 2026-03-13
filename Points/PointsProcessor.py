"""PointsProcessor — combines PointsHitters + PointsPitchers results,
assigns replacement levels, and produces the final ranked DataFrames.

Mirrors SgpProcessor.  All position-eligibility and replacement-level
logic is identical; the only mechanical differences are:
  • sort/sum key → ``Total_PTS`` (not ``Total_SGP``)
  • col selection → dynamic ``PTS_*`` detection (not hardcoded iloc slices)
  • export column list → PTS_* columns
"""
import os
import pandas as pd
import numpy as np
from openpyxl import load_workbook
from openpyxl.styles import Font

from utils.common_utils import build_config_hitter_counts


class PointsProcessor:
    """Orchestrates end-to-end points-league ranking.

    Args:
        points_hitters:  Initialized PointsHitters instance.
        points_pitchers: Initialized PointsPitchers instance.
    """

    def __init__(self, points_hitters, points_pitchers) -> None:
        print("Initializing PointsProcessor...")
        self.weeks = points_hitters.weeks
        temp_hitters = points_hitters.points_df.copy()
        temp_pitchers = points_pitchers.points_df.copy()
        temp_auc_hit = points_hitters.auc_calc.copy()
        self.suffix = f"{points_hitters.proj}_{points_pitchers.proj}"

        self.sufficient_pos_counts, self.position_mapping = build_config_hitter_counts()

        print("Preparing hitter points data...")
        self.hitters_df = self.prepare_data(
            temp_hitters, "Hitter", points_hitters.sb_included, temp_auc_hit
        )
        print("Preparing pitcher points data...")
        self.pitchers_df = self.prepare_data(temp_pitchers, "Pitcher")

        cols_in_hitters_df = ["Name", "PlayerId", "Total_PTS", "RL", "VAR"]
        sorter = "VAR"
        if self.weeks < 26:
            cols_in_hitters_df = cols_in_hitters_df[:3]
            sorter = "Total_PTS"

        print("Combining data for final points rankings...")
        self.combined_df = (
            pd.concat(
                [
                    self.hitters_df[cols_in_hitters_df],
                    self.pitchers_df[["Name", "PlayerId", "Total_PTS", "RL", "VAR"]],
                ]
            )
            .groupby(["Name", "PlayerId"], as_index=False)
            .sum()
            .sort_values(by=sorter, ascending=False)
        )

        print("Points data prepared!")

    # ------------------------------------------------------------------
    # Data preparation
    # ------------------------------------------------------------------

    def prepare_data(self, df, player_type, sb_included=False, auc_calc=None):
        df = df.reset_index()

        # Identify PTS_* score columns dynamically
        pts_cols = [c for c in df.columns if c.startswith("PTS_")]

        if player_type == "Hitter":
            # Optionally exclude SB from total
            active_pts = pts_cols if sb_included else [c for c in pts_cols if c != "PTS_SB"]

            df["Total_PTS"] = df[active_pts].sum(axis=1)
            df["Total_PTS_wSB"] = df[pts_cols].sum(axis=1)

            df = df.sort_values(by="Total_PTS", ascending=False).reset_index(drop=True)

            if self.weeks == 26:
                auc_calc = auc_calc.rename(columns={"POS": "ELIG"})
                df = df.merge(auc_calc[["PlayerId", "ELIG"]], on="PlayerId", how="left")

                df["POS"] = df["ELIG"].apply(self.determine_pos)

                for pos in ["1B", "3B", "2B", "SS", "C", "OF", "DH"]:
                    df[f"{pos}_count"] = (df["POS"] == pos).cumsum()

                df["CI_count"] = df["1B_count"] + df["3B_count"]
                df["MI_count"] = df["2B_count"] + df["SS_count"]
                df["UTIL"] = self.assign_util(df)

                df.to_excel("temp_players_pts.xlsx")

                print("Computing replacement level (RL) for points hitters...")
                df = self.compute_replacement_level(df)

        else:  # Pitcher
            df["Total_PTS"] = df[pts_cols].sum(axis=1)
            df["Starter"] = np.where(df["GS"] > 5, 1, 0)

            df = df.sort_values(by="Total_PTS", ascending=False).reset_index(drop=True)

            print("Computing replacement level for points pitchers...")
            starter_rl = df[df["Starter"] == 1]["Total_PTS"].iloc[96]
            reliever_rl = df[df["Starter"] == 0]["Total_PTS"].iloc[48]

            df["RL"] = df.apply(
                lambda row: starter_rl if row["Starter"] == 1 else reliever_rl, axis=1
            )
            df["VAR"] = df["Total_PTS"] - df["RL"]

        print(f"[✔] {player_type} points data preparation complete!")
        return df

    # ------------------------------------------------------------------
    # Position helpers (identical logic to SgpProcessor)
    # ------------------------------------------------------------------

    def determine_pos(self, elig):
        if pd.isna(elig):
            return "ERROR"
        for pos in ["C", "2B", "OF", "SS", "3B", "1B", "DH"]:
            if pos in elig:
                return pos
        return "ERROR"

    def assign_util(self, df):
        """Assign UTIL position based on rostered thresholds."""
        print("Determining UTIL players (points)...")
        util_list = []
        util_count = 0

        for _, row in df.iterrows():
            limit = (
                self.sufficient_pos_counts[
                    self.position_mapping.get(row["POS"], "UTIL")
                ]
                + 1
            )
            if (
                row["POS"] == "DH"
                or (row["POS"] == "OF" and row["OF_count"] >= limit)
                or (row["POS"] == "C" and row["C_count"] >= limit)
                or (
                    row["POS"] in ["1B", "3B"]
                    and row["1B_count"] + row["3B_count"] >= limit
                )
                or (
                    row["POS"] in ["2B", "SS"]
                    and row["2B_count"] + row["SS_count"] >= limit
                )
            ):
                util_count += 1
                util_list.append(util_count)
            else:
                util_list.append("")

        return util_list

    def compute_replacement_level(self, df):
        """Compute RL per position using the rostered universe — mirrors SgpProcessor."""
        print("Identifying rostered universe (points)...")

        def get_rostered_universe(df):
            rostered = []
            counts = {k: 0 for k in self.sufficient_pos_counts}
            df_sorted = df.sort_values(by="Total_PTS", ascending=False).reset_index(
                drop=True
            )

            for _, row in df_sorted.iterrows():
                assigned = False
                pos = self.position_mapping[row["POS"]]
                needed = self.sufficient_pos_counts[pos]

                if pos == "CI" and counts["CI"] < needed:
                    counts["CI"] += 1
                    rostered.append(row)
                    assigned = True
                elif pos == "MI" and counts["MI"] < needed:
                    counts["MI"] += 1
                    rostered.append(row)
                    assigned = True
                elif pos == "C" and counts["C"] < needed:
                    counts["C"] += 1
                    rostered.append(row)
                    assigned = True
                elif pos == "OF" and counts["OF"] < needed:
                    counts["OF"] += 1
                    rostered.append(row)
                    assigned = True

                if not assigned and counts["UTIL"] < self.sufficient_pos_counts["UTIL"]:
                    counts["UTIL"] += 1
                    rostered.append(row)

                if sum(counts.values()) >= 156:
                    break

            return (
                pd.DataFrame(rostered)
                .sort_values(by="Total_PTS", ascending=False)
                .reset_index(drop=True)
            )

        rostered_df = get_rostered_universe(df)
        rostered_df.to_excel("rostered_pts.xlsx")
        print(f"Rostered universe identified ({len(rostered_df)} players).")

        print("Finding worst rostered / best non-rostered per position...")
        worst_rostered = {}
        for pos in ["1B", "3B", "2B", "SS", "C", "OF"]:
            eligible_players = rostered_df[
                rostered_df["ELIG"].str.contains(pos, na=False)
            ].copy()

            def is_available(row, pos=pos):
                if row["POS"] == pos:
                    return True
                mapped_pos = self.position_mapping.get(row["POS"], row["POS"])
                if mapped_pos != "UTIL" and row[f"{mapped_pos}_count"] <= self.sufficient_pos_counts.get(
                    mapped_pos, float("inf")
                ):
                    return False
                return True

            eligible_players = eligible_players[
                eligible_players.apply(is_available, axis=1)
            ]
            worst_player = eligible_players.nsmallest(1, "Total_PTS")
            worst_rostered[pos] = worst_player["Total_PTS"].values[0]
            print(
                f"[DEBUG] Worst rostered {pos}: {worst_player['Name'].values[0]} "
                f"(PTS: {worst_rostered[pos]:.1f})"
            )

        best_replacements = {}
        for pos in worst_rostered:
            best_player = df[
                ~df["PlayerId"].isin(rostered_df["PlayerId"])
                & df["ELIG"].str.contains(pos, na=False)
            ].nlargest(1, "Total_PTS")
            if not best_player.empty:
                best_replacements[pos] = best_player["Total_PTS"].values[0]
                print(
                    f"[DEBUG] Best non-rostered {pos}: {best_player['Name'].values[0]} "
                    f"(PTS: {best_replacements[pos]:.1f})"
                )
            else:
                best_replacements[pos] = float("-inf")

        rl_values = {
            pos: (best_replacements[pos] + worst_rostered[pos]) / 2
            if worst_rostered[pos] != float("inf")
            and best_replacements[pos] != float("-inf")
            else float("inf")
            for pos in worst_rostered
        }

        max_worst = max(
            (v for v in worst_rostered.values() if v != float("inf")), default=float("inf")
        )
        max_best = max(
            (v for v in best_replacements.values() if v != float("-inf")), default=float("-inf")
        )
        rl_values["DH"] = (max_best + max_worst) / 2

        df["RL"] = df["ELIG"].apply(
            lambda elig: min(
                rl_values.get(pos, float("inf")) for pos in elig.split("/")
            )
        )
        df["VAR"] = df["Total_PTS"] - df["RL"]

        print("Points replacement level calculation complete!")
        return df

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_points(self, sb: bool) -> None:
        """Write a combined Excel workbook with Hitters / Pitchers / Combined sheets."""
        print("Exporting Points Results...")

        SAVE_FOLDER = os.path.join(os.getcwd(), "results")
        os.makedirs(SAVE_FOLDER, exist_ok=True)

        sb_string = "_sb_included" if sb else ""
        file_name = f"results/Points_Results_{self.suffix}{sb_string}.xlsx"

        # Dynamic PTS_ columns for each tab
        hit_pts_cols = [c for c in self.hitters_df.columns if c.startswith("PTS_")]
        pit_pts_cols = [c for c in self.pitchers_df.columns if c.startswith("PTS_")]

        hit_export = ["Name", "PlayerId", "PA"] + hit_pts_cols + ["Total_PTS_wSB", "Total_PTS", "RL", "VAR"]
        pit_export = ["Name", "PlayerId", "IP"] + pit_pts_cols + ["Total_PTS", "RL", "VAR"]

        # Drop cols that don't exist yet (in-season shortcut)
        hit_export = [c for c in hit_export if c in self.hitters_df.columns]
        pit_export = [c for c in pit_export if c in self.pitchers_df.columns]

        with pd.ExcelWriter(file_name) as writer:
            self.hitters_df[hit_export].to_excel(writer, sheet_name="Hitters", index=False)
            self.pitchers_df[pit_export].to_excel(writer, sheet_name="Pitchers", index=False)
            self.combined_df.to_excel(writer, sheet_name="Combined", index=False)

        # Apply blue/bold formatting to pitchers in the Combined sheet
        wb = load_workbook(file_name)
        ws_pitchers = wb["Pitchers"]
        ws_combined = wb["Combined"]
        blue_underlined = Font(color="0000FF", underline="single", bold=True)

        pitcher_ids = set()
        for row in ws_pitchers.iter_rows(min_row=2, values_only=True):
            name, player_id, *_ = row
            pitcher_ids.add((name, player_id))

        for row in ws_combined.iter_rows(min_row=2, max_row=ws_combined.max_row):
            if (row[0].value, row[1].value) in pitcher_ids:
                for cell in row:
                    cell.font = blue_underlined

        wb.save(file_name)
        print(f"Exported Points Results to {file_name}")
