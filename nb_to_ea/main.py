"""Script to migrate data from NationBuilder to EveryAction"""

import csv
import re
import signal
from pathlib import Path

import fire  # type: ignore


BASIC_MAP = dict(
    nationbuilder_id="Source ID",
    prefix="Prefix",
    first_name="First Name",
    middle_name="Middle Name",
    last_name="Last Name",
    suffix="Suffix",
)

"""
MISC_MAP = dict(
    note=
    employer=
    occupation=
    sex=
    recruiter_name=
    point_person_name=
    is_volunteer=
    availability=
)
"""

NB_ADDR_TYPES = ["primary", "address", "billing", "mailing", "user_submitted"]

ADDR_MAP = dict(
    address1="Address Line 1",
    address2="Address Line 2",
    address3="Address Line 3",
    city="City",
    state="State",
    zip="Zip",
    country="Country",
)

NB_EMAIL_TYPES = ["email1", "email2", "email3", "email4"]

PHONE_TYPE_MAP = dict(
    phone="Main",
    work_phone="Work",
    mobile="Cell",
    fax="Fax",
)

NB_DO_NOT_CALL = "do_not_call"
NB_DO_NOT_CONTACT = "do_not_contact"
NB_EMAIL_BAD_SUFFIX = "_is_bad"
NB_EMAIL_OPT_IN = "email_opt_in"
NB_FEDERAL_DO_NOT_CALL = "federal_donotcall"
NB_MOBILE_BAD = "is_mobile_bad"
NB_PHONE_NUMBER_SUFFIX = "_number"
NB_PHONE_OPT_IN_SUFFIX = "_opt_in"
NB_PHONE_TYPE_MOBILE = "mobile"

EA_ACTIVIST_CODE = "Activist Code"

EA_EMAIL_ADDRESS = "Email Address"
EA_EMAIL_STATUS = "Email Subscription Status"
EA_EMAIL_STATUS_NOT_SUBSCRIBED = "Not Subscribed"
EA_EMAIL_STATUS_SUBSCRIBED = "Subscribed"
EA_EMAIL_STATUS_UNSUBSCRIBED = "Unsubscribed"
EA_EMAIL_TYPE = "Email Type"
EA_EMAIL_TYPE_OTHER = "Other"
EA_EMAIL_TYPE_PERSONAL = "Personal"

EA_PHONE_NUMBER = "Phone"
EA_PHONE_OPT = "SMS Opt-In Status"
EA_PHONE_OPT_IN = "Opt-In"
EA_PHONE_OPT_OUT = "Opt-Out"
EA_PHONE_OPT_UNKNOWN = "Unknown"
EA_PHONE_TYPE = "Phone Type"
EA_PHONE_TYPE_OTHER = "Other"

ALL_EA_FIELDS = [
    *BASIC_MAP.values(),
    *ADDR_MAP.values(),
    EA_ACTIVIST_CODE,
    EA_EMAIL_ADDRESS,
    EA_EMAIL_STATUS,
    EA_EMAIL_TYPE,
    EA_PHONE_NUMBER,
    EA_PHONE_TYPE,
    EA_PHONE_OPT,
]


def main():
    """Entry point for nb_to_ea script"""

    signal.signal(signal.SIGINT, signal.SIG_DFL)  # Sane ^C behavior
    fire.Fire(fire_main)


def fire_main(*nb_csvs, ea_csv=None, limit=10, activist_code="Test"):
    """Converts NationBuilder CSV(s) to EveryAction CSV(s)

    :param nb_csvs: NationBuilder CSV(s) to convert (searches . by default)
    :param ea_csv: EveryAction CSV to write (default based on nb_path)
    """

    if nb_csvs:
        nb_paths = [Path(nb_csv) for nb_csv in nb_csvs]
    else:
        pattern = "nationbuilder-people-export-*.csv"
        nb_paths = list(Path(".").glob(pattern))
        if not nb_paths:
            print(f"💥 No input CSVs ({pattern}) found")
            raise SystemExit(1)

    if len(nb_paths) > 1 and ea_csv:
        print(f"💥 Multiple input files, but one output file")
        raise SystemExit(1)

    for nb_path in nb_paths:
        if ea_csv:
            ea_path = Path(ea_csv)
        else:
            np = nb_path.stem.split("-")
            np = [p for p in np if p not in ("", "nationbuilder", "export")]
            np.extend([f"limit{limit}"] if limit else [])
            np.extend([activist_code] if activist_code else [])
            ea_path = nb_path.with_name(f"everyaction-{'-'.join(np)}.txt")

        convert(nb_path, ea_path, limit=limit, activist_code=activist_code)


def convert(nb_path, ea_path, *, limit, activist_code):
    """Converts NationBuilder CSV to EveryAction CSV

    :param nb_path: Path to NationBuilder CSV
    :param ea_path: Path to EveryAction CSV
    """

    print(f"⬅️ Reading {nb_path}")
    print(f"▶️ Writing {ea_path}")

    with nb_path.open() as nb_file:
        nb_reader = csv.DictReader(nb_file)
        with ea_path.open("w") as ea_file:
            writer_args = dict(fieldnames=ALL_EA_FIELDS, dialect=csv.excel_tab)
            ea_writer = csv.DictWriter(ea_file, **writer_args)
            ea_writer.writeheader()
            input_count = output_count = 0
            for nb_row in nb_reader:
                # NationBuilder adds leading ' for Excel compatibility
                nb_row = {k: v.lstrip("'") for k, v in nb_row.items()}
                input_count += 1
                if limit and input_count >= limit:
                    print(f"🛑 Stopped at {limit} -> {output_count} rows")
                    break
                for out_row in convert_row(nb_row, activist_code=activist_code):
                    ea_writer.writerow({
                        k: v.replace("\t", " ").replace("&", " ").strip()
                        for k, v in out_row.items() if v
                    })
                    output_count += 1
            else:
                print(f"✅ {input_count} -> {output_count} rows")

    print()


def convert_row(nb_row, *, activist_code):
    """Converts a NationBuilder row to EveryAction row

    :param nb_row: NationBuilder row as dict
    :return: EveryAction row(s) as sequence of dicts
    """

    # QUESTIONS
    # - How to tell organizations from individuals?

    basic = {ek: nb_row.get(nk, "") for nk, ek in BASIC_MAP.items()}
    basic.update({EA_ACTIVIST_CODE: activist_code} if activist_code else {})
    basic[EA_EMAIL_TYPE] = EA_EMAIL_TYPE_OTHER
    basic[EA_PHONE_TYPE] = EA_PHONE_TYPE_OTHER
    basic[EA_PHONE_OPT] = EA_PHONE_OPT_UNKNOWN

    addr_maps = []
    for nb_atype in NB_ADDR_TYPES:
        amap = {e: nb_row.get(f"{nb_atype}_{n}") for n, e in ADDR_MAP.items()}
        if any(amap.values()) and amap not in addr_maps:
            addr_maps.append(amap)

    nb_email_opt_in = (nb_row.get(NB_EMAIL_OPT_IN) == "true")
    nb_no_contact = (nb_row.get(NB_DO_NOT_CONTACT) == "true")
    email_maps = []
    for nb_etype in NB_EMAIL_TYPES:
        email = nb_row.get(nb_etype)
        nb_bad = (nb_row.get(f"{nb_etype}{NB_EMAIL_BAD_SUFFIX}") == "true")
        if email and all(email != m[EA_EMAIL_ADDRESS] for m in email_maps):
            ea_status = (
                EA_EMAIL_STATUS_UNSUBSCRIBED if nb_bad or nb_no_contact else
                EA_EMAIL_STATUS_SUBSCRIBED if nb_email_opt_in else
                EA_EMAIL_STATUS_NOT_SUBSCRIBED
            )
            email_maps.append({
                EA_EMAIL_ADDRESS: email,
                EA_EMAIL_TYPE: EA_EMAIL_TYPE_PERSONAL,
                EA_EMAIL_STATUS: ea_status,
            })

    nb_no_call = (nb_row.get(NB_DO_NOT_CALL) == "true")
    nb_fed_no_call = (nb_row.get(NB_FEDERAL_DO_NOT_CALL) == "true")
    nb_mobile_bad = (nb_row.get(NB_MOBILE_BAD) == "true")
    phone_maps = []
    for nb_ptype, ea_ptype in PHONE_TYPE_MAP.items():
        number = nb_row.get(f"{nb_ptype}{NB_PHONE_NUMBER_SUFFIX}")
        opt_in = nb_row.get(f"{nb_ptype}{NB_PHONE_OPT_IN_SUFFIX}")
        if number:
            # Strip US country code and non-digits
            number = re.sub(r"[^\d]", "", number)
            number = re.sub(r"^1(\d{10})$", r"\1", number)
            pmap = {EA_PHONE_NUMBER: number, EA_PHONE_TYPE: ea_ptype}
            if nb_no_contact or nb_no_call or nb_fed_no_call:
                pmap[EA_PHONE_OPT] = EA_PHONE_OPT_OUT
            elif nb_mobile_bad and nb_ptype == NB_PHONE_TYPE_MOBILE:
                pmap[EA_PHONE_OPT] = EA_PHONE_OPT_OUT
            elif opt_in == "true":
                pmap[EA_PHONE_OPT] = EA_PHONE_OPT_IN
            elif opt_in == "false":
                pmap[EA_PHONE_OPT] = EA_PHONE_OPT_OUT
            if pmap not in phone_maps:
                phone_maps.append(pmap)

    """
    yield {
        **basic,
        **(addr_maps.pop(0) if addr_maps else {}),
        **(email_maps.pop(0) if email_maps else {}),
        **(phone_maps.pop(0) if phone_maps else {}),
    }
    """

    yield basic
    for addr_map in addr_maps:
        yield {**basic, **addr_map}
    for email_map in email_maps:
        yield {**basic, **email_map}
    for phone_map in phone_maps:
        yield {**basic, **phone_map}
