from __future__ import absolute_import

import os
import re
import logging

from .spec import DbRequestSpec

from uhslc_station_tools.utils import derive_full_year_from_yy

LOG = logging.getLogger(__name__)

_RE_S = re.compile(r"^s([A-Za-z0-9]{4})(\d{2})(\d{2})\.dat$", re.IGNORECASE)
_RE_T = re.compile(r"^t(\d{3})(\d{2})(\d{2})\.dat$", re.IGNORECASE)


def _yyyymm_from_yy_mm(yy, mm):
    """
    Convert two-digit year and month strings into an integer YYYYMM.

    Assumes YY is in the range 00–99 and maps to 2000–2099.

    Args:
        yy (str): Two-digit year string.
        mm (str): Two-digit month string.

    Returns:
        int: Year-month in YYYYMM format.
    """

    year = derive_full_year_from_yy(int(yy))
    month = int(mm)

    return year * 100 + month


def _parse_one_filename(path):
    """
    Parse a data filename to extract station identifier and YYYYMM.

    Supports:
        - sXXXXYYMM.dat  → UHSLC code (4-character station key)
        - tNNNYYMM.dat   → UHSLC numeric ID (3-digit station key)

    Args:
        path (str): Full file path.

    Returns:
        tuple:
            station_key (str or None),
            station_key_type (str or None),
            yyyymm (int or None)
    """

    base = os.path.basename(path).strip()

    m = _RE_S.match(base)
    if m:
        station_key = m.group(1)
        yy = m.group(2)
        mm = m.group(3)
        return station_key, "uhslc_code", _yyyymm_from_yy_mm(yy, mm)

    m = _RE_T.match(base)
    if m:
        station_key = m.group(1)  # "003"
        yy = m.group(2)
        mm = m.group(3)
        return station_key, "uhslc_id", _yyyymm_from_yy_mm(yy, mm)

    return None, None, None


def build_db_request_spec(station_obj=None, file_path=None, file_paths=None):
    """
    Build a DbRequestSpec for DB overlay based on selected file(s).

    Extracts station identifier and month range from filenames and
    ensures all files correspond to the same station.

    Args:
        station_obj: Unused placeholder for future expansion.
        file_path (str, optional): Single file path.
        file_paths (list[str], optional): Multiple file paths.

    Returns:
        DbRequestSpec or None:
            Specification containing station key, key type,
            start YYYYMM, and end YYYYMM, or None if parsing fails.
    """

    paths = []
    if file_paths:
        paths = list(file_paths)
    elif file_path:
        paths = [file_path]

    if not paths:
        return None

    parsed = []
    for p in paths:
        key, key_type, yyyymm = _parse_one_filename(p)
        if key and key_type and yyyymm:
            parsed.append((key, key_type, yyyymm))
        else:
            LOG.warning("DB overlay: filename did not match expected pattern: %s", p)

    if not parsed:
        return None

    keys = {(k, kt) for (k, kt, _) in parsed}
    if len(keys) != 1:
        LOG.warning("DB overlay: multiple station identifiers in selected files: %r", sorted(keys))
        return None

    station_key, station_key_type = parsed[0][0], parsed[0][1]
    months = [yyyymm for (_, _, yyyymm) in parsed]
    start_yyyymm = min(months)
    end_yyyymm = max(months)

    return DbRequestSpec(
        station_key=station_key,
        station_key_type=station_key_type,
        start_yyyymm=start_yyyymm,
        end_yyyymm=end_yyyymm
    )
