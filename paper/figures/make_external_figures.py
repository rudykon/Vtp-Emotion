#!/usr/bin/env python3
"""Create figures for external MAE evaluation and residual analysis."""

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
    "physiology": "EEG–fNIRS branch",
    "fixed_fusion": "Fixed fusion",
}
COLORS = {
    # Discrete colors sampled from the Blues and RdBu_r maps used in Figure 1.
    "global_constant": "#A6CEE4",
    "video_identity": "#6AAED6",
    "video_time": "#2070B4",
    "physiology": "#CFCFCF",
    "fixed_fusion": "#E48066",
    "gain": "#E48066",
    "gain_text": "#C43B3C",
    "loss": "#327CB7",
    "neutral": "#666666",
    "reference": "#777777",
}
EDGE_COLOR = "#444444"
GUIDE_COLOR = "#E2E2E2"
VIDEO_TIME_MAE_CMAP = mpl.colors.LinearSegmentedColormap.from_list(
    "video_time_mae_blue_orange",
    ("#173F6B", "#6FA8C9", "#F3F1E8", "#EFA47A", "#C84E3F"),
)

RESULT_SOURCE_FIELDS = (
    "sample_id",
    "subject",
    "video",
    "timestamp",
    "relative_time_bin",
    "target_valence",
    "target_arousal",
    "video_time_valence",
    "video_time_arousal",
    "fixed_fusion_valence",
    "fixed_fusion_arousal",
)


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

    fig = plt.figure(figsize=(7.2, 5.6), layout="constrained")
    grid = fig.add_gridspec(
        2,
        2,
        width_ratios=[1.0, 1.0],
        height_ratios=[0.95, 1.22],
    )
    ax_a = fig.add_subplot(grid[0, 0])
    ax_b = fig.add_subplot(grid[0, 1])
    ax_c = fig.add_subplot(grid[1, 0])
    ax_d = fig.add_subplot(grid[1, 1])

    # a, overall five-way MAE comparison.
    values = np.asarray([overall[variant] for variant in VARIANT_ORDER])
    y = np.arange(len(VARIANT_ORDER))
    bars = ax_a.barh(
        y,
        values,
        color=[COLORS[variant] for variant in VARIANT_ORDER],
        edgecolor=EDGE_COLOR,
        linewidth=0.45,
        height=0.67,
    )
    ax_a.set_yticks(y, [VARIANT_LABELS[variant] for variant in VARIANT_ORDER])
    ax_a.invert_yaxis()
    ax_a.set_xlim(0.0, 50.5)
    ax_a.set_xlabel("Mean absolute error")
    ax_a.set_title("External MAE comparison", loc="left")
    ax_a.grid(axis="x", color=GUIDE_COLOR, linewidth=0.5, zorder=0)
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
    add_panel_label(ax_a, "a", x=-0.25)

    # b, paired participant-level fusion increments, ranked by magnitude.
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
        ax.axvline(0.0, color=COLORS["reference"], linewidth=0.75)
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
            color=COLORS["gain_text"],
        )
        ax.grid(axis="x", color=GUIDE_COLOR, linewidth=0.45)
        ax.set_axisbelow(True)
        ax.spines["left"].set_visible(False)
        ax.tick_params(axis="y", length=0, pad=3)

    draw_ranked_increments(
        ax_b,
        subject_deltas,
        "Participant-level increment",
        f"{sum(delta > 0 for _, delta in subject_deltas)}/{len(subject_deltas)} improve",
        annotate_values=True,
    )
    add_panel_label(ax_b, "b", x=-0.18)

    draw_ranked_increments(
        ax_c,
        video_deltas,
        "Video-level increment",
        f"{sum(delta > 0 for _, delta in video_deltas)}/{len(video_deltas)} improve",
        annotate_values=False,
    )
    add_panel_label(ax_c, "c", x=-0.18)

    # d, error across normalized within-video time.
    x = (np.asarray(bins, dtype=float) + 0.5) * (100.0 / len(bins))
    time_variants = ("global_constant", "video_identity", "video_time", "fixed_fusion")
    markers = ("o", "s", "^", "D")
    line_handles = []
    for variant, marker in zip(time_variants, markers):
        series = [time_metrics[(time_bin, variant)] for time_bin in bins]
        line, = ax_d.plot(
            x,
            series,
            color=COLORS[variant],
            marker=marker,
            markersize=3.5,
            linewidth=1.45,
            label=VARIANT_LABELS[variant],
        )
        line_handles.append(line)
    ax_d.set_xlim(0, 100)
    ax_d.set_xticks([0, 20, 40, 60, 80, 100])
    ax_d.set_xlabel("Normalized video time (%)")
    ax_d.set_ylabel("Mean absolute error")
    ax_d.set_title("Error varies across video time", loc="left")
    ax_d.grid(color=GUIDE_COLOR, linewidth=0.45)
    ax_d.set_axisbelow(True)
    fig.legend(
        line_handles,
        [VARIANT_LABELS[variant] for variant in time_variants],
        loc="outside lower center",
        ncol=4,
        borderaxespad=0.2,
        labelspacing=0.35,
        handletextpad=0.45,
        columnspacing=1.2,
    )
    add_panel_label(ax_d, "d", x=-0.18)

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


def ensure_prediction_source_data(evaluation_dir: Path, source_dir: Path) -> Path:
    """Return local sample-level source data needed by result figures.

    The cache contains gated targets and is intentionally excluded from version
    control. Publication figures remain versioned, but redrawing them requires
    locally restored evaluation artifacts under the applicable data terms.
    """
    source_path = source_dir / "source_data_external_predictions.csv"
    paired_path = evaluation_dir / "paired_predictions.csv"

    if paired_path.exists():
        rows = read_csv(paired_path)
        missing = set(RESULT_SOURCE_FIELDS).difference(rows[0] if rows else ())
        if missing:
            raise ValueError(f"{paired_path} is missing required fields: {sorted(missing)}")
        source_path.parent.mkdir(parents=True, exist_ok=True)
        with source_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=RESULT_SOURCE_FIELDS,
                lineterminator="\n",
            )
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row[field] for field in RESULT_SOURCE_FIELDS})
        return source_path

    if not source_path.exists():
        raise FileNotFoundError(
            f"Neither {source_path} nor {paired_path} is available for result figures"
        )
    rows = read_csv(source_path)
    missing = set(RESULT_SOURCE_FIELDS).difference(rows[0] if rows else ())
    if missing:
        raise ValueError(f"{source_path} is missing required fields: {sorted(missing)}")
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


def aggregate_video_time_mae(
    rows: list[dict[str, str]],
    variant: str,
) -> tuple[np.ndarray, np.ndarray, list[int], list[int]]:
    videos = sorted({int(row["video"]) for row in rows})
    bins = sorted({int(row["relative_time_bin"]) for row in rows})
    errors: dict[tuple[int, int], list[float]] = defaultdict(list)
    for row in rows:
        key = (int(row["video"]), int(row["relative_time_bin"]))
        valence_error = abs(
            float(row[f"{variant}_valence"]) - float(row["target_valence"])
        )
        arousal_error = abs(
            float(row[f"{variant}_arousal"]) - float(row["target_arousal"])
        )
        errors[key].append((valence_error + arousal_error) / 2.0)

    missing = [
        (video, time_bin)
        for video in videos
        for time_bin in bins
        if not errors[(video, time_bin)]
    ]
    if missing:
        raise ValueError(f"Missing video-time cells for {variant}: {missing}")

    matrix = np.asarray(
        [
            [np.mean(errors[(video, time_bin)]) for time_bin in bins]
            for video in videos
        ]
    )
    counts = np.asarray(
        [[len(errors[(video, time_bin)]) for time_bin in bins] for video in videos]
    )
    return matrix, counts, videos, bins


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
    video_positions = np.arange(valence_matrix.shape[0])
    video_labels = np.arange(1, valence_matrix.shape[0] + 1)
    time_positions = np.arange(valence_matrix.shape[1])
    time_midpoints = (time_positions + 0.5) * 100.0 / valence_matrix.shape[1]
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
    ax_a.set_title(f"External labels ({len(rows):,} one-second observations)", loc="left")
    colorbar = fig.colorbar(density, ax=ax_a, fraction=0.047, pad=0.03)
    colorbar.set_label("Samples per hexagon (log scale)")
    add_panel_label(ax_a, "a", x=-0.2)

    image_b = ax_b.imshow(valence_matrix, aspect="auto", cmap="RdBu_r", norm=norm)
    ax_b.set_title("Mean valence across video and normalized time", loc="left")
    ax_b.set_ylabel("Video")
    ax_b.set_yticks(video_positions, video_labels)
    ax_b.set_xticks([])
    add_panel_label(ax_b, "b", x=-0.08)

    ax_c.imshow(arousal_matrix, aspect="auto", cmap="RdBu_r", norm=norm)
    ax_c.set_title("Mean arousal across video and normalized time", loc="left")
    ax_c.set_ylabel("Video")
    ax_c.set_yticks(video_positions, video_labels)
    ax_c.set_xticks(time_positions, [f"{midpoint:g}" for midpoint in time_midpoints])
    ax_c.set_xlabel("Normalized video-time bin midpoint (%)")
    add_panel_label(ax_c, "c", x=-0.08)

    colorbar_heat = fig.colorbar(image_b, ax=[ax_b, ax_c], fraction=0.025, pad=0.02)
    colorbar_heat.set_label("Mean label (neutral = 128)")

    save_publication_figure(fig, output_dir / "external_data_landscape")


def make_prediction_quality_figure(
    evaluation_dir: Path,
    source_dir: Path,
    output_dir: Path,
) -> None:
    source_path = ensure_prediction_source_data(evaluation_dir, source_dir)
    rows = read_csv(source_path)
    if not rows:
        raise ValueError(f"No paired predictions in {source_path}")

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.25), layout="constrained")
    collections = []
    maximum_count = 1.0
    for index, (axis, dimension, label) in enumerate(
        zip(axes, ("valence", "arousal"), ("Valence", "Arousal"))
    ):
        target = np.asarray([float(row[f"target_{dimension}"]) for row in rows])
        prediction = np.asarray(
            [float(row[f"fixed_fusion_{dimension}"]) for row in rows]
        )
        mae = float(np.mean(np.abs(prediction - target)))
        density = axis.hexbin(
            target,
            prediction,
            gridsize=35,
            extent=(1, 255, 1, 255),
            mincnt=1,
            cmap="Blues",
            linewidths=0.0,
        )
        collections.append(density)
        maximum_count = max(maximum_count, float(np.max(density.get_array())))

        axis.plot(
            [1, 255],
            [1, 255],
            color=COLORS["fixed_fusion"],
            linewidth=1.1,
            linestyle="--",
            zorder=3,
        )
        axis.axvline(128, color=COLORS["reference"], linewidth=0.55, linestyle=":")
        axis.axhline(128, color=COLORS["reference"], linewidth=0.55, linestyle=":")
        axis.set_xlim(1, 255)
        axis.set_ylim(1, 255)
        axis.set_xticks([1, 64, 128, 192, 255])
        axis.set_yticks([1, 64, 128, 192, 255])
        axis.set_aspect("equal", adjustable="box")
        axis.set_xlabel(f"True {dimension}")
        axis.set_ylabel(f"Predicted {dimension}")
        axis.set_title(f"{label} (MAE = {mae:.2f})", loc="left")
        add_panel_label(axis, chr(ord("a") + index), x=-0.17)

    shared_norm = mpl.colors.LogNorm(vmin=1.0, vmax=maximum_count)
    for collection in collections:
        collection.set_norm(shared_norm)
    colorbar = fig.colorbar(collections[0], ax=axes, fraction=0.035, pad=0.03)
    colorbar.set_label("Samples per hexagon (log scale)")

    save_publication_figure(fig, output_dir / "external_prediction_quality")


def make_video_time_mae_figure(
    evaluation_dir: Path,
    source_dir: Path,
    output_dir: Path,
) -> None:
    source_path = ensure_prediction_source_data(evaluation_dir, source_dir)
    rows = read_csv(source_path)
    prior, prior_counts, videos, bins = aggregate_video_time_mae(rows, "video_time")
    fusion, fusion_counts, fusion_videos, fusion_bins = aggregate_video_time_mae(
        rows,
        "fixed_fusion",
    )
    if videos != fusion_videos or bins != fusion_bins:
        raise ValueError("Prior and fusion video-time grids are misaligned")
    if not np.array_equal(prior_counts, fusion_counts):
        raise ValueError("Prior and fusion video-time grids use different samples")

    overall_prior = float(np.average(prior, weights=prior_counts))
    overall_fusion = float(np.average(fusion, weights=fusion_counts))
    norm = mpl.colors.Normalize(vmin=0.0, vmax=65.0)
    fig, axes = plt.subplots(
        1,
        2,
        figsize=(7.2, 3.4),
        layout="constrained",
        sharey=True,
    )
    images = []
    titles = (
        ("Video–time prior", overall_prior, COLORS["video_time"]),
        ("Fixed fusion", overall_fusion, COLORS["fixed_fusion"]),
    )
    for index, (axis, matrix, title_info) in enumerate(
        zip(axes, (prior, fusion), titles)
    ):
        title, overall_mae, title_color = title_info
        image = axis.imshow(
            matrix,
            aspect="auto",
            interpolation="nearest",
            cmap=VIDEO_TIME_MAE_CMAP,
            norm=norm,
        )
        images.append(image)
        axis.set_title(title, loc="left")
        axis.text(
            1.0,
            1.01,
            f"Overall MAE = {overall_mae:.2f}",
            transform=axis.transAxes,
            ha="right",
            va="bottom",
            fontsize=6.4,
            fontweight="bold",
            color=title_color,
        )
        axis.set_xticks(
            np.arange(len(bins)),
            [f"{(time_bin + 0.5) * 100.0 / len(bins):g}" for time_bin in bins],
        )
        axis.set_xlabel("Normalized video time (%)")
        axis.set_yticks(np.arange(len(videos)), [f"V{video}" for video in videos])
        if index == 0:
            axis.set_ylabel("Video")
        add_panel_label(axis, chr(ord("a") + index), x=-0.17)

    colorbar = fig.colorbar(
        images[0],
        ax=axes,
        fraction=0.035,
        pad=0.03,
        ticks=[0, 20, 40, 60],
    )
    colorbar.set_label("Overall MAE (lower is better)")

    save_publication_figure(fig, output_dir / "external_video_time_mae")


def main() -> None:
    args = parse_args()
    evaluation_dir = args.evaluation_dir.resolve()
    source_dir = args.source_dir.resolve()
    output_dir = args.output_dir.resolve()
    apply_publication_style()
    make_source_decomposition_figure(source_dir, output_dir)
    make_data_landscape_figure(evaluation_dir, source_dir, output_dir)
    make_prediction_quality_figure(evaluation_dir, source_dir, output_dir)
    make_video_time_mae_figure(evaluation_dir, source_dir, output_dir)
    print(f"Wrote external analysis figures to {output_dir}")


if __name__ == "__main__":
    main()
