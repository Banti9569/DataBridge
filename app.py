"""
app.py - Flask Web Application & REST API for DataBridge.

Connects the web frontend to:
1. data_cleaner.py (validation & cleaning rules)
2. database.py (SQLite schema, constraints, queries, and transactions)
"""

import os
import io
import csv
from typing import Dict, Any, List
from flask import Flask, render_template, request, jsonify

import data_cleaner
import database

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CSV_PATH = os.path.join(BASE_DIR, "customers.csv")
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "databridge.db")

# Ensure database and table exist at startup
database.init_db(DEFAULT_DB_PATH)


@app.route("/")
def index():
    """Serves the DataBridge web dashboard."""
    return render_template("index.html")


def process_csv_content(csv_file_stream) -> Dict[str, Any]:
    """
    Parses, cleans, and validates CSV content from an open file or stream,
    inserts clean records into SQLite, and returns a detailed audit report.
    """
    # Use csv.DictReader with utf-8-sig to handle Windows Excel BOM
    reader = csv.DictReader(csv_file_stream)

    if not reader.fieldnames:
        return {
            "success": False,
            "error": "Could not read CSV headers. File may be empty or corrupted."
        }

    clean_headers = [h.strip() for h in reader.fieldnames if h]
    missing_cols = [col for col in data_cleaner.REQUIRED_FIELDS if col not in clean_headers]

    if missing_cols:
        return {
            "success": False,
            "error": f"CSV is missing required column(s): {', '.join(missing_cols)}. Expected schema: {', '.join(data_cleaner.REQUIRED_FIELDS)}"
        }

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

    for row_idx, raw_row in enumerate(reader, start=2):
        total_rows += 1
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
                "category": cat,
                "reason": validation["error_message"]
            })

    if total_rows == 0:
        return {
            "success": False,
            "error": "The CSV file contains headers but no data rows."
        }

    # Insert valid records into SQLite using transactions
    inserted_count, skipped_in_db = database.insert_customers_batch(DEFAULT_DB_PATH, valid_records)

    duplicates_within_csv = error_counts["duplicate_id"]
    total_duplicates_skipped = duplicates_within_csv + skipped_in_db
    invalid_rejected = len(rejected_details)

    report_data = {
        "total_rows_read": total_rows,
        "valid_records": len(valid_records),
        "successfully_inserted": inserted_count,
        "duplicates_skipped": total_duplicates_skipped,
        "invalid_records_rejected": invalid_rejected,
        "error_counts": error_counts,
        "rejected_details": rejected_details,
    }

    return {
        "success": True,
        "report": report_data
    }


@app.route("/api/import", methods=["POST"])
def api_import():
    """
    API endpoint to import and clean CSV data.
    Supports either:
    1. File upload via multipart/form-data (key: 'file')
    2. JSON payload with 'use_sample': true to load customers.csv directly.
    """
    try:
        # Option A: Import sample dataset
        if request.is_json and request.json.get("use_sample"):
            if not os.path.isfile(DEFAULT_CSV_PATH):
                return jsonify({"success": False, "error": "Sample file customers.csv not found on server."}), 404

            with open(DEFAULT_CSV_PATH, mode="r", encoding="utf-8-sig", newline="") as f:
                result = process_csv_content(f)
            return jsonify(result)

        # Option B: Uploaded file
        if "file" in request.files:
            uploaded_file = request.files["file"]
            if uploaded_file.filename == "":
                return jsonify({"success": False, "error": "No file was selected."}), 400

            # Read content from file buffer as text
            content_str = uploaded_file.read().decode("utf-8-sig", errors="replace")
            stream = io.StringIO(content_str)
            result = process_csv_content(stream)
            return jsonify(result)

        return jsonify({"success": False, "error": "Invalid request. Please upload a CSV file or request sample import."}), 400

    except Exception as e:
        return jsonify({"success": False, "error": f"Import operation failed: {str(e)}"}), 500


@app.route("/api/customers", methods=["GET"])
def api_customers():
    """API endpoint to get all customer records."""
    try:
        customers = database.get_all_customers(DEFAULT_DB_PATH)
        return jsonify({"success": True, "customers": customers})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/search", methods=["GET"])
def api_search():
    """API endpoint to search customers by name or city."""
    query = request.args.get("q", "").strip()
    try:
        if not query:
            results = database.get_all_customers(DEFAULT_DB_PATH)
        else:
            results = database.search_customers(query, DEFAULT_DB_PATH)
        return jsonify({"success": True, "customers": results, "query": query})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/stats", methods=["GET"])
def api_stats():
    """API endpoint to fetch aggregated database statistics."""
    try:
        stats = database.get_database_stats(DEFAULT_DB_PATH)
        return jsonify({"success": True, "stats": stats})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/reset", methods=["POST"])
def api_reset():
    """API endpoint to reset/clear customer data (helpful for testing and demos)."""
    try:
        with database.get_connection(DEFAULT_DB_PATH) as conn:
            conn.execute("DELETE FROM customers;")
            conn.commit()
        return jsonify({"success": True, "message": "Database table has been reset successfully."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/query", methods=["POST"])
def api_query():
    """API endpoint to execute safe read-only SQL queries from the Web SQL Console."""
    try:
        data = request.get_json() or {}
        query = data.get("query", "").strip()
        result = database.execute_custom_query(query, DEFAULT_DB_PATH)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/schema", methods=["GET"])
def api_schema():
    """API endpoint to retrieve table schema metadata and SQLite health diagnostics."""
    try:
        schema = database.get_schema_info(DEFAULT_DB_PATH)
        health = database.get_database_health(DEFAULT_DB_PATH)
        return jsonify({"success": True, "schema": schema, "health": health})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/export/csv", methods=["GET"])
def api_export_csv():
    """Exports all stored clean customers as a downloadable CSV file."""
    from flask import Response
    try:
        customers = database.get_all_customers(DEFAULT_DB_PATH)
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=["customer_id", "name", "email", "city", "age", "imported_at"]
        )
        writer.writeheader()
        for row in customers:
            writer.writerow(row)

        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=cleaned_customers.csv"}
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/export/json", methods=["GET"])
def api_export_json():
    """Exports all stored clean customers as a downloadable formatted JSON file."""
    from flask import Response
    import json
    try:
        customers = database.get_all_customers(DEFAULT_DB_PATH)
        json_str = json.dumps(customers, indent=2)
        return Response(
            json_str,
            mimetype="application/json",
            headers={"Content-Disposition": "attachment; filename=cleaned_customers.json"}
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    # Host on localhost:5000 in debug mode for local development
    print("=" * 60)
    print("  DataBridge Web Server Starting...")
    print("  Open your browser at: http://127.0.0.1:5000")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5000, debug=True)

