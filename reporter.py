"""
reporter.py - Reporting and Terminal Presentation Module for DataBridge.

This module provides clean, human-readable terminal output for:
1. Post-import data audit summaries (metrics, errors, and rejected row details).
2. Tabular display of customer records stored in the SQLite database.
3. Database statistics dashboard (totals, demographics, city distribution).
"""

from typing import List, Dict, Any


def print_banner(title: str, width: int = 68) -> None:
    """Print a clean visual banner header."""
    print("\n" + "=" * width)
    print(title.center(width))
    print("=" * width)


def print_import_report(report_data: Dict[str, Any]) -> None:
    """
    Displays the complete Data Integration Import Report:
    - Total rows read
    - Valid records
    - Successfully inserted records
    - Duplicate records skipped
    - Invalid records rejected
    - Breakdown by error category
    - Detailed list of rejected records with row numbers and reasons
    """
    print_banner("DATABRIDGE IMPORT & CLEANING AUDIT REPORT")

    total_read = report_data.get("total_rows_read", 0)
    valid_count = report_data.get("valid_records", 0)
    inserted_count = report_data.get("successfully_inserted", 0)
    duplicates_skipped = report_data.get("duplicates_skipped", 0)
    invalid_rejected = report_data.get("invalid_records_rejected", 0)
    errors = report_data.get("error_counts", {})
    rejected_details = report_data.get("rejected_details", [])

    print(f"  * Total Rows Read from File:         {total_read:>5}")
    print(f"  * Valid Records Identified:          {valid_count:>5}")
    print(f"  * Successfully Inserted into DB:     {inserted_count:>5}")
    print(f"  * Duplicate Records Skipped:         {duplicates_skipped:>5}")
    print(f"  * Invalid Records Rejected:          {invalid_rejected:>5}")

    print("\n" + "-" * 68)
    print("  ERROR BREAKDOWN BY CATEGORY")
    print("-" * 68)
    print(f"  - Missing-value errors:              {errors.get('missing_value', 0):>5}")
    print(f"  - Invalid-email errors:              {errors.get('invalid_email', 0):>5}")
    print(f"  - Invalid-age errors:                {errors.get('invalid_age', 0):>5}")
    print(f"  - Duplicate-ID errors (in batch):    {errors.get('duplicate_id', 0):>5}")

    if rejected_details:
        print("\n" + "-" * 68)
        print("  REJECTED ROWS LOG (Audit Trail)")
        print("-" * 68)
        header = f"  {'Row #':<7} | {'Customer ID':<13} | {'Reason':<42}"
        print(header)
        print("  " + "-" * 64)
        for item in rejected_details:
            row_no = str(item.get("row_num", "-"))
            cid = str(item.get("customer_id") or "N/A")
            msg = str(item.get("reason", ""))
            if len(msg) > 42:
                msg = msg[:39] + "..."
            print(f"  {row_no:<7} | {cid:<13} | {msg:<42}")

    print("=" * 68 + "\n")


def print_customers_table(customers: List[Dict[str, Any]]) -> None:
    """
    Format and display customer records in an aligned terminal table.
    """
    if not customers:
        print("\n[INFO] No customer records found in the database.\n")
        return

    print_banner(f"STORED CUSTOMERS ({len(customers)} Total Records)")

    # Columns: ID (10), Name (20), Email (26), City (16), Age (5)
    header = f"{'ID':<10} | {'Name':<20} | {'Email':<26} | {'City':<16} | {'Age':<5}"
    divider = "-" * len(header)

    print(header)
    print(divider)

    for c in customers:
        cid = str(c.get("customer_id", ""))[:9]
        name = str(c.get("name", ""))[:19]
        email = str(c.get("email", ""))[:25]
        city = str(c.get("city", ""))[:15]
        age = str(c.get("age", ""))[:4]

        print(f"{cid:<10} | {name:<20} | {email:<26} | {city:<16} | {age:<5}")

    print(divider)
    print(f"Total rows displayed: {len(customers)}\n")


def print_database_stats(stats: Dict[str, Any]) -> None:
    """
    Print an overview of current database metrics and demographics.
    """
    print_banner("DATABRIDGE DATABASE STATISTICS")

    total = stats.get("total_customers", 0)
    if total == 0:
        print("  [INFO] The database is currently empty. Import a CSV to view statistics.\n")
        print("=" * 68 + "\n")
        return

    print(f"  * Total Customers in DB:             {total}")
    print(f"  * Unique Cities Represented:         {stats.get('unique_cities', 0)}")
    print(f"  * Average Customer Age:              {stats.get('average_age', 0.0)} years")
    print(f"  * Age Range:                         {stats.get('min_age', 0)} - {stats.get('max_age', 0)} years")

    city_breakdown = stats.get("city_breakdown", [])
    if city_breakdown:
        print("\n  Top Cities by Customer Count:")
        print("  " + "-" * 36)
        for item in city_breakdown:
            city_name = item.get("city", "Unknown")
            count = item.get("count", 0)
            bar = "#" * count
            print(f"   * {city_name:<16} {count:>3} {bar}")

    print("=" * 68 + "\n")
