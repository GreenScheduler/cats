# pyright: reportUnusedCallResult=none, reportUninitializedInstanceVariable=none
# Script to generate UK outcodes from the ONS Postcode Directory
# Example (May 2026): https://geoportal.statistics.gov.uk/datasets/6fff67d204fd4f339591ed667a6e3642/about

import argparse
import csv
from pathlib import Path
from typing import cast


class Args(argparse.Namespace):
    input_file: str
    output_file: str


def get_outcodes(input_file: str) -> set[str]:
    outcodes: set[str] = set()
    with Path(input_file).open(newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            outcodes.add(row["pcd8"].split()[0])
    return outcodes


def main():
    parser = argparse.ArgumentParser(
        description="Write UK postcodes out-code component from ONS data"
    )
    parser.add_argument("input_file", help="Path to the input CSV file")
    parser.add_argument(
        "-o",
        "--output-file",
        help="Path to output outcodes file",
        default="uk_outcodes.txt",
    )
    args = cast(Args, parser.parse_args())
    outcodes = get_outcodes(args.input_file)
    Path(args.output_file).write_text("\n".join(sorted(outcodes)))


if __name__ == "__main__":
    main()
