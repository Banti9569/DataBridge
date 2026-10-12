# DataBridge — CSV Data Cleaner & Importer

A beginner-friendly, production-grade **Data Integration (ETL) pipeline** built in pure Python.

DataBridge extracts raw customer records from CSV files, cleans and validates the data against enterprise business rules, loads verified records into an **SQLite** relational database with strict constraints and transactions, and generates comprehensive audit reports.

---

## Table of Contents
1. [Project Introduction](#project-introduction)
2. [Problem Statement](#problem-statement)
3. [Features](#features)
4. [Technologies Used](#technologies-used)
5. [Project Structure](#project-structure)
6. [Sample CSV Format](#sample-csv-format)
7. [Installation & Setup (Windows 11)](#installation--setup-windows-11)
8. [How to Run the Application](#how-to-run-the-application)
9. [How to Run Automated Tests](#how-to-run-automated-tests)
10. [Example Terminal Output](#example-terminal-output)
11. [SQL Concepts Demonstrated](#sql-concepts-demonstrated)
12. [Future Improvements](#future-improvements)

---

## Project Introduction

In modern data architecture, real-world data is dirty. Upstream user inputs frequently contain extra whitespace, malformed emails, unrealistic numeric values, missing fields, and duplicate IDs. 

**DataBridge** was built by a Computer Science & AIML student preparing for **Data Integration (DI) Engineer** roles. It mirrors core industry ETL (Extract, Transform, Load) pipelines using Python's standard library.

---

## Problem Statement

When loading customer data into a relational database:
- **Direct import without validation leads to database corruption** (e.g., negative ages, empty names, malformed emails).
- **SQL Injection risks arise** if input strings are directly concatenated into queries.
- **Duplicate records cause key collision errors** or corrupt downstream analytics.
- **Lack of auditability prevents engineers from understanding why rows failed.**

**DataBridge solves this** by validating data in-memory, maintaining a strict audit trail, skipping duplicate keys safely, and guaranteeing database integrity with transactions and parameterized queries.

---

## Features

- **CSV Ingestion (Extract)**:
  - Safely parses CSV files using `csv.DictReader` with `utf-8-sig` encoding (resilient to Windows Excel UTF-8 BOM).
  - Validates CSV headers and rejects malformed files before database operations.
  
- **Data Cleaning & Validation (Transform)**:
  - **Standardized Customer ID**: Normalizes IDs to uppercase, strips whitespace, validates alphanumeric formatting (2–30 chars), and provides interactive 1-click clipboard copying.
  - **Whitespace Normalization**: Automatically strips leading/trailing spaces and collapses redundant internal spaces.
  - **Missing Value Detection**: Rejects records with blank or missing required fields (`customer_id`, `name`, `email`, `city`, `age`).
  - **Email Format Validation**: Verifies email structure with RFC-compliant regex (`user@domain.ext`).
  - **Age Validation**: Ensures age is a positive integer between 1 and 120.
  - **Batch Duplicate Detection**: Catches duplicate `customer_id` values within the import batch.
  
- **SQLite Relational Storage (Load)**:
  - Automatically initializes `databridge.db` and the `customers` table.
  - Uses **parameterized queries (`?`)** to eliminate SQL injection.
  - Uses **SQL constraints** (`PRIMARY KEY`, `NOT NULL`, `CHECK`).
  - Implements **transactions** (`commit` / `rollback`) to ensure atomic operations.
  - Skips existing database records without crashing.

- **Web Dashboard & SQL Console**:
  - **Drag-and-Drop Ingestion**: Ingest custom CSV files or 1-click test with sample data.
  - **Interactive SQL Query Console**: Run arbitrary read-only queries with millisecond execution metrics.
  - **Database Schema Inspector**: Live table DDL constraints and SQLite file integrity checks.
  - **Clean Data Export**: 1-click export of verified database records to **CSV** and **JSON**.
  - **Demographics & Analytics**: Live search, age statistics, and dynamic city distribution bar charts.

- **Dual-Mode Execution**:
  - **Web Dashboard**: Modern glassmorphic dark-mode web application (`python app.py`).
  - **Terminal CLI**: Fast interactive menu interface (`python main.py`).

---

## Technologies Used

- **Python 3.8+** (Standard Library only — zero external pip dependencies)
- **`csv`**: Structured file parsing with dialect handling.
- **`sqlite3`**: Embedded ACID-compliant relational database.
- **`re`**: Regular expression validation.
- **`unittest`**: Built-in test automation framework.
- **`os` & `sys`**: Windows-compatible filesystem path handling.

---

## Project Structure

```
DataBridge/
├── app.py                  # Flask Web Server & REST API
├── templates/
│   └── index.html          # Modern dark-mode ETL web dashboard
├── static/
│   ├── css/
│   │   └── style.css       # Design system, glassmorphism, responsive styles
│   └── js/
│       └── app.js          # Drag-and-drop upload, live search, dynamic charts
├── main.py                 # Terminal interactive menu CLI interface
├── data_cleaner.py         # Pure functions for whitespace, regex, age, and duplicate validation
├── database.py             # SQLite connection, schema, transactions, and parameterized queries
├── reporter.py             # Terminal tables, audit report, and metrics dashboard
├── customers.csv           # Sample dataset with clean, messy, and invalid records
├── requirements.txt        # Dependency documentation (Flask)
├── README.md               # Comprehensive project documentation
├── .gitignore              # Ignores SQLite databases, cache, and virtual environments
└── tests/
    ├── __init__.py         # Package marker for unit testing
    └── test_data_cleaner.py # Automated unit tests for all validation rules
```

---

## Sample CSV Format

The project includes `customers.csv` containing realistic test cases:

```csv
customer_id,name,email,city,age
CUST101,John Doe,john.doe@example.com,New York,29
CUST102,  Jane Smith  ,jane.smith@email.com, Los Angeles ,34
CUST103,Michael Brown,michael.brown@sample.org,Chicago,42
CUST104,Emily Davis,,Houston,25
CUST105,Robert Johnson,robert.j@domain,Phoenix,38
CUST106,Sarah Wilson,sarah.w@techco.com,Philadelphia,28
CUST107,David Miller,david.m@webmail.net,San Antonio,-5
CUST108,,alex.turner@cloud.io,San Diego,31
CUST109,Lisa Anderson,lisa.anderson@example.com,Dallas,150
CUST110,James Thomas,james.t@corp.net,San Jose,45
CUST103,Michael Duplicate,duplicate.michael@sample.org,Chicago,42
CUST111,Patricia Jackson,patricia.j@domain.org,Austin,52
CUST112,  Christopher White  , chris.white@gmail.com , Seattle , 27 
CUST113,Amanda Harris,amanda.harris@company.com,,33
CUST114,Daniel Martin,daniel.martin_not_an_email,Denver,40
CUST115,Elizabeth Clark,elizabeth.c@network.org,Boston,twenty
CUST116,Kevin Lewis,kevin.lewis@startup.co,Miami,36
CUST117,Rachel Walker,rachel.w@domain.com,Atlanta,29
```

---

## Installation & Setup (Windows 11)

Open **PowerShell** in Windows 11 and follow these steps:

### Step 1: Navigate to the project directory
```powershell
cd "c:\Users\hazip\OneDrive\Desktop\All Project\Databridge"
```

### Step 2: Create a virtual environment
```powershell
python -m venv venv
```

### Step 3: Activate the virtual environment
```powershell
.\venv\Scripts\Activate.ps1
```
*(Note: If PowerShell shows an Execution Policy error, run `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` once and re-run the activate command).*

### Step 4: Install dependencies
```powershell
pip install -r requirements.txt
```

---

## How to Run the Application

You can run DataBridge in **two modes**:

### Mode A: Interactive Web Dashboard (Recommended for Demos)
```powershell
python app.py
```
Open your browser and navigate to:
👉 **`http://127.0.0.1:5000`**

Features on the web dashboard:
- **Drag-and-Drop CSV Uploader**: Ingest any `.csv` file directly.
- **1-Click Sample Ingestion**: Test the pipeline with `customers.csv`.
- **Live Audit Cards**: Displays read, valid, inserted, duplicates, and rejections.
- **Detailed Rejection Log**: Shows exact line numbers and reasons for failed rows.
- **Database Explorer**: Instant, debounced search by customer name or city.
- **Demographics & Charts**: Interactive city distribution chart and age metrics.
- **Reset Database**: One-click wipe for repeated testing.

### Mode B: Terminal Interactive Menu (CLI)
```powershell
python main.py
```
Follow the terminal menu options (1–5).

---

## How to Run Automated Tests

To run the comprehensive unit test suite:

```powershell
python -m unittest discover -s tests -v
```

Expected output:
```
test_collapse_multiple_internal_spaces (test_data_cleaner.TestDataCleaner) ... ok
test_clean_text_handles_none_and_empty (test_data_cleaner.TestDataCleaner) ... ok
test_detect_duplicate_customer_ids (test_data_cleaner.TestDataCleaner) ... ok
test_detect_missing_city (test_data_cleaner.TestDataCleaner) ... ok
test_detect_missing_email (test_data_cleaner.TestDataCleaner) ... ok
test_detect_missing_name (test_data_cleaner.TestDataCleaner) ... ok
test_duplicate_row_rejection_in_batch (test_data_cleaner.TestDataCleaner) ... ok
test_invalid_emails (test_data_cleaner.TestDataCleaner) ... ok
test_negative_and_zero_age_rejected (test_data_cleaner.TestDataCleaner) ... ok
test_non_numeric_age_rejected (test_data_cleaner.TestDataCleaner) ... ok
test_remove_leading_trailing_spaces (test_data_cleaner.TestDataCleaner) ... ok
test_unrealistic_high_age_rejected (test_data_cleaner.TestDataCleaner) ... ok
test_valid_age_values (test_data_cleaner.TestDataCleaner) ... ok
test_valid_emails (test_data_cleaner.TestDataCleaner) ... ok
test_valid_row_is_cleaned_and_accepted (test_data_cleaner.TestDataCleaner) ... ok

----------------------------------------------------------------------
Ran 15 tests in 0.005s

OK
```

---

## Example Terminal Output

### Import & Audit Report:
```
====================================================================
              DATABRIDGE IMPORT & CLEANING AUDIT REPORT              
====================================================================
  • Total Rows Read from File:            18
  • Valid Records Identified:             10
  • Successfully Inserted into DB:        10
  • Duplicate Records Skipped:             1
  • Invalid Records Rejected:              8

--------------------------------------------------------------------
  ERROR BREAKDOWN BY CATEGORY
--------------------------------------------------------------------
  - Missing-value errors:                  3
  - Invalid-email errors:                  2
  - Invalid-age errors:                    3
  - Duplicate-ID errors (in batch):        1

--------------------------------------------------------------------
  REJECTED ROWS LOG (Audit Trail)
--------------------------------------------------------------------
  Row #   | Customer ID   | Reason                                    
  ----------------------------------------------------------------
  5       | CUST104       | Required field 'email' is missing or em...
  6       | CUST105       | Invalid email format: 'robert.j@domain'.  
  8       | CUST107       | Invalid age: '-5'. Must be an integer b...
  9       | MISSING       | Required field 'name' is missing or emp...
  10      | CUST109       | Invalid age: '150'. Must be an integer ...
  12      | CUST103       | Duplicate customer_id 'CUST103' detecte...
  15      | CUST113       | Required field 'city' is missing or emp...
  16      | CUST114       | Invalid email format: 'daniel.martin_no...
  17      | CUST115       | Invalid age: 'twenty'. Must be an integ...
====================================================================
```

---

## SQL Concepts Demonstrated

1. **DDL (Data Definition Language)**:
   - `CREATE TABLE IF NOT EXISTS`: Idempotent schema initialization.
   - `PRIMARY KEY`: Unique identifier enforcing entity integrity on `customer_id`.
   - `NOT NULL`: Ensures no empty fields enter critical database columns.
   - `CHECK(age >= 1 AND age <= 120)`: Declarative domain constraint.
   - `DEFAULT CURRENT_TIMESTAMP`: Tracks ingestion time without manual input.

2. **DML (Data Manipulation Language)**:
   - `INSERT INTO customers (customer_id, name, email, city, age) VALUES (?, ?, ?, ?, ?)`:
     Parameterized queries preventing **SQL Injection**.

3. **Transaction Control**:
   - `conn.commit()` and `conn.rollback()` ensuring all-or-nothing atomicity.

4. **DQL (Data Query Language) & Aggregation**:
   - `SELECT COUNT(*)`, `AVG(age)`, `MIN(age)`, `MAX(age)`
   - `GROUP BY city ORDER BY count DESC`
   - `LIKE` queries with wildcards (`%`) for pattern matching.

---

## Future Improvements

- Add export feature to save audit reports as JSON or CSV log files.
- Add support for JSON and Parquet input file formats.
- Integrate logging module with log rotation for enterprise telemetry.
- Support scheduled batch imports using Windows Task Scheduler or cron.
