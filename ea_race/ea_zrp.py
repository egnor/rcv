"""Script to annotate EveryAction contact data with race predictions"""

import click
import csv
import pandas
import signal
import zrp
import zrp.download
from pathlib import Path


@click.command()
@click.argument("ea_contacts_file", nargs=-1)
def main(ea_contacts_file):
    """Tags EveryAction contacts with imputed racial identity
    to facilitate analysis of racial disparities in contacts"""

    signal.signal(signal.SIGINT, signal.SIG_DFL)  # Sane ^C behavior

    zrp_version_path = Path(zrp.__file__).parent / "data" / "version"
    if not zrp_version_path.is_file():
        print("⬇️ Downloading ZRP data")
        zrp.download.download()
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
    ea_df = pandas.read_csv(
        ea_path, encoding="utf16", sep="\t", dialect=csv.excel_tab
    )
    print(f"✅ {len(ea_df)} contacts")

    predictor = zrp.ZRP(
        key="VANID",
        first_name="First",
        middle_name="Mid",
        last_name="Last",
        # house_number=???
        street_address="AddressLine1",
        city="City",
        state="State/Province",
        zip_code="Zip4",
    )

    print(ea_df.columns)
    output_df = predictor.transform(ea_df)
