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

TAG_ACTIVIST_MAP = {
    # "AB 2808 opposition signer": "Petition: Opposed AB 2808",
    "attended-abcs-of-rcv-20220728": "Volunteer: Historic Interest",
    "attended-abcs_of_rcv_20220924": "Volunteer: Historic Interest",
    "attended-abcs_of_rcv_20221206": "Volunteer: Historic Interest",
    "attended-abcs_of_rcv_20230228": "Volunteer: Historic Interest",
    "attended-all_volunteers_meeting_20220912": "Volunteer: Historic Interest",
    "attended-all_volunteers_meeting_20221013": "Volunteer: Historic Interest",
    "attended-all_volunteers_meeting_20230130": "Volunteer: Historic Interest",
    "attended-canvass-the-california-theatre_20230304": "Volunteer: Historic Interest",
    # "attended-kickback-party-los-angeles_20221011": "Event: Social",
    # "attended-kickback-party-san-jose_20221030": "Event: Social",
    "attended-morgan_hill_mushroom_mardi_gras_festival_20220529": "Volunteer: Historic Interest",
    "attended-Postcard-Party-Los-Angeles-20220726": "Volunteer: Historic Interest",
    "attended-Postcard-Party-San-Jose-20220813": "Volunteer: Historic Interest",
    # "attended-statewide-strategy-meeting-20230206": "Event: Statewide",
    "attended-thai_new_year_songkran_festival_20220828": "Volunteer: Historic Interest",
    "attended-volunteer-outreach-meeting-20230321": "Volunteer: Historic Interest",
    "basecamp": "Volunteer: Historic Interest",
    "besj-calrcv-city-council-call-in-2022-04-06": "Volunteer: Historic Interest",
    # "BESJ": "Campaign: San Jose",
    "call-party-20211017-vol": "Volunteer: Historic Interest",
    "call-party-20211024-vol": "Volunteer: Historic Interest",
    "call-party-20211114-vol": "Volunteer: Historic Interest",
    "canvass": "Volunteer: For Canvassing",
    # "CfER": "Organization: CfER",
    "digital-ad-volunteer-signup": "Volunteer: Historic Interest",
    "Donor_501c3": "Donor: 501(c)(3)",
    "Donor_501c3_onetime": "Donor: 501(c)(3)",
    "Donor_501c3_recurring": "Donor: 501(c)(3)",
    "Donor_wants_to_donate_please_call": "Donor: Historic Interest",
    "Field_Ops_Phone_Bank_02_22_23_RSVP": "Volunteer: Historic Interest",
    "Field_Ops_Phone_Bank_02_26_23_RSVP": "Volunteer: Historic Interest",
    "Field_Ops_Phone_Bank_06_08_22": "Volunteer: Historic Interest",
    "Field_Ops_Phone_Bank_08_17_22_RSVP": "Volunteer: Historic Interest",
    "Field_Ops_Phone_Bank_11_13_22_RSVP": "Volunteer: Historic Interest",
    "Field_Ops_Phone_Bank_RSVP_02012023": "Volunteer: Historic Interest",
    "Field_Ops_Phone_Bank_RSVP": "Volunteer: Historic Interest",
    "FO-Open-to-Volunteering": "Volunteer: Historic Interest",
    "FO-Yes-to-Volunteering": "Volunteer: For Canvassing",
    "FO-Yes-to-Yearly": "Donor: Historic Interest",
    "get-involved-donor-signup": "Donor: Historic Interest",
    "get-involved-volunteer-signup": "Volunteer: Historic Interest",
    "local-campaign-Alameda": "Volunteer: Historic Interest",
    "local-campaign-Belmont": "Volunteer: Historic Interest",
    "local-campaign-Eureka": "Volunteer: Historic Interest",
    "local-campaign-LEAD": "Volunteer: Historic Interest",
    "local-campaign-LosAngeles": "Volunteer: Historic Interest",
    "local-campaign-Petaluma": "Volunteer: Historic Interest",
    "local-campaign-RedondoBeach": "Volunteer: Historic Interest",
    "local-campaign-Sacramento": "Volunteer: Historic Interest",
    "local-campaign-SanBernardino": "Volunteer: Historic Interest",
    "local-campaign-SanDiego": "Volunteer: Historic Interest",
    "local-campaign-SanJose": "Volunteer: Historic Interest",
    "local-campaign-SantaBarbara": "Volunteer: Historic Interest",
    "local-campaign-SantaClaraCounty": "Volunteer: Historic Interest",
    "Maybe-Volunteer": "Volunteer: Historic Interest",
    "MEDIA": "Press: Media Member",
    "MoreChoiceSanDiego-Volunteer": "Volunteer: Historic Interest",
    # "mtg-statewide-20210921-LAUNCH": "Event: Statewide",
    # "mtg-statewide-20211110": "Event: Statewide",
    # "mtg-statewide-20211208": "Event: Statewide",
    # "mtg-statewide-20220216": "Event: Statewide",
    # "mtg-statewide-20220428": "Event: Statewide",
    "POL-CANDIDATE-Local": "Political: Candidate",
    "POL-CANDIDATE-State-Assembly": "Political: Candidate",
    "POL-CANDIDATE-State-Senate": "Political: Candidate",
    "POL-CANDIDATE-US-House": "Political: Candidate",
    "POL-ELECTED-OFFICIAL": "Political: Elected",
    "POL-FORMER": "Political: Insider",
    "politician": "Political: Insider",
    # "RANK-THE-VOTE": "Organization: Rank The Vote",
    "recurring_donor": "Donor: Recurring",
    "rsvp-abcs_of_rcv_20230924": "Volunteer: Historic Interest",
    "rsvp-abcs_of_rcv_20221206": "Volunteer: Historic Interest",
    "rsvp-abcs_of_rcv_20230228": "Volunteer: Historic Interest",
    "rsvp-abcs_of_rcv_20230329": "Volunteer: Historic Interest",
    "rsvp-all_volunteers_meeting_20220912": "Volunteer: Historic Interest",
    "rsvp-all_volunteers_meeting_20221013": "Volunteer: Historic Interest",
    "rsvp-all_volunteers_meeting_20230130": "Volunteer: Historic Interest",
    "rsvp-all_volunteers_meeting_20230314": "Volunteer: Historic Interest",
    # "rsvp-annual-celebration-statewide-strategy-meeting-september_20220922": "Event: Statewide",
    # "rsvp-cal_rcv_book_club_april": "Event: Social",
    # "rsvp-calrcv-pitch-training-zoom-20211117-vol": "Event: Training",
    "rsvp-canvass-canvass-the-grove_20220806": "Volunteer: Historic Interest",
    "rsvp-canvass-CSUN-20211213-vol": "Volunteer: Historic Interest",
    "rsvp-canvass-dalycity-20211204-vol": "Volunteer: Historic Interest",
    "rsvp-canvass-hayward-20211030-vol": "Volunteer: Historic Interest",
    "rsvp-canvass-hayward-20211127-vol": "Volunteer: Historic Interest",
    "rsvp-canvass-the-california-theatre_20230304": "Volunteer: Historic Interest",
    "rsvp-canvass-the-masonic-auditorium_20230304": "Volunteer: Historic Interest",
    "rsvp-canvass-the-venice-boardwalk_20220820": "Volunteer: Historic Interest",
    "rsvp-Field_Ops_Phone_Bank_11_20_22": "Volunteer: Historic Interest",
    "rsvp-Field_Ops_Phone_Bank_11_27_22": "Volunteer: Historic Interest",
    "rsvp-field-ops-redondo-text-bank-02132023": "Volunteer: Historic Interest",
    "rsvp-field-ops-redondo-text-bank-02162023": "Volunteer: Historic Interest",
    "rsvp-field-ops-team-meeting-canvass-prep-20220803": "Volunteer: Historic Interest",
    "rsvp-kchcc_latino_food_festival_menudo_pozole_cook-off_20220529": "Volunteer: Historic Interest",
    # "rsvp-kickback-orange_county_20221025": "Event: Social",
    # "rsvp-kickback-party-los-angeles_20221011": "Event: Social",
    # "rsvp-kickback-party-sacramento_20221022": "Event: Social",
    # "rsvp-kickback-party-san-jose_20221022": "Event: Social",
    "rsvp-la_city_council_call-in_20221018": "Volunteer: Historic Interest",
    # "rsvp-meetup-sf-20211021": "Event: Social",
    "rsvp-morgan_hill_mushroom_mardi_gras_festival_20220529": "Volunteer: Historic Interest",
    # "rsvp-mtg-statewide-20220622": "Event: Statewide",
    # "rsvp-orange_county_meet_greet_at_mimis_cafe_20220319": "Event: Social",
    "rsvp-Postcard-Party-Los-Angeles-20220726": "Volunteer: Historic Interest",
    "rsvp-Postcard-Party-Orange-County-20220824": "Volunteer: Historic Interest",
    "rsvp-Postcard-Party-Sacramento-20220730": "Volunteer: Historic Interest",
    "rsvp-Postcard-Party-San-Jose-20220813": "Volunteer: Historic Interest",
    "rsvp-public_comment_san_bernardino_cc_20230215": "Volunteer: Historic Interest",
    # "rsvp-raise_a_glass_to_ranked_choice_voting_20220522": "Event: Social",
    "rsvp-rcv_for_your_city_20230309": "Volunteer: Historic Interest",
    "rsvp-reddit-ama-california-politics-rcv-day-20220123": "Volunteer: Historic Interest",
    # "rsvp-sacramento_meet_greet_at_sac_yard": "Event: Social",
    # "rsvp_statewide_feb_2023": "Event: Statewide",
    # "rsvp-statewide-strategy-meeting-20220428": "Event: Statewide",
    # "rsvp-statewide-strategy-meeting-20220921": "Event: Statewide",
    # "rsvp-statewide-strategy-meeting-20230206": "Event: Statewide",
    "rsvp-train_the_trainer_05-25-2022": "Volunteer: Historic Interest",
    "rsvp-virtual_phone_bank_santa_clara_county_action_20221211": "Volunteer: Historic Interest",
    "rsvp-volunteer-outreach-meeting-20230321": "Volunteer: Historic Interest",
    "rsvp-volunteer-outreach-meeting-20230405": "Volunteer: Historic Interest",
    "RSVPd-for-7_26_22-postcard-event": "Volunteer: Historic Interest",
    "Santa Clara County Effort - Support": "Volunteer: Historic Interest",
    # "sf-lit-discussion-20211112": "Event: Social",
    "team-diversity-equity-inclusion": "Volunteer: Historic Interest",
    "team-endorsements-speakers": "Volunteer: Historic Interest",
    "team-exec-messaging": "Volunteer: Historic Interest",
    "team-field-ops": "Volunteer: Historic Interest",
    "team-fundraising": "Volunteer: Historic Interest",
    "TEAM-LEAD": "Volunteer: Historic Interest",
    "team-local-campaigns": "Volunteer: Historic Interest",
    "team-marketing": "Volunteer: Historic Interest",
    "team-policy-research": "Volunteer: Historic Interest",
    "team-tech-data-mgmt": "Volunteer: Historic Interest",
    "training-callhub-2022-03-25": "Volunteer: Historic Interest",
    "training-calrcv-pitch-zoom-20211117": "Volunteer: Historic Interest",
    "training-fundraising-capital-campaign-outreach-2022-02-12": "Volunteer: Historic Interest",
    "training-letter-to-editor-2023-01-09": "Volunteer: Historic Interest",
    "VIP": "Identity: Important Person",
    "volunteer": "Volunteer: Historic Interest",
    "volunteer-liveo-south-la": "Volunteer: Historic Interest",
    "z-INTEREST-team-data-mgmt": "Volunteer: Historic Interest",
    "z-INTEREST-team-diversity-equity-inclusion": "Volunteer: Historic Interest",
    "z-INTEREST-team-endorsements-own-group": "Volunteer: Historic Interest",
    "z-INTEREST-team-endorsements-speakers": "Volunteer: Historic Interest",
    "z-INTEREST-team-field-ops": "Volunteer: Historic Interest",
    "z-INTEREST-team-fundraising": "Volunteer: Historic Interest",
    "z-INTEREST-team-live-outreach": "Volunteer: Historic Interest",
    "z-INTEREST-team-marketing": "Volunteer: Historic Interest",
    "z-INTEREST-team-policy-research": "Volunteer: Historic Interest",
    "z-INTEREST-team-speakers": "Volunteer: Historic Interest",
    "z-INTEREST-team-tech-data-mgmt": "Volunteer: Historic Interest",
    "z-INTEREST-team-volunteer-onboarding": "Volunteer: Historic Interest",
    "z-INTEREST-vol-event-host": "Volunteer: Historic Interest",
    "z-INTEREST-vol-event-host-speakers": "Volunteer: Historic Interest",
    "z-INTEREST-vol-local-campaigns": "Volunteer: Historic Interest",
}

TAG_SOURCE_MAP = {
    "BESJ-intake-contact": "BESJ Website",
    "BESJ-intake-join": "BESJ Website",
    "canvass-cal-state-fullerton-2022-02-08": "Canvass via NB",
    "canvass-CalStateLA-20211206-vol": "Canvass via NB",
    "canvass-csuf-titan-walk-_20220208": "Canvass via NB",
    "canvass-csulb-university-student-union_20220301-rsvp": "Canvass via NB",
    "canvass-elac-campus-center_20220222-rsvp": "Canvass via NB",
    "canvass-foothill-college-political-awareness-day-20220511": "Canvass via NB",
    "canvass-hayward-farmers-mkt-20211030": "Canvass via NB",
    "canvass-hercules-bay-festival-20211003": "Canvass via NB",
    "canvass-hercules-bay-festival-20211003-vol": "Canvass via NB",
    "canvass-irvine-20211024-vol": "Canvass via NB",
    "canvass-irvine-andrew-yang-foward-book-tour-20211024": "Canvass via NB",
    "canvass-la-basic-income-march-20210925": "Canvass via NB",
    "canvass-la-bim-20210925-vol": "Canvass via NB",
    "canvass-la-cal-state-20211206": "Canvass via NB",
    "canvass-libertarian-convention-20220218": "Canvass via NB",
    "canvass-menlo-park-voting-center-20211102": "Canvass via NB",
    "canvass-mv-basic-income-march-20210925": "Canvass via NB",
    "canvass-mv-bim-20210925-vol": "Canvass via NB",
    "canvass-northridge-cal-state-20211213": "Canvass via NB",
    "canvass-palo-alto-farmers-market-2022-01-23": "Canvass via NB",
    "canvass-palo-alto-farmers-market-2022-01-30": "Canvass via NB",
    "canvass-seic-20211102-vol": "Canvass via NB",
    "canvass-sf-20211021-vol": "Canvass via NB",
    "canvass-sf-20211023-vol": "Canvass via NB",
    "canvass-sf-andrew-yang-foward-book-tour-20211023": "Canvass via NB",
    "canvass-smc-quad-student-union_20220125-rsvp": "Canvass via NB",
    "canvass-ucla-bruin-walk-_20220106": "Canvass via NB",
    "canvass-venice-beach-20220820": "Canvass via NB",
    "digital-ad-supporter-signup": "Digital Ads via NB",
    "digital-ad-volunteer-signup": "Digital Ads via NB",
    "event-panel-discussion-20220209": "NationBuilder Event",
    "get-involved-donor-signup": "NationBuilder Website",
    "get-involved-volunteer-and-donor-signup": "NationBuilder Website",
    "get-involved-volunteer-signup": "NationBuilder Website",
    "OK to do not email": "Founding",
    "SD-launch-event-20211118": "NationBuilder Event",
    "signup-bernie-sanders-event-mar-4-2023": "Canvass via NB",
    "signup-canvass-canvass-the-grove_20220806": "Canvass via NB",
    "signup-imported-from-AB2808-capitol-canary-campaign": "Anti-AB2808 Petition via NB",
    "signup-imported-from-Alexandra-Chandler-RCV-Supporters-in-CA": "Founding from Rank The Vote",
    "signup-imported-from-Benevity": "Benevity",
    "signup-imported-from-groups-promo-tracker-2021-09-13": "Founding",
    "signup-imported-from-launch-Zoom-registrations": "Founding",
    "signup-imported-from-slack": "Founding",
    "signup-imported-from-VCMA-NationBuilder": "Founding from Voter Choice MA",
    "signup-liveo": "Canvass via NB",
    "signup-manually-added-to-NB": "Manual Add via NB",
    "signup-recruiter": "Direct Recruit via NB",
    "signup-thai-new-year-songkran-festival-20220828": "Canvass via NB",
    "signup-website": "NationBuilder Website",
    "signup-website-contact": "NationBuilder Website",
    "signup-website-donate": "NationBuilder Website",
    "signup-website-event": "NationBuilder Website",
    "signup-zoom": "NationBuilder Event",
    "signup-zoom-attended": "NationBuilder Event",
    "sm-Facebook": "Facebook via NB",
    "sm-Twitter": "Twitter via NB",
    "sm-Twitter-AB2808": "Twitter via NB",
    "table-morgan-hill-mushroom-mardi-gras-20220528": "Canvass via NB",
    "table-san-bernardino-arts-fest-20220319": "Canvass via NB",
    "tabling-central-ave-farmers-market_20220203-rsvp": "Canvass via NB",
    "tabling-central-ave-farmers-market_20220310-rsvp": "Canvass via NB",
    "tabling-crenshaw-farmers-market_20220219-rsvp": "Canvass via NB",
    "tabling-crenshaw-farmers-market_20220326-rsvp": "Canvass via NB",
    "ucsb-calpirg-event-20220224": "Canvass via NB",
}

NB_DO_NOT_CALL = "do_not_call"
NB_DO_NOT_CONTACT = "do_not_contact"
NB_EMAIL_BAD_SUFFIX = "_is_bad"
NB_EMAIL_OPT_IN = "email_opt_in"
NB_FACEBOOK_USERNAME = "facebook_username"
NB_FEDERAL_DO_NOT_CALL = "federal_donotcall"
NB_ID = "nationbuilder_id"
NB_IS_VOLUNTEER = "is_volunteer"
NB_MOBILE_BAD = "is_mobile_bad"
NB_MOBILE_OPT_IN = "mobile_opt_in"
NB_NOTE = "note"
NB_PHONE_NUMBER_SUFFIX = "_number"
NB_PHONE_TYPE_MOBILE = "mobile"
NB_TAG_LIST = "tag_list"
NB_TWITTER_LOGIN = "twitter_login"
NB_WEBSITE = "website"

EA_ACTIVIST_CODE = "Activist Code"
# EA_ACTIVIST_NATIONBUILDER = "Origins: NationBuilder"
EA_ACTIVIST_VOLUNTEER = "Volunteer: Historic Interest"
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
EA_NOTES = "Notes"
EA_ORIGIN_SOURCE_CODE = "Origin Source Code"
EA_ORIGIN_SOURCE_CODE_OTHER = "Other via NB"
EA_PHONE_NUMBER = "Phone"
EA_PHONE_TYPE = "Phone Type"
EA_PHONE_TYPE_OTHER = "Other"
EA_PHONE_SMS_OPT = "SMS Opt-In Status"
EA_PHONE_SMS_OPT_IN = "Opt-In"
EA_PHONE_SMS_OPT_OUT = "Opt-Out"
EA_PHONE_SMS_OPT_UNKNOWN = "Unknown"
EA_RELATIONSHIP_SECONDARY = "Secondary Member"
EA_RELATIONSHIP_TYPE = "Relationship"
EA_RELATIONSHIP_TYPE_ORGANIZER = "Organizer"
EA_RELATIONSHIP_TYPE_RECRUITED_BY = "Recruited By"

ALL_EA_FIELDS = [
    *IDENTITY_MAP.values(),
    *ADDR_MAP.values(),
    *MISC_MAP.values(),
    EA_ACTIVIST_CODE,
    EA_EXT_FACEBOOK_URL,
    EA_EXT_NATIONBUILDER_ID,
    EA_EXT_OTHER,
    EA_EXT_TWITTER_HANDLE,
    EA_EMAIL_ADDRESS,
    EA_EMAIL_STATUS,
    EA_EMAIL_TYPE,
    EA_NOTES,
    EA_ORIGIN_SOURCE_CODE,
    EA_PHONE_NUMBER,
    EA_PHONE_TYPE,
    EA_PHONE_SMS_OPT,
    EA_RELATIONSHIP_SECONDARY,
    EA_RELATIONSHIP_TYPE,
]

EA_FIELD_LIMITS = {
    "Employer Name": 50,
    "Prefix": 10,
    "First Name": 50,
    "Middle Name": 50,
    "Last Name": 50,
    "Suffix": 10,
    "Notes": 1000,
}


def main():
    """Entry point for nb_to_ea script"""

    signal.signal(signal.SIGINT, signal.SIG_DFL)  # Sane ^C behavior
    fire.Fire(fire_main)


def fire_main(*nb_csvs, ea_csv=None, limit=10, add_notes=False):
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
        print("💥 Multiple input files, but one output file")
        raise SystemExit(1)

    for nb_path in nb_paths:
        if ea_csv:
            ea_path = Path(ea_csv)
        else:
            np = nb_path.stem.split("-")
            np = [p for p in np if p not in ("", "nationbuilder", "export")]
            np.extend([f"limit{limit}"] if limit else [])
            ea_path = nb_path.with_name(f"everyaction-{'-'.join(np)}.txt")

        convert_file(nb_path, ea_path, limit=limit, add_notes=add_notes)


def convert_file(nb_path, ea_path, *, limit, add_notes):
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
                # NationBuilder adds leading ' for Excel's benefit
                nb_row = {k: v.lstrip("'") for k, v in nb_row.items()}
                input_count += 1
                if limit and input_count >= limit:
                    print(f"🛑 Stopped at {limit} -> {output_count} rows")
                    break
                for ea_row in convert_nb_row(nb_row, add_notes=add_notes):
                    ea_writer.writerow(sanitize_ea_row(ea_row))
                    output_count += 1
            else:
                print(f"✅ {input_count} -> {output_count} rows")

    print()


def convert_nb_row(nb_row, *, add_notes):
    """Converts a NationBuilder row to EveryAction row

    :param nb_row: NationBuilder row as dict
    :return: EveryAction row(s) as sequence of dicts
    """

    identity = {ek: nb_row.get(nk, "") for nk, ek in IDENTITY_MAP.items()}
    identity[EA_EMAIL_TYPE] = EA_EMAIL_TYPE_OTHER
    identity[EA_EMAIL_STATUS] = EA_EMAIL_STATUS_NOT_SUBSCRIBED
    identity[EA_PHONE_TYPE] = EA_PHONE_TYPE_OTHER
    identity[EA_PHONE_SMS_OPT] = EA_PHONE_SMS_OPT_UNKNOWN

    nb_no_call = to_bool(nb_row.get(NB_DO_NOT_CALL))
    nb_no_contact = to_bool(nb_row.get(NB_DO_NOT_CONTACT))
    nb_fed_no_call = to_bool(nb_row.get(NB_FEDERAL_DO_NOT_CALL))
    nb_mobile_bad = to_bool(nb_row.get(NB_MOBILE_BAD))
    nb_mobile_opt_in = to_bool(nb_row.get(NB_MOBILE_OPT_IN))
    if nb_no_contact or nb_no_call or nb_fed_no_call or nb_mobile_bad:
        identity[EA_PHONE_SMS_OPT] = EA_PHONE_SMS_OPT_OUT
    elif nb_mobile_opt_in is True:
        identity[EA_PHONE_SMS_OPT] = EA_PHONE_SMS_OPT_IN
    elif nb_mobile_opt_in is False:
        identity[EA_PHONE_SMS_OPT] = EA_PHONE_SMS_OPT_OUT

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

    misc[EA_ORIGIN_SOURCE_CODE] = EA_ORIGIN_SOURCE_CODE_OTHER
    nb_tag_list = nb_row.get(NB_TAG_LIST)
    nb_tags = [t.strip() for t in nb_tag_list.split(",")] if nb_tag_list else []
    for nb_tag in nb_tags:
        ea_source_code = TAG_SOURCE_MAP.get(nb_tag)
        if ea_source_code:
            misc[EA_ORIGIN_SOURCE_CODE] = ea_source_code
            break  # Take the code from the first matching tag

    extra_maps = [misc]

    if add_notes:
        nb_note = nb_row.get(NB_NOTE)
        if add_notes and nb_note:
            extra_maps.append({EA_NOTES: f"NB note: {nb_note}"})

        nb_tag_notes = []
        for tag in sorted(nb_tags):
            if (not nb_tag_notes) or len(nb_tag_notes[-1]) + len(tag) > 900:
                nb_tag_notes.append("")
            nb_tag_notes[-1] += (", " if nb_tag_notes[-1] else "") + tag

        if len(nb_tag_notes) == 1:
            extra_maps.append({EA_NOTES: f"NB tags: {nb_tag_notes[0]}"})
        else:
            for li, nb_tag_note in enumerate(nb_tag_notes, 1):
                tag_note = f"NB tags {li}/{len(nb_tag_notes)}: {nb_tag_note}"
                extra_maps.append({EA_NOTES: tag_note})

    for nb_atype in NB_ADDR_TYPES:
        amap = {e: nb_row.get(f"{nb_atype}_{n}") for n, e in ADDR_MAP.items()}
        extra_maps.append(amap)

    nb_email_opt_in = to_bool(nb_row.get(NB_EMAIL_OPT_IN))
    for nb_etype in NB_EMAIL_TYPES:
        email = nb_row.get(nb_etype)
        nb_bad = to_bool(nb_row.get(f"{nb_etype}{NB_EMAIL_BAD_SUFFIX}"))
        if email:
            ea_status = (
                EA_EMAIL_STATUS_UNSUBSCRIBED
                if nb_bad or nb_no_contact
                else EA_EMAIL_STATUS_SUBSCRIBED
                if nb_email_opt_in
                else EA_EMAIL_STATUS_NOT_SUBSCRIBED
            )
            emap = {
                EA_EMAIL_ADDRESS: email,
                EA_EMAIL_TYPE: EA_EMAIL_TYPE_PERSONAL,
                EA_EMAIL_STATUS: ea_status,
            }
            extra_maps.append(emap)

    for nb_ptype, ea_ptype in PHONE_TYPE_MAP.items():
        # Strip US country code and non-digits
        value = nb_row.get(f"{nb_ptype}{NB_PHONE_NUMBER_SUFFIX}", "")
        digits = re.sub(r"[^\d]", "", value)
        digits = re.sub(r"^1(\d{10})$", r"\1", digits)
        if digits and "@" not in value:
            pmap = {EA_PHONE_NUMBER: digits, EA_PHONE_TYPE: ea_ptype}
            extra_maps.append(pmap)

    if to_bool(nb_row.get(NB_IS_VOLUNTEER)):
        extra_maps.append({EA_ACTIVIST_CODE: EA_ACTIVIST_VOLUNTEER})

    for nb_tag in nb_tags:
        ea_code = TAG_ACTIVIST_MAP.get(nb_tag)
        if ea_code:
            extra_maps.append({EA_ACTIVIST_CODE: ea_code})

    return [
        {**identity, **dict(extra)}
        for extra in sorted(set(tuple(m.items()) for m in extra_maps))
        if any(v for k, v in extra)
    ]


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
