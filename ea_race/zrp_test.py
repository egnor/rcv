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


@click.command()
@click.option("--first_name")
@click.option("--middle_name")
@click.option("--last_name")
@click.option("--house_number")
@click.option("--street_address")
@click.option("--city")
@click.option("--state")
@click.option("--zip_code")
@click.option("--race")
@click.option("--census_tract")
@click.option("--block_group")
@click.option("--street_address_2")
@click.option("--name_prefix")
@click.option("--name_suffix")
def main(**kwargs):
    signal.signal(signal.SIGINT, signal.SIG_DFL)  # Sane ^C behavior

    zrp_data_path = Path(zrp.__file__).parent / "data"
    zrp_download_sentinel = zrp_data_path / "downloaded.txt"
    if not zrp_download_sentinel.is_file():
        print("⬇️ Downloading ZRP data")
        zrp.download.download()
        zrp_download_sentinel.write_text("downloaded: {zrp.about.__version__}")
        print()

    zrp_df = pandas.DataFrame(kwargs, index=[0])

    artifacts_dir = Path("artifacts")
    if artifacts_dir.is_dir():
        print(f"🗑️ Removing {artifacts_dir}")
        shutil.rmtree(artifacts_dir)

    print("🔮 Running prediction")
    predictor = zrp.ZRP()
    predictor.fit()
    output_df = predictor.transform(zrp_df)
    for i, t in enumerate(output_df.itertuples()):
        print(t)
