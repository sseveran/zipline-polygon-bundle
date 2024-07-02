import os
import glob
import pandas as pd
from concurrent.futures import ProcessPoolExecutor


def convert_timestamp(x):
    """Some Polygon timestamps are in nanoseconds, some in milliseconds, some in seconds."""
    unix_time = int(x)
    return pd.to_datetime(
        unix_time,
        unit=(
            "ns"
            if unix_time > 100_000_000_000_000
            else "ms" if unix_time > 10_000_000_000 else "s"
        ),
    )


def convert_minute_csv_to_parquet(path, extension, compression="infer", force=False):
    parquet_path = path.replace(extension, ".parquet")
    if not force and os.path.exists(parquet_path):
        print(f"Skipping {path} because {parquet_path} exists")
        return
    print(path)
    try:
        bars_df = pd.read_csv(
            path,
            compression=compression,
            converters={"ticker": lambda x: str(x), "window_start": convert_timestamp},
        )
        # bars_df.info()
        if len(bars_df) == 0:
            print(f"WARNING: Empty {path}")
            return
        if len(bars_df) < 100000:
            print(f"WARNING: Short {path}")
        bars_df.set_index(["window_start", "ticker"], inplace=True)
        bars_df.sort_index(inplace=True)
        bars_df.to_parquet(parquet_path)
        if not os.path.exists(parquet_path):
            print(f"ERROR: Failed to write {parquet_path}")
    except Exception as e:
        print(f"Failed for {path}: {e}")

def process_all_minute_csv_to_parquet(
    data_dir,
    recursive=True,
    extension=".csv.gz",
    compression="infer",
    force=False,
    max_workers=8,
):
    """Big CSV files are very slow to read.  So we only read them once and convert them to Parquet."""
    csv_pattern = f"**/*{extension}" if recursive else f"*{extension}"
    # for path in glob.glob(os.path.join(data_dir, csv_pattern), recursive=recursive):
    #     convert_minute_csv_to_parquet(path, extension=extension, compression=compression, force=force)
    paths = glob.glob(os.path.join(data_dir, csv_pattern), recursive=recursive)
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        executor.map(
            convert_minute_csv_to_parquet,
            paths,
            [extension] * len(paths),
            [compression] * len(paths),
            [force] * len(paths),
        )


if __name__ == "__main__":
    process_all_minute_csv_to_parquet(data_dir="data/polygon/flatfiles/us_stocks_sip/minute_aggs_v1")
