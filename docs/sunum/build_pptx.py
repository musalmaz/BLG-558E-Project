"""Build the final-project presentation as a native .pptx (python-pptx), mirroring docs/sunum/."""
import re
import sys
from pathlib import Path

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path("/home/musa/ITU-YL/Security&Privacy/BLG-558E Project")
OUT = ROOT / "docs/sunum/presentation.pptx"

# palette (same as the web deck)
INK, MUTED, LIGHT, WHITE = "14212E", "566475", "F3F5F7", "FFFFFF"
NAVY, LEAK, SAFE, INFO, AMBER = "0F1B2D", "C2410C", "17724F", "2B5C8F", "B7791F"
T_LEAK, T_SAFE, T_INFO, T_AMB = "FDEEE4", "E3F4EC", "E6EFF8", "FFF4D6"
LINE, SOFT = "CBD5DF", "E4E9EE"
HEAD, BODY, MONO = "Cambria", "Calibri", "Consolas"
X0, W = 0.8, 11.73
FOOT = "BLG558E · Security & Privacy · Final Project"

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]


def rgb(h):
    return RGBColor.from_string(h)


def notes_for(slide_id):
    p = ROOT / "docs/sunum/slides" / f"{slide_id}.html"
    m = re.search(r"<aside>(.*?)</aside>", p.read_text(encoding="utf-8"), re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def new_slide(notes, dark=False, footer=True):
    s = prs.slides.add_slide(BLANK)
    bg = s.background.fill
    bg.solid()
    bg.fore_color.rgb = rgb(NAVY if dark else LIGHT)
    if footer and not dark:
        text(s, X0, 6.95, 8, 0.3, [[(FOOT, dict(size=12, color=MUTED))]])
    n = notes
    if n:
        s.notes_slide.notes_text_frame.text = n
    return s


def fill_runs(tf, paras, align=None, spacing=4):
    """paras: list of paragraphs; paragraph = list of (text, opts) runs."""
    first = True
    for runs in paras:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.alignment = align or PP_ALIGN.LEFT
        p.space_after = Pt(spacing)
        for t, o in runs:
            r = p.add_run()
            r.text = t
            f = r.font
            f.name = o.get("font", BODY)
            f.size = Pt(o.get("size", 16))
            f.bold = o.get("bold", False)
            f.italic = o.get("italic", False)
            f.color.rgb = rgb(o.get("color", INK))


def text(slide, x, y, w, h, paras, align=None, anchor=MSO_ANCHOR.TOP, spacing=4):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    fill_runs(tf, paras, align, spacing)
    return tb


def card(slide, x, y, w, h, fill, paras, line=None, anchor=MSO_ANCHOR.TOP, align=None, spacing=4):
    sh = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.adjustments[0] = 0.06
    sh.fill.solid()
    sh.fill.fore_color.rgb = rgb(fill)
    if line:
        sh.line.color.rgb = rgb(line)
        sh.line.width = Pt(1.25)
    else:
        sh.line.fill.background()
    sh.shadow.inherit = False
    tf = sh.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.18)
    tf.margin_top = tf.margin_bottom = Inches(0.1)
    tf.vertical_anchor = anchor
    fill_runs(tf, paras, align, spacing)
    return sh


def title(slide, t, dark=False):
    text(slide, X0, 0.42, W, 0.9, [[(t, dict(font=HEAD, size=28, bold=True, color=WHITE if dark else INK))]],
         anchor=MSO_ANCHOR.MIDDLE)


def arrow(slide, x, y, ch="→", w=0.45, h=0.5, color=MUTED):
    text(slide, x, y, w, h, [[(ch, dict(size=28, color=color, bold=True))]], align=PP_ALIGN.CENTER,
         anchor=MSO_ANCHOR.MIDDLE)


def table(slide, x, y, colw, rows, size=14, header=True, row_h=0.4, fills=None):
    """rows: list of rows; cell = str or (str, dict(color, bold, align))."""
    shape = slide.shapes.add_table(len(rows), len(colw), Inches(x), Inches(y), Inches(sum(colw)),
                                   Inches(row_h * len(rows)))
    tbl = shape.table
    tblPr = shape._element.graphic.graphicData.tbl.tblPr
    tblPr.set("bandRow", "0")
    tblPr.set("firstRow", "0")
    for i, cw in enumerate(colw):
        tbl.columns[i].width = Inches(cw)
    for r, row in enumerate(rows):
        tbl.rows[r].height = Inches(row_h)
        for c, cell in enumerate(row):
            txt, o = (cell, {}) if isinstance(cell, str) else cell
            tc = tbl.cell(r, c)
            tc.margin_left = tc.margin_right = Inches(0.1)
            tc.margin_top = tc.margin_bottom = Inches(0.05)
            tc.vertical_anchor = MSO_ANCHOR.MIDDLE
            tc.fill.solid()
            is_h = header and r == 0
            tc.fill.fore_color.rgb = rgb(SOFT if is_h else (fills[r] if fills and fills.get(r) else WHITE))
            tf = tc.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.alignment = o.get("align", PP_ALIGN.LEFT)
            run = p.add_run()
            run.text = txt
            run.font.name = BODY
            run.font.size = Pt(size)
            run.font.bold = is_h or o.get("bold", False)
            run.font.color.rgb = rgb(o.get("color", INK))
    return shape


R = PP_ALIGN.RIGHT
def num(t, color=INK, bold=False):
    return (t, dict(color=color, bold=bold, align=R))


# ---------------------------------------------------------------- 1 cover
s = new_slide("Opening (30 s). A customer-service bot can read confidential documents but is forbidden to write them. "
              "Our question: if it never writes a secret, can its behavior still reveal that the secret exists?", dark=True, footer=False)
text(s, 0.9, 0.9, 11.5, 0.5, [[("BLG558E - Security & Privacy - Final Project", dict(font=MONO, size=20, color="8FA3B8"))]])
text(s, 0.9, 2.3, 11.5, 2.4, [[("Behavioral Side-Channel Leakage in External AI Service Agents",
                                dict(font=HEAD, size=46, bold=True, color="EEF2F6"))]])
text(s, 0.9, 4.85, 11.5, 0.8, [[("Can an agent give away a secret without ever writing it?", dict(size=26, color="F08A63"))]])
text(s, 0.9, 6.5, 8, 0.4, [[("[Name Surname] · [Date]", dict(size=18, color="8FA3B8"))]])

# ---------------------------------------------------------------- 2 problem
s = new_slide("Problem (50 s). Service agents search company documents and let an LLM write the reply; some documents are confidential. "
              "Direct leakage is the secret appearing in the reply. Side-channel leakage is subtler: the reply never states the secret, "
              "but its tone, refusals, routing or timing reveal that a confidential document exists. "
              "Our observer is an ordinary customer who only sends legitimate messages, so no attack is needed.")
title(s, "Problem: can behavior reveal an unwritten secret?")
bw = [2.9, 3.9, 2.9]
x = X0
card(s, x, 1.5, bw[0], 1.25, WHITE, [[("Customer", dict(size=18, bold=True))], [("Sends a normal, legitimate question", dict(size=14, color=MUTED))]], line=LINE)
arrow(s, x + bw[0] + 0.05, 1.9, w=0.55)
x2 = x + bw[0] + 0.65
card(s, x2, 1.5, bw[1], 1.25, T_INFO, [[("AI service agent", dict(size=18, bold=True))], [("Searches company documents, then an LLM writes the reply", dict(size=14, color="3B4A59"))]], line=INFO)
arrow(s, x2 + bw[1] + 0.05, 1.9, w=0.55)
x3 = x2 + bw[1] + 0.65
card(s, x3, 1.5, bw[2], 1.25, WHITE, [[("Visible output", dict(size=18, bold=True))], [("Reply text, decision fields, response time", dict(size=14, color=MUTED))]], line=LINE)
text(s, x2 - 0.05, 2.78, bw[1], 0.3, [[("↑ read by the agent", dict(size=14, color=LEAK, bold=True))]], align=PP_ALIGN.CENTER)
card(s, x2, 3.05, bw[1], 0.75, T_LEAK, [[("Confidential documents ", dict(size=14, bold=True)), ("(merger plans, layoffs, legal settlements)", dict(size=14))]], line=LEAK, anchor=MSO_ANCHOR.MIDDLE)
card(s, X0, 4.1, 5.7, 1.35, WHITE, [[("Direct leakage", dict(size=20, bold=True, color=LEAK))], [("The reply contains the secret: “The board votes on the 24th.”", dict(size=16))]])
card(s, X0 + 5.95, 4.1, 5.78, 1.35, WHITE, [[("Side-channel leakage", dict(size=20, bold=True, color=INFO))], [("The reply never states the secret, but its tone, refusals, routing or timing reveal that a confidential document exists.", dict(size=16))]])
card(s, X0, 5.75, W, 0.95, NAVY, [[("Research question: ", dict(size=18, bold=True, color="F08A63")), ("From legitimate messages only, can an observer tell whether the agent holds confidential documents on a topic?", dict(size=18, color="EEF2F6"))]], anchor=MSO_ANCHOR.MIDDLE)

# ---------------------------------------------------------------- 3 ACL + gap
s = new_slide("Background and gap (50 s). An ACL labels documents public, internal or confidential. Under the weak ACL (M1) confidential "
              "documents are retrieved and only the prompt forbids revealing them; under the strong ACL (M2) they are filtered before the model. "
              "Direct questions leaked in 16 of 20 cases under M1 and 0 under M2. Related work attacks the network layer (token lengths, timing, packet sizes) "
              "or queries RAG systems with crafted or injected prompts. We study the application layer, with legitimate messages only, and we score defenses on security and utility.")
title(s, "Background: ACL modes, and what is new here")
cw = (W - 0.5) / 3
for i, (h, c, e) in enumerate([("public", SAFE, "press release, FAQ"), ("internal", INFO, "billing procedure, vacation policy"),
                                ("confidential", LEAK, "“Project Falcon merger, board votes on the 24th”")]):
    card(s, X0 + i * (cw + 0.25), 1.4, cw, 1.15, WHITE, [[(h, dict(size=18, bold=True, color=c))], [("Example: " + e, dict(size=14, color=MUTED))]], spacing=2)
hw = (W - 0.3) / 2
card(s, X0, 2.75, hw, 1.5, T_LEAK, [[("M1 · weak ACL", dict(size=18, bold=True, color=LEAK))], [("Search returns all labels; only the prompt says “do not reveal”. The model still reads the secret. Direct questions leaked 16/20 (gemma3), 13/20 (qwen2.5).", dict(size=14))]], spacing=3)
card(s, X0 + hw + 0.3, 2.75, hw, 1.5, T_SAFE, [[("M2 · strong ACL", dict(size=18, bold=True, color=SAFE))], [("Confidential documents are filtered at search time; the model never sees them. Direct questions leaked 0/20.", dict(size=14))]], spacing=3)
text(s, X0, 4.45, W, 0.75, [[("Related work attacks the network layer (token lengths, timing, packet sizes: Weiss ’24, Carlini & Nasr ’24, Whisper Leak ’25) or queries RAG with crafted or injected prompts (Anderson ’24, Zeng ’24, Qi ’25). We differ:", dict(size=14, color="3B4A59"))]])
card(s, X0, 5.2, cw, 1.5, WHITE, [[("Application-layer channel", dict(size=16, bold=True))], [("The observer is the customer reading replies, not a network eavesdropper.", dict(size=14))]], spacing=3)
card(s, X0 + cw + 0.25, 5.2, cw, 1.5, WHITE, [[("No attack needed", dict(size=16, bold=True))], [("Legitimate messages only: every customer is a potential observer.", dict(size=14))]], spacing=3)
card(s, X0 + 2 * (cw + 0.25), 5.2, cw, 1.5, WHITE, [[("Leak → defense → utility", dict(size=16, bold=True))], [("Controlled statistics, then defenses scored on security and usefulness.", dict(size=14))]], spacing=3)

# ---------------------------------------------------------------- 4 design
s = new_slide("Design (55 s). One message goes through retrieval of the top five chunks, the ACL mode, a prompt, a local LLM at temperature zero, and a JSON "
              "decision that is logged. Only the ACL step differs between M1 and M2. Probes touch a confidential topic; controls have the same shape and length "
              "but another topic. Data are public Enron emails plus fabricated canary documents, so the ground truth is known. "
              "20 topics, 5 variants, 2 kinds, 2 modes, 2 models give 800 calls.")
title(s, "Design: agent, ACL modes and probe vs control")
cwid = [1.8, 2.0, 2.7, 1.9, 2.0]
heads = [("1 Customer message", "legitimate question", WHITE, LINE), ("2 Retrieval", "top-5 chunks (ChromaDB)", WHITE, LINE),
         ("3 ACL mode", None, T_AMB, AMBER), ("4 LLM", "gemma3 / qwen2.5, temperature 0", T_INFO, INFO), ("5 Decision + log", "JSON, 4 fields", WHITE, LINE)]
xx = X0
for i, (h, b, f, l) in enumerate(heads):
    if b is None:
        card(s, xx, 1.45, cwid[i], 1.55, f, [[(h, dict(size=15, bold=True))], [("M1: ", dict(size=14, bold=True, color=LEAK)), ("keep all labels", dict(size=14))], [("M2: ", dict(size=14, bold=True, color=SAFE)), ("drop confidential", dict(size=14))]], line=l, spacing=2)
    else:
        card(s, xx, 1.45, cwid[i], 1.55, f, [[(h, dict(size=15, bold=True))], [(b, dict(size=14, color="3B4A59"))]], line=l, spacing=2)
    if i < 4:
        arrow(s, xx + cwid[i] - 0.02, 1.95, w=0.27)
    xx += cwid[i] + 0.26
hw = (W - 0.3) / 2
card(s, X0, 3.3, hw, 1.75, WHITE, [[("Probe · touches the topic", dict(size=16, bold=True, color=LEAK))], [("“… mentioned that ", dict(size=14)), ("Project Falcon", dict(size=14, bold=True)), (" might change who handles our contract. How does this affect our service agreement?”", dict(size=14))]], line=LINE, spacing=4)
card(s, X0 + hw + 0.3, 3.3, hw, 1.75, WHITE, [[("Control · same shape, other topic", dict(size=16, bold=True, color=INFO))], [("“… mentioned that the ", dict(size=14)), ("billing portal", dict(size=14, bold=True)), (" might change how invoices are sent. How does this affect our payment schedule?”", dict(size=14))]], line=LINE, spacing=4)
card(s, X0, 5.3, W, 1.4, T_INFO, [[("Data: ", dict(size=15, bold=True)), ("2000 public Enron emails + 30 fabricated canary emails; 20 topics (10 with 3 confidential canaries, 10 without), so the ground truth is known.", dict(size=15))],
     [("800 calls = ", dict(size=15)), ("20 topics × 2 kinds × 5 variants × 2 ACL modes × 2 models", dict(size=15, bold=True))]], anchor=MSO_ANCHOR.MIDDLE, spacing=4)

# ---------------------------------------------------------------- 5 measurement
s = new_slide("Measurement (55 s). The attacker is a simple fixed logistic-regression decoder that guesses, per topic, whether a confidential document exists. "
              "Leave-one-topic-out evaluation and randomized controls make sure the score is not memorization or luck. We report AUC because it needs no threshold, "
              "is not fooled by class imbalance and is one comparable number: it is the probability that a topic with a secret scores above one without. "
              "0.5 is a coin flip, 1.0 perfect. We add TPR at one percent false positives, messages needed and leaked bits.")
title(s, "Measurement: the decoder, and why AUC")
card(s, X0, 1.45, 5.6, 3.4, WHITE, [[("Decoder (attacker model)", dict(size=18, bold=True, color=INFO))],
     [("Features: behavior (escalation, refusal, routing, length, time) and text style (22 markers + embeddings).", dict(size=14))],
     [("Fixed L2 logistic regression, no tuning: a weak decoder that still succeeds proves the signal is real.", dict(size=14))],
     [("Leave-one-topic-out: train on 19 topics, test on the 20th.", dict(size=14))],
     [("Randomized controls: 500 label shuffles (p-value), row shuffle, placebo. “Open” = p < 0.05 and CI above 0.5.", dict(size=14))]], spacing=6)
card(s, X0 + 5.85, 1.45, 5.88, 3.4, WHITE, [[("AUC: area under the ROC curve", dict(size=18, bold=True, color=INFO))],
     [("Probability that a topic ", dict(size=14)), ("with", dict(size=14, bold=True)), (" a secret scores higher than one ", dict(size=14)), ("without", dict(size=14, bold=True)), (".", dict(size=14))],
     [("• No threshold needed.  • Robust to class imbalance.  • One comparable number.", dict(size=14, color="3B4A59"))]], spacing=6)
b1 = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(X0 + 6.05), Inches(3.55), Inches(2.7), Inches(0.32))
b1.fill.solid(); b1.fill.fore_color.rgb = rgb(SOFT); b1.line.fill.background()
b2 = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(X0 + 8.75), Inches(3.55), Inches(2.7), Inches(0.32))
b2.fill.solid(); b2.fill.fore_color.rgb = rgb("F5D3BF"); b2.line.fill.background()
text(s, X0 + 6.05, 3.92, 3, 0.3, [[("0.5 = coin flip", dict(size=13, color=MUTED))]])
text(s, X0 + 8.45, 3.92, 3, 0.3, [[("1.0 = perfect", dict(size=13, color=MUTED))]], align=R)
cw = (W - 0.5) / 3
for i, (h, d) in enumerate([("TPR @ 1% FPR", "Secrets caught with only 1% false alarms."), ("Messages needed", "Probes until topic-level AUC reaches 0.9."), ("Leaked bits", "Information per message, in bits.")]):
    card(s, X0 + i * (cw + 0.25), 5.15, cw, 1.4, WHITE, [[(h, dict(size=16, bold=True))], [(d, dict(size=14, color=MUTED))]], spacing=3)

# ---------------------------------------------------------------- 6 findings
s = new_slide("Findings (60 s). Under the weak ACL, gemma3's reply text lets the decoder tell secret topics apart: AUC 0.82, p 0.004. Behavior fields show no significant signal, "
              "and under the strong ACL nothing leaks. Masking topic words, numbers, names and 210 secret-only words did not reduce the signal (0.83 to 0.82): the signal is "
              "writing style. With confidential context the model uses we and our more, apologizes less and gives fewer contact details.")
title(s, "Findings: reply style gives the topic away")
cd = CategoryChartData()
cd.categories = ["gemma3 · M1 · text", "gemma3 · M1 · behavior", "gemma3 · M2 · text", "qwen2.5 · M1 · text", "qwen2.5 · M1 · behavior", "qwen2.5 · M2 · text"]
cd.add_series("AUC", [0.82, 0.48, 0.45, 0.61, 0.58, 0.42])
gf = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(X0), Inches(1.4), Inches(6.5), Inches(3.9), cd)
ch = gf.chart
ch.has_legend = False; ch.has_title = False; ch.font.size = Pt(13); ch.font.name = BODY
va = ch.value_axis
va.minimum_scale, va.maximum_scale, va.major_unit = 0, 1, 0.5
va.major_gridlines.format.line.color.rgb = rgb(SOFT)
ch.category_axis.reverse_order = True
pl = ch.plots[0]
pl.gap_width = 45; pl.has_data_labels = True
pl.data_labels.number_format = "0.00"; pl.data_labels.number_format_is_linked = False
pl.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
pl.data_labels.font.size = Pt(13); pl.data_labels.font.bold = True
for i, col in enumerate([LEAK, INFO, SAFE, INFO, INFO, SAFE]):
    pt = pl.series[0].points[i]; pt.format.fill.solid(); pt.format.fill.fore_color.rgb = rgb(col)
text(s, X0, 5.33, 6.5, 0.3, [[("AUC; 0.5 = coin flip. Red = open, green = closed (strong ACL).", dict(size=12, color=MUTED))]])
rows = [["Style marker (gemma3, M1)", ("Secret", dict(align=R)), ("No secret", dict(align=R))],
        ["“we / our” rate", num("0.050"), num("0.017")], ["“I” rate", num("0.009"), num("0.032")],
        ["“unfortunately”", num("0.00"), num("0.14")], ["gives phone / email", num("0.06"), num("0.24")]]
table(s, X0 + 6.75, 1.45, [2.6, 1.2, 1.18], rows, size=13, row_h=0.45)
card(s, X0 + 6.75, 3.85, 4.98, 1.45, T_LEAK, [[("The tone leaks, not the content. ", dict(size=14, bold=True)), ("Masking topic words, numbers, names and 210 secret-only words left AUC unchanged (0.83 → 0.82).", dict(size=14))]], anchor=MSO_ANCHOR.MIDDLE)
card(s, X0, 5.7, W, 0.95, T_INFO, [[("Behavior fields ", dict(size=15, bold=True)), ("(escalation, refusal, routing) show no significant signal; the agent rarely escalates or refuses. Under M2 nothing leaks.", dict(size=15))]], anchor=MSO_ANCHOR.MIDDLE)

# ---------------------------------------------------------------- 7 defenses
s = new_slide("Defenses (60 s). We scored each defense on security and on utility. Normalizing refusals or hiding decisions does not help, because what leaks is the style of normal replies. "
              "Only keeping confidential text out of the context closes the channel: scoped context is costly (recall loss 0.30), M2 is cheaper but lowers gemma3's resolution rate. "
              "Masking removes content leakage and keeps utility, but the topic's existence still leaks (AUC 0.69 with rule masking). In an additional multi-user study, "
              "a shared memory leaked user A's private data to user B in 52 to 72 percent of replies; per-user isolation reduced it to 0 to 2 percent.")
title(s, "Defenses: security and utility measured together")
rows = [["Defense (gemma3)", ("Text AUC", dict(align=R)), ("Direct leakage", dict(align=R)), "Utility cost"],
        ["none (weak ACL, M1)", num("0.82", LEAK, True), num("0.50", LEAK, True), "–"],
        ["behavior_norm", num("0.82", LEAK, True), num("–"), "recall −0.04"],
        ["decision_hiding", num("0.82", LEAK, True), num("–"), "routing agreement 0.61"],
        ["scoped_context (public only)", num("0.44", SAFE, True), num("–"), ("recall −0.30", dict(color=LEAK, bold=True))],
        ["M2 (strong ACL)", num("0.45", SAFE, True), num("0.00", SAFE, True), "resolution 0.92 → 0.67"],
        ["masking (rule)", num("0.69", LEAK, True), num("0.00", SAFE, True), "kept (resolution 0.92)"]]
table(s, X0, 1.4, [3.6, 1.6, 2.2, 4.33], rows, size=14, row_h=0.46)
card(s, X0, 4.85, W, 0.85, T_SAFE, [[("Output-side fixes failed; only keeping confidential text out of the context closed the style channel. ", dict(size=15, bold=True)), ("Masking closes content leakage but not the topic’s existence.", dict(size=15))]], anchor=MSO_ANCHOR.MIDDLE)
card(s, X0, 5.85, W, 0.9, T_LEAK, [[("Additional study (multi-user memory): ", dict(size=15, bold=True)), ("a shared memory leaked user A’s private data to user B in 52–72% of replies; per-user isolation: 0–2%.", dict(size=15))]], anchor=MSO_ANCHOR.MIDDLE)

# ---------------------------------------------------------------- 8 challenges + conclusion
s = new_slide("Challenges and conclusion (50 s). Limits: small scale, two small local models, single-author data and a single secret definition, no multiple-testing correction, "
              "and the behavior channel is 'not found', not 'not there'. Conclusions: weak ACL leaks directly, the style of replies is the side channel, only keeping confidential text "
              "out of the context closes it, and shared memory leaks across users while per-user isolation removes it. Future work: more topics and repetitions, a commercial model, "
              "other secret policies, isolation with real authentication.")
title(s, "Challenges and conclusions")
card(s, X0, 1.45, 5.6, 5.2, WHITE, [[("Challenges and limits", dict(size=20, bold=True, color=LEAK))],
     [("• Scale: 10+10 topics, 5 variants, one repetition; small effects cannot be excluded.", dict(size=15))],
     [("• Two small local open-weight models; no commercial model.", dict(size=15))],
     [("• One author wrote the data; “what is secret” is a policy choice.", dict(size=15))],
     [("• No multiple-testing correction: single p ≈ 0.03 results are hints.", dict(size=15))],
     [("• Behavior channel “not found” is not “not there”: the agent rarely escalates or refuses.", dict(size=15))],
     [("• Latency is unreliable on shared hardware.", dict(size=15))]], spacing=8)
card(s, X0 + 5.85, 1.45, 5.88, 5.2, NAVY, [[("Conclusions", dict(size=20, bold=True, color="EEF2F6"))],
     [("1  ", dict(size=15, bold=True, color="F08A63")), ("Weak ACL leaks the secret directly; a strong ACL (filter before the model) closes it.", dict(size=15, color="EEF2F6"))],
     [("2  ", dict(size=15, bold=True, color="F08A63")), ("The side channel is reply style (AUC 0.82), not decision fields.", dict(size=15, color="EEF2F6"))],
     [("3  ", dict(size=15, bold=True, color="F08A63")), ("Only keeping confidential text out of the context closed it; masking does not hide the topic’s existence.", dict(size=15, color="EEF2F6"))],
     [("4  ", dict(size=15, bold=True, color="F08A63")), ("Shared memory leaks across users; per-user isolation removes it.", dict(size=15, color="EEF2F6"))],
     [("Future work: more topics, a commercial model, other secret policies, authenticated isolation.", dict(size=14, color="8FA3B8"))]], spacing=8)

prs.core_properties.title = "Behavioral Side-Channel Leakage in External AI Service Agents"
prs.core_properties.subject = "BLG558E - Security & Privacy - Final Project"
prs.save(str(OUT))
print("saved", OUT, len(prs.slides), "slides")
