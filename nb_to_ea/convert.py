"""Script to migrate data from NationBuilder to EveryAction"""

import csv
import re
import signal
from pathlib import Path

import fire  # type: ignore

IDENTITY_MAP = dict(
    nationbuilder_id="Source ID",
    prefix="Prefix",
    first_name="First Name",
    middle_name="Middle Name",
    last_name="Last Name",
    suffix="Suffix",
)

MISC_MAP = dict(
    note="Notes",
    employer="Employer Name",
    occupation="Occupation Name",
)

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
NB_FACEBOOK_USERNAME = "facebook_username"
NB_FEDERAL_DO_NOT_CALL = "federal_donotcall"
NB_ID = "nationbuilder_id"
NB_MOBILE_BAD = "is_mobile_bad"
NB_MOBILE_OPT_IN = "mobile_opt_in"
NB_PHONE_NUMBER_SUFFIX = "_number"
NB_PHONE_TYPE_MOBILE = "mobile"
NB_TWITTER_LOGIN = "twitter_login"
NB_WEBSITE = "website"

EA_EMAIL_ADDRESS = "Email Address"
EA_EMAIL_STATUS = "Email Subscription Status"
EA_EMAIL_STATUS_NOT_SUBSCRIBED = "Not Subscribed"
EA_EMAIL_STATUS_SUBSCRIBED = "Subscribed"
EA_EMAIL_STATUS_UNSUBSCRIBED = "Unsubscribed"
EA_EMAIL_TYPE = "Email Type"
EA_EMAIL_TYPE_OTHER = "Other"
EA_EMAIL_TYPE_PERSONAL = "Personal"
EA_EXT_FACEBOOK_URL = "Facebook URL"
EA_EXT_NATIONBUILDER_ID = "NationBuilder ID"
EA_EXT_OTHER = "Other Website"
EA_EXT_TWITTER_HANDLE = "Twitter Handle"
EA_PHONE_NUMBER = "Phone"
EA_PHONE_TYPE = "Phone Type"
EA_PHONE_TYPE_OTHER = "Other"
EA_SMS_OPT = "SMS Opt-In Status"
EA_SMS_OPT_IN = "Opt-In"
EA_SMS_OPT_OUT = "Opt-Out"
EA_SMS_OPT_UNKNOWN = "Unknown"

ALL_EA_FIELDS = [
    *IDENTITY_MAP.values(),
    *ADDR_MAP.values(),
    *MISC_MAP.values(),
    EA_EXT_FACEBOOK_URL,
    EA_EXT_NATIONBUILDER_ID,
    EA_EXT_OTHER,
    EA_EXT_TWITTER_HANDLE,
    EA_EMAIL_ADDRESS,
    EA_EMAIL_STATUS,
    EA_EMAIL_TYPE,
    EA_PHONE_NUMBER,
    EA_PHONE_TYPE,
    EA_SMS_OPT,
]


def main():
    """Entry point for nb_to_ea script"""

    signal.signal(signal.SIGINT, signal.SIG_DFL)  # Sane ^C behavior
    fire.Fire(fire_main)


def fire_main(*nb_csvs, ea_csv=None, limit=10):
    """Converts NationBuilder CSV(s) to EveryAction CSV(s)

    :param nb_csvs: NationBuilder CSV(s) to convert (searches . by default)
    :param ea_csv: EveryAction CSV to write (default based on nb_csvs)
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
            ea_path = nb_path.with_name(f"everyaction-{'-'.join(np)}.txt")

        convert(nb_path, ea_path, limit=limit)


def convert(nb_path, ea_path, *, limit):
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
                for out_row in convert_row(nb_row):
                    ea_writer.writerow(
                        {
                            k: v.replace("\t", " ").replace("&", "&").strip()
                            for k, v in out_row.items()
                            if v
                        }
                    )
                    output_count += 1
            else:
                print(f"✅ {input_count} -> {output_count} rows")

    print()


def convert_row(nb_row):
    """Converts a NationBuilder row to EveryAction row

    :param nb_row: NationBuilder row as dict
    :return: EveryAction row(s) as sequence of dicts
    """

    identity = {ek: nb_row.get(nk, "") for nk, ek in IDENTITY_MAP.items()}
    identity[EA_EMAIL_TYPE] = EA_EMAIL_TYPE_OTHER
    identity[EA_EMAIL_STATUS] = EA_EMAIL_STATUS_NOT_SUBSCRIBED
    identity[EA_PHONE_TYPE] = EA_PHONE_TYPE_OTHER
    identity[EA_SMS_OPT] = EA_SMS_OPT_UNKNOWN

    nb_no_call = convert_bool(nb_row.get(NB_DO_NOT_CALL))
    nb_no_contact = convert_bool(nb_row.get(NB_DO_NOT_CONTACT))
    nb_fed_no_call = convert_bool(nb_row.get(NB_FEDERAL_DO_NOT_CALL))
    nb_mobile_bad = convert_bool(nb_row.get(NB_MOBILE_BAD))
    nb_mobile_opt_in = convert_bool(nb_row.get(NB_MOBILE_OPT_IN))
    if nb_no_contact or nb_no_call or nb_fed_no_call or nb_mobile_bad:
        identity[EA_SMS_OPT] = EA_SMS_OPT_OUT
    elif nb_mobile_opt_in is True:
        identity[EA_SMS_OPT] = EA_SMS_OPT_IN
    elif nb_mobile_opt_in is False:
        identity[EA_SMS_OPT] = EA_SMS_OPT_OUT

    misc = {ek: nb_row.get(nk, "") for nk, ek in MISC_MAP.items()}
    misc[EA_EXT_NATIONBUILDER_ID] = nb_row.get(NB_ID)

    website = nb_row.get(NB_WEBSITE)
    if website:
        twitter_match = re.match(r"^https?://twitter.com/(\w*)$", website)
        if twitter_match:
            misc[EA_EXT_TWITTER_HANDLE] = twitter_match.group(1)
        elif re.match(r"^https?://www.facebook.com/", website):
            misc[EA_EXT_FACEBOOK_URL] = website
        else:
            misc[EA_EXT_OTHER] = website

    facebook_user = nb_row.get(NB_FACEBOOK_USERNAME)
    if facebook_user:
        facebook_user = facebook_user.strip("/").split("/")[-1]
        misc[EA_EXT_FACEBOOK_URL] = f"https://www.facebook.com/{facebook_user}"

    twitter_login = nb_row.get(NB_TWITTER_LOGIN)
    if twitter_login:
        misc[EA_EXT_TWITTER_HANDLE] = twitter_login.strip("@")

    addr_maps = []
    for nb_atype in NB_ADDR_TYPES:
        amap = {e: nb_row.get(f"{nb_atype}_{n}") for n, e in ADDR_MAP.items()}
        if any(amap.values()) and amap not in addr_maps:
            addr_maps.append(amap)

    nb_email_opt_in = convert_bool(nb_row.get(NB_EMAIL_OPT_IN))
    email_maps = []
    for nb_etype in NB_EMAIL_TYPES:
        email = nb_row.get(nb_etype)
        nb_bad = convert_bool(nb_row.get(f"{nb_etype}{NB_EMAIL_BAD_SUFFIX}"))
        if email and all(email != m[EA_EMAIL_ADDRESS] for m in email_maps):
            ea_status = (
                EA_EMAIL_STATUS_UNSUBSCRIBED
                if nb_bad or nb_no_contact
                else EA_EMAIL_STATUS_SUBSCRIBED
                if nb_email_opt_in
                else EA_EMAIL_STATUS_NOT_SUBSCRIBED
            )
            email_maps.append(
                {
                    EA_EMAIL_ADDRESS: email,
                    EA_EMAIL_TYPE: EA_EMAIL_TYPE_PERSONAL,
                    EA_EMAIL_STATUS: ea_status,
                }
            )

    phone_maps = []
    for nb_ptype, ea_ptype in PHONE_TYPE_MAP.items():
        # Strip US country code and non-digits
        value = nb_row.get(f"{nb_ptype}{NB_PHONE_NUMBER_SUFFIX}", "")
        digits = re.sub(r"[^\d]", "", value)
        digits = re.sub(r"^1(\d{10})$", r"\1", digits)
        if digits and "@" not in value:
            pmap = {EA_PHONE_NUMBER: digits, EA_PHONE_TYPE: ea_ptype}
            if pmap not in phone_maps:
                phone_maps.append(pmap)

    yield {**identity, **misc}
    for addr_map in addr_maps:
        yield {**identity, **addr_map}
    for email_map in email_maps:
        yield {**identity, **email_map}
    for phone_map in phone_maps:
        yield {**identity, **phone_map}


def convert_bool(value):
    """Converts text value from CSV to boolean

    :param value: Value to convert
    :return: Boolean value
    """

    value = value.lower() if isinstance(value, str) else value
    return (
        True if value in ("true", "yes", "y", "1", 1, True) else
        False if value in ("false", "no", "n", "0", 0, False) else
        None if value in ("", "na", "n/a", None) else
        bool(value)
    )
