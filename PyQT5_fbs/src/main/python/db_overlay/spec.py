from __future__ import absolute_import
from collections import namedtuple

DbRequestSpec = namedtuple("DbRequestSpec", ["station_key", "station_key_type", "start_yyyymm", "end_yyyymm"])
"""
Lightweight container describing a DB data request.

Attributes:
    station_key (str): Station identifier (e.g., UHSLC code or ID).
    station_key_type (str): Identifier type ("uhslc_code" or "uhslc_id").
    start_yyyymm (int): Start month in YYYYMM format (inclusive).
    end_yyyymm (int): End month in YYYYMM format (inclusive).
"""

def month_span_inclusive(start_yyyymm, end_yyyymm):
    """
    Compute the number of months between two YYYYMM values (inclusive).

    Args:
        start_yyyymm (int): Start month in YYYYMM format.
        end_yyyymm (int): End month in YYYYMM format.

    Returns:
        int: Total number of months including both endpoints.
    """

    sy, sm = divmod(int(start_yyyymm), 100)
    ey, em = divmod(int(end_yyyymm), 100)
    return (ey - sy) * 12 + (em - sm) + 1
