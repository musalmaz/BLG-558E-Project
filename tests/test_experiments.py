"""Faz 5 analysis tests on a synthetic decoder_results table."""
import numpy as np
import pandas as pd

from src.experiments.analyze import m1_vs_m2, main_results, to_markdown
from src.experiments.figures import auc_figure, bits_figure


def _res() -> pd.DataFrame:
    rows = []
    for model in ("a", "b"):
        for mode, auc in (("M1_weak", 0.8), ("M2_strong", 0.5)):
            for g in ("behavior_nolat", "text"):
                rows.append({"model": model, "acl_mode": mode, "group": g, "auc": auc, "auc_ci_lo": auc - .1,
                             "auc_ci_hi": auc + .1, "tpr_at_fpr": 0.1, "messages_needed": np.nan,
                             "leaked_bits_model": auc - 0.5, "p_topic_perm": 0.01, "channel_open": auc > .6,
                             "row_shuffle_auc_mean": 0.5, "null_auc_mean": 0.5, "placebo_auc_control_rows": 0.5})
    return pd.DataFrame(rows)


def test_main_table_has_control_rows_and_delta():
    res = _res()
    long, cmp = main_results(res), m1_vs_m2(res)
    assert len(long) == 4 * len(res)
    assert set(long.row_type) == {"decoder", "control_row_shuffle", "control_topic_perm_null",
                                  "control_placebo_control_rows"}
    assert np.allclose(cmp.delta_auc, 0.3) and len(cmp) == 4
    md = to_markdown(long, cmp)
    assert "row shuffle" in md and "ΔAUC" in md and ">5" in md


def test_figures_written(tmp_path):
    auc_figure(_res(), tmp_path / "a.png")
    bits_figure(_res(), tmp_path / "b.png")
    assert (tmp_path / "a.png").stat().st_size > 0 and (tmp_path / "b.png").stat().st_size > 0


def test_ratio_table_and_figure(tmp_path):
    from src.experiments.ratio import ratio_figure, ratio_table, to_markdown as ratio_md
    res = _res()
    tab = ratio_table({1: res, 3: res})
    assert set(tab.docs_per_topic) == {1, 3} and set(res.acl_mode) == {"M1_weak", "M2_strong"}
    assert len(tab) == 2 * (len(res) // 2)  # M2 rows dropped
    ratio_figure(tab, tmp_path / "r.png")
    assert (tmp_path / "r.png").stat().st_size > 0 and "Belge/konu" in ratio_md(tab)
