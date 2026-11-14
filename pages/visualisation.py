import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Copy the existing dataframe so the original data in Colab remains untouched
df_plot = df_birth.copy()
df_plot['date'] = pd.to_datetime(df_plot['date'])
df_plot['year'] = df_plot['date'].dt.year

# (Optional) Remove the '#' on the line below if you only want to filter for 2020–2024:
# df_plot = df_plot[(df_plot['year'] >= 2020) & (df_plot['year'] <= 2024)]

# Create a dual-axis visualization (Bars for Total Live Births, Line for Crude Birth Rate)
sns.set_theme(style="whitegrid")
fig, ax1 = plt.subplots(figsize=(13, 6))

bars = ax1.bar(
    df_plot['year'], df_plot['abs'],
    color='#2b5c8f', alpha=0.85, width=0.6,
    label='Total Live Births (abs)'
)
ax1.set_title('Trends in Live Births and Crude Birth Rate in Malaysia (2000–2025)', fontsize=13, fontweight='bold', pad=15)
ax1.set_xlabel('Year', fontweight='bold')
ax1.set_ylabel('Total Live Births (abs)', color='#2b5c8f', fontweight='bold')
ax1.set_xticks(df_plot['year'])
ax1.tick_params(axis='x', rotation=45)
ax1.set_ylim(0, df_plot['abs'].max() * 1.15)

# Secondary Y-axis for Crude Birth Rate
ax2 = ax1.twinx()
ax2.plot(
    df_plot['year'], df_plot['rate'],
    color='#d95f02', marker='o', linewidth=2.5,
    label='Crude Birth Rate (per 1,000 population)'
)
ax2.set_ylabel('Crude Birth Rate', color='#d95f02', fontweight='bold')
ax2.set_ylim(0, df_plot['rate'].max() * 1.15)
ax2.grid(False)

# Combine legends from both axes
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right')

plt.tight_layout()
plt.show()
