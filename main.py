"""
main.py - Entry Point and Terminal Menu Interface for DataBridge.

This module orchestrates:
1. The interactive terminal menu loop.
2. Safe extraction and parsing of CSV files.
3. Execution of cleaning and validation rules.
4. Database storage with SQLite and transactions.
5. Invocation of audit reporting and data querying.
"""

import os
import sys
import csv
from typing import Dict, Any, List

# Import DataBridge application modules
import data_cleaner
import database
import reporter

# Resolve directory paths relative to this script for reliable execution on Windows
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CSV_PATH = os.path.join(BASE_DIR, "customers.csv")
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "databridge.db")


def import_csv_workflow(db_path: str = DEFAULT_DB_PATH) -> None:
    """
    Handles CSV import:
    1. Prompts user for CSV file path (defaults to customers.csv).
    2. Validates file existence and structure.
    3. Cleans and validates rows using data_cleaner.
    4. Inserts valid rows into SQLite.
    5. Displays complete audit report.
    """
    print("\n--- 1. Import CSV and Clean Data ---")
    prompt = f"Enter CSV file path [Press ENTER for default: customers.csv]: "
    user_input = input(prompt).strip()

    if not user_input:
        csv_path = DEFAULT_CSV_PATH
    else:
        # Support both absolute paths and relative paths entered by the user
        csv_path = os.path.abspath(user_input) if not os.path.isabs(user_input) else user_input

    # 1. Error Handling: Check if file exists
    if not os.path.isfile(csv_path):
        print(f"\n[ERROR] File not found: '{csv_path}'")
        print("Please check the path and make sure the file exists.\n")
        return

    # 2. Error Handling: Check if file is empty
    if os.path.getsize(csv_path) == 0:
        print(f"\n[ERROR] The selected file is completely empty: '{csv_path}'\n")
        return

    # Initialize database and tables if not already existing
    try:
        database.init_db(db_path)
    except Exception as e:
        print(f"\n[ERROR] Failed to initialize database: {e}\n")
        return

    print(f"\n[INFO] Reading and validating: '{csv_path}'...")

    # Statistics tracking containers
    total_rows = 0
    valid_records: List[Dict[str, Any]] = []
    seen_ids_in_batch = set()

    error_counts = {
        "missing_value": 0,
        "invalid_email": 0,
        "invalid_age": 0,
        "duplicate_id": 0,
    }
    rejected_details = []

    try:
        # Use utf-8-sig to automatically handle any Windows Excel UTF-8 BOM
        with open(csv_path, mode="r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)

            # 3. Error Handling: Check headers
            if not reader.fieldnames:
                print("\n[ERROR] Could not read CSV headers. The file may be corrupt or empty.\n")
                return

            # Clean and lowercase header names to be resilient to minor header whitespace
            clean_headers = [h.strip() for h in reader.fieldnames if h]
            missing_cols = [col for col in data_cleaner.REQUIRED_FIELDS if col not in clean_headers]

            if missing_cols:
                print(f"\n[ERROR] CSV is missing required column(s): {', '.join(missing_cols)}")
                print(f"Required schema: {', '.join(data_cleaner.REQUIRED_FIELDS)}\n")
                return

            # Read and validate each data row
            for row_idx, raw_row in enumerate(reader, start=2):  # start=2 accounts for header row
                total_rows += 1

                # Clean header keys in row dictionary if they had whitespace
                normalized_row = {k.strip(): v for k, v in raw_row.items() if k}

                validation = data_cleaner.validate_and_clean_row(normalized_row, seen_ids_in_batch)

                if validation["is_valid"]:
                    cleaned = validation["cleaned_data"]
                    seen_ids_in_batch.add(cleaned["customer_id"])
                    valid_records.append(cleaned)
                else:
                    cat = validation["error_category"]
                    if cat in error_counts:
                        error_counts[cat] += 1
                    cid = normalized_row.get("customer_id", "").strip()
                    rejected_details.append({
                        "row_num": row_idx,
                        "customer_id": cid or "MISSING",
                        "reason": validation["error_message"]
                    })

    except UnicodeDecodeError:
        print(f"\n[ERROR] Encoding error reading '{csv_path}'. Please ensure the file is saved as UTF-8.\n")
        return
    except csv.Error as e:
        print(f"\n[ERROR] CSV format error: {e}\n")
        return
    except Exception as e:
        print(f"\n[ERROR] An unexpected error occurred while reading the file: {e}\n")
        return

    if total_rows == 0:
        print("\n[WARNING] CSV header was found, but no data rows were present.\n")
        return

    # 4. Insert valid records into SQLite database using transactions
    try:
        inserted_count, skipped_in_db = database.insert_customers_batch(db_path, valid_records)
    except Exception as e:
        print(f"\n[ERROR] Database insertion failed: {e}\n")
        return

    # Total duplicates skipped = duplicates found within CSV batch + duplicates already existing in SQLite DB
    duplicates_within_csv = error_counts["duplicate_id"]
    total_duplicates_skipped = duplicates_within_csv + skipped_in_db

    # Invalid records rejected = total rows read - successfully valid rows that were inserted or existing
    invalid_rejected = len(rejected_details)

    # 5. Display comprehensive audit report
    report_data = {
        "total_rows_read": total_rows,
        "valid_records": len(valid_records),
        "successfully_inserted": inserted_count,
        "duplicates_skipped": total_duplicates_skipped,
        "invalid_records_rejected": invalid_rejected,
        "error_counts": error_counts,
        "rejected_details": rejected_details,
    }

    reporter.print_import_report(report_data)


def view_all_customers_workflow(db_path: str = DEFAULT_DB_PATH) -> None:
    """Displays all customers currently stored in SQLite."""
    print("\n--- 2. View All Customers ---")
    try:
        database.init_db(db_path)
        records = database.get_all_customers(db_path)
        reporter.print_customers_table(records)
    except Exception as e:
        print(f"\n[ERROR] Could not fetch customers: {e}\n")


def search_customers_workflow(db_path: str = DEFAULT_DB_PATH) -> None:
    """Searches customer records by name or city."""
    print("\n--- 3. Search Customers ---")
    query = input("Enter search term (name or city): ").strip()
    if not query:
        print("[INFO] Search query cannot be empty.\n")
        return

    try:
        database.init_db(db_path)
        results = database.search_customers(query, db_path)
        if not results:
            print(f"\n[INFO] No customers found matching '{query}'.\n")
        else:
            reporter.print_customers_table(results)
    except Exception as e:
        print(f"\n[ERROR] Search operation failed: {e}\n")


def show_statistics_workflow(db_path: str = DEFAULT_DB_PATH) -> None:
    """Displays database metrics and demographics summary."""
    print("\n--- 4. Show Database Statistics ---")
    try:
        database.init_db(db_path)
        stats = database.get_database_stats(db_path)
        reporter.print_database_stats(stats)
    except Exception as e:
        print(f"\n[ERROR] Could not calculate database statistics: {e}\n")


def display_menu() -> None:
    """Displays the main terminal menu options."""
    print("=" * 48)
    print("      DATABRIDGE - CSV Data Cleaner & Importer")
    print("=" * 48)
    print("  1. Import CSV and clean data")
    print("  2. View all customers")
    print("  3. Search customers")
    print("  4. Show database statistics")
    print("  5. Exit")
    print("=" * 48)


def main() -> None:
    """Main application loop."""
    # Ensure database is initialized at application startup
    try:
        database.init_db(DEFAULT_DB_PATH)
    except Exception as e:
        print(f"[WARNING] Database initialization note: {e}")

    while True:
        display_menu()
        choice = input("Select an option (1-5): ").strip()

        if choice == "1":
            import_csv_workflow(DEFAULT_DB_PATH)
        elif choice == "2":
            view_all_customers_workflow(DEFAULT_DB_PATH)
        elif choice == "3":
            search_customers_workflow(DEFAULT_DB_PATH)
        elif choice == "4":
            show_statistics_workflow(DEFAULT_DB_PATH)
        elif choice == "5":
            print("\nThank you for using DataBridge. Goodbye!\n")
            sys.exit(0)
        else:
            print(f"\n[INVALID OPTION] '{choice}' is not valid. Please enter a number between 1 and 5.\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user. Exiting DataBridge...\n")
        sys.exit(0)
