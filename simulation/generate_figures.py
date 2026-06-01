# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from kv_cache_sim import SimConfig, simulate_demand, simulate_prefetch, run_sweep
OUT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "figures")
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.family": "serif", "font.size": 10, "axes.labelsize": 11,
    "axes.titlesize": 12, "legend.fontsize": 9, "figure.dpi": 150})
def model_kv_stats():
    rows = []
    for name, nl, nh, hd in [
        ('LLaMA-7B', 32, 32, 128),
        ('LLaMA-13B', 40, 40, 128),
        ('LLaMA-70B', 80, 64, 128),
        ('GPT-3 175B', 96, 96, 128),
    ]:
        bpt = 2 * nl * nh * hd * 2
        rows.append(dict(model=name, layers=nl, heads=nh,
                         kv4k_MB=bpt*4096/1048576,
                         kv8k_MB=bpt*8192/1048576,
                         kv32k_MB=bpt*32768/1048576))
    return rows

def fig1():
    r = model_kv_stats()
    x = np.arange(len(r)); w = 0.25
    fig, ax = plt.subplots(figsize=(6,3.5))
    ax.bar(x-w,[i["kv4k_MB"] for i in r],w,label="4K",color="#4C72B0")
    ax.bar(x,[i["kv8k_MB"] for i in r],w,label="8K",color="#55A868")
    ax.bar(x+w,[i["kv32k_MB"] for i in r],w,label="32K",color="#C44E52")
    ax.set_ylabel("KV Cache (MB)"); ax.set_xticks(x)
    ax.set_xticklabels([i["model"] for i in r],fontsize=9); ax.legend()
    ax.set_title("KV Cache Footprint"); ax.grid(axis="y",alpha=0.3); plt.tight_layout()
    fig.savefig(os.path.join(OUT,"fig1_kv_sizes.png")); plt.close(fig); print("fig1")
def fig2():
    fig,ax=plt.subplots(figsize=(6,3.5));ax.set_xlim(0,10);ax.set_ylim(0,6);ax.axis("off")
    p=mpatches.FancyBboxPatch((0.5,2),3,3,boxstyle="round,pad=0.15",facecolor="#E8F4FD",edgecolor="#2B7A9E",linewidth=2);ax.add_patch(p)
    ax.text(2,4.3,"Mobile Device",ha="center",fontsize=11,fontweight="bold");ax.text(2,3.5,"Limited KV Cache",ha="center",fontsize=9,color="#2B7A9E")
    ax.annotate("",xy=(3.5,3.5),xytext=(6.5,3.5),arrowprops=dict(arrowstyle="<->",lw=2.5,color="#CC6677"))
    ax.text(5,3.8,"Wi-Fi 6",ha="center",fontsize=9,color="#CC6677")
    p=mpatches.FancyBboxPatch((6.5,2),3,3,boxstyle="round,pad=0.15",facecolor="#F0FFF0",edgecolor="#2E7D32",linewidth=2);ax.add_patch(p)
    ax.text(8,4.3,"Home PC",ha="center",fontsize=11,fontweight="bold");ax.text(8,3.5,"Large KV Cache",ha="center",fontsize=9,color="#2E7D32")
    ax.annotate("",xy=(3.5,2.5),xytext=(6.5,2.5),arrowprops=dict(arrowstyle="->",lw=2,color="#C44E52",linestyle="dashed"))
    ax.text(5,2.2,"Evict (write)",ha="center",fontsize=8,color="#C44E52")
    ax.annotate("",xy=(6.5,4.5),xytext=(3.5,4.5),arrowprops=dict(arrowstyle="->",lw=2,color="#4C72B0",linestyle="dashed"))
    ax.text(5,4.8,"Prefetch (read)",ha="center",fontsize=8,color="#4C72B0")
    ax.set_title("Architecture",fontsize=12);plt.tight_layout();fig.savefig(os.path.join(OUT,"fig2_architecture.png"));plt.close(fig);print("fig2")
def fig3():
    c=SimConfig(seq_len=256,local_memory=64*1024*1024,prefetch_window=8);d=simulate_demand(c);pf=simulate_prefetch(c)
    s,e=c.local_slots,c.seq_len;st=list(range(s,e))
    fig,(a1,a2)=plt.subplots(2,1,figsize=(6,4.5),sharex=True)
    dw=[x.wait_ms for x in d[s:e]];a1.bar(st,[c.compute_ms]*len(st),label="Compute",color="#4C72B0")
    a1.bar(st,dw,bottom=[c.compute_ms]*len(st),label="Wait",color="#C44E52")
    a1.set_ylabel("ms");a1.set_title("Demand Paging");a1.legend(fontsize=8);a1.grid(axis="y",alpha=.3)
    pw=[x.wait_ms for x in pf[s:e]]
    a2.bar(st,[c.compute_ms]*len(st),label="Compute",color="#4C72B0")
    a2.bar(st,pw,bottom=[c.compute_ms]*len(st),label="Wait",color="#C44E52")
    a2.set_ylabel("ms");a2.set_xlabel("Token");a2.set_title("Async Prefetch")
    a2.legend(fontsize=8);a2.grid(axis="y",alpha=.3);plt.tight_layout()
    fig.savefig(os.path.join(OUT,"fig3_step_latency.png"));plt.close(fig);print("fig3")
def fig4():
    c=SimConfig(seq_len=2048,local_memory=256*1024*1024);d=simulate_demand(c);pf=simulate_prefetch(c)
    fig,ax=plt.subplots(figsize=(6,3.5))
    ax.plot([x.idx for x in d],[x.wall_ms/1000 for x in d],label="Demand",color="#C44E52",lw=1.5)
    ax.plot([x.idx for x in pf],[x.wall_ms/1000 for x in pf],label="Prefetch",color="#4C72B0",lw=1.5)
    ax.axvline(x=c.local_slots,color="gray",linestyle="--",alpha=.5,label="Mem full")
    ax.set_xlabel("Token");ax.set_ylabel("Time (s)");ax.set_title("Generation Time")
    ax.legend();ax.grid(alpha=.3);ax.set_xlim(0,c.seq_len);plt.tight_layout()
    fig.savefig(os.path.join(OUT,"fig4_cumulative.png"));plt.close(fig);print("fig4")
def fig5():
    c=SimConfig(seq_len=2048,local_memory=256*1024*1024);d=simulate_demand(c);pf=simulate_prefetch(c)
    tb=c.kv_bpt/(1024*1024);lm=c.local_memory/(1024*1024)
    fig,(a1,a2)=plt.subplots(2,1,figsize=(6,4.5),sharex=True)
    for dd,aa in [(d,a1),(pf,a2)]:
        st=[x.idx for x in dd];lo=[x.local_cnt*tb for x in dd]
        re=[x.evictions_done*tb for x in dd];to=[l+r for l,r in zip(lo,re)]
        aa.fill_between(st,lo,label="Local",color="#55A868",alpha=.7)
        aa.fill_between(st,lo,to,label="Remote",color="#C44E52",alpha=.5)
        aa.axhline(y=lm,color="gray",linestyle="--",alpha=.5);aa.set_ylabel("MB")
        aa.legend(fontsize=8);aa.grid(alpha=.3)
    a1.set_title("Demand");a2.set_title("Prefetch");a2.set_xlabel("Token")
    plt.tight_layout();fig.savefig(os.path.join(OUT,"fig5_memory.png"));plt.close(fig);print("fig5")
def fig6():
    sw=run_sweep();pts=[x for x in sw if x.window==16 and x.mem_mb==512];xs=[x.latency_ms for x in pts]
    fig,a1=plt.subplots(figsize=(5.5,3.5));a2=a1.twinx()
    a1.plot(xs,[x.demand_s for x in pts],"o-",color="#C44E52",lw=1.5,label="Demand")
    a1.plot(xs,[x.prefetch_s for x in pts],"s-",color="#4C72B0",lw=1.5,label="Prefetch")
    a1.set_xlabel("Latency (ms)");a1.set_ylabel("Time (s)");a1.grid(alpha=.3)
    a2.plot(xs,[x.speedup for x in pts],"D-",color="#9467BD",lw=1.5,label="Speedup")
    a2.set_ylabel("Speedup",color="#9467BD");a2.tick_params(axis="y",labelcolor="#9467BD")
    l1,l2=a1.get_legend_handles_labels();l3,l4=a2.get_legend_handles_labels()
    a1.legend(l1+l3,l2+l4,fontsize=8);a1.set_title("Latency Impact")
    plt.tight_layout();fig.savefig(os.path.join(OUT,"fig6_latency_sweep.png"));plt.close(fig);print("fig6")
def fig7():
    sw=run_sweep();pts=[x for x in sw if abs(x.latency_ms-50)<0.1 and x.mem_mb==512]
    ws=[x.window for x in pts]
    fig,ax=plt.subplots(figsize=(5.5,3.5))
    ax.semilogx(ws,[x.speedup for x in pts],"o-",color="#4C72B0",lw=1.5)
    ax.axvline(x=4,color="gray",linestyle="--",alpha=.5,label="Critical w=4")
    ax.set_xlabel("Window");ax.set_ylabel("Speedup");ax.set_title("Speedup vs Window")
    ax.set_xticks(ws);ax.set_xticklabels([str(w) for w in ws])
    ax.grid(alpha=.3);ax.legend(fontsize=9);plt.tight_layout()
    fig.savefig(os.path.join(OUT,"fig7_window_sweep.png"));plt.close(fig);print("fig7")
def fig8():
    sw=run_sweep();pts=[x for x in sw if abs(x.latency_ms-50)<0.1 and x.window==16]
    xs=[x.mem_mb for x in pts]
    fig,a1=plt.subplots(figsize=(5.5,3.5));a2=a1.twinx()
    a1.plot(xs,[x.demand_s for x in pts],"o-",color="#C44E52",lw=1.5,label="Demand")
    a1.plot(xs,[x.prefetch_s for x in pts],"s-",color="#4C72B0",lw=1.5,label="Prefetch")
    a1.set_xlabel("Memory (MB)");a1.set_ylabel("Time (s)");a1.grid(alpha=.3)
    a2.plot(xs,[x.speedup for x in pts],"D-",color="#9467BD",lw=1.5,label="Speedup")
    a2.set_ylabel("Speedup",color="#9467BD");a2.tick_params(axis="y",labelcolor="#9467BD")
    l1,l2=a1.get_legend_handles_labels();l3,l4=a2.get_legend_handles_labels()
    a1.legend(l1+l3,l2+l4,fontsize=8);a1.set_title("Memory Impact")
    plt.tight_layout();fig.savefig(os.path.join(OUT,"fig8_memory_sweep.png"));plt.close(fig);print("fig8")
def fig9():
    c=SimConfig(seq_len=2048,local_memory=256*1024*1024);d=simulate_demand(c);pf=simulate_prefetch(c)
    tc=c.seq_len*c.compute_ms/1000;wd=sum(x.wait_ms for x in d)/1000;wp=sum(x.wait_ms for x in pf)/1000
    fig,ax=plt.subplots(figsize=(4.5,3.5))
    ax.bar(["Demand","Prefetch"],[tc,tc],label="Compute",color="#4C72B0")
    ax.bar(["Demand","Prefetch"],[wd,wp],bottom=[tc,tc],label="Wait",color="#C44E52")
    for i,t in enumerate([tc+wd,tc+wp]):ax.text(i,t+5,f"{t:.0f}s",ha="center",va="bottom",fontweight="bold",fontsize=10)
    ax.set_ylabel("Time (s)");ax.set_title("Time Composition");ax.legend(fontsize=9);ax.grid(axis="y",alpha=.3)
    plt.tight_layout();fig.savefig(os.path.join(OUT,"fig9_wait_distribution.png"));plt.close(fig);print("fig9")
def fig10():
    lats=[5,10,20,50,100,200];windows=[1,2,4,8,16,32,64]
    base=dict(num_layers=32,num_heads=32,head_dim=128,seq_len=4096,local_memory=512*1024*1024,latency_ms=50.0,bandwidth_mbps=500.0,prefetch_window=16)
    d=np.zeros((len(windows),len(lats)))
    for j,lat in enumerate(lats):
        for i,w in enumerate(windows):
            p=dict(base);p["latency_ms"]=float(lat);p["prefetch_window"]=w
            c=SimConfig(**p);dd,pf=simulate_demand(c),simulate_prefetch(c)
            d[i,j]=dd[-1].wall_ms/pf[-1].wall_ms
    fig,ax=plt.subplots(figsize=(6,4))
    im=ax.imshow(d,cmap="YlOrRd",aspect="auto",vmin=1)
    ax.set_xticks(range(len(lats)));ax.set_xticklabels([str(l) for l in lats])
    ax.set_yticks(range(len(windows)));ax.set_yticklabels([str(w) for w in windows])
    ax.set_xlabel("Latency (ms)");ax.set_ylabel("Window")
    for i in range(len(windows)):
        for j in range(len(lats)):
            ax.text(j,i,f"{d[i,j]:.1f}x",ha="center",va="center",fontsize=8,fontweight="bold",
                    color="white" if d[i,j]>3 else "black")
    fig.colorbar(im,ax=ax,shrink=0.8).set_label("Speedup")
    ax.set_title("Speedup Heatmap");plt.tight_layout()
    fig.savefig(os.path.join(OUT,"fig10_heatmap.png"));plt.close(fig);print("fig10")
if __name__=="__main__":
    for fn in [fig1,fig2,fig3,fig4,fig5,fig6,fig7,fig8,fig9,fig10]: fn()
    print("All done:",OUT)


