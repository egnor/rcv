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
    # "attended-abcs-of-rcv-20220728": "Event: Training",
    # "attended-abcs_of_rcv_20220924": "Event: Training",
    # "attended-abcs_of_rcv_20221206": "Event: Training",
    # "attended-abcs_of_rcv_20230228": "Event: Training",
    # "attended-all_volunteers_meeting_20220912": "Event: Volunteer",
    # "attended-all_volunteers_meeting_20221013": "Event: Volunteer",
    # "attended-all_volunteers_meeting_20230130": "Event: Volunteer",
    # "attended-canvass-the-california-theatre_20230304": "Action: Canvassed",
    # "attended-kickback-party-los-angeles_20221011": "Event: Social",
    # "attended-kickback-party-san-jose_20221030": "Event: Social",
    # "attended-morgan_hill_mushroom_mardi_gras_festival_20220529": "Action: Canvassed",
    # "attended-Postcard-Party-Los-Angeles-20220726": "Action: Writing",
    # "attended-Postcard-Party-San-Jose-20220813": "Action: Writing",
    # "attended-statewide-strategy-meeting-20230206": "Event: Statewide",
    # "attended-thai_new_year_songkran_festival_20220828": "Action: Canvassed",
    # "attended-volunteer-outreach-meeting-20230321": "Event: Volunteer",
    # "basecamp": "Member: On Basecamp",
    # "besj-calrcv-city-council-call-in-2022-04-06": "Action: Called/Texted",
    # "BESJ": an Jose",
    # "call-party-20211017-vol": "Action: Called/Texted",
    # "call-party-20211024-vol": "Action: Called/Texted",
    # "call-party-20211114-vol": "Action: Called/Texted",
    "canvass": "Volunteer: For Canvassing",
    # "CfER": "Organization: CfER",
    "digital-ad-volunteer-signup": "Volunteer: Interested",
    "Donor_501c3": "Donor: 501(c)(3)",
    "Donor_501c3_onetime": "Donor: 501(c)(3)",
    "Donor_501c3_recurring": "Donor: 501(c)(3)",
    "Donor_wants_to_donate_please_call": "Donor: Interested",
    # "Field_Ops_Phone_Bank_02_22_23_RSVP": "Action: Called/Texted",
    # "Field_Ops_Phone_Bank_02_26_23_RSVP": "Action: Called/Texted",
    # "Field_Ops_Phone_Bank_06_08_22": "Action: Called/Texted",
    # "Field_Ops_Phone_Bank_08_17_22_RSVP": "Action: Called/Texted",
    # "Field_Ops_Phone_Bank_11_13_22_RSVP": "Action: Called/Texted",
    # "Field_Ops_Phone_Bank_RSVP_02012023": "Action: Called/Texted",
    # "Field_Ops_Phone_Bank_RSVP": "Action: Called/Texted",
    "FO-Open-to-Volunteering": "Volunteer: Interested",
    "FO-Yes-to-Volunteering": "Volunteer: Interested",
    "FO-Yes-to-Yearly": "Donor: Interested",
    "get-involved-donor-signup": "Donor: Interested",
    "get-involved-volunteer-signup": "Volunteer: Interested",
    # "local-campaign-Alameda": "Campaign: Alameda",
    # "local-campaign-Belmont": "Campaign: Belmont",
    # "local-campaign-Eureka": "Campaign: Eureka",
    # "local-campaign-LEAD": "Administrative: Campaign Lead",
    # "local-campaign-LosAngeles": "Campaign: Los Angeles",
    # "local-campaign-Petaluma": "Campaign: Petaluma",
    # "local-campaign-RedondoBeach": "Campaign: Redondo Beach",
    # "local-campaign-Sacramento": "Campaign: Sacramento",
    # "local-campaign-SanBernardino": "Campaign: San Bernardino",
    # "local-campaign-SanDiego": "Campaign: San Diego",
    # "local-campaign-SanJose": "Campaign: San Jose",
    # "local-campaign-SantaBarbara": "Campaign: Santa Barbara",
    # "local-campaign-SantaClaraCounty": "Campaign: Santa Clara County",
    "Maybe-Volunteer": "Volunteer: Interested",
    "MEDIA": "Press: Media Member",
    # "MoreChoiceSanDiego-Volunteer": "Campaign: San Diego",
    "mtg-statewide-20210921-LAUNCH": "Event: Statewide",
    "mtg-statewide-20211110": "Event: Statewide",
    "mtg-statewide-20211208": "Event: Statewide",
    "mtg-statewide-20220216": "Event: Statewide",
    "mtg-statewide-20220428": "Event: Statewide",
    "POL-CANDIDATE-Local": "Political: Candidate",
    "POL-CANDIDATE-State-Assembly": "Political: Candidate",
    "POL-CANDIDATE-State-Senate": "Political: Candidate",
    "POL-CANDIDATE-US-House": "Political: Candidate",
    "POL-ELECTED-OFFICIAL": "Political: Elected",
    "POL-FORMER": "Political: Insider",
    "politician": "Political: Insider",
    # "RANK-THE-VOTE": "Organization: Rank The Vote",
    "recurring_donor": "Donor: Recurring",
    "rsvp-abcs_of_rcv_20230924": "Event: Training",
    "rsvp-abcs_of_rcv_20221206": "Event: Training",
    "rsvp-abcs_of_rcv_20230228": "Event: Training",
    "rsvp-abcs_of_rcv_20230329": "Event: Training",
    "rsvp-all_volunteers_meeting_20220912": "Event: Volunteer",
    "rsvp-all_volunteers_meeting_20221013": "Event: Volunteer",
    "rsvp-all_volunteers_meeting_20230130": "Event: Volunteer",
    "rsvp-all_volunteers_meeting_20230314": "Event: Volunteer",
    "rsvp-annual-celebration-statewide-strategy-meeting-september_20220922": "Event: Statewide",
    "rsvp-cal_rcv_book_club_april": "Event: Social",
    "rsvp-calrcv-pitch-training-zoom-20211117-vol": "Event: Training",
    # "rsvp-canvass-canvass-the-grove_20220806": "Action: Canvassed",
    # "rsvp-canvass-CSUN-20211213-vol": "Action: Canvassed",
    # "rsvp-canvass-dalycity-20211204-vol": "Action: Canvassed",
    # "rsvp-canvass-hayward-20211030-vol": "Action: Canvassed",
    # "rsvp-canvass-hayward-20211127-vol": "Action: Canvassed",
    # "rsvp-canvass-the-california-theatre_20230304": "Action: Canvassed",
    # "rsvp-canvass-the-masonic-auditorium_20230304": "Action: Canvassed",
    # "rsvp-canvass-the-venice-boardwalk_20220820": "Action: Canvassed",
    # "rsvp-Field_Ops_Phone_Bank_11_20_22": "Action: Called/Texted",
    # "rsvp-Field_Ops_Phone_Bank_11_27_22": "Action: Called/Texted",
    # "rsvp-field-ops-redondo-text-bank-02132023": "Action: Called/Texted",
    # "rsvp-field-ops-redondo-text-bank-02162023": "Action: Called/Texted",
    "rsvp-field-ops-team-meeting-canvass-prep-20220803": "Event: Training",
    # "rsvp-kchcc_latino_food_festival_menudo_pozole_cook-off_20220529": "Action: Canvassed",
    "rsvp-kickback-orange_county_20221025": "Event: Social",
    "rsvp-kickback-party-los-angeles_20221011": "Event: Social",
    "rsvp-kickback-party-sacramento_20221022": "Event: Social",
    "rsvp-kickback-party-san-jose_20221022": "Event: Social",
    # "rsvp-la_city_council_call-in_20221018": "Action: Called/Texted",
    "rsvp-meetup-sf-20211021": "Event: Social",
    # "rsvp-morgan_hill_mushroom_mardi_gras_festival_20220529": "Action: Canvassed",
    "rsvp-mtg-statewide-20220622": "Event: Statewide",
    "rsvp-orange_county_meet_greet_at_mimis_cafe_20220319": "Event: Social",
    # "rsvp-Postcard-Party-Los-Angeles-20220726": "Action: Writing",
    # "rsvp-Postcard-Party-Orange-County-20220824": "Action: Writing",
    # "rsvp-Postcard-Party-Sacramento-20220730": "Action: Writing",
    # "rsvp-Postcard-Party-San-Jose-20220813": "Action: Writing",
    # "rsvp-public_comment_san_bernardino_cc_20230215": "Action: Called/Texted",
    "rsvp-raise_a_glass_to_ranked_choice_voting_20220522": "Event: Social",
    "rsvp-rcv_for_your_city_20230309": "Event: Training",
    # "rsvp-reddit-ama-california-politics-rcv-day-20220123": "Action: Writing",
    "rsvp-sacramento_meet_greet_at_sac_yard": "Event: Social",
    "rsvp_statewide_feb_2023": "Event: Statewide",
    "rsvp-statewide-strategy-meeting-20220428": "Event: Statewide",
    "rsvp-statewide-strategy-meeting-20220921": "Event: Statewide",
    "rsvp-statewide-strategy-meeting-20230206": "Event: Statewide",
    "rsvp-train_the_trainer_05-25-2022": "Event: Training",
    # "rsvp-virtual_phone_bank_santa_clara_county_action_20221211": "Action: Called/Texted",
    "rsvp-volunteer-outreach-meeting-20230321": "Event: Volunteer",
    "rsvp-volunteer-outreach-meeting-20230405": "Event: Volunteer",
    # "RSVPd-for-7_26_22-postcard-event": "Action: Writing",
    "Santa Clara County Effort - Support": "Campaign: Santa Clara County",
    "sf-lit-discussion-20211112": "Event: Social",
    # "team-diversity-equity-inclusion": "Member: DEI Team",
    # "team-endorsements-speakers": "Member: Speakers Team",
    # "team-exec-messaging": "Member: Exec Team",
    # "team-field-ops": "Member: Field Ops Team",
    # "team-fundraising": "Member: Fundraising Team",
    "TEAM-LEAD": "Administrative: Team Lead",
    # "team-local-campaigns": "Member: Local Campaigns Team",
    # "team-marketing": "Member: Marketing Team",
    # "team-policy-research": "Member: Policy/Research Team",
    # "team-tech-data-mgmt": "Member: Tech/Data Team",
    "training-callhub-2022-03-25": "Event: Training",
    "training-calrcv-pitch-zoom-20211117": "Event: Training",
    "training-fundraising-capital-campaign-outreach-2022-02-12": "Event: Training",
    "training-letter-to-editor-2023-01-09": "Event: Training",
    "VIP": "Identity: Important Person",
    "volunteer": "Volunteer: Interested",
    "volunteer-liveo-south-la": "Volunteer: For Field Ops Team",
    "z-INTEREST-team-data-mgmt": "Volunteer: For Tech/Data Team",
    "z-INTEREST-team-diversity-equity-inclusion": "Volunteer: For DEI Team",
    "z-INTEREST-team-endorsements-own-group": "Volunteer: For Speakers Team",
    "z-INTEREST-team-endorsements-speakers": "Volunteer: For Speakers Team",
    "z-INTEREST-team-field-ops": "Volunteer: For Field Ops Team",
    "z-INTEREST-team-fundraising": "Volunteer: For Fundraising Team",
    "z-INTEREST-team-live-outreach": "Volunteer: For Field Ops Team",
    "z-INTEREST-team-marketing": "Volunteer: For Marketing Team",
    "z-INTEREST-team-policy-research": "Volunteer: For Policy Team",
    "z-INTEREST-team-speakers": "Volunteer: For Speakers Team",
    "z-INTEREST-team-tech-data-mgmt": "Volunteer: For Tech/Data Team",
    "z-INTEREST-team-volunteer-onboarding": "Volunteer: For Leads/Ops",
    "z-INTEREST-vol-event-host": "Volunteer: For Field Ops Team",
    "z-INTEREST-vol-event-host-speakers": "Volunteer: For Speakers Team",
    "z-INTEREST-vol-local-campaigns": "Volunteer: For Local Campaigns",
}

TAG_SOURCE_MAP = {
    "BESJ-intake-contact": "BESJ Website",
    "BESJ-intake-join": "BESJ Website",
    "canvass-cal-state-fullerton-2022-02-08": "Canvassing via NB",
    "canvass-CalStateLA-20211206-vol": "Canvassing via NB",
    "canvass-csuf-titan-walk-_20220208": "Canvassing via NB",
    "canvass-csulb-university-student-union_20220301-rsvp": "Canvassing via NB",
    "canvass-elac-campus-center_20220222-rsvp": "Canvassing via NB",
    "canvass-foothill-college-political-awareness-day-20220511": "Canvassing via NB",
    "canvass-hayward-farmers-mkt-20211030": "Canvassing via NB",
    "canvass-hercules-bay-festival-20211003": "Canvassing via NB",
    "canvass-hercules-bay-festival-20211003-vol": "Canvassing via NB",
    "canvass-irvine-20211024-vol": "Canvassing via NB",
    "canvass-irvine-andrew-yang-foward-book-tour-20211024": "Canvassing via NB",
    "canvass-la-basic-income-march-20210925": "Canvassing via NB",
    "canvass-la-bim-20210925-vol": "Canvassing via NB",
    "canvass-la-cal-state-20211206": "Canvassing via NB",
    "canvass-libertarian-convention-20220218": "Canvassing via NB",
    "canvass-menlo-park-voting-center-20211102": "Canvassing via NB",
    "canvass-mv-basic-income-march-20210925": "Canvassing via NB",
    "canvass-mv-bim-20210925-vol": "Canvassing via NB",
    "canvass-northridge-cal-state-20211213": "Canvassing via NB",
    "canvass-palo-alto-farmers-market-2022-01-23": "Canvassing via NB",
    "canvass-palo-alto-farmers-market-2022-01-30": "Canvassing via NB",
    "canvass-seic-20211102-vol": "Canvassing via NB",
    "canvass-sf-20211021-vol": "Canvassing via NB",
    "canvass-sf-20211023-vol": "Canvassing via NB",
    "canvass-sf-andrew-yang-foward-book-tour-20211023": "Canvassing via NB",
    "canvass-smc-quad-student-union_20220125-rsvp": "Canvassing via NB",
    "canvass-ucla-bruin-walk-_20220106": "Canvassing via NB",
    "canvass-venice-beach-20220820": "Canvassing via NB",
    "digital-ad-supporter-signup": "Digital Ads via NB",
    "digital-ad-volunteer-signup": "Digital Ads via NB",
    "event-panel-discussion-20220209": "Event via NB",
    "get-involved-donor-signup": "NationBuilder Website",
    "get-involved-volunteer-and-donor-signup": "NationBuilder Website",
    "get-involved-volunteer-signup": "NationBuilder Website",
    "OK to do not email": "Founding via NB",
    "SD-launch-event-20211118": "Event via NB",
    "signup-bernie-sanders-event-mar-4-2023": "Canvassing via NB",
    "signup-canvass-canvass-the-grove_20220806": "Canvassing via NB",
    "signup-imported-from-AB2808-capitol-canary-campaign": "Anti-AB2808 Petition via NB",
    "signup-imported-from-Alexandra-Chandler-RCV-Supporters-in-CA": "Founding from Rank The Vote via NB",
    "signup-imported-from-groups-promo-tracker-2021-09-13": "Founding via NB",
    "signup-imported-from-launch-Zoom-registrations": "Founding via NB",
    "signup-imported-from-slack": "Founding via NB",
    "signup-imported-from-VCMA-NationBuilder": "Founding from Voter Choice MA via NB",
    "signup-liveo": "Canvassing via NB",
    "signup-thai-new-year-songkran-festival-20220828": "Canvassing via NB",
    "signup-website": "NationBuilder Website",
    "signup-website-contact": "NationBuilder Website",
    "signup-website-donate": "NationBuilder Website",
    "signup-website-event": "NationBuilder Website",
    "signup-zoom": "Mobilize Events",
    "signup-zoom-attended": "Mobilize Events",
    "sm-Facebook": "Facebook via NB",
    "sm-Twitter": "Twitter via NB",
    "sm-Twitter-AB2808": "Twitter via NB",
    "table-morgan-hill-mushroom-mardi-gras-20220528": "Canvassing via NB",
    "table-san-bernardino-arts-fest-20220319": "Canvassing via NB",
    "tabling-central-ave-farmers-market_20220203-rsvp": "Canvassing via NB",
    "tabling-central-ave-farmers-market_20220310-rsvp": "Canvassing via NB",
    "tabling-crenshaw-farmers-market_20220219-rsvp": "Canvassing via NB",
    "tabling-crenshaw-farmers-market_20220326-rsvp": "Canvassing via NB",
    "ucsb-calpirg-event-20220224": "Canvassing via NB",
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
EA_ACTIVIST_NATIONBUILDER = "Origins: NationBuilder"
EA_ACTIVIST_VOLUNTEER = "Volunteer: Interested"
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

        convert_file(nb_path, ea_path, limit=limit)


def convert_file(nb_path, ea_path, *, limit):
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
                for ea_row in convert_nb_row(nb_row):
                    ea_writer.writerow(sanitize_ea_row(ea_row))
                    output_count += 1
            else:
                print(f"✅ {input_count} -> {output_count} rows")

    print()


def convert_nb_row(nb_row):
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
    misc[EA_ACTIVIST_CODE] = EA_ACTIVIST_NATIONBUILDER

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

    nb_note = nb_row.get(NB_NOTE)
    if nb_note:
        misc[EA_NOTES] = f"NB note: {nb_note}"

    nb_tag_list = nb_row.get(NB_TAG_LIST)
    nb_tags = [t.strip() for t in nb_tag_list.split(",")] if nb_tag_list else []
    for nb_tag in nb_tags:
        ea_source_code = TAG_SOURCE_MAP.get(nb_tag)
        if ea_source_code:
            misc[EA_ORIGIN_SOURCE_CODE] = ea_source_code
            break  # Take the code from the first matching tag

    extra_maps = [misc]

    nb_tag_notes = []
    for tag in sorted(nb_tags):
        if (not nb_tag_notes) or len(nb_tag_notes[-1]) + len(tag) > 900:
            nb_tag_notes.append("")
        nb_tag_notes[-1] += (", " if nb_tag_notes[-1] else "") + tag

    if len(nb_tag_notes) == 1:
        extra_maps.append({EA_NOTES: f"NB tags: {nb_tag_notes[0]}"})
    else:
        for li, nb_tag_note in enumerate(nb_tag_notes, 1):
            note = f"NB tags {li}/{len(nb_tag_notes)}: {nb_tag_note}"
            extra_maps.append({EA_NOTES: note})

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
