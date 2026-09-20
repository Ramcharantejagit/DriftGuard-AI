import argparse
import os
from pathlib import Path
import uvicorn

def main():
    parser = argparse.ArgumentParser(description="Run DriftGuard AI")
    parser.add_argument(
        "--watch",
        default=os.getenv("DRIFTGUARD_WATCH_PATH", str(Path(__file__).parent / "demo_project")),
        help="Project directory to monitor",
    )
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    os.environ["DRIFTGUARD_WATCH_PATH"] = str(Path(args.watch).resolve())
    print(f"\n🛡️  DriftGuard AI")
    print(f"Watching: {os.environ['DRIFTGUARD_WATCH_PATH']}")
    print(f"Dashboard: http://127.0.0.1:{args.port}\n")

    uvicorn.run("backend.app:app", host="127.0.0.1", port=args.port, reload=False)

if __name__ == "__main__":
    main()
