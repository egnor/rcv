"""Script to annotate EveryAction contact data with race predictions"""

import click
import csv
import json
import pandas
import shutil
import signal
import zrp
import zrp.download
from pathlib import Path

EA_TO_ZRP_COLUMNS = {
    "VANID": "key",
    "First": "first_name",
    "Mid": "middle_name",
    "Last": "last_name",
    "City": "city",
    "State/Province": "state",
}


@click.command()
@click.argument("ea_contacts_file", nargs=-1)
def main(ea_contacts_file):
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

    if ea_contacts_file:
        ea_path = Path(ea_contacts_file)
    else:
        pattern = "everyaction-contacts*.txt"
        ea_paths = list(Path(".").glob(pattern))
        if not ea_paths:
            print(f"💥 No input files ({pattern}) found")
            raise SystemExit(1)
        if len(ea_paths) > 1:
            print(f"💥 Multiple input files ({pattern}) found")
            raise SystemExit(1)
        ea_path = ea_paths[0]

    print(f"⬅️ Reading {ea_path}")
    csv_opts = {"encoding": "utf16", "sep": "\t", "dialect": csv.excel_tab}
    ea_df = pandas.read_csv(ea_path, dtype=str, **csv_opts)
    print(f"✅ loaded {len(ea_df)} contacts")

    zrp_df = pandas.DataFrame()
    for ea_col, zrp_col in EA_TO_ZRP_COLUMNS.items():
        zrp_df[zrp_col] = ea_df[ea_col].str.strip()

    zrp_df["zip_code"] = ea_df["Zip/Postal"]
    zrp_df["street_address"] = ea_df.AddressLine1.str.strip().str.extract(
        r'(?:\d[\w-]*)?\s+([^\d].*)', expand=False
    )
    zrp_df["house_number"] = ea_df.AddressLine1.str.extract(
        r'(\d[\w-]*)', expand=False
    )

    state_mapping_path = zrp_data_path / "processed" / "inv_state_mapping.json"
    valid_states = json.loads(state_mapping_path.read_bytes())

    found_states = list(sorted(zrp_df.state.dropna().unique()))
    bad_found_states = [s for s in found_states if s not in valid_states]
    if bad_found_states:
        print(f"⚠️ Bad states: {', '.join(bad_found_states)}")

    valid_state_mask = [s in valid_states for s in zrp_df.state]
    zrp_df = zrp_df[valid_state_mask]
    print(f"🎯 {len(zrp_df)} contacts with valid state")
    print()

    for i, t in enumerate(zrp_df.itertuples()):
        print(t)
        if i > 10:
            break

    artifacts_dir = Path("artifacts")
    if artifacts_dir.is_dir():
        print(f"🗑️ Removing {artifacts_dir}")
        shutil.rmtree(artifacts_dir)

    print("🔮 Running prediction")
    predictor = zrp.ZRP()
    output_df = predictor.transform(zrp_df)
    for i, t in enumerate(output_df.itertuples()):
        print(t)
