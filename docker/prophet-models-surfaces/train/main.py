import argparse
import json
from pathlib import Path

from prophet_ts.spec import load_model_spec

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--spec", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    spec = load_model_spec(args.spec)

    # TODO:
    # - fit implied vol surface parameterization (SVI/SABR/etc)
    # - enforce no-arbitrage constraints if specified
    metrics = {"status": "stub", "family": spec.model.family}
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2))
    (out / "surface_params.json").write_text("{}\n")

    print("Wrote artifacts to", out)

if __name__ == "__main__":
    main()
