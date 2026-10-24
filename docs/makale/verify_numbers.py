"""Recompute every number quoted in docs/makale/main.tex from results/ and the raw logs.

Run from the project root:  python docs/makale/verify_numbers.py
Prints one line per claim: OK / MISMATCH, claimed vs actual.
"""
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "results"
bad = 0


def chk(name, claimed, actual, tol=0.005):
    global bad
    try:
        ok = abs(float(claimed) - float(actual)) <= tol
    except (TypeError, ValueError):
        ok = claimed == actual
    bad += not ok
    a = f"{actual:.3f}" if isinstance(actual, float) else actual
    print(f"{'OK      ' if ok else 'MISMATCH'} {name}: claimed {claimed}, actual {a}")


def jl(p):
    return [json.loads(ln) for ln in open(p, encoding="utf-8") if ln.strip()]


# ---- data
ds = json.load(open(R / "data_summary.json"))
chk("documents", 2030, ds["n_docs"])
chk("enron documents", 2000, ds["n_enron_docs"])
chk("canary documents", 30, ds["n_canary_docs"])
chk("chunks", 7520, ds["n_chunks"])
canar = json.load(open(ROOT / "data/canaries/canaries.json"))["canaries"]
chk("topics", 20, len(canar))
chk("topics with canaries", 10, sum(c["present"] for c in canar))
chk("canaries per positive topic", 3, min(len(c["doc_ids"]) for c in canar if c["present"]))

# ---- direct questions (baseline_check.json)
bc = json.load(open(R / "baseline_check.json"))["cells"]
chk("direct leak gemma3 M1 (of 20)", 16, bc["gemma3|M1_weak"]["leaked"])
chk("direct leak qwen2.5 M1 (of 20)", 13, bc["qwen2.5|M1_weak"]["leaked"])
chk("direct leak M2 total (of 40)", 0, bc["gemma3|M2_strong"]["leaked"] + bc["qwen2.5|M2_strong"]["leaked"])

# ---- main decoder table (Table I)
d = pd.read_csv(R / "decoder_results.csv")
def row(model, mode, group):
    return d[(d.model == model) & (d.acl_mode == mode) & (d.group == group)].iloc[0]
for model, mode, group, auc, lo, hi, p in [
        ("gemma3", "M1_weak", "behavior", 0.48, 0.33, 0.63, 0.46), ("gemma3", "M1_weak", "text", 0.82, 0.75, 0.91, 0.004),
        ("gemma3", "M2_strong", "text", 0.45, 0.34, 0.56, 0.56), ("qwen2.5", "M1_weak", "behavior", 0.58, 0.41, 0.76, 0.18),
        ("qwen2.5", "M1_weak", "text", 0.61, 0.48, 0.72, 0.13), ("qwen2.5", "M2_strong", "text", 0.42, 0.32, 0.53, 0.69)]:
    r = row(model, mode, group)
    tag = f"TableI {model} {mode} {group}"
    chk(tag + " AUC", auc, r.auc); chk(tag + " CI lo", lo, r.auc_ci_lo); chk(tag + " CI hi", hi, r.auc_ci_hi)
    chk(tag + " p", p, r.p_topic_perm, tol=0.0055)
chk("messages needed gemma3 M1 text", 2, row("gemma3", "M1_weak", "text").messages_needed)
chk("min p over M2 rows (>=0.48)", True, bool((d[d.acl_mode == "M2_strong"].p_topic_perm >= 0.48).all()))

# ---- word-masking control
m = pd.read_csv(R / "decoder_results_masked.csv")
g = m[(m.model == "gemma3") & (m.acl_mode == "M1_weak") & (m.group == "text")].set_index("mask_level").auc
chk("masked AUC topic level", 0.83, float(g["topic"])); chk("masked AUC strict level", 0.82, float(g["strict"]))
from src.features.masking import leak_vocabulary  # noqa: E402
from src.features.dataset import load_log  # noqa: E402
from src.config import load_config  # noqa: E402
cfg = load_config()
chk("secret-only vocabulary size", 210, len(leak_vocabulary(load_log(R / "runs/probe_matrix_20topics_repeats1.jsonl", cfg), cfg)), tol=0)

# ---- style markers (gemma3, M1, probe rows, topic means)
f = pd.read_csv(R / "features.csv")
s = f[(f.model == "gemma3") & (f.acl_mode == "M1_weak") & (f.kind == "probe")]
t = s.groupby(["topic_id", "present"])[["first_plur", "first_sing", "unfortunately", "has_contact"]].mean().reset_index()
mu = t.groupby("present").mean(numeric_only=True)
for col, a1, a0 in [("first_plur", 0.050, 0.017), ("first_sing", 0.009, 0.032), ("unfortunately", 0.0, 0.14), ("has_contact", 0.06, 0.24)]:
    chk(f"style {col} present", a1, float(mu.loc[1, col])); chk(f"style {col} absent", a0, float(mu.loc[0, col]))
stylo = [c for c in f.columns if c in ("n_sentences", "avg_word_len", "avg_sent_len", "long_word_ratio", "type_token", "comma_rate",
         "period_rate", "question_rate", "exclam_rate", "colon_rate", "semicolon_rate", "upper_ratio", "digit_ratio", "first_sing",
         "first_plur", "second_person", "apology", "hedge", "negation", "unfortunately", "has_contact", "n_newlines")]
chk("stylometric markers", 22, len(stylo), tol=0)

# ---- k sweep
rr = pd.read_csv(R / "ratio_results.csv")
for k, a in [(1, 0.71), (2, 0.64), (3, 0.82)]:
    chk(f"k={k} gemma3 text AUC", a, float(rr[(rr.model == "gemma3") & (rr.group == "text") & (rr.docs_per_topic == k)].auc.iloc[0]))
rt = pd.read_csv(R / "ratio_retrieval.csv")
for k, a in [(1, 1.9), (2, 2.5), (3, 3.3)]:
    x = rt[(rt.docs_per_topic == k) & (rt.kind == "probe") & (rt.present == 1)].mean_conf.mean()
    chk(f"k={k} confidential chunks in top-5 (probe, present)", a, float(x), tol=0.06)

# ---- defenses (Table II)
df = pd.read_csv(R / "defense_results.csv")
def dr(defense, group="text"):
    return df[(df.model == "gemma3") & (df.defense == defense) & (df.group == group)].iloc[0]
for defense, auc in [("none", 0.82), ("behavior_norm", 0.82), ("decision_hiding", 0.82), ("scoped_context", 0.44), ("M2_reference", 0.45)]:
    chk(f"defense {defense} text AUC", auc, dr(defense).auc)
chk("behavior_norm recall loss", 0.04, dr("behavior_norm").recall_loss)
chk("scoped recall loss", 0.30, dr("scoped_context").recall_loss)
chk("scoped routing agreement", 0.60, dr("scoped_context").routing_agreement)
chk("decision_hiding routing agreement", 0.61, dr("decision_hiding").routing_agreement)
chk("M2 recall loss", 0.04, dr("M2_reference").recall_loss)
chk("resolution none", 0.92, dr("none").resolution); chk("resolution M2", 0.67, dr("M2_reference").resolution)

# ---- masking (Table II + text)
mk = pd.read_csv(R / "mask_results.csv")
def mr(model, cond, group="text"):
    return mk[(mk.model == model) & (mk.condition == cond) & (mk.group == group)].iloc[0]
chk("mask oracle gemma3 AUC", 0.84, mr("gemma3", "mask_oracle").auc); chk("mask oracle gemma3 p", 0.002, mr("gemma3", "mask_oracle").p_topic_perm, tol=0.0055)
chk("mask rule gemma3 AUC", 0.69, mr("gemma3", "mask_rule").auc); chk("mask rule gemma3 p", 0.016, mr("gemma3", "mask_rule").p_topic_perm, tol=0.0055)
chk("mask oracle qwen2.5 AUC", 0.60, mr("qwen2.5", "mask_oracle").auc); chk("mask rule qwen2.5 AUC", 0.59, mr("qwen2.5", "mask_rule").auc)
chk("direct leak gemma3 none", 0.50, mr("gemma3", "none").leak_direct); chk("direct leak gemma3 oracle", 0.0, mr("gemma3", "mask_oracle").leak_direct)
chk("direct leak gemma3 rule", 0.0, mr("gemma3", "mask_rule").leak_direct); chk("direct leak qwen2.5 none", 0.35, mr("qwen2.5", "none").leak_direct)
chk("direct leak qwen2.5 oracle", 0.0, mr("qwen2.5", "mask_oracle").leak_direct); chk("direct leak qwen2.5 rule", 0.0, mr("qwen2.5", "mask_rule").leak_direct)
chk("resolution mask oracle", 0.90, mr("gemma3", "mask_oracle").resolution); chk("resolution mask rule", 0.92, mr("gemma3", "mask_rule").resolution)
chk("approved line M1", 0.33, mr("gemma3", "none").recall_conf); chk("approved line oracle", 0.33, mr("gemma3", "mask_oracle").recall_conf)
chk("approved line rule", 0.39, mr("gemma3", "mask_rule").recall_conf)
chk("approved line M2", 0.0, mr("gemma3", "m2").recall_conf); chk("approved line scoped", 0.0, mr("gemma3", "scoped").recall_conf)
ph = re.compile(r"\[(REDACTED|NUM|DATE|NAME|EMAIL|PHONE)\]")
n = k = 0
for r in jl(R / "runs/def_mask_rule_raw.jsonl"):
    t_ = r["message_id"].split("|")
    if r["model"] == "gemma3" and t_[1] == "probe" and not r["parse_error"] and any(i.startswith("canary_" + t_[0]) for i in r["retrieved_doc_ids"]):
        n += 1; k += bool(ph.search(r["answer_text"] or ""))
chk("placeholder copied (rule, gemma3, probe, topic with canary)", 20, k, tol=0); chk("   of probes", 50, n, tol=0)
files = {q for pat in ("*mask*", "utilconf_*", "direct_*") for q in (R / "runs").glob(pat)}
calls = sum(len(jl(q)) for q in files)
chk("masking study log rows (claimed 'about 1200')", 1200, calls, tol=60)

# ---- cross-user study
xl = pd.read_csv(R / "xuser_leak.csv")
def xr(model, mode):
    r = xl[(xl.model == model) & (xl.acl_mode == mode) & (xl.kind == "probe") & (xl.present == 1)].iloc[0]
    return int(r.leaked), int(r.n)
for model, mode, claimed in [("gemma3", "X1_shared_weak", 36), ("qwen2.5", "X1_shared_weak", 26), ("gemma3", "X3_shared_summary", 35),
                             ("qwen2.5", "X3_shared_summary", 28), ("gemma3", "X2_isolated", 1), ("qwen2.5", "X2_isolated", 0)]:
    chk(f"cross-user {model} {mode} (of 50)", claimed, xr(model, mode)[0], tol=0)
chk("cross-user rows in log", 1200, len(jl(R / "runs/xuser.jsonl")), tol=0)
xd = pd.read_csv(R / "decoder_results_xuser.csv")
chk("cross-user decoder cells", 24, len(xd), tol=0); chk("cross-user cells open", 1, int(xd.channel_open.sum()), tol=0)
q = xd[(xd.model == "qwen2.5") & (xd.acl_mode == "X3_shared_summary") & (xd.group == "text")].iloc[0]
chk("qwen2.5 X3 text AUC", 0.67, q.auc); chk("qwen2.5 X3 text p", 0.03, q.p_topic_perm, tol=0.005)

# ---- additions for the expanded sections (figures and sanity checks)
sub = rr[(rr.model == "gemma3") & (rr.group == "text")].set_index("docs_per_topic")
for k, lo, hi in [(1, 0.596, 0.803), (2, 0.506, 0.748), (3, 0.747, 0.905)]:
    chk(f"Fig. k={k} CI lo", lo, float(sub.loc[k, "auc_ci_lo"])); chk(f"Fig. k={k} CI hi", hi, float(sub.loc[k, "auc_ci_hi"]))
chk("k=1 p", 0.012, float(sub.loc[1, "p_topic_perm"]), tol=0.0055)
chk("row-shuffle AUC min", 0.46, float(d.row_shuffle_auc_mean.min())); chk("row-shuffle AUC max", 0.51, float(d.row_shuffle_auc_mean.max()))
chk("placebo AUC min", 0.33, float(d.placebo_auc_control_rows.min())); chk("placebo AUC max", 0.55, float(d.placebo_auc_control_rows.max()))

# ---- masking example table (Table masking): chunk versions and replies
from src.defenses.masking import load_spans, mask_oracle, mask_rule  # noqa: E402
doc = next(x for x in json.load(open(ROOT / "data/canaries/canaries.json"))["docs"] if x["id"] == "canary_c00_2")
txt = "Subject: " + doc["subject"] + " " + doc["body"]
chk("example original has '24th'", True, "The board meets on the 24th." in txt)
chk("example oracle", True, "The board meets on the [REDACTED]." in mask_oracle(txt, load_spans(cfg)) and "Veltrix Holdings" in mask_oracle(txt, load_spans(cfg)))
mr_ = mask_rule(txt)
chk("example rule", True, "the [NAME] [NAME] merger with [NAME] [NAME]" in mr_ and "The board meets on the [DATE]." in mr_)
def reply(fname, model="gemma3"):
    r = next(x for x in jl(R / "runs" / fname) if x["model"] == model and x["message_id"].startswith("c02|direct|v0"))
    return r["answer_text"]
chk("example reply M1", True, "we expect to have 9 traders remaining on the Westmere trading desk" in reply("direct_none.jsonl"))
chk("example reply oracle", True, "approximately [REDACTED] traders on the Westmere trading desk" in reply("direct_mask_oracle.jsonl"))
chk("example reply M2", True, "I don't have the specific number of traders remaining" in reply("direct_m2.jsonl"))

# ---- config
chk("bootstrap resamples", 200, cfg["decoders"]["n_boot"], tol=0); chk("topic permutations", 500, cfg["decoders"]["n_topic_perm"], tol=0)
chk("main matrix rows", 800, len(jl(R / "runs/probe_matrix_20topics_repeats1.jsonl")), tol=0)
print("\nMISMATCHES:", bad)
