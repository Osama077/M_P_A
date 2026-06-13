"""
run_pipeline.py — Main Pipeline Entry Point
تشغيل كل الـ pipeline من الأول للآخر
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def run_full_pipeline(seasons=None):
    from config import SEASONS_LIST

    if seasons is None:
        seasons = SEASONS_LIST

    print("=" * 60)
    print(">>> MATCH PERFORMANCE ANALYSIS -- FULL PIPELINE")
    print(f">>> Seasons: {len(seasons)}")
    print("=" * 60)

    # Step 1: Data Loading
    from pipeline.data_loader import run as run_loader
    data = run_loader(seasons=seasons)
    if data is None:
        print("WARNING: No data loaded, aborting pipeline")
        return

    # Step 2: Feature Engineering
    from pipeline.feature_engineering import run as run_features
    run_features()

    # Step 3: xG Model
    from pipeline.xg_model import run as run_xg
    run_xg()

    # Step 4: VAEP Model
    from pipeline.vaep_model import run as run_vaep
    run_vaep()

    # Step 5: Scoring Model
    from pipeline.scoring_model import run as run_scoring
    run_scoring()

    # Step 6: Metadata (optional - builds player_info.parquet)
    from pipeline.metadata_loader import run as run_metadata
    run_metadata()

    # Step 7: Position-specific KPI Rating Engine
    from pipeline.position_kpi import run as run_position_kpi
    run_position_kpi()

    print("\n" + "=" * 60)
    print("FULL PIPELINE COMPLETE!")
    print("=" * 60)
    print("Run the API with: python run_api.py")


def run_api():
    import uvicorn
    from api.main import app
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=False)


def parse_seasons(season_str: str):
    """Parse comma-separated season labels into SEASONS_LIST entries."""
    from config import SEASONS_LIST
    labels = [s.strip() for s in season_str.split(",")]
    return [s for s in SEASONS_LIST if s[2] in labels]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Match Performance Analysis")
    parser.add_argument("--mode", choices=["pipeline","api","all"],
                        default="all", help="What to run")
    parser.add_argument("--seasons", type=str, default=None,
                        help="Comma-separated season labels, e.g. '2015/2016,2016/2017'")
    args = parser.parse_args()

    selected = parse_seasons(args.seasons) if args.seasons else None

    if args.mode in ("pipeline", "all"):
        run_full_pipeline(seasons=selected)
    if args.mode in ("api", "all"):
        run_api()
