import argparse
import time
from processor.SgpProcessor import SgpProcessor
from Sgp.SgpHitters import SgpHitters
from Sgp.SgpPitchers import SgpPitchers

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SGP Processing Script")
    parser.add_argument("-b", "--hitter_proj", type=str, required=True, help="Projection system for hitters (e.g., atc)")
    parser.add_argument("-p", "--pitcher_proj", type=str, required=True, help="Projection system for pitchers (e.g., atc)")
    parser.add_argument("-a", "--ip_adj", type=str, default=None, help="(Optional) Projection system to use for IP adjustment for pitchers")

    args = parser.parse_args()
    
    start_total_time = time.time()
    print("[*] Starting SGP processing...")

    print("[*] Processing hitters...")
    sgp_hit = SgpHitters(proj=args.hitter_proj)
    
    print("[*] Processing pitchers...")
    sgp_pit_adj = SgpPitchers(proj=args.pitcher_proj, ip_adj=args.ip_adj)
    
    print("[*] Running SgpProcessor for projections...")
    processor = SgpProcessor(sgp_hit, sgp_pit_adj)

    processor.export_sgp()
    print(f"[✔] Total execution time: {time.time() - start_total_time:.2f} seconds.")
