"""
Input validators for API query parameters.

Centralized validation logic to ensure consistent input handling across all endpoints.

## Case Normalization Behavior

The validators in this module perform automatic case normalization:

- **Legislatures**: Normalized to uppercase (e.g., 'l17' → 'L17', 'L17' → 'L17')
- **Party abbreviations**: Normalized to uppercase (e.g., 'ps' → 'PS', 'PS' → 'PS')

This allows API clients to use case-insensitive parameters for user convenience
while maintaining consistent internal representations.

## Example

```python
# All of these are valid and normalized to 'L17':
validate_legislatura('L17')  # → 'L17'
validate_legislatura('l17')  # → 'L17'
validate_legislatura('L17')  # → 'L17'

# All of these are valid and normalized to 'PS':
validate_partido('PS')   # → 'PS'
validate_partido('ps')   # → 'PS'
validate_partido('Ps')   # → 'PS'
```
"""

import re
from fastapi import HTTPException
from typing import Optional


# Legislature format pattern (L followed by digits, typically L15, L16, L17)
LEGISLATURE_PATTERN = re.compile(r'^L\d{1,3}$')

# Party abbreviation pattern (2-10 uppercase letters/numbers, e.g., PS, PSD, CH)
PARTY_PATTERN = re.compile(r'^[A-Z0-9]{2,10}$')

# Known valid legislatures (can be extended as new data becomes available)
VALID_LEGISLATURES = {'L15', 'L16', 'L17'}


def validate_legislatura(value: Optional[str]) -> Optional[str]:
    """
    Validate legislature parameter format.

    Args:
        value: Legislature string (e.g., 'L15', 'L16', 'L17')

    Returns:
        Uppercase normalized legislature string

    Raises:
        HTTPException: If format is invalid
    """
    if value is None:
        return None

    # Normalize to uppercase
    value = value.upper()

    # Check format
    if not LEGISLATURE_PATTERN.match(value):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid legislature format: '{value}'. Expected format: L<number> (e.g., L15, L16, L17)"
        )

    # Warn if not in known set (but allow it for future legislatures)
    if value not in VALID_LEGISLATURES:
        # Just normalize, don't reject - allows for future legislatures
        pass

    return value


def validate_partido(value: Optional[str]) -> Optional[str]:
    """
    Validate party abbreviation format.

    Args:
        value: Party abbreviation string (e.g., 'PS', 'PSD', 'CH')

    Returns:
        Uppercase normalized party abbreviation

    Raises:
        HTTPException: If format is invalid
    """
    if value is None:
        return None

    # Normalize to uppercase
    value = value.upper()

    # Check format
    if not PARTY_PATTERN.match(value):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid party abbreviation: '{value}'. Expected 2-10 uppercase letters/numbers (e.g., PS, PSD, CH)"
        )

    return value


def validate_pagination(limit: int, offset: int, max_limit: int = 500) -> tuple[int, int]:
    """
    Validate pagination parameters.

    Args:
        limit: Number of records to return
        offset: Number of records to skip
        max_limit: Maximum allowed limit

    Returns:
        Tuple of (validated_limit, validated_offset)

    Raises:
        HTTPException: If parameters are invalid
    """
    # Validate limit
    if limit < 1:
        raise HTTPException(
            status_code=400,
            detail="Limit must be at least 1"
        )

    if limit > max_limit:
        raise HTTPException(
            status_code=400,
            detail=f"Limit cannot exceed {max_limit}"
        )

    # Validate offset
    if offset < 0:
        raise HTTPException(
            status_code=400,
            detail="Offset cannot be negative"
        )

    # Check for unreasonably large offsets (potential abuse)
    if offset > 100000:
        raise HTTPException(
            status_code=400,
            detail="Offset too large. Please use more specific filters to narrow your search."
        )

    return limit, offset
