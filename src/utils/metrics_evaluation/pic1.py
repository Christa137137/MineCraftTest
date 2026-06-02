import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

h, r = 10, 10
bks = ['Water', 'Light', 'Projectile']
mds = ['Baseline-RT', 'Baseline-MBF', 'Proposed-LLM1', 'Proposed-LLM2', 'Proposed-LLM3']
ts = np.linspace(0, h, 21)
clrs = ["#C3CA0E", "#45C92B", "#366EC2", "#C90F0F", "#A80D81"]

f1, axs1 = plt.subplots(1, 3, figsize=(18, 7), sharey=True)
for i, bk in enumerate(bks):
    ax = axs1[i]
    for j, md in enumerate(mds):
        if 'RT' in md:
            y = 20 * (ts / h)**0.8
        elif 'MBF' in md:
            y = 40 * (ts / h)**0.7
        else:
            base = 80 if 'LLM1' in md else (75 if 'LLM2' in md else 85)
            y = base * (1 - np.exp(-0.3 * ts))
            y *= (base / y[-1])
        ax.plot(ts, y, color=clrs[j], linewidth=2.5, label=md)
    ax.set_title(bk, fontsize=14)
    ax.set_xlabel('Time (h)', fontsize=12)
    if i == 0: ax.set_ylabel('Inconsistency Count', fontsize=12)
    ax.set_ylim(0, 110)
    ax.grid(True, linestyle='--', alpha=0.6)

handles, labels = axs1[0].get_legend_handles_labels()
f1.legend(handles, labels, loc='upper center', bbox_to_anchor=(0.5, 0.98), ncol=5, frameon=False, fontsize=11)
plt.tight_layout(rect=[0, 0, 1, 0.90])
plt.show()

f2, axs2 = plt.subplots(1, 3, figsize=(18, 7), sharey=True)
for i, bk in enumerate(bks):
    ax = axs2[i]
    data_to_plot = []
    for md in mds:
        base = 20 if 'RT' in md else (40 if 'MBF' in md else (80 if 'LLM1' in md else (75 if 'LLM2' in md else 85)))
        data_to_plot.append(base + np.random.normal(0, 3, r))
    
    bp = ax.boxplot(data_to_plot, widths=0.6, patch_artist=False, showfliers=False)
    plt.setp(bp['boxes'], color='black', linewidth=1.5)
    plt.setp(bp['whiskers'], color='black', linewidth=1.5)
    plt.setp(bp['caps'], color='black', linewidth=1.5)
    plt.setp(bp['medians'], color='black', linewidth=1.5)
    
    ax.set_title(bk, fontsize=14)
    ax.set_xticklabels(mds, rotation=45, fontsize=10)
    if i == 0: ax.set_ylabel('Inconsistency Count', fontsize=12)
    ax.set_ylim(0, 110)
    ax.grid(True, linestyle='--', alpha=0.3)

legend_elements = [Line2D([0], [0], color=clrs[idx], lw=3, label=m) for idx, m in enumerate(mds)]
f2.legend(handles=legend_elements, loc='upper center', bbox_to_anchor=(0.5, 0.98), ncol=5, frameon=False, fontsize=11)
plt.tight_layout(rect=[0, 0, 1, 0.90])
plt.show()