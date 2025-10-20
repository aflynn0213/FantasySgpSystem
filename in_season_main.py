import argparse
from calendar import week
import os
from pathlib import Path
import yaml

from Sgp.loaders.ExcelProjectionLoader import ExcelProjectionLoader
from Sgp.loaders.ExcelLeagueHistLoader import ExcelLeagueHistLoader
from Sgp.params.SgpParams import SgpParams
from Sgp.processor.TeamProcessor import TeamProcessor
from Sgp.calc.SgpCalculator import SgpCalculator
from Sgp.SgpHitters import SgpHitters
from Sgp.SgpPitchers import SgpPitchers
from utils.inseason_export_sgp import export_sgp
from utils.common_utils import get_repo_root, load_config, parse_config_categories

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

    hit_calc = SgpCalculator(params=params,
                             data=hit_data,
                             params=params,
                             teamProcessor=team_processor_hit,
                             role="hitting")

    pit_calc = SgpCalculator(params=params,
                             data=pit_data,
                             params=params,
                             teamProcessor=team_processor_pit,
                             role="pitching")

    # Sgp Objects
    hitters = SgpHitters(proj=hitter_proj,
                         weeks=weeks,
                         proj_read=hit_data["proj_read"],
                         stats=hit_data["stats"],
                         auc_calc=hit_data["auc_calc"],
                         params=params,
                         team_rate_processor=hit_team_proc,
                         sgp_calculator=hit_calc,
                         config=cfg)

    pitchers = SgpPitchers(proj=pitcher_proj,
                           weeks=weeks,
                           proj_read=pit_data["proj_read"],
                           stats=pit_data["stats"],
                           auc_calc=pit_data["auc_calc"],
                           replacement_levels=repl,
                           cat_stds=stds,
                           team_rate_processor=pit_team_proc,
                           sgp_calculator=pit_calc,
                           config=cfg)

    df_hit = hitters.sgp_df.copy()
    df_pit = pitchers.sgp_df.copy()

    # compute totals and export
    cols_included = list(range(0,6))
    if (not sb_included):
        cols_included.remove(3)
        df_hit['Total_SGP_wSB'] = df_hit.iloc[:,0:6].sum(axis=1)
    else:
        df_hit['Total_SGP_wSB'] = float("nan")
    df_hit['Total_SGP'] = df_hit.iloc[:, cols_included].sum(axis=1)
    df_hit = df_hit.sort_values(by="Total_SGP", ascending=False)

    df_pit['Total_SGP'] = df_pit.iloc[:, 0:6].sum(axis=1)
    df_pit = df_pit.sort_values(by="Total_SGP", ascending=False)

    file_name_hit = export_sgp(df_hit, sb_included, hitter_proj.split('_')[1], "hitting")
    file_name_pit = export_sgp(df_pit, False, pitcher_proj.split('_')[1], "pitching")

    print(f"[FINISHED] Exported SGP Hitter Results to {file_name_hit}")
    print(f"[FINISHED] Exported SGP Pitcher Results to {file_name_pit}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SGP Processing Script")
    parser.add_argument("-b", "--hitter_proj", type=str, required=True, help="e.g., atc_pre")
    parser.add_argument("-p", "--pitcher_proj", type=str, required=True, help="e.g., atc_pre")
    parser.add_argument("-a", "--ip_adj", type=str, default=None, help="(Optional) Projection system to use for IP adjustment for pitchers")
    parser.add_argument("-sb", "--sb_included", action="store_true", default=False, help="Include SB in totals")
    parser.add_argument("-wk", "--weeks_completed", type=int, default=None, help="Number of weeks completed in season (optional)")

    args = parser.parse_args()

    repo_root = get_repo_root()

    # if user did not pass weeks, derive from proj suffix (pre => 26)
    weeks = args.weeks_completed
    if weeks is None:
        #default to _pre or full season projections
        weeks = cfg["defaults"].get("weeks_in_season", 26)

    build_and_run(args.hitter_proj, args.pitcher_proj, args.sb_included, args.ip_adj, weeks, repo_root)