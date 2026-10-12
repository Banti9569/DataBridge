"""
database.py - SQLite Database Management Module for DataBridge.

This module handles:
1. Automatic database and table initialization with schema constraints.
2. Parameterized SQL queries to prevent SQL injection vulnerabilities.
3. Safe insertion of customer records using transactions.
4. Duplicate checking against existing database records.
5. Querying records (view all, search by name or city).
6. Aggregating database statistics.
"""

import sqlite3
import os
from typing import List, Dict, Any, Tuple, Optional

DEFAULT_DB_FILE = "databridge.db"


def get_connection(db_path: str = DEFAULT_DB_FILE) -> sqlite3.Connection:
    """
    Establish and return a connection to the SQLite database.
    Sets row_factory to sqlite3.Row so query results can be accessed like dictionaries.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    # Enable foreign key support and ensure WAL mode for better concurrency if needed
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: str = DEFAULT_DB_FILE) -> None:
    """
    Automatically creates the 'customers' table if it does not already exist.
    Uses SQL constraints:
      - customer_id: PRIMARY KEY (ensures uniqueness and indexes IDs)
      - name, email, city, age: NOT NULL (ensures data completeness)
      - age: CHECK constraint (ensures reasonable age bounds)
      - imported_at: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """
    create_table_query = """
    CREATE TABLE IF NOT EXISTS customers (
        customer_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        city TEXT NOT NULL,
        age INTEGER NOT NULL CHECK(age >= 1 AND age <= 120),
        imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    try:
        with get_connection(db_path) as conn:
            conn.execute(create_table_query)
            conn.commit()
    except sqlite3.Error as e:
        raise RuntimeError(f"Database initialization failed: {e}") from e


def customer_exists(conn: sqlite3.Connection, customer_id: str) -> bool:
    """
    Check if a customer with the given ID already exists in the database.
    Uses parameterized SQL to prevent injection.
    """
    query = "SELECT 1 FROM customers WHERE customer_id = ? LIMIT 1;"
    cursor = conn.cursor()
    cursor.execute(query, (customer_id,))
    return cursor.fetchone() is not None


def insert_customer(conn: sqlite3.Connection, customer: Dict[str, Any]) -> bool:
    """
    Insert a single customer record using parameterized SQL.
    Returns True if inserted successfully, False if already exists (IntegrityError).
    """
    insert_query = """
    INSERT INTO customers (customer_id, name, email, city, age)
    VALUES (?, ?, ?, ?, ?);
    """
    try:
        cursor = conn.cursor()
        cursor.execute(
            insert_query,
            (
                customer["customer_id"],
                customer["name"],
                customer["email"],
                customer["city"],
                customer["age"],
            ),
        )
        return True
    except sqlite3.IntegrityError:
        # Unique constraint on customer_id violated
        return False


def insert_customers_batch(
    db_path: str, customers: List[Dict[str, Any]]
) -> Tuple[int, int]:
    """
    Inserts a list of cleaned customer records into the database within a transaction.
    
    Returns:
        (inserted_count, skipped_duplicates_in_db)
    """
    inserted = 0
    skipped_duplicates = 0

    if not customers:
        return inserted, skipped_duplicates

    conn = get_connection(db_path)
    try:
        # SQLite transaction begins automatically
        for cust in customers:
            if customer_exists(conn, cust["customer_id"]):
                skipped_duplicates += 1
            else:
                success = insert_customer(conn, cust)
                if success:
                    inserted += 1
                else:
                    skipped_duplicates += 1
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        raise RuntimeError(f"Database transaction error during batch insert: {e}") from e
    finally:
        conn.close()

    return inserted, skipped_duplicates


def get_all_customers(db_path: str = DEFAULT_DB_FILE) -> List[Dict[str, Any]]:
    """
    Retrieve all customer records from the SQLite database ordered by customer_id.
    """
    query = """
    SELECT customer_id, name, email, city, age, imported_at
    FROM customers
    ORDER BY customer_id ASC;
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def search_customers(keyword: str, db_path: str = DEFAULT_DB_FILE) -> List[Dict[str, Any]]:
    """
    Search customers by name or city using case-insensitive LIKE queries.
    Keyword search is parameterized to prevent SQL injection.
    """
    query = """
    SELECT customer_id, name, email, city, age, imported_at
    FROM customers
    WHERE LOWER(name) LIKE LOWER(?) OR LOWER(city) LIKE LOWER(?)
    ORDER BY customer_id ASC;
    """
    search_param = f"%{keyword.strip()}%"
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query, (search_param, search_param))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_database_stats(db_path: str = DEFAULT_DB_FILE) -> Dict[str, Any]:
    """
    Calculate and return key statistics about stored customers.
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        # Total record count
        cursor.execute("SELECT COUNT(*) AS total FROM customers;")
        total_customers = cursor.fetchone()["total"]

        if total_customers == 0:
            return {
                "total_customers": 0,
                "unique_cities": 0,
                "average_age": 0.0,
                "min_age": 0,
                "max_age": 0,
                "city_breakdown": [],
            }

        # Unique cities count
        cursor.execute("SELECT COUNT(DISTINCT city) AS unique_cities FROM customers;")
        unique_cities = cursor.fetchone()["unique_cities"]

        # Age statistics
        cursor.execute("SELECT AVG(age) AS avg_age, MIN(age) AS min_age, MAX(age) AS max_age FROM customers;")
        age_row = cursor.fetchone()
        avg_age = round(age_row["avg_age"], 1) if age_row["avg_age"] else 0.0
        min_age = age_row["min_age"] if age_row["min_age"] else 0
        max_age = age_row["max_age"] if age_row["max_age"] else 0

        # Top cities by customer count
        cursor.execute(
            """
            SELECT city, COUNT(*) AS count
            FROM customers
            GROUP BY city
            ORDER BY count DESC, city ASC
            LIMIT 5;
            """
        )
        city_rows = cursor.fetchall()
        city_breakdown = [{"city": r["city"], "count": r["count"]} for r in city_rows]

        return {
            "total_customers": total_customers,
            "unique_cities": unique_cities,
            "average_age": avg_age,
            "min_age": min_age,
            "max_age": max_age,
            "city_breakdown": city_breakdown,
        }


def execute_custom_query(query: str, db_path: str = DEFAULT_DB_FILE) -> Dict[str, Any]:
    """
    Executes a safe read-only SQL query submitted via the web SQL Console.
    Rejects mutation statements (DROP, DELETE, UPDATE, INSERT, ALTER) to protect data integrity.
    """
    import time

    cleaned_query = query.strip()
    if not cleaned_query:
        return {"success": False, "error": "Query cannot be empty."}

    # Restrict to read-only queries for web console safety
    first_word = cleaned_query.split()[0].upper()
    allowed_verbs = ("SELECT", "PRAGMA", "EXPLAIN", "WITH")
    if first_word not in allowed_verbs:
        return {
            "success": False,
            "error": f"Security restriction: Only read-only queries ({', '.join(allowed_verbs)}) are permitted in the web console."
        }

    start_time = time.perf_counter()
    try:
        with get_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(cleaned_query)
            
            # Fetch column names
            columns = [col[0] for col in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            row_dicts = [dict(row) for row in rows]
            execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return {
                "success": True,
                "columns": columns,
                "rows": row_dicts,
                "row_count": len(row_dicts),
                "execution_time_ms": execution_time_ms
            }
    except sqlite3.Error as e:
        return {
            "success": False,
            "error": f"SQL Error: {str(e)}"
        }


def get_schema_info(db_path: str = DEFAULT_DB_FILE) -> List[Dict[str, Any]]:
    """
    Returns column metadata for the 'customers' table using PRAGMA table_info.
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(customers);")
        rows = cursor.fetchall()
        return [
            {
                "cid": row["cid"],
                "name": row["name"],
                "type": row["type"],
                "notnull": bool(row["notnull"]),
                "dflt_value": row["dflt_value"],
                "pk": bool(row["pk"]),
            }
            for row in rows
        ]


def get_database_health(db_path: str = DEFAULT_DB_FILE) -> Dict[str, Any]:
    """
    Inspects physical database file size and executes SQLite PRAGMA integrity_check.
    """
    size_bytes = os.path.getsize(db_path) if os.path.exists(db_path) else 0
    size_kb = round(size_bytes / 1024, 2)

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        integrity = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) AS total FROM customers;")
        total = cursor.fetchone()["total"]

    return {
        "file_path": db_path,
        "file_size_kb": size_kb,
        "integrity_status": integrity,
        "total_records": total
    }

