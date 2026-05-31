"""
run_pipeline.py — Main Pipeline Entry Point
تشغيل كل الـ pipeline من الأول للآخر
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def run_full_pipeline():
    print("=" * 60)
    print(">>> MATCH PERFORMANCE ANALYSIS -- FULL PIPELINE")
    print("=" * 60)

    # Step 1: Data Loading
    from pipeline.data_loader import run as run_loader
    run_loader()

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

    print("\n" + "=" * 60)
    print("🎉 FULL PIPELINE COMPLETE!")
    print("=" * 60)
    print("Run the API with: python run_api.py")


def run_api():
    import uvicorn
    from api.main import app
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Match Performance Analysis")
    parser.add_argument("--mode", choices=["pipeline","api","all"],
                        default="all", help="What to run")
    args = parser.parse_args()

    if args.mode in ("pipeline", "all"):
        run_full_pipeline()
    if args.mode in ("api", "all"):
        run_api()
