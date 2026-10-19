
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter

# ==================================================
# 1. CONFIGURATION & VISUAL STYLE
# ==================================================

ROOT = Path(__file__).resolve().parent
PROCESSED = ROOT / "data" / "processed"
CHARTS = PROCESSED / "charts"

CHARTS.mkdir(parents=True, exist_ok=True)

COLORS = {
    "Commits": "#2563EB",
    "Issues": "#F59E0B",
    "Pull Requests": "#0F9D8A",
    "Vietnam": "#E45756",
    "International": "#2563EB",
    "Unknown": "#D1D5DB",
    "Identified": "#0F9D8A",
    "Unresolved": "#D9DEE7",
    "Text": "#1F2937",
    "Muted": "#64748B",
    "Grid": "#E5E7EB",
}

plt.rcParams.update({
    "figure.dpi": 120,
    "savefig.dpi": 220,
    "savefig.facecolor": "white",
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.labelsize": 10,
    "axes.labelcolor": COLORS["Muted"],
    "text.color": COLORS["Text"],
    "xtick.color": COLORS["Muted"],
    "ytick.color": COLORS["Muted"],
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.spines.left": False,
    "axes.spines.bottom": True,
    "axes.edgecolor": COLORS["Grid"],
    "axes.linewidth": 0.8,
    "grid.color": COLORS["Grid"],
    "grid.linewidth": 0.7,
    "legend.frameon": False,
})


def load_csv(filename):
    path = PROCESSED / filename

    if not path.exists():
        print("Khong tim thay:", path)
        return None

    return pd.read_csv(path, encoding="utf-8-sig")


def format_number(value, _position=None):
    return f"{value:,.0f}"


def save_chart(fig, filename):
    output = CHARTS / filename

    fig.savefig(
        output,
        bbox_inches="tight",
        facecolor="white",
    )

    plt.close(fig)
    print("Da luu:", output)


# ==================================================
# 2. CHART 1 - MONTHLY ACTIVITY
# Moi loai hoat dong co truc Y rieng
# ==================================================

monthly = load_csv("monthly_activity.csv")

if monthly is not None and not monthly.empty:
    required = {"month", "records", "table"}

    if required.issubset(monthly.columns):
        monthly["month"] = pd.to_datetime(
            monthly["month"],
            format="%Y-%m",
            errors="coerce",
        )

        monthly = monthly.dropna(subset=["month"])

        pivot = monthly.pivot_table(
            index="month",
            columns="table",
            values="records",
            aggfunc="sum",
            fill_value=0,
        ).sort_index()

        preferred_order = [
            name for name in
            ["Commits", "Issues", "Pull Requests"]
            if name in pivot.columns
        ]

        if preferred_order:
            fig, axes = plt.subplots(
                len(preferred_order),
                1,
                figsize=(12, 3.2 * len(preferred_order)),
                sharex=True,
            )

            if len(preferred_order) == 1:
                axes = [axes]

            for ax, name in zip(axes, preferred_order):
                series = pivot[name]

                ax.plot(
                    series.index,
                    series.values,
                    color=COLORS.get(name, COLORS["International"]),
                    linewidth=2.2,
                )

                ax.fill_between(
                    series.index,
                    series.values,
                    color=COLORS.get(name, COLORS["International"]),
                    alpha=0.10,
                )

                ax.set_title(name, loc="left", pad=9)
                ax.set_ylabel("Records")
                ax.yaxis.set_major_formatter(
                    FuncFormatter(format_number)
                )
                ax.grid(axis="y", alpha=0.8)
                ax.set_axisbelow(True)

                # Khong hien tick qua day
                ax.xaxis.set_major_locator(mdates.YearLocator())
                ax.xaxis.set_major_formatter(
                    mdates.DateFormatter("%Y")
                )

            axes[-1].set_xlabel("Year")

            fig.suptitle(
                "GitHub Activity Trends",
                x=0.07,
                ha="left",
                fontsize=19,
                fontweight="bold",
                color=COLORS["Text"],
            )

            fig.text(
                0.07,
                0.985,
                "Monthly records in the collected dataset | 2020–2026",
                fontsize=10,
                color=COLORS["Muted"],
                va="top",
            )

            fig.tight_layout(rect=[0.04, 0.02, 0.99, 0.94])

            save_chart(fig, "01_monthly_activity.png")


# ==================================================
# 3. CHART 2 - COUNTRY COMPARISON
# Luon giu Vietnam trong bieu do
# ==================================================

country = load_csv("activity_by_country.csv")

if country is not None and not country.empty:
    required = {"country_or_region", "activity_records"}

    if required.issubset(country.columns):
        country_summary = (
            country.groupby("country_or_region")["activity_records"]
            .sum()
            .sort_values(ascending=False)
        )

        excluded = {
            "Unknown",
            "Other/Unknown",
            "Unprofiled",
            "No Author Login",
        }

        recognized = country_summary[
            ~country_summary.index.isin(excluded)
        ]

        top = recognized.head(8).copy()

        if "Vietnam" in recognized.index:
            top.loc["Vietnam"] = recognized["Vietnam"]

        top = top.sort_values()

        fig, ax = plt.subplots(figsize=(10, 6.5))

        bar_colors = [
            COLORS["Vietnam"] if name == "Vietnam"
            else COLORS["International"]
            for name in top.index
        ]

        bars = ax.barh(
            top.index,
            top.values,
            color=bar_colors,
            height=0.66,
        )

        ax.set_title(
            "GitHub Activity by Identified Country / Region",
            loc="left",
            fontsize=15,
            pad=18,
        )

        ax.text(
            0,
            1.02,
            "Based on self-reported developer profile locations",
            transform=ax.transAxes,
            fontsize=9,
            color=COLORS["Muted"],
        )

        ax.set_xlabel("Activity records")
        ax.xaxis.set_major_formatter(
            FuncFormatter(format_number)
        )

        ax.grid(axis="x", alpha=0.8)
        ax.set_axisbelow(True)

        max_value = max(top.values) if len(top) else 1
        ax.set_xlim(0, max_value * 1.18)

        for bar, value in zip(bars, top.values):
            ax.text(
                value + max_value * 0.015,
                bar.get_y() + bar.get_height() / 2,
                f"{value:,.0f}",
                va="center",
                fontsize=9,
                color=COLORS["Text"],
            )

        fig.tight_layout()

        save_chart(fig, "02_activity_by_country.png")


# ==================================================
# 4. CHART 3 - COUNTRY ATTRIBUTION COVERAGE
# Dung phan tram de so sanh cong bang
# ==================================================

coverage = load_csv("country_activity_coverage.csv")

if coverage is not None and not coverage.empty:
    required = {
        "table",
        "rows_with_recognized_country",
        "rows_unknown_or_unprofiled",
    }

    if required.issubset(coverage.columns):
        data = coverage.set_index("table")[
            [
                "rows_with_recognized_country",
                "rows_unknown_or_unprofiled",
            ]
        ].copy()

        data.columns = ["Identified", "Unresolved"]

        totals = data.sum(axis=1).replace(0, pd.NA)

        percentages = data.div(totals, axis=0).fillna(0) * 100

        fig, ax = plt.subplots(figsize=(10, 5.5))

        y_positions = range(len(percentages))

        identified = percentages["Identified"]
        unresolved = percentages["Unresolved"]

        ax.barh(
            y_positions,
            identified,
            color=COLORS["Identified"],
            height=0.58,
            label="Country identified",
        )

        ax.barh(
            y_positions,
            unresolved,
            left=identified,
            color=COLORS["Unresolved"],
            height=0.58,
            label="Country unresolved",
        )

        ax.set_yticks(list(y_positions))
        ax.set_yticklabels(percentages.index)
        ax.invert_yaxis()

        ax.set_xlim(0, 100)
        ax.set_xlabel("Share of records (%)")

        ax.set_title(
            "Country Attribution Coverage",
            loc="left",
            fontsize=15,
            pad=18,
        )

        ax.text(
            0,
            1.04,
            "Profile location is self-reported and may be missing",
            transform=ax.transAxes,
            fontsize=9,
            color=COLORS["Muted"],
        )

        ax.xaxis.set_major_formatter(
            FuncFormatter(lambda x, _pos: f"{x:.0f}%")
        )

        ax.grid(axis="x", alpha=0.5)
        ax.set_axisbelow(True)
        ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.25), ncol=2)

        # Hien ty le nhan dien ben canh moi thanh
        for index, value in enumerate(identified):
            ax.text(
                99,
                index,
                f"{value:.1f}% identified",
                ha="right",
                va="center",
                fontsize=9,
                color=COLORS["Text"],
                fontweight="bold",
            )

        fig.tight_layout()

        save_chart(fig, "03_country_coverage.png")


print("\n=== HOAN TAT ===")
print("Thu muc bieu do:", CHARTS)
print("Da tao lai cac bieu do voi style thong nhat.")
