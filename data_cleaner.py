"""
data_cleaner.py - Data Cleaning and Validation Module for DataBridge.

This module contains pure, reusable helper functions for:
1. Removing extra whitespace from strings.
2. Detecting missing required values.
3. Validating email addresses.
4. Validating age values.
5. Detecting duplicate customer IDs.
"""

import re
from typing import Tuple, Optional, Dict, Any, Set

# Regular expression pattern for simple, robust email validation
# Matches: username @ domain_name . top_level_domain (e.g., user@example.com)
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$")

# Reasonable age boundaries for customer data
MIN_AGE = 1
MAX_AGE = 120

# List of mandatory columns for customer data
REQUIRED_FIELDS = ("customer_id", "name", "email", "city", "age")


def clean_text(value: Optional[str]) -> str:
    """
    Remove leading and trailing whitespace, and collapse multiple consecutive
    internal spaces into a single space.
    
    Example:
        clean_text("   John    Doe   ") -> "John Doe"
        clean_text(None) -> ""
    """
    if value is None:
        return ""
    # Strip leading/trailing spaces and normalize internal whitespace
    return " ".join(str(value).strip().split())


def validate_email(email: Optional[str]) -> Tuple[bool, str]:
    """
    Validate that an email string is well-formed.
    
    Returns:
        (is_valid, cleaned_email_or_empty)
    """
    cleaned = clean_text(email).lower()
    if not cleaned:
        return False, ""
    
    if EMAIL_REGEX.match(cleaned):
        return True, cleaned
    return False, cleaned


def validate_age(age_value: Any) -> Tuple[bool, Optional[int]]:
    """
    Validate that age is an integer within a reasonable human range [1, 120].
    
    Returns:
        (is_valid, age_as_int_or_None)
    """
    if age_value is None:
        return False, None

    cleaned_str = clean_text(str(age_value))
    if not cleaned_str:
        return False, None

    try:
        age_int = int(cleaned_str)
        if MIN_AGE <= age_int <= MAX_AGE:
            return True, age_int
        return False, None
    except ValueError:
        # String could not be converted to an integer (e.g., "twenty", "abc")
        return False, None


# Regular expression pattern for customer ID validation
# Matches: 2-30 alphanumeric characters, hyphens, or underscores (e.g., CUST101, CUST-102)
CUSTOMER_ID_REGEX = re.compile(r"^[A-Za-z0-9_-]{2,30}$")


def clean_customer_id(customer_id: Optional[str]) -> Tuple[bool, str]:
    """
    Cleans, standardizes to uppercase, and validates customer_id.
    Accepts alphanumeric identifiers, hyphens, and underscores between 2 and 30 characters.
    
    Example:
        clean_customer_id("  cust-101  ") -> (True, "CUST-101")
        clean_customer_id("x") -> (False, "X")
    """
    cleaned = clean_text(customer_id).upper()
    if not cleaned:
        return False, ""
    if CUSTOMER_ID_REGEX.match(cleaned):
        return True, cleaned
    return False, cleaned


def is_duplicate_id(customer_id: str, seen_ids: Set[str]) -> bool:
    """
    Check if a customer_id has already been seen in the current batch (case-insensitive).
    """
    cid = clean_text(customer_id).upper()
    return any(clean_text(s).upper() == cid for s in seen_ids)


def validate_and_clean_row(
    raw_row: Dict[str, Any],
    seen_ids: Set[str]
) -> Dict[str, Any]:
    """
    Validates and cleans a single customer record dictionary.

    Args:
        raw_row: Dictionary representing a CSV row.
        seen_ids: Set of customer IDs already encountered in the current import.

    Returns:
        A dictionary with the structure:
        {
            "is_valid": bool,
            "cleaned_data": Optional[Dict[str, Any]],
            "error_category": Optional[str], # 'missing_value', 'invalid_id', 'invalid_email', 'invalid_age', 'duplicate_id'
            "error_message": Optional[str]
        }
    """
    # 1. Check for missing required fields
    for field in REQUIRED_FIELDS:
        val = raw_row.get(field)
        cleaned_val = clean_text(val)
        if not cleaned_val:
            return {
                "is_valid": False,
                "cleaned_data": None,
                "error_category": "missing_value",
                "error_message": f"Required field '{field}' is missing or empty."
            }

    # Extract and clean fields
    name = clean_text(raw_row.get("name"))
    raw_email = raw_row.get("email")
    city = clean_text(raw_row.get("city"))
    raw_age = raw_row.get("age")

    # 2. Validate and standardize customer_id
    id_valid, standardized_id = clean_customer_id(raw_row.get("customer_id"))
    if not id_valid:
        return {
            "is_valid": False,
            "cleaned_data": None,
            "error_category": "invalid_id",
            "error_message": f"Invalid customer_id format: '{raw_row.get('customer_id')}'. Expected alphanumeric identifier (e.g. CUST101)."
        }

    # 3. Check for duplicate customer_id within the batch
    if is_duplicate_id(standardized_id, seen_ids):
        return {
            "is_valid": False,
            "cleaned_data": None,
            "error_category": "duplicate_id",
            "error_message": f"Duplicate customer_id '{standardized_id}' detected in import batch."
        }

    # 3. Validate email
    email_valid, cleaned_email = validate_email(raw_email)
    if not email_valid:
        return {
            "is_valid": False,
            "cleaned_data": None,
            "error_category": "invalid_email",
            "error_message": f"Invalid email format: '{raw_email}'."
        }

    # 4. Validate age
    age_valid, cleaned_age = validate_age(raw_age)
    if not age_valid:
        return {
            "is_valid": False,
            "cleaned_data": None,
            "error_category": "invalid_age",
            "error_message": f"Invalid age: '{raw_age}'. Must be an integer between {MIN_AGE} and {MAX_AGE}."
        }

    # Record is completely valid
    cleaned_record = {
        "customer_id": standardized_id,
        "name": name,
        "email": cleaned_email,
        "city": city,
        "age": cleaned_age
    }

    return {
        "is_valid": True,
        "cleaned_data": cleaned_record,
        "error_category": None,
        "error_message": None
    }
