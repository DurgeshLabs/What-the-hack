"""Normalize the compact CICIDS2017 archive format into a reproducible training replay."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from ai.datasets.download_cicids2017 import map_cicids_to_raw_flows


DAY_FILES = ("monday.csv", "tuesday.csv", "wednesday.csv", "thursday.csv", "friday.csv")


def prepare(archive_dir: str, output: str, stride: int = 4) -> None:
    """Keep every Nth source-ordered flow, normalize it, and give each day a unique replay day."""
    if stride < 1:
        raise ValueError("stride must be at least 1")
    frames: list[pd.DataFrame] = []
    for offset, filename in enumerate(DAY_FILES):
        source = Path(archive_dir) / filename
        if not source.is_file():
            raise FileNotFoundError(f"Missing expected archive file: {source}")
        raw = pd.read_csv(source, low_memory=False).iloc[::stride].reset_index(drop=True)
        normalized = map_cicids_to_raw_flows(raw)
        base = pd.Timestamp("2017-07-03T00:00:00Z") + pd.Timedelta(days=offset)
        normalized["timestamp"] = (base + pd.to_timedelta(pd.RangeIndex(len(normalized)) * 80, unit="ms")).strftime("%Y-%m-%dT%H:%M:%SZ")
        frames.append(normalized)
        print(f"{filename}: {len(raw):,} source-ordered rows retained")
    result = pd.concat(frames, ignore_index=True)
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(destination, index=False)
    print(f"Wrote {len(result):,} normalized training rows to {destination}")
    print("Labels:", result["label"].value_counts().to_dict())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive_dir")
    parser.add_argument("--out", default="ai/datasets/cleaned/cicids2017_archive_clean.csv")
    parser.add_argument("--stride", type=int, default=4, help="retain every Nth row in source order (default: 4)")
    args = parser.parse_args()
    prepare(args.archive_dir, args.out, args.stride)
