import argparse
from calendar import week
import os
from pathlib import Path
import yaml

from Sgp.loaders.ExcelProjectionLoader import ExcelProjectionLoader
from Sgp.loaders.ExcelLeagueHistLoader import ExcelLeagueHistLoader
from Sgp.params.SgpParams import SgpParams
from Sgp.processor.TeamProcessor import TeamProcessor
from Sgp.processor.SgpProcessor import SgpProcessor
from Sgp.calc.SgpCalculator import SgpCalculator
from Sgp.SgpHitters import SgpHitters
from Sgp.SgpPitchers import SgpPitchers
from Points.PointsHitters import PointsHitters
from Points.PointsPitchers import PointsPitchers
from Points.PointsProcessor import PointsProcessor
from utils.inseason_export_sgp import export_sgp, export_points
from utils.common_utils import get_repo_root, load_config

cfg = load_config(os.path.join(get_repo_root(), "config.yml"))

def build_and_run(hitter_proj, pitcher_proj, sb_included, ip_adj, weeks, repo_root):
    # Prepare loaders
    proj_loader = ExcelProjectionLoader(base_dir=repo_root, weeks=weeks)
    league_loader = ExcelLeagueHistLoader(workbook_path=os.path.join(repo_root, cfg["league_params"]["workbook_path"]),
                                          sheet_name=cfg["league_params"].get("parameters_sheet", "Parameters"))
    
    # Load projection data
    hit_data = proj_loader.load(hitter_proj, "hitting")
    pit_data = proj_loader.load(pitcher_proj, "pitching",ip_adj)
    
    params = SgpParams()

    # Load league parameters (Parameters sheet -> mapping -> repl/std dicts)
    league_loader.load()
    params.process_parameters_map(league_loader.data)

    # Build team processors and calculators (pass replacement/stds to calculators)
    team_processor_hit = TeamProcessor(hit_data, params)
    team_processor_pit = TeamProcessor(pit_data, params)

    hit_calc = SgpCalculator(data=hit_data,
                             params=params,
                             teamProcessor=team_processor_hit,
                             role="hitting")

    pit_calc = SgpCalculator(data=pit_data,
                             params=params,
                             teamProcessor=team_processor_pit,
                             role="pitching")

    # Sgp Objects
    hitters = SgpHitters(data=hit_data,
                         params=params,
                         sgp_calculator=hit_calc,
                         sb_included=sb_included)

    pitchers = SgpPitchers(data=pit_data,
                           params=params,
                           sgp_calculator=pit_calc,
                           ip_adj=ip_adj)

    processor = SgpProcessor(hitters, pitchers)
    processor.export_sgp(sb_included)

    # Build a consistent label: {h}_{p}[_{ip_adj}]_{period}
    _period = hitter_proj.split('_')[1]
    _ip_str = f"_{ip_adj}" if ip_adj else ""
    _label = f"{processor.suffix}{_ip_str}_{_period}"

    file_name_hit      = export_sgp(processor.hitters_df,  sb_included, _label, "hitting")
    file_name_pit      = export_sgp(processor.pitchers_df, False,        _label, "pitching")
    file_name_combined = export_sgp(processor.combined_df, sb_included,  _label, "combined")

    print(f"[FINISHED] Exported SGP Hitter Results to {file_name_hit}")
    print(f"[FINISHED] Exported SGP Pitcher Results to {file_name_pit}")
    print(f"[FINISHED] Exported SGP Combined Results to {file_name_combined}")


def build_and_run_points(hitter_proj, pitcher_proj, sb_included, ip_adj, weeks, repo_root):
    """Points-league parallel of build_and_run.  No league-history Excel needed."""
    proj_loader = ExcelProjectionLoader(base_dir=repo_root, weeks=weeks)

    hit_data = proj_loader.load(hitter_proj, "hitting")
    pit_data = proj_loader.load(pitcher_proj, "pitching", ip_adj)

    hitters = PointsHitters(data=hit_data, sb_included=sb_included)
    pitchers = PointsPitchers(data=pit_data, ip_adj=ip_adj)

    processor = PointsProcessor(hitters, pitchers)
    processor.export_points(sb_included)

    _period = hitter_proj.split("_")[1]
    _ip_str = f"_{ip_adj}" if ip_adj else ""
    _label  = f"{processor.suffix}{_ip_str}_{_period}"

    file_name_hit      = export_points(processor.hitters_df,  sb_included, _label, "hitting")
    file_name_pit      = export_points(processor.pitchers_df, False,        _label, "pitching")
    file_name_combined = export_points(processor.combined_df, sb_included,  _label, "combined")

    print(f"[FINISHED] Exported Points Hitter Results to {file_name_hit}")
    print(f"[FINISHED] Exported Points Pitcher Results to {file_name_pit}")
    print(f"[FINISHED] Exported Points Combined Results to {file_name_combined}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SGP / Points Processing Engine for Fantasy Baseball Projections")
    parser.add_argument("-b", "--hitter_proj", type=str, required=True, help="e.g., atc_pre")
    parser.add_argument("-p", "--pitcher_proj", type=str, required=True, help="e.g., atc_pre")
    parser.add_argument("-a", "--ip_adj", type=str, default=None, help="(Optional) Projection system to use for IP adjustment for pitchers")
    parser.add_argument("-sb", "--sb_included", action="store_true", default=False, help="Include SB in totals")
    parser.add_argument("-wk", "--weeks_completed", type=int, default=None, help="Number of weeks completed in season (optional)")
    parser.add_argument(
        "-m", "--mode",
        type=str,
        default="categories",
        choices=["categories", "points"],
        help="Scoring mode: 'categories' (default, SGP) or 'points' (weighted-sum points league)",
    )

    args = parser.parse_args()
    print(f"Running with hitter_proj={args.hitter_proj}, pitcher_proj={args.pitcher_proj}, sb_included={args.sb_included}, ip_adj={args.ip_adj}, weeks_completed={args.weeks_completed}, mode={args.mode}")
    
    repo_root = get_repo_root()

    # if user did not pass weeks, derive from proj suffix (pre => 26)
    weeks = args.weeks_completed
    if weeks is None:
        #default to _pre or full season projections
        weeks = cfg["defaults"].get("weeks_in_season", 26)

    if args.mode == "points":
        build_and_run_points(args.hitter_proj, args.pitcher_proj, args.sb_included, args.ip_adj, weeks, repo_root)
    else:
        build_and_run(args.hitter_proj, args.pitcher_proj, args.sb_included, args.ip_adj, weeks, repo_root)

    
