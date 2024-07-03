"""Script to migrate financial transactions from NationBuilder to EveryAction"""

import csv
import re
import signal
from pathlib import Path

import click

FIELD_MAP = dict(
    nationbuilder_id="Online Reference Number",
    signup_nationbuilder_id="NationBuilder ID",
    signup_prefix="Prefix",
    signup_first_name="First Name",
    signup_middle_name="Middle Name",
    signup_last_name="Last Name",
    signup_suffix="Suffix",
    payment_type_name="Payment Method",
    amount="Amount",
    succeeded_at="Date Received",
    check_number="Check Number",
)

C3_VIA_NB = "501c3 Donation via NB"
C4_VIA_NB = "501c4 Donation via NB"

ACCOUNT_TRACKING_SOURCE_MAP = {
    "California RCV Institute Inc. 501(c)(3) donations - tax deductible": {
        "": f"Online One-Time {C3_VIA_NB}",
        "/R": f"Online Recurring {C3_VIA_NB}",
        "501c3_es_onetime": f"Online One-Time {C3_VIA_NB}",
        "501c3_manual_entry_onetime": f"Manual One-Time {C3_VIA_NB}",
        "501c3_via_benevity_recurring": f"Benevity One-Time {C3_VIA_NB}",
        "501c3_website_onetime": f"Online One-Time {C3_VIA_NB}",
        "501c3_website_recurring/R": f"Online Recurring {C3_VIA_NB}",
    },
    "California RCV Coalition Inc. 501(c)(4) Donation - not tax deductible": {
        "": f"Online One-Time {C4_VIA_NB}",
        "/R": f"Online Recurring {C4_VIA_NB}",
        "501c4_campaign_redondo_beach_2023": f"Online One-Time {C4_VIA_NB}",
        "501c4_website_onetime": f"Online One-Time {C4_VIA_NB}",
        "501c4_website_recurring/R": f"Online Recurring {C4_VIA_NB}",
        "donation_mtg_statewide_onetime": f"Online One-Time {C4_VIA_NB}",
        "donation_mtg_statewide_recurring/R": f"Online Recurring {C4_VIA_NB}",
        "fnd_q1cc_event_ticket": f"Online One-Time {C4_VIA_NB}",
    },
    "": {
        "": f"Manual One-Time {C4_VIA_NB}",
        "501c3_manual_entry_onetime": f"Manual One-Time {C3_VIA_NB}",
        "501c3_manual_entry_recurring": f"Manual Recurring {C3_VIA_NB}",
        "501c3_via_benevity_onetime": f"Benevity One-Time {C3_VIA_NB}",
        "501c3_via_benevity_recurring": f"Benevity Recurring {C3_VIA_NB}",
        "501c4_campaign_redondo_beach_2023": f"Online One-Time {C4_VIA_NB}",
        "501c4_in_kind": f"Manual One-Time {C4_VIA_NB}",
        "501c4_manual_entry_onetime": f"Manual One-Time {C4_VIA_NB}",
    },
}

NB_ACCOUNT = "merchant_account_name"
NB_DONOR_ID = "signup_nationbuilder_id"
NB_DONOR_NAME = "signup_full_name"
NB_ID = "nationbuilder_id"
NB_METHOD = "payment_type_name"
NB_NOTE = "note"
NB_PAGE = "page_slug"
NB_RECRUITER_ID = "recruiter_id"
NB_RECRUITER_NAME = "recruiter_name"
NB_RECURRING = "recurring_donation_status"
NB_TRACKING = "tracking_code_slug"

EA_AMOUNT = "Amount"
EA_NOTE = "Internal Note"
EA_SOURCE_CODE = "Source Code"
EA_NB_ID = FIELD_MAP[NB_ID]

ALL_EA_FIELDS = [
    *FIELD_MAP.values(),
    EA_SOURCE_CODE,
    EA_NOTE,
]

EA_FIELD_LIMITS = {
    "Prefix": 10,
    "First Name": 50,
    "Middle Name": 50,
    "Last Name": 50,
    "Suffix": 10,
    "Internal Note": 255,
}


@click.command()
@click.argument("nb_csvs", nargs=-1)
@click.option("--ea_exclude", help="EveryAction contribution report")
@click.option("--ea_csv", help="EveryAction CSV to write")
def main(nb_csvs, ea_exclude, ea_csv):
    """Converts NationBuilder CSV(s) to EveryAction CSV(s)"""

    signal.signal(signal.SIGINT, signal.SIG_DFL)  # Sane ^C behavior

    if nb_csvs:
        nb_paths = [Path(nb_csv) for nb_csv in nb_csvs]
    else:
        pattern = "nationbuilder-financialtransactions-export-*.csv"
        nb_paths = list(sorted(Path(".").glob(pattern)))
        if not nb_paths:
            print(f"💥 No input CSVs ({pattern}) found")
            raise SystemExit(1)

    if len(nb_paths) > 1 and ea_csv:
        print("💥 Multiple input files, but one output file")
        raise SystemExit(1)

    if ea_exclude:
        exc_paths = [Path(ea_exclude)]
    else:
        pattern = "ContributionReport-*.txt"
        exc_paths = list(sorted(Path(".").glob(pattern)))

    excludes = {}
    for exc_path in exc_paths:
        excludes.update(read_excludes(exc_path))

    for nb_path in nb_paths:
        if ea_csv:
            ea_path = Path(ea_csv)
        else:
            np = nb_path.stem.split("-")
            np = [p for p in np if p not in ("", "nationbuilder", "export")]
            ea_path = nb_path.with_name(f"everyaction-{'-'.join(np)}.txt")

        convert_file(nb_path, ea_path, excludes)


def read_excludes(exc_path):
    """Reads EveryAction contribution report to exclude

    :param exc_path: Path to EveryAction contribution report
    :return: Dict of NB transaction IDs/amounts already processed
    """

    print(f"⬅️ Reading {exc_path}")

    with exc_path.open(encoding="utf16") as exc_file:
        exc_reader = csv.DictReader(exc_file, dialect=csv.excel_tab)
        excludes = {}
        row_count = 0
        for exc_row in exc_reader:
            nb_id, amount = exc_row[EA_NB_ID], exc_row[EA_AMOUNT]
            if nb_id and amount:
                excludes[nb_id] = amount
            row_count += 1

        print(f"✅ {row_count} rows: {len(excludes)} excludable transactions")

    print()
    return excludes


def convert_file(nb_path, ea_path, excludes):
    """Converts NationBuilder transactions CSV to EveryAction CSV

    :param nb_path: Path to NationBuilder CSV
    :param ea_path: Path to EveryAction CSV
    :param excludes: Dict of NB transaction IDs/amounts to exclude
    """

    print(f"⬅️ Reading {nb_path}")
    print(f"▶️ Writing {ea_path}")

    def money(s):
        return float(s.replace("$", "").replace(",", ""))

    with nb_path.open() as nb_file:
        nb_reader = csv.DictReader(nb_file)
        with ea_path.open("w") as ea_file:
            writer_args = dict(fieldnames=ALL_EA_FIELDS, dialect=csv.excel_tab)
            ea_writer = csv.DictWriter(ea_file, **writer_args)
            ea_writer.writeheader()
            row_count = exc_count = 0
            for nb_row in nb_reader:
                # NationBuilder adds leading ' for Excel's benefit
                nb_row = {k: v.lstrip("'") for k, v in nb_row.items()}
                ea_row = convert_nb_row(nb_row)
                nb_id = ea_row[EA_NB_ID]
                amount = ea_row[EA_AMOUNT]
                exc_amount = excludes.get(nb_id)
                if not exc_amount:
                    ea_writer.writerow(sanitize_ea_row(ea_row))
                elif money(exc_amount) == money(amount):
                    exc_count += 1
                else:
                    print(f"💥 NB# {nb_id}: ${amount} != prior ${exc_amount}")
                    raise SystemExit(1)
                row_count += 1

            print(
                f"✅ {row_count} rows - {exc_count} excluded = "
                f"{row_count - exc_count} written"
            )

    print()


def convert_nb_row(nb):
    """Converts a NationBuilder transaction row to an EveryAction row

    :param nb: NationBuilder row as dict
    :return: EveryAction row as dict
    """

    ea_row = {ek: nb.get(nk, "") for nk, ek in FIELD_MAP.items()}

    nb_donor_id = nb.get(NB_DONOR_ID)
    nb_rec_id = nb.get(NB_RECRUITER_ID)
    nb_rec = nb.get(NB_RECRUITER_NAME) if nb_rec_id != nb_donor_id else ""

    ea_row[EA_NOTE] = (
        f"From NB"
        + (f": {nb.get(NB_NOTE)} " if nb.get(NB_NOTE) else " ")
        + f"*** txid={nb.get(NB_ID)} donor=[{nb.get(NB_DONOR_NAME)}] "
        + (f"recruiter=[{nb_rec}] " if nb_rec else "")
        + (f"page={nb.get(NB_PAGE)} " if nb.get(NB_PAGE) else "")
        + (f"tracking={nb.get(NB_TRACKING)} " if nb.get(NB_TRACKING) else "")
        + f"method=[{nb.get(NB_METHOD)}] "
        + (f"r={nb.get(NB_RECURRING)} " if nb.get(NB_RECURRING) else "")
    )

    nb_account = nb.get(NB_ACCOUNT, "")
    nb_recurring = nb.get(NB_RECURRING)
    nb_tracking = nb.get(NB_TRACKING, "") + ("/R" if nb_recurring else "")

    tracking_source_map = ACCOUNT_TRACKING_SOURCE_MAP.get(nb_account)
    if not tracking_source_map:
        print(f"💥 Bad NB merchant account: [{nb_account}]")
        raise SystemExit(1)

    source = tracking_source_map.get(nb_tracking)
    if not source:
        print(f"💥 Bad NB tracking code: [{nb_tracking}] ({nb_account})")
        raise SystemExit(1)

    ea_row[EA_SOURCE_CODE] = source
    return ea_row


def sanitize_ea_row(row):
    """Sanitizes an EveryAction row

    :param row: EveryAction row as dict
    :return: Row with length limits applied and bad characters stripped
    """

    out = {}
    for k, v in row.items():
        v = v.replace("\t", " ").replace("\n", " ").strip()
        if v:
            limit = EA_FIELD_LIMITS.get(k, 10000)
            if len(v) > limit:
                v = v[: limit - 3]
                v = v[: v.rindex(" ") + 1] if " " in v[limit // 2 :] else v
                v = v + "..."
            out[k] = v[: limit - 3] + "..." if len(v) > limit else v

    return out


def to_bool(value):
    """Converts text value from CSV to boolean

    :param value: Value to convert
    :return: Boolean value
    """

    value = value.lower() if isinstance(value, str) else value
    if value in ("true", "yes", "y", "1", 1, True):
        return True
    if value in ("false", "no", "n", "0", 0, False):
        return False
    if value in ("", "na", "n/a", None):
        return None
    return bool(value)
