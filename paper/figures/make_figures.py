#!/usr/bin/env python3
"""Regenerate the paper's two-panel MAE source-decomposition figure."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
SOURCE_CSV = HERE / "source_data_components.csv"
DEFAULT_OUTPUT_PREFIX = HERE / "source_dominance"

COMPONENT_LABELS = {
    "Physiological branch": "Physiology",
    "Video--time prior": "Video–time prior",
    "Fused prediction": "Fixed fusion",
}
METRICS = ("Overall", "Valence", "Arousal")
PHYSIOLOGY_COLOR = "#B8BEC8"
PRIOR_COLOR = "#7B9FC6"
FUSION_COLOR = "#174F7A"
GAIN_COLOR = "#238B45"
TEXT_COLOR = "#272727"
GUIDE_COLOR = "#D8DCE2"


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
        -0.37,
        1.10,
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
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
            "font.size": 7.2,
            "axes.labelsize": 7.2,
            "axes.titlesize": 7.6,
            "xtick.labelsize": 6.8,
            "ytick.labelsize": 6.9,
            "text.color": TEXT_COLOR,
            "axes.labelcolor": TEXT_COLOR,
            "axes.titlecolor": TEXT_COLOR,
            "xtick.color": TEXT_COLOR,
            "ytick.color": TEXT_COLOR,
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
    overall_prior_share = 100.0 * (
        physiology["Overall"] - prior["Overall"]
    ) / (physiology["Overall"] - fusion["Overall"])

    fig, axes = plt.subplots(
        2,
        1,
        figsize=(3.35, 3.35),
        gridspec_kw={"height_ratios": [1.35, 1.0], "hspace": 0.72},
    )

    # (a) Hero panel: the primary overall-MAE result.
    ax = axes[0]
    components = tuple(COMPONENT_LABELS)
    values = np.asarray([data[component]["Overall"] for component in components])
    y = np.arange(len(components), dtype=float)
    colors = [PHYSIOLOGY_COLOR, PRIOR_COLOR, FUSION_COLOR]
    bars = ax.barh(y, values, height=0.58, color=colors, edgecolor="none")
    ax.set_yticks(y, [COMPONENT_LABELS[item] for item in components])
    ax.invert_yaxis()
    ax.set_xlim(0, 55)
    ax.set_xticks([0, 20, 40])
    ax.set_xlabel("Overall mean absolute error (lower is better)")
    ax.set_title("Held-out viewers", loc="left", pad=5, fontweight="bold")
    ax.grid(axis="x", color=GUIDE_COLOR, linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0, pad=5)
    for index, (bar, value) in enumerate(zip(bars, values)):
        ax.text(
            value + 0.75,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.2f}",
            ha="left",
            va="center",
            fontsize=7.0,
            fontweight="bold" if index == 2 else "normal",
            color=FUSION_COLOR if index == 2 else TEXT_COLOR,
        )
    ax.text(
        0.0,
        -0.34,
        f"Prior captures {overall_prior_share:.1f}% of the overall reduction",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=6.6,
        color=FUSION_COLOR,
        bbox={"boxstyle": "round,pad=0.28", "facecolor": "#EEF4FA", "edgecolor": "none"},
    )
    add_panel_label(ax, "a")

    # (b) Supporting panel: the small dimension-specific fusion increment.
    ax = axes[1]
    increments = np.asarray([prior[metric] - fusion[metric] for metric in METRICS])
    y = np.arange(len(METRICS), dtype=float)
    ax.hlines(y, 0.0, increments, color="#AEB6C0", linewidth=2.0, zorder=1)
    ax.scatter(increments, y, s=30, color=GAIN_COLOR, edgecolor="white", linewidth=0.7, zorder=2)
    ax.axvline(0.0, color=TEXT_COLOR, linewidth=0.7)
    ax.set_yticks(y, METRICS)
    ax.invert_yaxis()
    ax.set_xlim(-0.004, 0.112)
    ax.set_xticks([0.00, 0.05, 0.10])
    ax.set_xlabel("MAE reduction: prior − fusion")
    ax.set_title("Small fusion increment", loc="left", pad=5, fontweight="bold")
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0, pad=5)
    for row, value in zip(y, increments):
        ax.text(
            value + 0.004,
            row,
            f"{value:.3f}",
            ha="left",
            va="center",
            fontsize=6.8,
            color=TEXT_COLOR,
        )
    add_panel_label(ax, "b")

    fig.subplots_adjust(left=0.31, right=0.98, top=0.96, bottom=0.14)

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
    with Image.open(output_tiff) as tiff_image:
        rgba = tiff_image.convert("RGBA")
    rgb = Image.new("RGB", rgba.size, "white")
    rgb.paste(rgba, mask=rgba.getchannel("A"))
    rgb.save(output_tiff, dpi=(600, 600), compression="tiff_lzw")
    plt.close(fig)
    print(f"Wrote {output_pdf}")
    print(f"Wrote {output_svg}")
    print(f"Wrote {output_png}")
    print(f"Wrote {output_tiff}")


if __name__ == "__main__":
    main()
