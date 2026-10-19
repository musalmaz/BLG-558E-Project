"""Defense 1: bind refusal/escalation answers to one fixed template (refusal types become indistinguishable)."""


def normalize(row: dict, cfg: dict) -> dict:
    """Return a copy where any refusal or escalated answer is the fixed template with one canonical type.

    Decides on the model's raw decision (`raw_refusal_type`/`raw_escalated` if present), so it stays
    correct when applied after other defenses that rewrite the decision fields.
    """
    d = cfg["defenses"]
    out = dict(row)
    raw_ref = out.get("raw_refusal_type", out["refusal_type"])
    raw_esc = out.get("raw_escalated", out["escalated"])
    out.setdefault("raw_refusal_type", out["refusal_type"])
    out.setdefault("raw_escalated", out["escalated"])
    if (raw_ref not in (None, "none")) or raw_esc:
        out["answer_text"] = d["refusal_template"]
        if out["refusal_type"] not in (None, "none"):
            out["refusal_type"] = d["canonical_refusal_type"]
    return out
