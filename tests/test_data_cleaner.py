"""
test_data_cleaner.py - Unit Tests for DataBridge Cleaning & Validation Logic.

Uses Python's built-in unittest framework.
Covers:
1. Removing extra whitespace from strings.
2. Detecting missing values.
3. Validating email addresses.
4. Validating age constraints.
5. Detecting duplicate customer IDs.

Run using:
    python -m unittest discover -s tests -v
"""

import sys
import os
import unittest

# Ensure the root directory of DataBridge is on sys.path so modules import seamlessly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data_cleaner import (
    clean_text,
    validate_email,
    validate_age,
    is_duplicate_id,
    validate_and_clean_row,
)


class TestDataCleaner(unittest.TestCase):
    """Test suite for data_cleaner module functions."""

    # ---------------------------------------------------------
    # 1. Tests for Removing Extra Spaces
    # ---------------------------------------------------------
    def test_remove_leading_trailing_spaces(self):
        """Test that leading and trailing whitespace is stripped."""
        raw_text = "   Alice Smith   "
        expected = "Alice Smith"
        self.assertEqual(clean_text(raw_text), expected)

    def test_collapse_multiple_internal_spaces(self):
        """Test that multiple spaces between words are collapsed to a single space."""
        raw_text = "John    William     Doe"
        expected = "John William Doe"
        self.assertEqual(clean_text(raw_text), expected)

    def test_clean_text_handles_none_and_empty(self):
        """Test that None and empty strings return an empty string safely."""
        self.assertEqual(clean_text(None), "")
        self.assertEqual(clean_text(""), "")
        self.assertEqual(clean_text("     "), "")

    # ---------------------------------------------------------
    # 2. Tests for Detecting Missing Values
    # ---------------------------------------------------------
    def test_detect_missing_name(self):
        """Test that a row with an empty name is rejected with missing_value category."""
        row = {
            "customer_id": "CUST001",
            "name": "",
            "email": "test@example.com",
            "city": "Boston",
            "age": "25",
        }
        result = validate_and_clean_row(row, seen_ids=set())
        self.assertFalse(result["is_valid"])
        self.assertEqual(result["error_category"], "missing_value")
        self.assertIn("name", result["error_message"])

    def test_detect_missing_email(self):
        """Test that a row with missing email is rejected."""
        row = {
            "customer_id": "CUST002",
            "name": "Bob Martin",
            "email": "   ",  # whitespace only
            "city": "Dallas",
            "age": "30",
        }
        result = validate_and_clean_row(row, seen_ids=set())
        self.assertFalse(result["is_valid"])
        self.assertEqual(result["error_category"], "missing_value")
        self.assertIn("email", result["error_message"])

    def test_detect_missing_city(self):
        """Test that a row missing city is rejected."""
        row = {
            "customer_id": "CUST003",
            "name": "Carol White",
            "email": "carol@example.com",
            "city": "",
            "age": "40",
        }
        result = validate_and_clean_row(row, seen_ids=set())
        self.assertFalse(result["is_valid"])
        self.assertEqual(result["error_category"], "missing_value")

    # ---------------------------------------------------------
    # 3. Tests for Validating Email Addresses
    # ---------------------------------------------------------
    def test_valid_emails(self):
        """Test standard, valid email formats."""
        valid_examples = [
            "user@example.com",
            "first.last@company.org",
            "student+test@univ.edu",
            "john_doe-123@sub.domain.co",
        ]
        for email in valid_examples:
            is_valid, cleaned = validate_email(email)
            self.assertTrue(is_valid, f"Expected '{email}' to be valid.")
            self.assertEqual(cleaned, email.lower())

    def test_invalid_emails(self):
        """Test malformed email formats are flagged as invalid."""
        invalid_examples = [
            "plainaddress",
            "missing-domain@",
            "@missing-username.com",
            "user@domain",        # missing dot in domain
            "user@domain.c",      # could pass or fail, standard regex requires valid domain
            "user name@domain.com",  # spaces inside
            "",
            None,
        ]
        for email in invalid_examples:
            is_valid, _ = validate_email(email)
            self.assertFalse(is_valid, f"Expected '{email}' to be rejected as invalid.")

    # ---------------------------------------------------------
    # 4. Tests for Validating Age
    # ---------------------------------------------------------
    def test_valid_age_values(self):
        """Test reasonable positive integers are accepted and converted."""
        valid_cases = [("25", 25), ("1", 1), ("120", 120), (45, 45)]
        for raw, expected in valid_cases:
            is_valid, age_int = validate_age(raw)
            self.assertTrue(is_valid, f"Expected age '{raw}' to be valid.")
            self.assertEqual(age_int, expected)

    def test_negative_and_zero_age_rejected(self):
        """Test that 0 or negative ages are rejected."""
        self.assertFalse(validate_age("-5")[0])
        self.assertFalse(validate_age("0")[0])
        self.assertFalse(validate_age(-10)[0])

    def test_unrealistic_high_age_rejected(self):
        """Test that age above 120 is rejected."""
        self.assertFalse(validate_age("121")[0])
        self.assertFalse(validate_age("200")[0])

    def test_non_numeric_age_rejected(self):
        """Test that words or non-numeric values for age are rejected."""
        self.assertFalse(validate_age("twenty")[0])
        self.assertFalse(validate_age("abc")[0])
        self.assertFalse(validate_age(None)[0])

    # ---------------------------------------------------------
    # 5. Tests for Detecting Duplicate Customer IDs
    # ---------------------------------------------------------
    def test_detect_duplicate_customer_ids(self):
        """Test duplicate detection in the tracking set."""
        seen = {"CUST001", "CUST002"}
        self.assertFalse(is_duplicate_id("CUST003", seen))
        self.assertTrue(is_duplicate_id("CUST001", seen))

    def test_duplicate_row_rejection_in_batch(self):
        """Test that validate_and_clean_row rejects a previously seen ID."""
        seen_ids = {"CUST100"}
        row = {
            "customer_id": "CUST100",
            "name": "Jane Duplicate",
            "email": "jane@example.com",
            "city": "Denver",
            "age": "28",
        }
        result = validate_and_clean_row(row, seen_ids)
        self.assertFalse(result["is_valid"])
        self.assertEqual(result["error_category"], "duplicate_id")
        self.assertIn("Duplicate customer_id", result["error_message"])

    def test_valid_row_is_cleaned_and_accepted(self):
        """Test that a properly formed row is cleaned and returns valid."""
        seen_ids = set()
        row = {
            "customer_id": "  CUST200  ",
            "name": "  Bruce   Wayne  ",
            "email": "  BRUCE@wayne-enterprises.com  ",
            "city": "  Gotham  ",
            "age": "  35  ",
        }
        result = validate_and_clean_row(row, seen_ids)
        self.assertTrue(result["is_valid"])
        self.assertIsNone(result["error_category"])
        cleaned = result["cleaned_data"]
        self.assertEqual(cleaned["customer_id"], "CUST200")
        self.assertEqual(cleaned["name"], "Bruce Wayne")
        self.assertEqual(cleaned["email"], "bruce@wayne-enterprises.com")
        self.assertEqual(cleaned["city"], "Gotham")
        self.assertEqual(cleaned["age"], 35)


    def test_clean_customer_id_normalization(self):
        """Test that customer ID is stripped and standardized to uppercase."""
        from data_cleaner import clean_customer_id
        is_valid, cleaned_id = clean_customer_id("  cust-101  ")
        self.assertTrue(is_valid)
        self.assertEqual(cleaned_id, "CUST-101")

    def test_invalid_customer_id_format(self):
        """Test that malformed customer IDs with invalid characters are rejected."""
        from data_cleaner import clean_customer_id
        self.assertFalse(clean_customer_id("!")[0])
        self.assertFalse(clean_customer_id("")[0])
        self.assertFalse(clean_customer_id(None)[0])


if __name__ == "__main__":
    unittest.main()
