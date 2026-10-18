"""Chain Faz 3 runner (optional) and Faz 4 decoders over the full {mode x model x topic} matrix."""
import argparse
import json

from src.config import load_config, resolve
from src.decoders.run_all import run as run_decoders
from src.features.dataset import load_log


def main() -> None:
    cfg = load_config()
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default="results/runs/probe_matrix_20topics_repeats1.jsonl")
    ap.add_argument("--collect", action="store_true",
                    help="first run missing agent calls (resume); needs Ollama, AC power, ~40-call chunks")
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--out-prefix", default="", help="suffix for result files, e.g. _k1")
    a = ap.parse_args()
    log = resolve(a.log)
    if a.collect:
        from src.agent.agent import AgentRunner
        from src.probes.generator import load_probes
        from src.probes.runner import build_matrix, run as run_probes
        jobs = build_matrix(cfg, load_probes(), [m["name"] for m in cfg["models"]], None,
                            cfg["probes"]["variants_per_topic"], a.repeats)
        print(run_probes(jobs, AgentRunner(cfg, log_path=str(log)), log))
    df = load_log(log, cfg)
    res, stats, feat = run_decoders(df, cfg)
    d = cfg["decoders"]
    res.to_csv(resolve(d["results_csv"].replace(".csv", f"{a.out_prefix}.csv")), index=False)
    resolve(d["stat_tests_json"].replace(".json", f"{a.out_prefix}.json")).write_text(
        json.dumps(stats, indent=2, default=float), encoding="utf-8")
    print(f"{len(res)} decoder rows written")


if __name__ == "__main__":
    main()
