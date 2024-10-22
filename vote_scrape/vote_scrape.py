"""Script to extract California primary data from PDF"""

import boto3
import click

PDF_URLS = {
    2012: "https://elections.cdn.sos.ca.gov/sov/2012-primary/pdf/13-sov-summary.pdf",
    2014: "https://elections.cdn.sos.ca.gov/sov/2014-primary/pdf/20-summary.pdf",
    2016: "https://elections.cdn.sos.ca.gov/sov/2016-primary/13-sov-summary.pdf",
    2018: "https://elections.cdn.sos.ca.gov/sov/2018-primary/sov/17-summary.pdf",
    2020: "https://elections.cdn.sos.ca.gov/sov/2020-primary/sov/15-sov-summary.pdf",
    2022: "https://elections.cdn.sos.ca.gov/sov/2022-primary/sov/16-summary.pdf",
    2024: "https://elections.cdn.sos.ca.gov/sov/2024-primary/sov/08-sov-summary-updated.pdf",
}


@click.command()
def main():
    print("Hello!")
