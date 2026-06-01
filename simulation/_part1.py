#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.colors import HexColor
from reportlab.platypus import (Paragraph, Spacer, Image, Table, TableStyle,
    PageBreak, Frame, PageTemplate, BaseDocTemplate, NextPageTemplate, HRFlowable)

D=os.path.dirname
OUT=os.path.join(D(D(__file__)),"reports")
FIG=os.path.join(D(D(__file__)),"figures")
os.makedirs(OUT,exist_ok=True)
PDF=os.path.join(OUT,"KV_Cache_Offloading_Report.pdf")

FIGS={}
for fn in ["fig1_kv_sizes","fig2_architecture","fig3_step_latency","fig4_cumulative",
           "fig5_memory","fig6_latency_sweep","fig7_window_sweep","fig8_memory_sweep",
           "fig9_wait_distribution","fig10_heatmap"]:
    p=os.path.join(FIG,fn+".png")
    if os.path.exists(p):FIGS[fn]=p
print(f"Figures: {len(FIGS)}")

S=ParagraphStyle
TS=S("TS",fontSize=18,leading=22,alignment=TA_CENTER)
ST=S("ST",fontSize=13,leading=16,alignment=TA_CENTER,textColor=HexColor("#555"))
AU=S("AU",fontSize=10,alignment=TA_CENTER,spaceAfter=16)
AB=S("AB",fontSize=9,leading=12,alignment=TA_JUSTIFY,leftIndent=14,rightIndent=14,spaceAfter=10)
AH=S("AH",fontSize=10,alignment=TA_CENTER,spaceAfter=6)
B=S("B",fontSize=9,leading=12,alignment=TA_JUSTIFY,spaceAfter=5,spaceBefore=2)
H1=S("H1",fontSize=11,leading=14,spaceAfter=5,spaceBefore=10,textColor=HexColor("#1a1a2e"))
H2=S("H2",fontSize=10,leading=13,spaceAfter=3,spaceBefore=6,textColor=HexColor("#333355"))
CP=S("CP",fontSize=8,leading=10,alignment=TA_CENTER,spaceAfter=7,spaceBefore=3)
RF=S("RF",fontSize=8,leading=10,leftIndent=16,firstLineIndent=-16,spaceAfter=3)
HL=S("HL",parent=B,backColor=HexColor("#FFF8DC"),borderPadding=5,borderColor=HexColor("#DAA520"),borderWidth=0.5)
CB=S("CB",fontName="Courier",fontSize=7.5,leading=10,leftIndent=8,spaceAfter=4)
FN=S("FN",parent=CP,alignment=TA_CENTER)

def doc():
    mg=0.7*inch;gp=0.2*inch
    d=BaseDocTemplate(PDF,pagesize=letter,leftMargin=mg,rightMargin=mg,topMargin=0.8*inch,bottomMargin=0.7*inch)
    pw=letter[0]-2*mg;cw=(pw-gp)/2;fh=letter[1]-1.5*inch;fb=0.7*inch
    d.addPageTemplates([PageTemplate(id="T",frames=[Frame(mg,fb,pw,fh)]),
        PageTemplate(id="2C",frames=[Frame(mg,fb,cw,fh),Frame(mg+cw+gp,fb,cw,fh)])])
    return d

def im(s,k,w,c):
    if k in FIGS:
        s.append(Image(FIGS[k],width=w,height=w*0.583))
        s.append(Paragraph(c,CP))

def cb(s,lines):
    for l in lines: s.append(Paragraph(l,CB))

print("Setup OK")
