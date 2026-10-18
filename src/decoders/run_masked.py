"""Re-run the text-based decoders on answers with topic/canary terms masked (no new agent calls)."""
import argparse
import json

import pandas as pd

from src.config import load_config, resolve
from src.decoders.run_all import run
from src.features.dataset import load_log
from src.features.masking import leak_vocabulary, mask_text, topic_terms


def main() -> None:
    cfg = load_config()
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=cfg["paths"]["agent_log"])
    ap.add_argument("--levels", nargs="+", default=["topic", "strict"])
    a = ap.parse_args()
    df = load_log(resolve(a.log), cfg)
    terms = topic_terms(cfg)
    leak = leak_vocabulary(df, cfg)
    print(f"topic terms: {len(terms)}, leak-only vocab: {len(leak)}")
    cfg["decoders"]["groups"] = ["text", "behavior+text"]
    out = []
    for level in a.levels:
        d = df.copy()
        d["answer_text"] = [mask_text(t, terms | (leak if level == "strict" else set()), level)
                            for t in d["answer_text"].fillna("")]
        cfg["decoders"]["embeddings_cache"] = f"results/cache/embeddings_masked_{level}.npz"
        res, stats, _ = run(d, cfg)
        res.insert(0, "mask_level", level)
        out.append(res)
        print(d.loc[d.acl_mode == "M1_weak", "answer_text"].iloc[3][:200])
    res = pd.concat(out)
    res.to_csv(resolve("results/decoder_results_masked.csv"), index=False)
    pd.set_option("display.width", 200)
    print(res[["mask_level", "model", "acl_mode", "group", "auc", "auc_ci_lo", "auc_ci_hi", "messages_needed",
               "p_topic_perm", "advantage_topic_perm", "placebo_auc_control_rows", "channel_open"]]
          .round(3).to_string())


if __name__ == "__main__":
    main()
