"""Script to annotate EveryAction contact data with race predictions"""

import csv
import json
import shutil
import signal
from pathlib import Path

import click
import pandas
import zrp
import zrp.download

EA_TO_ZRP_COLUMNS = {
    "VANID": "ZEST_KEY",
    "First": "first_name",
    "Mid": "middle_name",
    "Last": "last_name",
    "City": "city",
    "State/Province": "state",
}


@click.command()
@click.argument("input_filename", default="")
@click.argument("output_filename", default="")
def main(input_filename, output_filename):
    """Tags EveryAction contacts with imputed racial identity
    to facilitate analysis of racial disparities in contacts"""

    signal.signal(signal.SIGINT, signal.SIG_DFL)  # Sane ^C behavior

    zrp_data_path = Path(zrp.__file__).parent / "data"
    zrp_download_sentinel = zrp_data_path / "downloaded.txt"
    if not zrp_download_sentinel.is_file():
        print("⬇️ Downloading ZRP data")
        zrp.download.download()
        zrp_download_sentinel.write_text("downloaded: {zrp.about.__version__}")
        print()

    if input_filename:
        in_path = Path(input_filename)
    else:
        pattern = "everyaction-contacts*.txt"
        in_paths = list(Path(".").glob(pattern))
        if not in_paths:
            print(f"💥 No input files ({pattern}) found")
            raise SystemExit(1)
        if len(in_paths) > 1:
            print(f"💥 Multiple input files ({pattern}) found")
            raise SystemExit(1)
        in_path = in_paths[0]

    if output_filename:
        out_path = Path(output_filename)
    else:
        out_path = in_path.with_name(f"{in_path.stem}-zrp.csv")

    if out_path.is_file():
        print(f"🗑️ Removing {out_path}")
        out_path.unlink()

    print(f"⬅️ Reading {in_path}")
    csv_opts = {"encoding": "utf16", "sep": "\t", "dialect": csv.excel_tab}
    ea_df = pandas.read_csv(in_path, dtype=str, **csv_opts)
    print(f"✅ loaded {len(ea_df)} contacts")

    input_df = pandas.DataFrame()
    for ea_col, zrp_col in EA_TO_ZRP_COLUMNS.items():
        input_df[zrp_col] = ea_df[ea_col].str.strip()

    input_df["zip_code"] = ea_df["Zip/Postal"]
    input_df["street_address"] = ea_df.AddressLine1.str.strip().str.extract(
        r"(?:\d[\w-]*)?\s+([^\d].*)", expand=False
    )
    input_df["house_number"] = ea_df.AddressLine1.str.extract(
        r"(\d[\w-]*)", expand=False
    )

    state_mapping_path = zrp_data_path / "processed" / "inv_state_mapping.json"
    valid_states = json.loads(state_mapping_path.read_bytes())

    found_states = list(sorted(input_df.state.dropna().unique()))
    bad_found_states = [s for s in found_states if s not in valid_states]
    if bad_found_states:
        print(f"⚠️ Bad states: {', '.join(bad_found_states)}")

    valid_state_mask = [s in valid_states for s in input_df.state]
    input_df = input_df[valid_state_mask]
    print(f"🎯 {len(input_df)} contacts with valid state")
    print()

    artifacts_dir = Path("artifacts")
    if artifacts_dir.is_dir():
        print(f"🗑️ Removing {artifacts_dir}")
        shutil.rmtree(artifacts_dir)

    print("🔮 Running prediction")
    predictor = zrp.ZRP()
    predictor.fit()
    output_df = predictor.transform(input_df)
    output_df.set_index("ZEST_KEY", drop=True, inplace=True)
    added_cols = output_df.columns.difference(input_df.columns)
    combined_df = input_df.join(output_df[added_cols], on="ZEST_KEY")

    print(f"➡️ Writing {out_path}")
    combined_df.to_csv(out_path, index=False)
