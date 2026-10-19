
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
PROCESSED = ROOT / "data" / "processed"
CHARTS = PROCESSED / "charts"

CHARTS.mkdir(parents=True, exist_ok=True)


def load_csv(filename):
    path = PROCESSED / filename

    if not path.exists():
        print("Khong tim thay:", path)
        return None

    return pd.read_csv(path, encoding="utf-8-sig")


# ==================================================
# CHART 1: HOAT DONG THEO THANG
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

        fig, ax = plt.subplots(figsize=(12, 6))

        for column in pivot.columns:
            ax.plot(
                pivot.index,
                pivot[column],
                marker="o",
                markersize=2,
                linewidth=1.5,
                label=column,
            )

        ax.set_title("Monthly GitHub Activity (2020–2026)")
        ax.set_xlabel("Month")
        ax.set_ylabel("Number of activity records")
        ax.grid(True, alpha=0.3)
        ax.legend()
        fig.autofmt_xdate()
        fig.tight_layout()

        output = CHARTS / "01_monthly_activity.png"
        fig.savefig(output, dpi=180)
        plt.close(fig)

        print("Da luu:", output)


# ==================================================
# CHART 2: QUOC GIA CO HOAT DONG
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

        top = recognized.head(10)

        # Dua Vietnam vao bieu do neu chua nam trong top 10
        if "Vietnam" in recognized.index and "Vietnam" not in top.index:
            top = pd.concat([top, recognized.loc[["Vietnam"]]])

        top = top.sort_values()

        fig, ax = plt.subplots(figsize=(10, 7))

        top.plot(kind="barh", ax=ax)

        ax.set_title(
            "GitHub Activity by Identified Country/Region\n"
            "(Based on developer-reported profile locations)"
        )
        ax.set_xlabel("Number of activity records")
        ax.set_ylabel("Country / region")
        ax.grid(axis="x", alpha=0.3)

        fig.tight_layout()

        output = CHARTS / "02_activity_by_country.png"
        fig.savefig(output, dpi=180)
        plt.close(fig)

        print("Da luu:", output)


# ==================================================
# CHART 3: DO PHU QUOC GIA
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

        data.columns = [
            "Country identified",
            "Country unresolved",
        ]

        fig, ax = plt.subplots(figsize=(10, 6))

        data.plot(
            kind="bar",
            stacked=True,
            ax=ax,
        )

        ax.set_title("Country Attribution Coverage")
        ax.set_xlabel("Activity type")
        ax.set_ylabel("Number of records")
        ax.tick_params(axis="x", rotation=0)
        ax.legend(title="Attribution status")
        ax.grid(axis="y", alpha=0.3)

        fig.tight_layout()

        output = CHARTS / "03_country_coverage.png"
        fig.savefig(output, dpi=180)
        plt.close(fig)

        print("Da luu:", output)


print("\n=== HOAN TAT TRUC QUAN HOA ===")
print("Thu muc bieu do:", CHARTS)
print("Kiem tra cac file PNG truoc khi dua vao Word/PowerPoint.")
