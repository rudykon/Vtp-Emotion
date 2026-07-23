#!/usr/bin/env python3
"""Create figures for external MAE evaluation and post-hoc analysis."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Arial", "DejaVu Sans", "Liberation Sans"]
plt.rcParams["svg.fonttype"] = "none"

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]
DEFAULT_EVALUATION_DIR = PROJECT_ROOT / "artifacts" / "external_evaluation"

VARIANT_ORDER = (
    "global_constant",
    "video_identity",
    "video_time",
    "physiology",
    "fixed_fusion",
)
VARIANT_LABELS = {
    "global_constant": "Global constant",
    "video_identity": "Video identity",
    "video_time": "Video–time prior",
    "physiology": "Physiological branch",
    "fixed_fusion": "Fixed fusion",
}
COLORS = {
    "global_constant": "#B4C0E4",
    "video_identity": "#7884B4",
    "video_time": "#484878",
    "physiology": "#CFCFCF",
    "fixed_fusion": "#D79AAF",
    "gain": "#2E9E44",
    "loss": "#D85852",
    "neutral": "#666666",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluation-dir", type=Path, default=DEFAULT_EVALUATION_DIR)
    parser.add_argument("--source-dir", type=Path, default=HERE)
    parser.add_argument("--output-dir", type=Path, default=HERE)
    return parser.parse_args(argv)


def apply_publication_style() -> None:
    mpl.rcParams.update(
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
            "axes.spines.right": False,
            "axes.spines.top": False,
            "axes.linewidth": 0.65,
            "xtick.major.width": 0.65,
            "ytick.major.width": 0.65,
            "legend.frameon": False,
        }
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def add_panel_label(ax: plt.Axes, label: str, x: float = -0.13, y: float = 1.04) -> None:
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


def normalize_svg(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    path.write_text(
        "\n".join(line.rstrip() for line in text.splitlines()) + "\n",
        encoding="utf-8",
    )


def save_publication_figure(fig: plt.Figure, prefix: Path) -> None:
    prefix.parent.mkdir(parents=True, exist_ok=True)
    svg_path = prefix.with_suffix(".svg")
    fig.savefig(svg_path, bbox_inches="tight")
    normalize_svg(svg_path)
    fig.savefig(prefix.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(prefix.with_suffix(".png"), dpi=300, bbox_inches="tight")
    tiff_path = prefix.with_suffix(".tiff")
    fig.savefig(
        tiff_path,
        dpi=600,
        bbox_inches="tight",
        pil_kwargs={"compression": "tiff_lzw"},
    )
    with Image.open(tiff_path) as tiff_image:
        rgba = tiff_image.convert("RGBA")
    rgb = Image.new("RGB", rgba.size, "white")
    rgb.paste(rgba, mask=rgba.getchannel("A"))
    rgb.save(tiff_path, dpi=(600, 600), compression="tiff_lzw")
    plt.close(fig)


def load_metric_tables(source_dir: Path) -> tuple[list[dict[str, str]], ...]:
    return (
        read_csv(source_dir / "source_data_external_overall.csv"),
        read_csv(source_dir / "source_data_external_subject.csv"),
        read_csv(source_dir / "source_data_external_video.csv"),
        read_csv(source_dir / "source_data_external_time.csv"),
    )


def make_source_decomposition_figure(source_dir: Path, output_dir: Path) -> None:
    overall_rows, subject_rows, video_rows, time_rows = load_metric_tables(source_dir)
    overall = {row["variant"]: float(row["overall_mae"]) for row in overall_rows}
    subjects = sorted({row["subject"] for row in subject_rows})
    subject_metrics = {
        (row["subject"], row["variant"]): float(row["overall_mae"])
        for row in subject_rows
    }
    videos = sorted({int(row["video"]) for row in video_rows})
    video_metrics = {
        (int(row["video"]), row["variant"]): float(row["overall_mae"])
        for row in video_rows
    }
    bins = sorted({int(row["relative_time_bin"]) for row in time_rows})
    time_metrics = {
        (int(row["relative_time_bin"]), row["variant"]): float(row["overall_mae"])
        for row in time_rows
    }

    fig = plt.figure(figsize=(7.2, 5.3), layout="constrained")
    grid = fig.add_gridspec(
        2,
        3,
        width_ratios=[1.0, 1.28, 1.45],
        height_ratios=[1.05, 1.15],
    )
    ax_a = fig.add_subplot(grid[0, :2])
    ax_b = fig.add_subplot(grid[1, 0])
    ax_c = fig.add_subplot(grid[1, 1])
    ax_d = fig.add_subplot(grid[:, 2])

    # a, overall five-way MAE comparison.
    values = np.asarray([overall[variant] for variant in VARIANT_ORDER])
    y = np.arange(len(VARIANT_ORDER))
    bars = ax_a.barh(
        y,
        values,
        color=[COLORS[variant] for variant in VARIANT_ORDER],
        edgecolor="#444444",
        linewidth=0.45,
        height=0.67,
    )
    ax_a.set_yticks(y, [VARIANT_LABELS[variant] for variant in VARIANT_ORDER])
    ax_a.invert_yaxis()
    ax_a.set_xlim(0.0, 50.5)
    ax_a.set_xlabel("Mean absolute error")
    ax_a.set_title("External MAE comparison", loc="left")
    ax_a.grid(axis="x", color="#E2E2E2", linewidth=0.5, zorder=0)
    ax_a.set_axisbelow(True)
    for bar, value in zip(bars, values):
        ax_a.text(
            value + 0.65,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.2f}",
            va="center",
            ha="left",
            fontsize=6.7,
        )
    add_panel_label(ax_a, "a", x=-0.08)

    # b, paired viewer-level fusion increments, ranked by magnitude.
    subject_deltas = [
        (
            f"S{index + 1}",
            subject_metrics[(subject, "video_time")]
            - subject_metrics[(subject, "fixed_fusion")],
        )
        for index, subject in enumerate(subjects)
    ]
    subject_deltas.sort(key=lambda item: item[1], reverse=True)

    # c, video-level heterogeneity using the same signed encoding.
    video_deltas = [
        (
            f"V{video}",
            video_metrics[(video, "video_time")]
            - video_metrics[(video, "fixed_fusion")],
        )
        for video in videos
    ]
    video_deltas.sort(key=lambda item: item[1], reverse=True)

    delta_xlim = (-0.36, 1.40)
    delta_ticks = [0.0, 0.5, 1.0]

    def draw_ranked_increments(
        ax: plt.Axes,
        rows: list[tuple[str, float]],
        title: str,
        summary: str,
        annotate_values: bool,
    ) -> None:
        y_positions = np.arange(len(rows), dtype=float)
        for y_position, (_, delta) in zip(y_positions, rows):
            color = COLORS["gain"] if delta >= 0 else COLORS["loss"]
            marker = "o" if delta >= 0 else "X"
            ax.hlines(
                y_position,
                min(0.0, delta),
                max(0.0, delta),
                color=color,
                linewidth=1.45,
                alpha=0.55,
                zorder=1,
            )
            ax.scatter(
                delta,
                y_position,
                color=color,
                marker=marker,
                s=25,
                edgecolor="white" if delta >= 0 else color,
                linewidth=0.6,
                zorder=2,
            )
            if annotate_values:
                label_x = delta + 0.045 if delta >= 0 else 0.045
                label = f"+{delta:.3f}" if delta >= 0 else f"−{abs(delta):.3f}"
                ax.text(
                    label_x,
                    y_position,
                    label,
                    ha="left",
                    va="center",
                    fontsize=6.1,
                    color=COLORS["neutral"],
                )
        ax.axvline(0.0, color="#444444", linewidth=0.75)
        ax.set_yticks(y_positions, [label for label, _ in rows])
        ax.invert_yaxis()
        ax.set_xlim(*delta_xlim)
        ax.set_xticks(delta_ticks)
        ax.set_xlabel("Prior MAE − fusion MAE")
        ax.set_title(title, loc="left", pad=13)
        ax.text(
            1.0,
            1.005,
            summary,
            transform=ax.transAxes,
            ha="right",
            va="bottom",
            fontsize=6.1,
            fontweight="bold",
            color=COLORS["gain"],
        )
        ax.grid(axis="x", color="#E5E5E5", linewidth=0.45)
        ax.set_axisbelow(True)
        ax.spines["left"].set_visible(False)
        ax.tick_params(axis="y", length=0, pad=3)

    draw_ranked_increments(
        ax_b,
        subject_deltas,
        "Viewer-level increment",
        f"{sum(delta > 0 for _, delta in subject_deltas)}/{len(subject_deltas)} improve",
        annotate_values=True,
    )
    add_panel_label(ax_b, "b", x=-0.31)

    draw_ranked_increments(
        ax_c,
        video_deltas,
        "Video-level increment",
        f"{sum(delta > 0 for _, delta in video_deltas)}/{len(video_deltas)} improve",
        annotate_values=False,
    )
    add_panel_label(ax_c, "c", x=-0.22)

    # d, error across normalized within-video time.
    x = (np.asarray(bins, dtype=float) + 0.5) * (100.0 / len(bins))
    time_variants = ("global_constant", "video_identity", "video_time", "fixed_fusion")
    markers = ("o", "s", "^", "D")
    for variant, marker in zip(time_variants, markers):
        series = [time_metrics[(time_bin, variant)] for time_bin in bins]
        ax_d.plot(
            x,
            series,
            color=COLORS[variant],
            marker=marker,
            markersize=3.5,
            linewidth=1.45,
            label=VARIANT_LABELS[variant],
        )
    ax_d.set_xlim(0, 100)
    ax_d.set_xticks([0, 20, 40, 60, 80, 100])
    ax_d.set_xlabel("Normalized video time (%)")
    ax_d.set_ylabel("Mean absolute error")
    ax_d.set_title("Error varies across video time", loc="left")
    ax_d.grid(color="#E5E5E5", linewidth=0.45)
    ax_d.set_axisbelow(True)
    ax_d.legend(loc="center", bbox_to_anchor=(0.58, 0.60), ncol=2, columnspacing=0.8, handletextpad=0.4)
    add_panel_label(ax_d, "d", x=-0.16)

    save_publication_figure(fig, output_dir / "external_source_decomposition")


def ensure_sample_source_data(evaluation_dir: Path, source_dir: Path) -> Path:
    source_path = source_dir / "source_data_external_samples.csv"
    if source_path.exists():
        return source_path
    paired_path = evaluation_dir / "paired_predictions.csv"
    rows = read_csv(paired_path)
    fields = (
        "sample_id",
        "subject",
        "video",
        "timestamp",
        "relative_time_bin",
        "target_valence",
        "target_arousal",
    )
    source_path.parent.mkdir(parents=True, exist_ok=True)
    with source_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row[field] for field in fields})
    return source_path


def aggregate_video_time_targets(rows: list[dict[str, str]]) -> tuple[np.ndarray, np.ndarray]:
    videos = sorted({int(row["video"]) for row in rows})
    bins = sorted({int(row["relative_time_bin"]) for row in rows})
    valence: dict[tuple[int, int], list[float]] = defaultdict(list)
    arousal: dict[tuple[int, int], list[float]] = defaultdict(list)
    for row in rows:
        key = (int(row["video"]), int(row["relative_time_bin"]))
        valence[key].append(float(row["target_valence"]))
        arousal[key].append(float(row["target_arousal"]))
    valence_matrix = np.asarray(
        [[np.mean(valence[(video, time_bin)]) for time_bin in bins] for video in videos]
    )
    arousal_matrix = np.asarray(
        [[np.mean(arousal[(video, time_bin)]) for time_bin in bins] for video in videos]
    )
    return valence_matrix, arousal_matrix


def make_data_landscape_figure(
    evaluation_dir: Path,
    source_dir: Path,
    output_dir: Path,
) -> None:
    sample_path = ensure_sample_source_data(evaluation_dir, source_dir)
    rows = read_csv(sample_path)
    valence = np.asarray([float(row["target_valence"]) for row in rows])
    arousal = np.asarray([float(row["target_arousal"]) for row in rows])
    valence_matrix, arousal_matrix = aggregate_video_time_targets(rows)
    deviation = max(
        float(np.quantile(np.abs(valence - 128.0), 0.98)),
        float(np.quantile(np.abs(arousal - 128.0), 0.98)),
        40.0,
    )
    deviation = min(deviation, 127.0)
    norm = mpl.colors.TwoSlopeNorm(vmin=128.0 - deviation, vcenter=128.0, vmax=128.0 + deviation)

    fig = plt.figure(figsize=(7.2, 4.55), layout="constrained")
    grid = fig.add_gridspec(2, 3, width_ratios=[1.15, 1.0, 1.0])
    ax_a = fig.add_subplot(grid[:, 0])
    ax_b = fig.add_subplot(grid[0, 1:])
    ax_c = fig.add_subplot(grid[1, 1:])

    density = ax_a.hexbin(
        valence,
        arousal,
        gridsize=30,
        extent=(1, 255, 1, 255),
        mincnt=1,
        bins="log",
        cmap="Blues",
        linewidths=0.0,
    )
    ax_a.axvline(128, color="#777777", linewidth=0.65, linestyle="--")
    ax_a.axhline(128, color="#777777", linewidth=0.65, linestyle="--")
    ax_a.set_xlim(1, 255)
    ax_a.set_ylim(1, 255)
    ax_a.set_aspect("equal", adjustable="box")
    ax_a.set_xlabel("Valence")
    ax_a.set_ylabel("Arousal")
    ax_a.set_title(f"External affective coverage (n = {len(rows):,})", loc="left")
    colorbar = fig.colorbar(density, ax=ax_a, fraction=0.047, pad=0.03)
    colorbar.set_label("Samples per hexagon (log scale)")
    add_panel_label(ax_a, "a", x=-0.2)

    image_b = ax_b.imshow(valence_matrix, aspect="auto", cmap="RdBu_r", norm=norm)
    ax_b.set_title("Mean valence across video and normalized time", loc="left")
    ax_b.set_ylabel("Video")
    ax_b.set_yticks(np.arange(15), np.arange(1, 16))
    ax_b.set_xticks([])
    add_panel_label(ax_b, "b", x=-0.08)

    ax_c.imshow(arousal_matrix, aspect="auto", cmap="RdBu_r", norm=norm)
    ax_c.set_title("Mean arousal across video and normalized time", loc="left")
    ax_c.set_ylabel("Video")
    ax_c.set_yticks(np.arange(15), np.arange(1, 16))
    ax_c.set_xticks(np.arange(10), [f"{5 + 10 * index}" for index in range(10)])
    ax_c.set_xlabel("Normalized video-time bin midpoint (%)")
    add_panel_label(ax_c, "c", x=-0.08)

    colorbar_heat = fig.colorbar(image_b, ax=[ax_b, ax_c], fraction=0.025, pad=0.02)
    colorbar_heat.set_label("Mean label (neutral = 128)")

    save_publication_figure(fig, output_dir / "external_data_landscape")


def main() -> None:
    args = parse_args()
    evaluation_dir = args.evaluation_dir.resolve()
    source_dir = args.source_dir.resolve()
    output_dir = args.output_dir.resolve()
    apply_publication_style()
    make_source_decomposition_figure(source_dir, output_dir)
    make_data_landscape_figure(evaluation_dir, source_dir, output_dir)
    print(f"Wrote external analysis figures to {output_dir}")


if __name__ == "__main__":
    main()
