def build():
    s=[]
    s.append(NextPageTemplate("T"))
    s.append(Spacer(1,1.2*inch))
    s.append(Paragraph("Distributed KV Cache Offloading",TS))
    s.append(Paragraph("for Mobile LLM Inference",TS))
    s.append(Spacer(1,0.1*inch))
    s.append(Paragraph("A Simulation Study of Async Prefetch Over Wi-Fi 6",ST))
    s.append(Spacer(1,0.3*inch))
    s.append(HRFlowable(width="50%",thickness=1,color=HexColor("#4C72B0")))
    s.append(Spacer(1,0.15*inch))
    s.append(Paragraph("Data Communication Course Project Report | 2026",AU))
    s.append(Spacer(1,0.25*inch))
    s.append(Paragraph("<b>Abstract</b>",AH))
    s.append(Paragraph(
        "LLM inference on mobile devices is constrained by GPU memory. The KV cache "
        "grows at ~512 KB/token for a 7B model. A 4K sequence needs 2 GB, exceeding "
        "mobile budgets. We simulate distributed KV cache offloading over Wi-Fi 6. "
        "Results: 3.72x speedup with 512 MB memory and 50 ms latency. A prefetch "
        "window of 4 tokens fully hides the 108 ms per-token transfer. Speedup "
        "reaches 11.2x at 200 ms RTT.",AB))
    s.append(PageBreak())
    s.append(NextPageTemplate("2C"))
    return s
