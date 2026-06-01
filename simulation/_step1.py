# -*- coding: utf-8 -*-
import os, sys
# Write a simple placeholder report
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.colors import HexColor
from reportlab.platypus import (Paragraph, Spacer, Image, Table, TableStyle,
    PageBreak, Frame, PageTemplate, BaseDocTemplate, NextPageTemplate, HRFlowable)

OUT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")
FIG = os.path.join(os.path.dirname(os.path.dirname(__file__)), "figures")
os.makedirs(OUT, exist_ok=True)

print("Step 1: config OK")
print("OUT:", OUT)
print("FIG:", FIG)
