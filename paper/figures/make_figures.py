#!/usr/bin/env python3
"""Regenerate the paper's three-panel MAE and post-hoc analysis figure."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
SOURCE_CSV = HERE / "source_data_components.csv"
DEFAULT_OUTPUT_PREFIX = HERE / "source_dominance"

COMPONENT_LABELS = {
    "Physiological branch": "Physiology",
    "Video--time prior": "Video–time prior",
    "Fused prediction": "Fixed fusion",
}
METRICS = ("Overall", "Valence", "Arousal")
METRIC_COLORS = ("#4C78A8", "#F58518", "#54A24B")
PRIOR_COLOR = "#2C7FB8"
FUSION_COLOR = "#238B45"


def normalize_svg(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    path.write_text(
        "\n".join(line.rstrip() for line in text.splitlines()) + "\n",
        encoding="utf-8",
    )


def load_components(path: Path) -> dict[str, dict[str, float]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    data = {
        row["component"]: {metric: float(row[metric]) for metric in METRICS}
        for row in rows
    }
    missing = set(COMPONENT_LABELS) - set(data)
    if missing:
        raise ValueError(f"Missing component rows: {sorted(missing)}")
    return data


def add_panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(
        -0.17,
        1.08,
        label,
        transform=ax.transAxes,
        fontsize=8.5,
        fontweight="bold",
        va="top",
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=SOURCE_CSV)
    parser.add_argument("--output-prefix", type=Path, default=DEFAULT_OUTPUT_PREFIX)
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    output_pdf = args.output_prefix.with_suffix(".pdf")
    output_svg = args.output_prefix.with_suffix(".svg")
    output_png = args.output_prefix.with_suffix(".png")
    output_tiff = args.output_prefix.with_suffix(".tiff")
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 7.2,
            "axes.labelsize": 7.2,
            "axes.titlesize": 7.4,
            "xtick.labelsize": 6.8,
            "ytick.labelsize": 6.8,
            "legend.fontsize": 6.4,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.linewidth": 0.6,
            "xtick.major.width": 0.6,
            "ytick.major.width": 0.6,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
        }
    )

    data = load_components(args.input)
    physiology = data["Physiological branch"]
    prior = data["Video--time prior"]
    fusion = data["Fused prediction"]

    fig, axes = plt.subplots(
        3,
        1,
        figsize=(3.30, 4.65),
        gridspec_kw={"height_ratios": [1.65, 1.0, 1.05]},
        layout="constrained",
    )

    # (a) Component MAE on the same held-out samples.
    ax = axes[0]
    components = tuple(COMPONENT_LABELS)
    y = np.arange(len(components), dtype=float)
    height = 0.22
    for metric_index, (metric, color) in enumerate(zip(METRICS, METRIC_COLORS)):
        values = [data[component][metric] for component in components]
        offset = (metric_index - 1) * height
        bars = ax.barh(y + offset, values, height=height, color=color, label=metric)
        ax.bar_label(bars, fmt="%.2f", padding=1.5, fontsize=5.8)
    ax.set_yticks(y, [COMPONENT_LABELS[item] for item in components])
    ax.invert_yaxis()
    component_max = max(data[component][metric] for component in components for metric in METRICS)
    ax.set_xlim(0, component_max * 1.14)
    ax.set_xlabel("Mean absolute error")
    ax.set_title("Held-out MAE comparison", loc="left", pad=12)
    ax.grid(axis="x", color="#D9D9D9", linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(ncol=3, frameon=False, loc="lower left", bbox_to_anchor=(0.0, 1.0))
    add_panel_label(ax, "a")

    # (b) The incremental reduction added by fusion beyond the prior.
    ax = axes[1]
    increments = np.asarray([prior[metric] - fusion[metric] for metric in METRICS])
    x = np.arange(len(METRICS))
    increment_colors = [FUSION_COLOR if value >= 0 else "#B23A48" for value in increments]
    bars = ax.bar(x, increments, width=0.58, color=increment_colors)
    ax.bar_label(bars, fmt="%.3f", padding=2, fontsize=6.4)
    ax.set_xticks(x, METRICS)
    increment_scale = max(float(np.max(np.abs(increments))), 1e-6)
    ax.set_ylim(min(0.0, float(increments.min()) - 0.25 * increment_scale), max(0.0, float(increments.max()) + 0.35 * increment_scale))
    ax.axhline(0.0, color="#555555", linewidth=0.6)
    ax.set_ylabel("MAE reduction")
    ax.set_title("Fusion increment beyond the prior", loc="left")
    ax.grid(axis="y", color="#D9D9D9", linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)
    add_panel_label(ax, "b")

    # (c) Share of the observed physiology-to-fusion reduction.
    ax = axes[2]
    prior_gains = np.asarray([physiology[m] - prior[m] for m in METRICS])
    fusion_gains = np.asarray([prior[m] - fusion[m] for m in METRICS])
    total_gains = prior_gains + fusion_gains
    prior_shares = 100.0 * prior_gains / total_gains
    fusion_shares = 100.0 * fusion_gains / total_gains
    y = np.arange(len(METRICS))
    ax.barh(y, prior_shares, color=PRIOR_COLOR, label="Prior gain")
    ax.barh(y, fusion_shares, left=prior_shares, color=FUSION_COLOR, label="Fusion increment")
    for index, share in enumerate(prior_shares):
        ax.text(share / 2.0, index, f"{share:.1f}%", ha="center", va="center", color="white", fontsize=6.6)
    ax.set_yticks(y, METRICS)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("Share of total observed MAE reduction (%)")
    ax.set_title("Composition of MAE reduction", loc="left", pad=12)
    ax.legend(ncol=2, frameon=False, loc="lower left", bbox_to_anchor=(0.0, 1.0))
    add_panel_label(ax, "c")

    fig.savefig(output_pdf, bbox_inches="tight")
    fig.savefig(output_svg, bbox_inches="tight")
    normalize_svg(output_svg)
    fig.savefig(output_png, dpi=300, bbox_inches="tight")
    fig.savefig(
        output_tiff,
        dpi=600,
        bbox_inches="tight",
        pil_kwargs={"compression": "tiff_lzw"},
    )
    plt.close(fig)
    print(f"Wrote {output_pdf}")
    print(f"Wrote {output_svg}")
    print(f"Wrote {output_png}")
    print(f"Wrote {output_tiff}")


if __name__ == "__main__":
    main()
