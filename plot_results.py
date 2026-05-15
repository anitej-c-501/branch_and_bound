import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

df = pd.read_csv('results.csv')

INTERESTING = ['air05', 'cap6000', 'misc07']
STRATEGIES = ['default', 'random', 'pseudocost', 'strong', 'reliability']
COLORS = {
    'default':     '#2196F3',
    'random':      '#F44336',
    'pseudocost':  '#4CAF50',
    'strong':      '#FF9800',
    'reliability': '#9C27B0',
}

df = df[df['instance'].isin(INTERESTING)]
df['strategy'] = pd.Categorical(df['strategy'], categories=STRATEGIES, ordered=True)
df = df.sort_values(['instance', 'strategy'])

fig, axes = plt.subplots(1, 3, figsize=(14, 5), sharey=False)
fig.suptitle('B&B Node Count by Instance and Branching Strategy', fontsize=13, fontweight='bold')

for ax, instance in zip(axes, INTERESTING):
    sub = df[df['instance'] == instance].sort_values('strategy')
    bars = ax.bar(
        sub['strategy'],
        sub['nodes'],
        color=[COLORS[s] for s in sub['strategy']],
        edgecolor='white',
        linewidth=0.5,
        width=0.6
    )
    ax.set_title(instance, fontsize=11, fontweight='bold')
    ax.set_xlabel('Strategy')
    ax.set_ylabel('Nodes' if ax == axes[0] else '')
    ax.tick_params(axis='x', rotation=30)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{int(x):,}'))
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, h * 1.01, f'{int(h):,}',
                ha='center', va='bottom', fontsize=7.5)

plt.tight_layout()
plt.savefig('plot_nodes.png', dpi=150, bbox_inches='tight')
plt.close()
print("Saved plot_nodes.png")

fig, axes = plt.subplots(1, 3, figsize=(14, 5), sharey=False)
fig.suptitle('Runtime by Instance and Branching Strategy', fontsize=13, fontweight='bold')

for ax, instance in zip(axes, INTERESTING):
    sub = df[df['instance'] == instance].sort_values('strategy')
    bars = ax.bar(
        sub['strategy'],
        sub['runtime'],
        color=[COLORS[s] for s in sub['strategy']],
        edgecolor='white',
        linewidth=0.5,
        width=0.6
    )
    ax.set_title(instance, fontsize=11, fontweight='bold')
    ax.set_xlabel('Strategy')
    ax.set_ylabel('Runtime (s)' if ax == axes[0] else '')
    ax.tick_params(axis='x', rotation=30)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, h * 1.01, f'{h:.1f}s',
                ha='center', va='bottom', fontsize=7.5)

plt.tight_layout()
plt.savefig('plot_runtime.png', dpi=150, bbox_inches='tight')
plt.close()
print("Saved plot_runtime.png")

df['time_per_node'] = df['runtime'] / df['nodes'].clip(lower=1)

fig, axes = plt.subplots(1, 3, figsize=(14, 5), sharey=False)
fig.suptitle('Runtime per Node by Instance and Branching Strategy', fontsize=13, fontweight='bold')

for ax, instance in zip(axes, INTERESTING):
    sub = df[df['instance'] == instance].sort_values('strategy')
    bars = ax.bar(
        sub['strategy'],
        sub['time_per_node'],
        color=[COLORS[s] for s in sub['strategy']],
        edgecolor='white',
        linewidth=0.5,
        width=0.6
    )
    ax.set_title(instance, fontsize=11, fontweight='bold')
    ax.set_xlabel('Strategy')
    ax.set_ylabel('Time per Node (s)' if ax == axes[0] else '')
    ax.tick_params(axis='x', rotation=30)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, h * 1.01, f'{h:.3f}s',
                ha='center', va='bottom', fontsize=7.5)

plt.tight_layout()
plt.savefig('plot_time_per_node.png', dpi=150, bbox_inches='tight')
plt.close()
print("Saved plot_time_per_node.png")

df['time_per_node'] = df['runtime'] / df['nodes'].clip(lower=1)

def compute_fair_node_number(df):
    result = df.copy()
    for instance in df['instance'].unique():
        mask = df['instance'] == instance
        min_tpn = df.loc[mask, 'time_per_node'].min()
        result.loc[mask, 'fair_node_number'] = df.loc[mask, 'nodes'] * (df.loc[mask, 'time_per_node'] / min_tpn)
    return result

df = compute_fair_node_number(df)

fig, axes = plt.subplots(1, 3, figsize=(14, 5), sharey=False)
fig.suptitle('Fair Node Number by Instance and Branching Strategy', fontsize=13, fontweight='bold')

for ax, instance in zip(axes, INTERESTING):
    sub = df[df['instance'] == instance].sort_values('strategy')
    bars = ax.bar(
        sub['strategy'],
        sub['fair_node_number'],
        color=[COLORS[s] for s in sub['strategy']],
        edgecolor='white',
        linewidth=0.5,
        width=0.6
    )
    ax.set_title(instance, fontsize=11, fontweight='bold')
    ax.set_xlabel('Strategy')
    ax.set_ylabel('Fair Node Number' if ax == axes[0] else '')
    ax.tick_params(axis='x', rotation=30)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{int(x):,}'))
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, h * 1.01, f'{int(h):,}',
                ha='center', va='bottom', fontsize=7.5)

plt.tight_layout()
plt.savefig('plot_fair_node_number.png', dpi=150, bbox_inches='tight')
plt.close()
print("Saved plot_fair_node_number.png")


print("\n=== Summary Table ===")
summary = df[['instance', 'strategy', 'nodes', 'runtime', 'gap', 'fair_node_number']].copy()
summary['runtime'] = summary['runtime'].round(1)
summary['gap'] = summary['gap'].round(4)
summary['fair_node_number'] = summary['fair_node_number'].round(1)
print(summary.to_string(index=False))