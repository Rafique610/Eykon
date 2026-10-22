import matplotlib.pyplot as plt
import numpy as np
import os
import shutil

# Set clean aesthetic styling
plt.rcParams['font.sans-serif'] = 'Segoe UI', 'DejaVu Sans', 'Helvetica', 'Arial'
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.edgecolor'] = '#E0E0E0'
plt.rcParams['axes.linewidth'] = 0.8
plt.rcParams['grid.color'] = '#EAEAEA'
plt.rcParams['grid.linestyle'] = '--'
plt.rcParams['grid.alpha'] = 0.7

fig, axes = plt.subplots(2, 3, figsize=(18, 11), dpi=300)
fig.patch.set_facecolor('#F8F9FA')

# Colors
COLOR_HIGH = '#1A73E8'   # Google Blue for Flagship Pixel
COLOR_MID = '#F25C05'    # Vibrant Amber/Orange for Mid-Range Infinix
COLOR_HIGH_LIGHT = '#D2E3FC'
COLOR_MID_LIGHT = '#FFE0B2'

HIGH_LABEL = 'High-Range Flagship\n(Google Pixel 9 Pro XL · Tensor G4 4nm)'
MID_LABEL = 'Mid-Range Device\n(Infinix Note 12 · Helio G96 12nm)'

devices = ['Pixel 9 Pro XL\n(High-Range · 4nm)', 'Infinix Note 12\n(Mid-Range · 12nm)']
colors = [COLOR_HIGH, COLOR_MID]

# -------------------------------------------------------------
# 1. LATENCY (Cold Start vs Warm Inference)
# -------------------------------------------------------------
ax1 = axes[0, 0]
ax1.set_facecolor('white')
x = np.arange(len(devices))
width = 0.35

cold_times = [6.3, 23.3]
warm_times = [4.7, 11.1]

rects1 = ax1.bar(x - width/2, cold_times, width, label='Cold Start (Init + Graph)', color=['#669DF6', '#FB8C00'], edgecolor='none', zorder=3)
rects2 = ax1.bar(x + width/2, warm_times, width, label='Warm Inference (RAG Query)', color=[COLOR_HIGH, COLOR_MID], edgecolor='none', zorder=3)

ax1.set_ylabel('Latency (Seconds) — Lower is Better', fontsize=11, fontweight='bold', color='#333333')
ax1.set_title('1. Query Response Latency', fontsize=13, fontweight='bold', pad=12, color='#202124')
ax1.set_xticks(x)
ax1.set_xticklabels(devices, fontsize=10, fontweight='bold')
ax1.grid(axis='y', zorder=0)
ax1.legend(loc='upper left', frameon=True, facecolor='white', framealpha=0.9, edgecolor='#E0E0E0', fontsize=9)

for r in rects1:
    h = r.get_height()
    ax1.annotate(f'{h:.1f}s', xy=(r.get_x() + r.get_width() / 2, h), xytext=(0, 3),
                 textcoords="offset points", ha='center', va='bottom', fontsize=9.5, fontweight='bold')
for r in rects2:
    h = r.get_height()
    ax1.annotate(f'{h:.1f}s', xy=(r.get_x() + r.get_width() / 2, h), xytext=(0, 3),
                 textcoords="offset points", ha='center', va='bottom', fontsize=9.5, fontweight='bold')
ax1.set_ylim(0, 26)

# -------------------------------------------------------------
# 2. POWER DRAW (Sustained Watts)
# -------------------------------------------------------------
ax2 = axes[0, 1]
ax2.set_facecolor('white')
power_vals = [1.42, 4.68]

bars2 = ax2.bar(devices, power_vals, color=colors, width=0.48, zorder=3)
ax2.set_ylabel('Power Consumption (Watts) — Lower is Better', fontsize=11, fontweight='bold', color='#333333')
ax2.set_title('2. Sustained Power Draw During Inference', fontsize=13, fontweight='bold', pad=12, color='#202124')
ax2.grid(axis='y', zorder=0)
ax2.set_ylim(0, 5.5)

for b in bars2:
    h = b.get_height()
    ax2.annotate(f'{h:.2f} W\n({int(h*1000)} mW)', xy=(b.get_x() + b.get_width() / 2, h), xytext=(0, 3),
                 textcoords="offset points", ha='center', va='bottom', fontsize=10, fontweight='bold')

ax2.annotate('3.3x Power Efficiency Gap\n(4nm FinFET vs 12nm)', xy=(0.5, 3.2), xycoords='data',
             ha='center', fontsize=9.5, fontstyle='italic', bbox=dict(boxstyle="round,pad=0.4", fc="#FFF9C4", ec="#FBC02D", lw=1))

# -------------------------------------------------------------
# 3. ENERGY CONSUMED PER QUERY (Joules)
# -------------------------------------------------------------
ax3 = axes[0, 2]
ax3.set_facecolor('white')
energy_vals = [6.72, 58.56]

bars3 = ax3.bar(devices, energy_vals, color=colors, width=0.48, zorder=3)
ax3.set_ylabel('Energy (Joules) — Lower is Better', fontsize=11, fontweight='bold', color='#333333')
ax3.set_title('3. Net Energy Consumed Per Query', fontsize=13, fontweight='bold', pad=12, color='#202124')
ax3.grid(axis='y', zorder=0)
ax3.set_ylim(0, 68)

for b in bars3:
    h = b.get_height()
    ax3.annotate(f'{h:.2f} J\n({h/3.6:.1f} mWh)', xy=(b.get_x() + b.get_width() / 2, h), xytext=(0, 3),
                 textcoords="offset points", ha='center', va='bottom', fontsize=10, fontweight='bold')

ax3.annotate('8.7x More Energy Efficient\nPer Answer Synthesis', xy=(0.5, 35), xycoords='data',
             ha='center', fontsize=9.5, fontstyle='italic', bbox=dict(boxstyle="round,pad=0.4", fc="#E8F5E9", ec="#81C784", lw=1))

# -------------------------------------------------------------
# 4. THERMAL STEADY-STATE PROFILE
# -------------------------------------------------------------
ax4 = axes[1, 0]
ax4.set_facecolor('white')

sensors = ['SoC Die', 'Chassis Skin', 'Battery Cell']
x4 = np.arange(len(sensors))
w4 = 0.35

pixel_thermals = [31.8, 33.1, 29.4]
infinix_thermals = [58.9, 37.7, 33.9]

r_p = ax4.bar(x4 - w4/2, pixel_thermals, w4, label='Pixel 9 Pro XL (High-Range)', color=COLOR_HIGH, zorder=3)
r_i = ax4.bar(x4 + w4/2, infinix_thermals, w4, label='Infinix Note 12 (Mid-Range)', color=COLOR_MID, zorder=3)

ax4.set_ylabel('Temperature (°C) — Steady State', fontsize=11, fontweight='bold', color='#333333')
ax4.set_title('4. Steady-State Thermals (Sustained Run)', fontsize=13, fontweight='bold', pad=12, color='#202124')
ax4.set_xticks(x4)
ax4.set_xticklabels(sensors, fontsize=10, fontweight='bold')
ax4.grid(axis='y', zorder=0)
ax4.set_ylim(0, 75)
ax4.legend(loc='upper right', frameon=True, facecolor='white', framealpha=0.9, edgecolor='#E0E0E0', fontsize=9.5)

for r in r_p:
    h = r.get_height()
    ax4.annotate(f'{h:.1f}°', xy=(r.get_x() + r.get_width() / 2, h), xytext=(0, 3),
                 textcoords="offset points", ha='center', va='bottom', fontsize=9.5, fontweight='bold')
for r in r_i:
    h = r.get_height()
    ax4.annotate(f'{h:.1f}°', xy=(r.get_x() + r.get_width() / 2, h), xytext=(0, 3),
                 textcoords="offset points", ha='center', va='bottom', fontsize=9.5, fontweight='bold')

# -------------------------------------------------------------
# 5. PHYSICAL RAM FOOTPRINT & DEVICE LOAD
# -------------------------------------------------------------
ax5 = axes[1, 1]
ax5.set_facecolor('white')

ram_mb = [311.9, 2120.1]
bars5 = ax5.bar(devices, ram_mb, color=colors, width=0.48, zorder=3)

ax5.set_ylabel('Active Physical RAM RSS (MB) — Lower is Better', fontsize=11, fontweight='bold', color='#333333')
ax5.set_title('5. Physical RAM Allocation & % of System RAM', fontsize=13, fontweight='bold', pad=12, color='#202124')
ax5.grid(axis='y', zorder=0)
ax5.set_ylim(0, 2600)

labels_ram = [
    '311.9 MB\n(~2.5% of 16 GB RAM)',
    '2,120.1 MB\n(~26.5% of 8 GB RAM)'
]

for i, b in enumerate(bars5):
    h = b.get_height()
    ax5.annotate(labels_ram[i], xy=(b.get_x() + b.get_width() / 2, h), xytext=(0, 3),
                 textcoords="offset points", ha='center', va='bottom', fontsize=9.5, fontweight='bold')

# -------------------------------------------------------------
# 6. CONTINUOUS GENERATION ENDURANCE (Hours)
# -------------------------------------------------------------
ax6 = axes[1, 2]
ax6.set_facecolor('white')

endurance_hours = [13.7, 4.1]
bars6 = ax6.bar(devices, endurance_hours, color=colors, width=0.48, zorder=3)

ax6.set_ylabel('Continuous Querying (Hours) — Higher is Better', fontsize=11, fontweight='bold', color='#333333')
ax6.set_title('6. Continuous Back-to-Back Battery Life', fontsize=13, fontweight='bold', pad=12, color='#202124')
ax6.grid(axis='y', zorder=0)
ax6.set_ylim(0, 16)

labels_endurance = [
    '13.7 Hours\n(~10,500 Queries)',
    '4.1 Hours\n(~1,200 Queries)'
]

for i, b in enumerate(bars6):
    h = b.get_height()
    ax6.annotate(labels_endurance[i], xy=(b.get_x() + b.get_width() / 2, h), xytext=(0, 3),
                 textcoords="offset points", ha='center', va='bottom', fontsize=9.5, fontweight='bold')

# Main Super Title
plt.suptitle('Eykon On-Device RAG Hardware Benchmark: High-Range vs Mid-Range Mobile Comparison\n'
             'Workload: Gemma 4 E2B LiteRT-LM (2.4 GB INT4) + SQLite Room FTS Hybrid Retrieval',
             fontsize=15, fontweight='bold', color='#202124', y=0.98)

plt.tight_layout(rect=[0, 0.03, 1, 0.94])

# Save in scratch
out_scratch = 'scratch/benchmark_high_vs_mid_range.png'
plt.savefig(out_scratch, dpi=300, bbox_inches='tight')
print(f'Successfully saved to {out_scratch}')

# Copy to artifacts dir
artifact_dir = r'C:\Users\rafique_\.gemini\antigravity\brain\8f2736b2-adcb-4223-ace7-e353ce0f8c07'
if os.path.exists(artifact_dir):
    out_artifact = os.path.join(artifact_dir, 'benchmark_high_vs_mid_range.png')
    shutil.copyfile(out_scratch, out_artifact)
    print(f'Successfully copied to {out_artifact}')
