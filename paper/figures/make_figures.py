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
    "Physiological branch": "EEG–fNIRS branch",
    "Video--time prior": "Video–time prior",
    "Fused prediction": "Fixed fusion",
}
METRICS = ("Overall", "Valence", "Arousal")
PHYSIOLOGY_COLOR = "#CFCFCF"
PRIOR_COLOR = "#484878"
FUSION_COLOR = "#D79AAF"
GAIN_COLOR = "#2E9E44"
LOSS_COLOR = "#D85852"
NEUTRAL_COLOR = "#666666"
EDGE_COLOR = "#444444"
GUIDE_COLOR = "#E2E2E2"


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


def add_panel_label(
    ax: plt.Axes,
    label: str,
    x: float = -0.13,
    y: float = 1.04,
) -> None:
    ax.text(
        x,
        y,
        label,
        transform=ax.transAxes,
        fontsize=8.5,
        fontweight="bold",
        ha="left",
        va="bottom",
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
            "font.sans-serif": ["Arial", "DejaVu Sans", "Liberation Sans"],
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "font.size": 7.2,
            "axes.labelsize": 7.2,
            "axes.titlesize": 7.5,
            "xtick.labelsize": 6.7,
            "ytick.labelsize": 6.7,
            "legend.fontsize": 6.4,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.linewidth": 0.65,
            "xtick.major.width": 0.65,
            "ytick.major.width": 0.65,
            "legend.frameon": False,
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
        figsize=(3.35, 3.5),
        layout="constrained",
    )

    # (a) Hero panel: the primary overall-MAE result.
    ax = axes[0]
    components = tuple(COMPONENT_LABELS)
    values = np.asarray([data[component]["Overall"] for component in components])
    y = np.arange(len(components), dtype=float)
    colors = [PHYSIOLOGY_COLOR, PRIOR_COLOR, FUSION_COLOR]
    bars = ax.barh(
        y,
        values,
        height=0.67,
        color=colors,
        edgecolor=EDGE_COLOR,
        linewidth=0.45,
    )
    ax.set_yticks(y, [COMPONENT_LABELS[item] for item in components])
    ax.invert_yaxis()
    ax.set_xlim(0.0, 50.5)
    ax.set_xlabel("Mean absolute error")
    ax.set_title("Internal MAE comparison", loc="left")
    ax.grid(axis="x", color=GUIDE_COLOR, linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)
    for bar, value in zip(bars, values):
        ax.text(
            value + 0.65,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.2f}",
            ha="left",
            va="center",
            fontsize=6.7,
        )
    ax.text(
        1.0,
        1.005,
        f"Prior: {overall_prior_share:.1f}%",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=6.1,
        fontweight="bold",
        color=GAIN_COLOR,
    )
    add_panel_label(ax, "a", x=-0.37)

    # (b) Supporting panel: the small dimension-specific fusion increment.
    ax = axes[1]
    increments = np.asarray([prior[metric] - fusion[metric] for metric in METRICS])
    y = np.arange(len(METRICS), dtype=float)
    for y_position, increment in zip(y, increments):
        color = GAIN_COLOR if increment >= 0 else LOSS_COLOR
        marker = "o" if increment >= 0 else "X"
        ax.hlines(
            y_position,
            min(0.0, increment),
            max(0.0, increment),
            color=color,
            linewidth=1.45,
            alpha=0.55,
            zorder=1,
        )
        ax.scatter(
            increment,
            y_position,
            s=25,
            color=color,
            marker=marker,
            edgecolor="white" if increment >= 0 else color,
            linewidth=0.6,
            zorder=2,
        )
        label_x = increment + 0.004 if increment >= 0 else 0.004
        label = f"+{increment:.3f}" if increment >= 0 else f"−{abs(increment):.3f}"
        ax.text(
            label_x,
            y_position,
            label,
            ha="left",
            va="center",
            fontsize=6.1,
            color=NEUTRAL_COLOR,
        )
    ax.axvline(0.0, color=EDGE_COLOR, linewidth=0.75)
    ax.set_yticks(y, METRICS)
    ax.invert_yaxis()
    ax.set_xlim(-0.004, 0.112)
    ax.set_xticks([0.00, 0.05, 0.10])
    ax.set_xlabel("Prior MAE − fusion MAE")
    ax.set_title("Target-level increment", loc="left", pad=13)
    ax.text(
        1.0,
        1.005,
        f"{sum(increment > 0 for increment in increments)}/{len(increments)} improve",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=6.1,
        fontweight="bold",
        color=GAIN_COLOR,
    )
    ax.grid(axis="x", color="#E5E5E5", linewidth=0.45)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0, pad=3)
    add_panel_label(ax, "b", x=-0.37)

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
