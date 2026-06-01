# -*- coding: utf-8 -*-
"""Generate the KV Cache Offloading PDF report."""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.colors import HexColor
from reportlab.platypus import (Paragraph, Spacer, Image, Table, TableStyle,
    PageBreak, Frame, PageTemplate, BaseDocTemplate, NextPageTemplate,
    HRFlowable)

OUT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")
FIG = os.path.join(os.path.dirname(os.path.dirname(__file__)), "figures")
os.makedirs(OUT, exist_ok=True)
PDF = os.path.join(OUT, "KV_Cache_Offloading_Report.pdf")

# Build figure dict
FIGS = {}
for fn in ["fig1_kv_sizes","fig2_architecture","fig3_step_latency",
           "fig4_cumulative","fig5_memory","fig6_latency_sweep",
           "fig7_window_sweep","fig8_memory_sweep","fig9_wait_distribution",
           "fig10_heatmap"]:
    p = os.path.join(FIG, fn+".png")
    if os.path.exists(p): FIGS[fn] = p
print(f"Figures: {len(FIGS)}")

# Styles
TS = ParagraphStyle("T", fontSize=18, leading=22, alignment=TA_CENTER)
ST = ParagraphStyle("ST", fontSize=13, leading=16, parent=TS, textColor=HexColor("#555555"))
AU = ParagraphStyle("AU", fontSize=10, leading=13, alignment=TA_CENTER, spaceAfter=16)
AB = ParagraphStyle("AB", fontSize=9, leading=12, alignment=TA_JUSTIFY,
    leftIndent=14, rightIndent=14, spaceAfter=10, textColor=HexColor("#333333"))
AH = ParagraphStyle("AH", fontSize=10, leading=13, alignment=TA_CENTER, spaceAfter=6)
B = ParagraphStyle("B", fontSize=9, leading=12, alignment=TA_JUSTIFY, spaceAfter=5, spaceBefore=2)
H1 = ParagraphStyle("H1", fontSize=11, leading=14, spaceAfter=5, spaceBefore=10, textColor=HexColor("#1a1a2e"))
H2 = ParagraphStyle("H2", fontSize=10, leading=13, spaceAfter=3, spaceBefore=6, textColor=HexColor("#333355"))
CP = ParagraphStyle("CP", fontSize=8, leading=10, alignment=TA_CENTER, spaceAfter=7, spaceBefore=3, textColor=HexColor("#444"))
RF = ParagraphStyle("RF", fontSize=8, leading=10, leftIndent=16, firstLineIndent=-16, spaceAfter=3)
HL = ParagraphStyle("HL", parent=B, backColor=HexColor("#FFF8DC"), borderPadding=5, borderColor=HexColor("#DAA520"), borderWidth=0.5)
CB = ParagraphStyle("CB", fontName="Courier", fontSize=7.5, leading=10, leftIndent=8, spaceAfter=4, spaceBefore=2)

def make_doc():
    margin=0.7*inch; gap=0.2*inch
    doc=BaseDocTemplate(PDF, pagesize=letter, leftMargin=margin, rightMargin=margin, topMargin=0.8*inch, bottomMargin=0.7*inch)
    pw=letter[0]-2*margin; cw=(pw-gap)/2.0; fh=letter[1]-0.8*inch-0.7*inch; fb=0.7*inch
    doc.addPageTemplates([
        PageTemplate(id="T", frames=[Frame(margin,fb,pw,fh)]),
        PageTemplate(id="2C", frames=[Frame(margin,fb,cw,fh), Frame(margin+cw+gap,fb,cw,fh)]),
    ])
    return doc

def fig(story, key, w, caption):
    if key not in FIGS: return
    img=Image(FIGS[key], width=w, height=w*0.583)
    story.append(img); story.append(Paragraph(caption, CP))

def code(story, lines):
    for l in lines: story.append(Paragraph(l, CB))

print("Building content...")
