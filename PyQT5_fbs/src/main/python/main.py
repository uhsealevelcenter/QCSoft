import os
import sys
import csv
import time
import traceback
import tempfile

try:
    from uhslc_station_tools.db.envfile import load_env_db
    load_env_db()
except Exception:
    pass

import logging
logging.basicConfig(level=logging.INFO)
logging.getLogger().setLevel(logging.INFO)
logging.info("DB read logging mode | TSDB_LOG_SQL=%s", os.getenv("TSDB_LOG_SQL", "spec"))
logging.info("DB debug logging mode | TSDB_LOG_DEBUG=%s", os.getenv("TSDB_LOG_DEBUG", "0"))

from PyQt5 import QtWidgets, QtCore
from fbs_runtime.application_context import cached_property
from fbs_runtime.application_context.PyQt5 import ApplicationContext

from my_widgets import *
from db_overlay.extract import build_db_request_spec
from db_overlay.spec import month_span_inclusive
from uhslc_station_tools.extractor import load_station_data
from uhslc_station_tools import utils
from uhslc_station_tools.utils import is_valid_files
from uhslc_station_tools.datasource.timescale_source import TimescaleSource, _log_sql
from uhslc_station_tools.db.connection import init_pool, health_check, get_conn
from uhslcdesign import Ui_MainWindow
from psycopg2.extras import execute_batch, execute_values

import numpy as np
import pandas as pd
from datetime import datetime, timezone

from uhslc_station_tools.datasource.queries import (
    CONNECTION_FOR_DB_STATION_ID_IN_RANGE,
    DATE_RANGE_BY_TIME_SERIES_QUALITY,
    RECORD_QUALITY_ALL,
    TEMPORAL_RESOLUTION_ALL,
    SOURCE_ALL,
    TIME_SERIES_DATA_BY_TARGET_AND_RANGE,
    TIME_SERIES_DATA_UPSERT,
    TIME_SERIES_DATA_DELETE_EXACT_TIMES,
    CHANNEL_DATA_UPSERT,
    CHANNEL_DATA_UPSERT_VALUES,
    CHANNEL_DATA_DELETE_EXACT_TIMES,
    POSTGRES_COPY_CSV_TEMPLATE,
    HF_CHANNEL_DATA_STAGE_DELETE_TABLE,
    HF_CHANNEL_DATA_STAGE_UPSERT_TABLE,
    HF_CHANNEL_DATA_STAGE_DELETE_COLUMNS,
    HF_CHANNEL_DATA_STAGE_UPSERT_COLUMNS,
    HF_CHANNEL_DATA_STAGE_DROP_DELETE,
    HF_CHANNEL_DATA_STAGE_DROP_UPSERT,
    HF_CHANNEL_DATA_STAGE_CREATE_DELETE,
    HF_CHANNEL_DATA_STAGE_CREATE_UPSERT,
    HF_CHANNEL_DATA_STAGE_INDEX_DELETE,
    HF_CHANNEL_DATA_STAGE_INDEX_UPSERT,
    HF_CHANNEL_DATA_STAGE_ANALYZE_DELETE,
    HF_CHANNEL_DATA_STAGE_ANALYZE_UPSERT,
    HF_CHANNEL_DATA_STAGE_DELETE_APPLY,
    HF_CHANNEL_DATA_STAGE_UPSERT_APPLY,
    HF_CHANNEL_DATA_TARGET_WINDOW_EXISTS,
    CHANNELS_FOR_CONNECTION,
    PRIMARY_CHANNEL_UPSERT,
)

if is_pyqt5():
    pass
else:
    pass


def _normalize_sensor_key(value):
    """
    Normalize sensor/channel keys so DB names and file names match
    case-insensitively.

    Examples:
        'prs' -> 'PRS'
        ' PRS ' -> 'PRS'
    """

    if value is None:
        return ""

    return str(value).strip().upper()

def _naive_utc_now():
    """
    Return current UTC time as a naive datetime.

    HF channel_data timestamps in this tool are handled as naive UTC values.
    Use this cutoff to prevent writes/deletes for data valid in the future.
    """

    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)

def _execute_hf_channel_data_upsert_values(cur, params, page_size=10000):
    """
    Bulk upsert HF channel_data rows using execute_values.

    Current HF upsert params are shaped for CHANNEL_DATA_UPSERT:

        (data, time, channel_id, quality_id, data_flag_id, conflict_quality_id)

    execute_values only needs the INSERT values:

        (data, time, channel_id, quality_id, data_flag_id)

    The conflict target still needs the partial-index quality_id in SQL, so
    this groups by quality_id and formats the integer quality_id into the
    statement safely after converting it to int.
    """

    if not params:
        return 0

    grouped = {}
    for p in params:
        quality_id = int(p[3])
        data_flag_id = None if p[4] is None else int(p[4])

        grouped.setdefault(quality_id, []).append((
            p[0],          # data
            p[1],          # time
            int(p[2]),     # channel_id
            quality_id,    # quality_id
            data_flag_id,  # data_flag_id
        ))

    statement_count = 0

    for quality_id, rows in grouped.items():
        sql = CHANNEL_DATA_UPSERT_VALUES.format(quality_id=int(quality_id))

        execute_values(
            cur,
            sql,
            rows,
            template="(%s, %s, %s, %s, %s)",
            page_size=page_size,
        )

        statement_count += int(np.ceil(len(rows) / float(page_size)))

    return statement_count

def _pg_copy_csv_value(value):
    """
    Convert a Python/Pandas value into a COPY CSV field.

    COPY is used only as a transport into temp tables. The temp table columns
    are created from channel_data itself, so PostgreSQL still performs the final
    type conversion to the same target types used by the old parameterized
    INSERT/DELETE path.
    """

    if value is None:
        return r"\N"

    try:
        if pd.isna(value):
            return r"\N"
    except Exception:
        pass

    if isinstance(value, pd.Timestamp):
        if pd.isna(value):
            return r"\N"
        value = value.to_pydatetime()
    elif isinstance(value, np.datetime64):
        ts = pd.Timestamp(value)
        if pd.isna(ts):
            return r"\N"
        value = ts.to_pydatetime()

    if isinstance(value, datetime):
        return value.isoformat(sep=" ")

    if isinstance(value, np.integer):
        return int(value)

    if isinstance(value, np.floating):
        if np.isnan(value):
            return r"\N"
        return repr(float(value))

    if isinstance(value, float):
        if np.isnan(value):
            return r"\N"
        return repr(value)

    return value


def _copy_csv_rows(cur, table_name, columns, rows):
    """
    Bulk-load rows into a temp table using PostgreSQL COPY CSV.

    table_name and columns are internal constants, not user input.
    """

    if rows is None:
        return 0

    if not isinstance(rows, list):
        rows = list(rows)

    if not rows:
        return 0

    column_sql = ", ".join(columns)
    copy_sql = POSTGRES_COPY_CSV_TEMPLATE.format(
        table_name=table_name,
        columns=column_sql,
    )

    with tempfile.SpooledTemporaryFile(max_size=64 * 1024 * 1024, mode="w+", newline="") as buffer:
        writer = csv.writer(buffer, lineterminator="\n")

        for row in rows:
            writer.writerow([_pg_copy_csv_value(value) for value in row])

        buffer.seek(0)
        cur.copy_expert(copy_sql, buffer)

    return len(rows)


def _flatten_hf_delete_params(delete_params):
    """
    Expand existing HF delete params into one exact-key row per timestamp.

    Input shape is the existing CHANNEL_DATA_DELETE_EXACT_TIMES param shape:
        (channel_id, quality_id, [times...])
    """

    for channel_id, quality_id, times in (delete_params or []):
        for t in (times or []):
            yield (int(channel_id), int(quality_id), t)


def _flatten_hf_upsert_params(upsert_params):
    """
    Convert existing HF upsert params into the five inserted columns.

    Input shape is the existing CHANNEL_DATA_UPSERT param shape:
        (data, time, channel_id, quality_id, data_flag_id, conflict_quality_id)
    """

    for p in (upsert_params or []):
        data_flag_id = None if p[4] is None else int(p[4])
        yield (
            p[0],          # data
            p[1],          # time
            int(p[2]),     # channel_id
            int(p[3]),     # quality_id
            data_flag_id,  # data_flag_id
        )

def _execute_hf_channel_data_staged_write(cur, delete_params, upsert_params):
    """
    Execute the already-computed HF DB changes efficiently.

    This preserves the existing Python diff/reconcile semantics:
    callers still compute the exact same delete_params and upsert_params.

    Execution strategy:

      - Split upsert rows by (channel_id, quality_id).
      - For groups with no deletes and no existing target rows in that
        group/time window, COPY directly into channel_data.
      - For groups with existing rows, or groups that also have deletes, use
        temp staging and INSERT ... ON CONFLICT DO UPDATE.

    This keeps the first-time-load fast path for fully empty windows, while
    also handling partial-baseline cases efficiently, for example when one
    sensor already has fd-multi rows but other sensors do not.
    """

    delete_rows = list(_flatten_hf_delete_params(delete_params))
    upsert_rows = list(_flatten_hf_upsert_params(upsert_params))

    result = {
        "delete_rows_staged": len(delete_rows),
        "upsert_rows_staged": len(upsert_rows),
        "delete_stmt_count": 0,
        "upsert_stmt_count": 0,
        "delete_rows_affected": 0,
        "upsert_rows_affected": 0,
        "update_changed_rows_affected": 0,
        "insert_missing_rows_affected": 0,
        "combined_upsert_rows_affected": 0,
        "quality_ids": sorted({int(row[3]) for row in upsert_rows}),
        "execute_mode": "copy_staging_upsert",
        "direct_copy_used": False,
        "preflight_target_has_existing_rows": None,
        "preflight_group_count": 0,
        "preflight_existing_group_count": 0,
        "direct_copy_group_count": 0,
        "staged_upsert_group_count": 0,
        "direct_copy_rows_affected": 0,
        "staged_upsert_rows": len(upsert_rows),
    }

    timing_start = time.perf_counter()
    timings = {}

    if not delete_rows and not upsert_rows:
        timings["total_staged_write_seconds"] = time.perf_counter() - timing_start
        result["timings"] = timings
        return result

    # Mixed fast path:
    #
    # The old fast path only used direct COPY when the entire target
    # channel/quality/time window was empty. In partial-baseline cases, one
    # existing channel forced every other channel through ON CONFLICT.
    #
    # Instead, preflight each (channel_id, quality_id) group. Groups that are
    # empty in channel_data can be copied directly; only groups with existing
    # target rows continue through the staged upsert path.
    direct_copy_rows = []
    if upsert_rows:
        groups = {}
        for row in upsert_rows:
            key = (int(row[2]), int(row[3]))  # (channel_id, quality_id)
            groups.setdefault(key, []).append(row)

        delete_groups = {(int(row[0]), int(row[1])) for row in delete_rows}
        staged_upsert_rows = []
        existing_group_count = 0
        preflight_group_count = 0

        t0 = time.perf_counter()
        for (channel_id, quality_id), rows in sorted(groups.items()):
            # Keep any group with deletes on the conservative staged path.
            if (channel_id, quality_id) in delete_groups:
                staged_upsert_rows.extend(rows)
                continue

            times = [row[1] for row in rows if row[1] is not None]
            if not times:
                staged_upsert_rows.extend(rows)
                continue

            preflight_group_count += 1
            cur.execute(
                HF_CHANNEL_DATA_TARGET_WINDOW_EXISTS,
                (
                    [quality_id],
                    [channel_id],
                    min(times),
                    max(times),
                ),
            )
            target_has_existing_rows = bool(cur.fetchone()[0])

            if target_has_existing_rows:
                existing_group_count += 1
                staged_upsert_rows.extend(rows)
            else:
                direct_copy_rows.extend(rows)

        timings["preflight_existing_rows_seconds"] = time.perf_counter() - t0

        result["preflight_group_count"] = preflight_group_count
        result["preflight_existing_group_count"] = existing_group_count
        result["direct_copy_group_count"] = len({(int(row[2]), int(row[3])) for row in direct_copy_rows})
        result["staged_upsert_group_count"] = len({(int(row[2]), int(row[3])) for row in staged_upsert_rows})
        result["staged_upsert_rows"] = len(staged_upsert_rows)

        if preflight_group_count:
            result["preflight_target_has_existing_rows"] = bool(existing_group_count)

        if direct_copy_rows:
            t0 = time.perf_counter()
            _copy_csv_rows(
                cur,
                "channel_data",
                HF_CHANNEL_DATA_STAGE_UPSERT_COLUMNS,
                direct_copy_rows,
            )
            timings["copy_direct_channel_data_seconds"] = time.perf_counter() - t0

            result["execute_mode"] = "copy_mixed_direct_staging" if staged_upsert_rows or delete_rows else "copy_direct_insert"
            result["direct_copy_used"] = True
            result["direct_copy_rows_affected"] = len(direct_copy_rows)
            result["upsert_rows_affected"] += len(direct_copy_rows)
            result["insert_missing_rows_affected"] += len(direct_copy_rows)
            result["combined_upsert_rows_affected"] += len(direct_copy_rows)

        upsert_rows = staged_upsert_rows
        result["quality_ids"] = sorted({int(row[3]) for row in upsert_rows})

        if direct_copy_rows and not delete_rows and not upsert_rows:
            timings["total_staged_write_seconds"] = time.perf_counter() - timing_start
            result["upsert_stmt_count"] = 1
            result["timings"] = timings

            logging.info(
                "HF direct COPY write timings | upsert_rows=%d | direct_copy_rows=%d | "
                "direct_copy_groups=%d | preflight_groups=%d | quality_ids=%s | timings=%s",
                result["upsert_rows_staged"],
                result["direct_copy_rows_affected"],
                result["direct_copy_group_count"],
                result["preflight_group_count"],
                sorted({int(row[3]) for row in direct_copy_rows}),
                timings,
            )

            return result

    cur.execute(HF_CHANNEL_DATA_STAGE_DROP_DELETE)
    cur.execute(HF_CHANNEL_DATA_STAGE_DROP_UPSERT)

    if delete_rows:
        cur.execute(HF_CHANNEL_DATA_STAGE_CREATE_DELETE)

        t0 = time.perf_counter()
        _copy_csv_rows(
            cur,
            HF_CHANNEL_DATA_STAGE_DELETE_TABLE,
            HF_CHANNEL_DATA_STAGE_DELETE_COLUMNS,
            delete_rows,
        )
        timings["copy_delete_seconds"] = time.perf_counter() - t0

        t0 = time.perf_counter()
        cur.execute(HF_CHANNEL_DATA_STAGE_INDEX_DELETE)
        cur.execute(HF_CHANNEL_DATA_STAGE_ANALYZE_DELETE)
        timings["index_analyze_delete_seconds"] = time.perf_counter() - t0

        t0 = time.perf_counter()
        cur.execute(HF_CHANNEL_DATA_STAGE_DELETE_APPLY)
        timings["apply_delete_seconds"] = time.perf_counter() - t0

        result["delete_stmt_count"] = 1
        result["delete_rows_affected"] = max(cur.rowcount, 0)

    if upsert_rows:
        cur.execute(HF_CHANNEL_DATA_STAGE_CREATE_UPSERT)

        t0 = time.perf_counter()
        _copy_csv_rows(
            cur,
            HF_CHANNEL_DATA_STAGE_UPSERT_TABLE,
            HF_CHANNEL_DATA_STAGE_UPSERT_COLUMNS,
            upsert_rows,
        )
        timings["copy_upsert_seconds"] = time.perf_counter() - t0

        t0 = time.perf_counter()
        cur.execute(HF_CHANNEL_DATA_STAGE_INDEX_UPSERT)
        cur.execute(HF_CHANNEL_DATA_STAGE_ANALYZE_UPSERT)
        timings["index_analyze_upsert_seconds"] = time.perf_counter() - t0

        t0 = time.perf_counter()

        for quality_id in result["quality_ids"]:
            quality_id = int(quality_id)

            t_upsert = time.perf_counter()
            cur.execute(HF_CHANNEL_DATA_STAGE_UPSERT_APPLY.format(quality_id=quality_id))
            upsert_rows_affected = max(cur.rowcount, 0)
            timings["apply_upsert_seconds_q%s" % quality_id] = time.perf_counter() - t_upsert

            result["upsert_stmt_count"] += 1
            result["upsert_rows_affected"] += upsert_rows_affected
            result["combined_upsert_rows_affected"] += upsert_rows_affected

        timings["apply_upsert_seconds"] = time.perf_counter() - t0

    if direct_copy_rows and (delete_rows or upsert_rows):
        result["upsert_stmt_count"] += 1

    if not result["direct_copy_used"]:
        result["staged_upsert_rows"] = len(upsert_rows)

    timings["total_staged_write_seconds"] = time.perf_counter() - timing_start
    result["timings"] = timings

    logging.info(
        "HF staged write timings | delete_rows=%d | upsert_rows=%d | staged_upsert_rows=%d | "
        "direct_copy_rows=%d | direct_copy_groups=%d | staged_upsert_groups=%d | "
        "combined_upsert_rows_affected=%d | direct_copy_used=%s | "
        "preflight_existing_group_count=%d | preflight_group_count=%d | quality_ids=%s | timings=%s",
        result["delete_rows_staged"],
        result["upsert_rows_staged"],
        result["staged_upsert_rows"],
        result["direct_copy_rows_affected"],
        result["direct_copy_group_count"],
        result["staged_upsert_group_count"],
        result["combined_upsert_rows_affected"],
        result["direct_copy_used"],
        result["preflight_existing_group_count"],
        result["preflight_group_count"],
        result["quality_ids"],
        timings,
    )

    return result

def _env_bool(name, default=False):
    """Return True when an environment variable is set to a truthy value."""

    value = os.getenv(name)
    if value is None:
        return bool(default)

    return str(value).strip().lower() in ("1", "true", "yes", "on")


# Env vars.
DB_OVERLAY_MAX_MONTHS = int(os.getenv("TSDB_OVERLAY_MAX_MONTHS", "4"))
DB_SAVE_GATE_WATCHDOG_MS = int(os.getenv("TSDB_SAVE_GATE_WATCHDOG_MS", "120000"))
TSDB_EXECUTE_WRITES = _env_bool("TSDB_EXECUTE_WRITES", False)
TSDB_BACKGROUND_HF_WRITES = _env_bool("TSDB_BACKGROUND_HF_WRITES", False)
logging.info("DB write execution mode | TSDB_EXECUTE_WRITES=%s", os.getenv("TSDB_EXECUTE_WRITES", "0"))


class DbOverlayWorker(QtCore.QObject):

    finished = QtCore.pyqtSignal(object, object, int)  # (spec, station_obj, gen)
    failed = QtCore.pyqtSignal(object, str, int)  # (spec, error_str, gen)

    def __init__(self, spec, gen, force_level_2=None, force_base_channel_data=False):
        """Initialize a background worker for DB station loading."""

        super(DbOverlayWorker, self).__init__()
        self.spec = spec
        self.gen = gen
        self.force_level_2 = force_level_2
        self.force_base_channel_data = bool(force_base_channel_data)

    @QtCore.pyqtSlot()
    def run(self):
        """Load station data from the database in a worker thread and emit the result or failure."""

        try:
            init_pool(minconn=1, maxconn=5)
            if not health_check():
                raise RuntimeError("DB health_check returned False")

            src = TimescaleSource()

            use_level_2 = (self.spec.station_key_type == "uhslc_id") if self.force_level_2 is None else bool(self.force_level_2)
            if self.spec.station_key_type == "uhslc_code":
                station = src.load_station(self.spec.station_key, self.spec.start_yyyymm, self.spec.end_yyyymm, use_level_2=use_level_2, force_base_channel_data=self.force_base_channel_data)
            elif self.spec.station_key_type == "uhslc_id":
                station = src.load_station_by_uhslc_id(int(self.spec.station_key), self.spec.start_yyyymm, self.spec.end_yyyymm, use_level_2=use_level_2, force_base_channel_data=self.force_base_channel_data)
            else:
                raise ValueError("Unknown station_key_type: {0}".format(self.spec.station_key_type))

            self.finished.emit(self.spec, station, self.gen)

        except Exception as e:
            self.failed.emit(self.spec, "{0}".format(e), self.gen)


class HfDbWriteWorker(QtCore.QObject):

    finished = QtCore.pyqtSignal(str, object)  # job_key, result dict
    failed = QtCore.pyqtSignal(str, str)       # job_key, traceback string

    def __init__(
        self,
        job_key,
        station_key,
        range_start,
        range_end,
        delete_params,
        upsert_params,
        upsert_page_size=10000,
    ):
        super(HfDbWriteWorker, self).__init__()

        self.job_key = str(job_key)
        self.station_key = station_key
        self.range_start = range_start
        self.range_end = range_end

        # Copy payloads so the worker does not depend on mutable caller state.
        self.delete_params = list(delete_params or [])
        self.upsert_params = list(upsert_params or [])
        self.upsert_page_size = int(upsert_page_size)

    @QtCore.pyqtSlot()
    def run(self):
        try:
            init_pool(minconn=1, maxconn=5)

            hf_write_result = {}

            with get_conn() as conn:
                try:
                    with conn.cursor() as cur:
                        hf_write_result = _execute_hf_channel_data_staged_write(
                            cur,
                            self.delete_params,
                            self.upsert_params,
                        )

                    t0 = time.perf_counter()
                    conn.commit()
                    hf_write_result.setdefault("timings", {})["commit_seconds"] = time.perf_counter() - t0

                except Exception:
                    conn.rollback()
                    raise

            self.finished.emit(
                self.job_key,
                {
                    "station": self.station_key,
                    "range_start": self.range_start,
                    "range_end": self.range_end,
                    "delete_stmts": hf_write_result.get("delete_stmt_count", 0),
                    "delete_rows_staged": hf_write_result.get("delete_rows_staged", len(self.delete_params)),
                    "delete_rows_affected": hf_write_result.get("delete_rows_affected", 0),
                    "upsert_rows": len(self.upsert_params),
                    "upsert_rows_staged": hf_write_result.get("upsert_rows_staged", len(self.upsert_params)),
                    "staged_upsert_rows": hf_write_result.get("staged_upsert_rows", len(self.upsert_params)),
                    "direct_copy_rows": hf_write_result.get("direct_copy_rows_affected", 0),
                    "direct_copy_group_count": hf_write_result.get("direct_copy_group_count", 0),
                    "staged_upsert_group_count": hf_write_result.get("staged_upsert_group_count", 0),
                    "upsert_rows_affected": hf_write_result.get("upsert_rows_affected", 0),
                    "upsert_stmt_count": hf_write_result.get("upsert_stmt_count", 0),
                    "execute_mode": hf_write_result.get("execute_mode", "copy_staging_upsert"),
                    "timings": hf_write_result.get("timings", {}),
                },
            )

        except Exception:
            self.failed.emit(self.job_key, traceback.format_exc())


class AppContext(ApplicationContext):  # 1. Subclass ApplicationContext

    def run(self):  # 2. Implement run()
        """Configure, show, and run the main application window."""

        version = self.build_settings["version"]
        name = self.build_settings["app_name"]
        # if sys.platform == 'darwin' and darkdetect.isDark():
        #     p = self.app.palette()
        #     p.setColor(QPalette.Base, QColor(101, 101, 101))
        #     p.setColor(QPalette.WindowText, QColor(231, 231, 231))
        #     p.setColor(QPalette.Text, QColor(231, 231, 231))
        #     self.app.setPalette(p)
        self.window.setWindowTitle(name + " v" + str(version))
        self.window.show()
        return self.app.exec_()  # 3. End run() with this line

    @cached_property
    def window(self):
        """Create and cache the main application window."""

        return ApplicationWindow()


class ApplicationWindow(QMainWindow):

    def __init__(self):
        """Initialize the main window, UI screens, DB state, caches, and signal connections."""

        super(ApplicationWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Create Screen objects.
        self.start_screen = Start(self.ui)
        self.help_screen = HelpScreen(self.ui)

        # One-time debug flag to verify cached overlay sensor->channel_id mapping.
        self._logged_overlay_channel_mapping = False

        # Load record quality and temporal resolution database metadata.
        self.tsdb_meta = self._load_tsdb_lookup_metadata()

        self.fd_source_name = "uhslc"

        # Allow Start.save_button() to call back into ApplicationWindow for DB reconcile/write hooks.
        self.start_screen.db_upsert_hook = self._reconcile_hf_db_from_cached_overlay
        self.start_screen.fd_db_upsert_hook = self._reconcile_fd_db_from_saved_products

        self.ui.actionInstructions.triggered.connect(lambda: self.ui.stackedWidget.setCurrentIndex(1))
        self.ui.backButton.clicked.connect(lambda: self.ui.stackedWidget.setCurrentIndex(0))

        close_app = self.ui.actionQuit
        close_app.triggered.connect(self.close_application)

        open_file = self.ui.actionOpen
        open_file.triggered.connect(self.file_open)

        reload_file = self.ui.actionReload
        reload_file.triggered.connect(self.get_loaded_files)

        opents_file = self.ui.actionOpen_TS
        opents_file.triggered.connect(self.open_ts)

        # DB overlay checkbox.
        self.db_overlay_enabled = False
        self.db_overlay_spec = None  # filled after file_open/open_ts loads a station

        self.db_overlay_checkbox = QtWidgets.QCheckBox("Load from DB")
        self.db_overlay_checkbox.setChecked(False)
        self.db_overlay_checkbox.stateChanged.connect(self.on_db_overlay_toggled)
        self.start_screen.db_overlay_checkbox = self.db_overlay_checkbox

        # DB overlay cache + background fetch state.
        self._db_overlay_cache = {}  # key -> station_obj
        self._db_overlay_gen = 0
        self._db_overlay_thread = None
        self._db_overlay_worker = None

        # Background DB write state.
        self._hf_db_write_threads = {}
        self._hf_db_write_workers = {}
        self._hf_db_write_jobs_inflight = set()

        # Level-2 baseline cache used ONLY for save/upsert diff (always fd-multi quality).
        self._db_level2_cache = {}  # key -> station_obj
        self._db_level2_gen = 0
        self._db_level2_thread = None
        self._db_level2_worker = None

        # Count of in-flight background DB prefetch jobs that should temporarily
        # block Save until they finish or fail.
        self._db_save_gate_pending_count = 0

        # Per-job watchdog timers so Save cannot remain disabled forever if a DB
        # prefetch worker hangs and never emits finished/failed.
        self._db_overlay_watchdog_timer = None
        self._db_overlay_watchdog_gen = None

        self._db_level2_watchdog_timer = None
        self._db_level2_watchdog_gen = None

        # Tracks whether the last prefetch attempt failed; used to disable checkbox after failure until next file load.
        self._db_overlay_last_prefetch_failed = False

        # When True, all DB-related GUI behavior is disabled for the current loaded span
        # because the loaded month range exceeds DB_OVERLAY_MAX_MONTHS.
        self._db_ops_disabled_for_span = False

        # Prevent duplicate warning popups during a single save.
        self._db_ops_disabled_warning_shown = False

    def file_open(self, reload=False, ts=False):
        """Open station files, load them into the UI, and start any allowed background DB prefetch work."""

        if not reload:
            # filters = "s*.dat;; ts*.dat"
            if ts:
                filters = "t*.dat"
            else:
                filters = "s*.dat"
            if ts:
                if st.get_path(st.SAVE_KEY):
                    path = st.get_path(st.SAVE_KEY)
                else:
                    # path = "C:\\Users\\komar\\OneDrive\\Desktop\\monp"
                    path = os.path.expanduser('~')
            else:
                if st.get_path(st.LOAD_KEY):
                    path = st.get_path(st.LOAD_KEY)
                else:
                    # path = "C:\\Users\\komar\\OneDrive\\Desktop\\monp"
                    path = os.path.expanduser('~')
            self.file_name = QtWidgets.QFileDialog.getOpenFileNames(self, 'Open File', path, filters)

        # Validating files selected.
        if is_valid_files(self.file_name[0]):
            pass
        else:
            self.critical_dialog(title="ERROR",
                                 text="Warning, wrong files selected",
                                 info_text=("Files must be from the same station and be consecutive months "
                                            "in chronological order (e.g., Dec → Jan is allowed). "
                                            "Please select valid files to continue."),
                                 details=''''MAC:
            The files are loaded in order in which they were selected. Select files from the oldest to the youngest.\nWINDOWS:
            The order is determined by the file order in the File Explorer. The files should be sorted by name before selecting them.
            ''')
            return

        try:
            # self.file_name[0] is an array of filenames loaded.
            month_count = len(self.file_name[0])
            self.ui.lineEdit_2.setText("Loaded: " + str(month_count) + " months")
            station = load_station_data(self.file_name[0])
        except (FileNotFoundError, IndexError) as e:
            print('Error:', e)
            return

        self.start_screen.station = station
        self.start_screen.make_sensor_buttons(station.month_collection[0].sensor_collection.sensors)

        # Cancel any stale watchdog timers from a previous load before resetting
        # the Save gate state.
        self._cancel_db_overlay_watchdog()
        self._cancel_db_level2_watchdog()

        # Reset Save gate state for the newly loaded station before launching any
        # new background DB work.
        self._set_db_save_gate_pending_count(0)

        # If the previous station's DB overlay prefetch failed, allow the user to try again
        # for the newly loaded files by re-enabling the checkbox (leave it unchecked).
        self._db_overlay_last_prefetch_failed = False
        self._db_ops_disabled_for_span = False
        self._db_ops_disabled_warning_shown = False
        try:
            self.db_overlay_checkbox.blockSignals(True)
            self.db_overlay_checkbox.setEnabled(True)
            self.db_overlay_checkbox.setChecked(False)
        finally:
            try:
                self.db_overlay_checkbox.blockSignals(False)
            except Exception:
                pass

        # Ensure no old DB overlay is displayed while new station loads
        self.db_overlay_enabled = False
        if hasattr(self.start_screen, "set_db_overlay_enabled"):
            self.start_screen.set_db_overlay_enabled(False)

        self._clear_db_overlay_plot()

        # Derive DB overlay request spec from the loaded files.
        try:
            all_paths = self.file_name[0] if self.file_name else None
            self.db_overlay_spec = build_db_request_spec(station, file_paths=all_paths)

            # Stamp explicit DB station identity onto the file-loaded Station so that
            # save-time DB hooks do not have to infer identifiers from Month.station_id.
            self._hydrate_station_identity_from_spec(station, self.db_overlay_spec)
            self.start_screen.station = station

            if self.db_overlay_spec:
                logging.info(
                    "DB overlay spec from file load: %s %s-%s",
                    self.db_overlay_spec.station_key,
                    self.db_overlay_spec.start_yyyymm,
                    self.db_overlay_spec.end_yyyymm
                )
                if self.db_overlay_enabled:
                    self.statusBar().showMessage(
                        "DB overlay enabled (will use {0} {1}-{2})".format(
                            self.db_overlay_spec.station_key,
                            self.db_overlay_spec.start_yyyymm,
                            self.db_overlay_spec.end_yyyymm
                        ),
                        5000
                    )
            else:
                logging.warning("DB overlay spec could not be derived from file load.")
                if self.db_overlay_enabled:
                    self.statusBar().showMessage(
                        "DB overlay enabled, but could not derive station/time range from loaded files.",
                        6000
                    )
            self._db_ops_disabled_for_span = not self._db_ops_allowed_for_spec(self.db_overlay_spec)

            if self._db_ops_disabled_for_span:
                msg = self._db_ops_disabled_message(self.db_overlay_spec)
                logging.warning("DB work disabled for loaded files: %s", msg)
                self._set_db_save_gate_pending_count(0)

                # Force DB overlay off for this session/load.
                self.db_overlay_enabled = False
                if hasattr(self.start_screen, "set_db_overlay_enabled"):
                    self.start_screen.set_db_overlay_enabled(False)
                self._clear_db_overlay_plot()

                try:
                    self.db_overlay_checkbox.blockSignals(True)
                    self.db_overlay_checkbox.setChecked(False)
                    self.db_overlay_checkbox.setEnabled(False)
                finally:
                    try:
                        self.db_overlay_checkbox.blockSignals(False)
                    except Exception:
                        pass

                self.statusBar().showMessage(msg, 10000)

            if not self._db_ops_disabled_for_span:
                self._prefetch_db_overlay_if_allowed(self.db_overlay_spec)

                # Regular s*.dat loads still need a separate save-time L2 baseline
                # because their visible overlay is raw/L0.
                #
                # TS t*.dat loads do not need a second read: their visible overlay is
                # fd-multi/L2 from base channel_data and is reused as the save baseline.
                if not self._db_overlay_can_supply_l2_baseline(self.db_overlay_spec):
                    self._prefetch_db_level2_baseline_if_allowed(self.db_overlay_spec)

        except Exception as e:

            logging.exception("Error deriving DB overlay spec: %r", e)

    def critical_dialog(self, title, text, info_text, details):
        """Show a modal critical message dialog with summary, details, and informative text."""

        msg_box = QtWidgets.QMessageBox(self)
        msg_box.setIcon(QtWidgets.QMessageBox.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(text)
        msg_box.setInformativeText(info_text)
        msg_box.setDetailedText(str(details))
        msg_box.setDefaultButton(QtWidgets.QMessageBox.Ok)
        msg_box.exec_()

    def closeEvent(self, event):
        """Prevent closing the window while an HF DB write is still running."""

        if getattr(self, "_hf_db_write_jobs_inflight", None):
            QtWidgets.QMessageBox.warning(
                self,
                "HF DB Write In Progress",
                "An HF database write is still running in the background.\n\n"
                "Please wait for it to finish before quitting.",
            )
            event.ignore()
            return

        choice = QtWidgets.QMessageBox.question(
            self,
            "Warning",
            "Are you sure you want to quit?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )

        if choice == QtWidgets.QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

    def close_application(self):
        """Prompt the user for confirmation and close the application if confirmed."""

        self.close()

    def get_loaded_files(self):
        """Reload the currently selected files through the standard file loading workflow."""

        self.file_open(reload=True)

    def open_ts(self):
        """Open TS files through the standard file loading workflow."""

        self.file_open(reload=False, ts=True)

    def _naive(self, ts):
        """Convert a timestamp-like value to a naive pandas timestamp, preserving None for invalid inputs."""

        if ts is None or pd.isna(ts):
            return None
        ts = pd.to_datetime(ts, errors="coerce")
        if getattr(ts, "tzinfo", None) is not None:
            ts = ts.tz_localize(None)

        return ts

    def _db_debug_enabled(self):
        """Return True when DB debug logging is enabled by environment setting."""

        return str(os.getenv("TSDB_LOG_DEBUG", "0")).strip().lower() in ("1", "true", "on")

    def _db_live_writes_enabled(self, is_test_mode=False, context="DB write"):
        """Return True only when live database writes are explicitly enabled and not in test mode."""

        if is_test_mode:
            logging.warning(
                "%s execution skipped because test mode is enabled. "
                "Test mode never writes to the database.",
                context,
            )
            return False

        if not TSDB_EXECUTE_WRITES:
            logging.info(
                "%s execution disabled; continuing in log-only mode. "
                "Set TSDB_EXECUTE_WRITES=1 to execute.",
                context,
            )
            return False

        return True

    def _hydrate_station_identity_from_spec(self, station, spec):
        """
        Populate explicit DB station identity fields onto a file-loaded Station object
        using a lightweight station-row lookup derived from the DB overlay request spec.

        This avoids depending on a full station/month/channel load merely to resolve
        station identifiers needed later by save-time DB upserts.
        """

        if station is None or spec is None:
            return station

        try:
            src = TimescaleSource()

            if spec.station_key_type == "uhslc_code":
                station_row = src.get_station_identity_by_uhslc_code(spec.station_key)
            elif spec.station_key_type == "uhslc_id":
                station_row = src.get_station_identity_by_uhslc_id(int(spec.station_key))
            else:
                logging.warning(
                    "Station identity hydration skipped: unknown station_key_type=%s",
                    spec.station_key_type,
                )
                return station

            if not station_row:
                logging.warning(
                    "Station identity hydration found no station row for station_key_type=%s station_key=%s",
                    getattr(spec, "station_key_type", None),
                    getattr(spec, "station_key", None),
                )
                return station

            station.station_db_id = station_row.get("id")
            station.uhslc_id = station_row.get("uhslc_id")
            station.uhslc_code = station_row.get("uhslc_code")

            # Preserve existing file_station_id if already present; otherwise derive a sane fallback.
            if getattr(station, "file_station_id", None) in (None, ""):
                fallback_file_station_id = station_row.get("uhslc_id") or station_row.get("uhslc_code")
                if fallback_file_station_id not in (None, ""):
                    station.file_station_id = str(fallback_file_station_id).strip()

            logging.info(
                "Hydrated file-loaded Station identity | station_db_id=%s | uhslc_id=%s | uhslc_code=%s | file_station_id=%s",
                getattr(station, "station_db_id", None),
                getattr(station, "uhslc_id", None),
                getattr(station, "uhslc_code", None),
                getattr(station, "file_station_id", None),
            )

        except Exception:
            logging.exception(
                "Failed to hydrate file-loaded Station identity from DB spec: station_key_type=%s station_key=%s",
                getattr(spec, "station_key_type", None),
                getattr(spec, "station_key", None),
            )

        return station

    def _load_tsdb_lookup_metadata(self):
        """Load and normalize record quality, temporal resolution, and source metadata for the session."""

        try:
            init_pool(minconn=1, maxconn=5)
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(RECORD_QUALITY_ALL)
                    rq_rows = cur.fetchall()
                    rq_cols = [d[0] for d in cur.description]

                    cur.execute(TEMPORAL_RESOLUTION_ALL)
                    tr_rows = cur.fetchall()
                    tr_cols = [d[0] for d in cur.description]

                    cur.execute(SOURCE_ALL)
                    src_rows = cur.fetchall()
                    src_cols = [d[0] for d in cur.description]

            rq_df = pd.DataFrame(rq_rows, columns=rq_cols)
            tr_df = pd.DataFrame(tr_rows, columns=tr_cols)
            src_df = pd.DataFrame(src_rows, columns=src_cols)

            if not rq_df.empty:
                rq_df["id"] = pd.to_numeric(rq_df["id"], errors="coerce")
                rq_df["level"] = pd.to_numeric(rq_df["level"], errors="coerce")
                rq_df["short_name"] = rq_df["short_name"].astype(str)

            if not tr_df.empty:
                tr_df["id"] = pd.to_numeric(tr_df["id"], errors="coerce")
                tr_df["num_minutes"] = pd.to_numeric(tr_df["num_minutes"], errors="coerce")
                tr_df["resolution"] = tr_df["resolution"].astype(str)

            if not src_df.empty:
                src_df["id"] = pd.to_numeric(src_df["id"], errors="coerce")
                src_df["priority"] = pd.to_numeric(src_df["priority"], errors="coerce")
                src_df["name"] = src_df["name"].astype(str)

            return {
                "record_quality_df": rq_df,
                "temporal_resolution_df": tr_df,
                "source_df": src_df,
                "quality_id_by_short_name": rq_df.set_index("short_name")["id"].to_dict() if not rq_df.empty else {},
                "quality_short_name_by_id": rq_df.set_index("id")["short_name"].to_dict() if not rq_df.empty else {},
                "resolution_id_by_name": tr_df.set_index("resolution")["id"].to_dict() if not tr_df.empty else {},
                "resolution_name_by_id": tr_df.set_index("id")["resolution"].to_dict() if not tr_df.empty else {},
                "source_priority_by_name": src_df.set_index("name")["priority"].to_dict() if not src_df.empty else {},
                "source_id_by_name": src_df.set_index("name")["id"].to_dict() if not src_df.empty else {},
            }

        except Exception:

            logging.exception("Failed to load TSDB lookup metadata for session.")
            return {
                "record_quality_df": pd.DataFrame(),
                "temporal_resolution_df": pd.DataFrame(),
                "source_df": pd.DataFrame(),
                "quality_id_by_short_name": {},
                "quality_short_name_by_id": {},
                "resolution_id_by_name": {},
                "resolution_name_by_id": {},
                "source_priority_by_name": {},
                "source_id_by_name": {},
            }

    def quality_id(self, short_name, default=None):
        """Return the record quality ID for a given short name."""

        return self.tsdb_meta.get("quality_id_by_short_name", {}).get(short_name, default)

    def quality_name(self, quality_id, default=None):
        """Return the record quality short name for a given ID."""

        return self.tsdb_meta.get("quality_short_name_by_id", {}).get(int(quality_id), default)

    def resolution_id(self, resolution_name, default=None):
        """Return the temporal resolution ID for a given resolution name."""

        return self.tsdb_meta.get("resolution_id_by_name", {}).get(resolution_name, default)

    def resolution_name(self, resolution_id, default=None):
        """Return the temporal resolution name for a given ID."""

        return self.tsdb_meta.get("resolution_name_by_id", {}).get(int(resolution_id), default)

    def source_id(self, source_name, default=None):
        """Return the source ID for a given source name."""
        return self.tsdb_meta.get("source_id_by_name", {}).get(source_name, default)

    def source_priority(self, source_name, default=None):
        """Return the source priority for a given source name."""
        return self.tsdb_meta.get("source_priority_by_name", {}).get(source_name, default)

    def require_source_priority(self, source_name):
        """Return the source priority for a source name or raise if it is unknown."""
        priority = self.source_priority(source_name)
        if priority is None:
            raise KeyError(f"Unknown source.name priority for: {source_name}")

        return int(priority)

    def _set_db_overlay_checkbox_enabled(self, enabled: bool):
        """Enable or disable the DB overlay checkbox if it is available."""

        try:
            self.db_overlay_checkbox.setEnabled(bool(enabled))
        except Exception:
            pass

    def require_quality_id(self, short_name):
        """Return the record quality ID for a short name or raise if it is unknown."""

        qid = self.quality_id(short_name)
        if qid is None:
            raise KeyError(f"Unknown record_quality.short_name: {short_name}")

        return int(qid)

    def require_resolution_id(self, resolution_name):
        """Return the temporal resolution ID for a resolution name or raise if it is unknown."""

        rid = self.resolution_id(resolution_name)
        if rid is None:
            raise KeyError(f"Unknown temporal_resolution.resolution: {resolution_name}")

        return int(rid)

    def on_db_overlay_toggled(self, state):
        """Handle DB overlay checkbox changes and apply or clear the overlay as needed."""

        if not self.db_overlay_checkbox.isEnabled():
            return

        checked = bool(state)
        self.db_overlay_enabled = checked

        if hasattr(self.start_screen, "set_db_overlay_enabled"):
            self.start_screen.set_db_overlay_enabled(checked)

        if self.db_overlay_enabled:
            if self.db_overlay_spec:
                self.statusBar().showMessage(
                    "DB overlay enabled ({0} {1}-{2})".format(
                        self.db_overlay_spec.station_key,
                        self.db_overlay_spec.start_yyyymm,
                        self.db_overlay_spec.end_yyyymm,
                    ),
                    4000
                )
                # If it’s already cached, draw immediately; otherwise show a lightweight “loading” message.
                applied = self._apply_db_overlay_if_ready()
                if not applied:
                    # duration=0 keeps the message until we clear it
                    self.statusBar().showMessage("DB overlay is loading…", 0)
            else:
                self.statusBar().showMessage(
                    "DB overlay enabled, but no spec yet (load station files first).",
                    5000
                )
        else:
            self.statusBar().showMessage("DB overlay disabled.", 3000)
            self._clear_db_overlay_plot()

    def _db_cache_key(self, spec):
        """Build the cache key used for DB overlay station data."""

        return (spec.station_key_type, spec.station_key, int(spec.start_yyyymm), int(spec.end_yyyymm))

    def _db_level2_cache_key(self, spec):
        """Build the cache key used for level 2 baseline station data."""

        # separate cache from overlay cache; explicitly identifies "baseline L2"
        return ("L2BASE", spec.station_key_type, spec.station_key, int(spec.start_yyyymm), int(spec.end_yyyymm))

    def _db_overlay_can_supply_l2_baseline(self, spec):
        """
        Return True when the visible DB overlay is the same authoritative L2
        data needed for save-time HF reconcile.

        This is true for TS loads because their visible overlay is fd-multi/L2.
        Regular s*.dat loads cannot reuse the overlay because their visible
        overlay is raw/L0.
        """

        return bool(spec and spec.station_key_type == "uhslc_id")

    def _loaded_span_months(self, spec):
        """Return the inclusive loaded month span for a DB request spec."""

        if not spec:
            return None

        return month_span_inclusive(spec.start_yyyymm, spec.end_yyyymm)

    def _db_ops_allowed_for_spec(self, spec):
        """Return True when DB overlay and update operations are allowed for the given spec."""

        span = self._loaded_span_months(spec)
        if span is None:
            return True

        return span <= DB_OVERLAY_MAX_MONTHS

    def _db_ops_disabled_message(self, spec=None):
        """Build the user facing message explaining why DB features are disabled for the current span."""

        span = self._loaded_span_months(spec or self.db_overlay_spec)
        if span is None:
            span_text = "unknown"
        else:
            span_text = str(span)

        return (
            "Loaded range exceeds {max_months} months "
            "(loaded span: {span} months). "
            "DB overlay and DB update features are disabled for this session; "
            "Save will update local files only."
        ).format(
            max_months=DB_OVERLAY_MAX_MONTHS,
            span=span_text,
        )

    def _show_db_ops_disabled_warning_once(self):
        """Show the DB features disabled warning once for the current save cycle."""

        if self._db_ops_disabled_warning_shown:
            return

        self._db_ops_disabled_warning_shown = True
        msg = self._db_ops_disabled_message()

        logging.warning("DB work disabled for current load span: %s", msg)
        self.statusBar().showMessage(msg, 10000)

        box = QtWidgets.QMessageBox(self)
        box.setIcon(QtWidgets.QMessageBox.Warning)
        box.setWindowTitle("DB Features Disabled")
        box.setText("DB overlay and DB updates are disabled for this loaded range.")
        box.setInformativeText(msg)
        box.setStandardButtons(QtWidgets.QMessageBox.Ok)
        box.exec_()

    def _set_db_save_gate_pending_count(self, count):
        """
        Update the in-flight DB prefetch count and propagate Save-button state
        to the Start screen.
        """

        self._db_save_gate_pending_count = max(0, int(count))
        pending = (
            self._db_save_gate_pending_count > 0
            or bool(getattr(self, "_hf_db_write_jobs_inflight", set()))
        )

        try:
            if hasattr(self, "start_screen") and self.start_screen is not None:
                self.start_screen.set_db_save_gate_pending(pending)
        except Exception:
            logging.exception("Failed to propagate DB save gate state to Start screen")

    def _begin_db_save_gate(self):
        """Increment the pending DB prefetch count and keep Save disabled while work is in flight."""

        self._set_db_save_gate_pending_count(self._db_save_gate_pending_count + 1)

    def _end_db_save_gate(self):
        """Decrement the pending DB prefetch count and re-evaluate Save button availability."""

        self._set_db_save_gate_pending_count(self._db_save_gate_pending_count - 1)

    def _cancel_db_overlay_watchdog(self):
        """Stop and clear the active DB overlay watchdog timer."""

        try:
            if self._db_overlay_watchdog_timer is not None:
                self._db_overlay_watchdog_timer.stop()
                self._db_overlay_watchdog_timer.deleteLater()
        except Exception:
            pass
        finally:
            self._db_overlay_watchdog_timer = None
            self._db_overlay_watchdog_gen = None

    def _cancel_db_level2_watchdog(self):
        """Stop and clear the active level 2 baseline watchdog timer."""

        try:
            if self._db_level2_watchdog_timer is not None:
                self._db_level2_watchdog_timer.stop()
                self._db_level2_watchdog_timer.deleteLater()
        except Exception:
            pass
        finally:
            self._db_level2_watchdog_timer = None
            self._db_level2_watchdog_gen = None

    def _arm_db_overlay_watchdog(self, spec, gen):
        """Start the DB overlay watchdog timer for the current prefetch generation."""

        self._cancel_db_overlay_watchdog()

        timer = QtCore.QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self._on_db_overlay_watchdog_timeout(spec, gen))
        timer.start(DB_SAVE_GATE_WATCHDOG_MS)

        self._db_overlay_watchdog_timer = timer
        self._db_overlay_watchdog_gen = gen

    def _arm_db_level2_watchdog(self, spec, gen):
        """Start the level 2 baseline watchdog timer for the current prefetch generation."""

        self._cancel_db_level2_watchdog()

        timer = QtCore.QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self._on_db_level2_watchdog_timeout(spec, gen))
        timer.start(DB_SAVE_GATE_WATCHDOG_MS)

        self._db_level2_watchdog_timer = timer
        self._db_level2_watchdog_gen = gen

    def _on_db_overlay_watchdog_timeout(self, spec, gen):
        """Handle DB overlay watchdog timeout by releasing the Save gate and disabling overlay for the attempt."""

        if gen != self._db_overlay_gen:
            return
        if gen != self._db_overlay_watchdog_gen:
            return

        logging.error(
            "DB overlay watchdog timeout after %s ms for %s %s-%s. "
            "Re-enabling Save and disabling DB overlay for this attempt.",
            DB_SAVE_GATE_WATCHDOG_MS,
            spec.station_key,
            spec.start_yyyymm,
            spec.end_yyyymm,
        )

        self._cancel_db_overlay_watchdog()
        self._end_db_save_gate()

        # Treat watchdog expiry like a failed overlay prefetch from the UI perspective.
        self._db_overlay_last_prefetch_failed = True

        try:
            self.db_overlay_checkbox.blockSignals(True)
            self.db_overlay_checkbox.setChecked(False)
            self.db_overlay_checkbox.setEnabled(False)
        finally:
            try:
                self.db_overlay_checkbox.blockSignals(False)
            except Exception:
                pass

        self.db_overlay_enabled = False
        if hasattr(self.start_screen, "set_db_overlay_enabled"):
            self.start_screen.set_db_overlay_enabled(False)

        self._clear_db_overlay_plot()

        self.statusBar().showMessage(
            "DB overlay timed out after 2 minutes; Save has been re-enabled.",
            10000
        )

        self.critical_dialog(
            title="DB Overlay Timeout",
            text="DB overlay prefetch timed out",
            info_text=(
                "The background DB overlay request did not complete within 2 minutes. "
                "Save has been re-enabled. DB overlay has been disabled for this attempt."
            ),
            details=(
                "Spec: {0} {1}-{2}\n"
                "Timeout: {3} ms\n"
                "The worker may still be blocked in DB/network I/O."
            ).format(
                spec.station_key,
                spec.start_yyyymm,
                spec.end_yyyymm,
                DB_SAVE_GATE_WATCHDOG_MS,
            ),
        )

    def _on_db_level2_watchdog_timeout(self, spec, gen):
        """Handle level 2 baseline watchdog timeout by releasing the Save gate and continuing without the baseline cache."""

        if gen != self._db_level2_gen:
            return
        if gen != self._db_level2_watchdog_gen:
            return

        logging.error(
            "DB baseline (L2) watchdog timeout after %s ms for %s %s-%s. "
            "Re-enabling Save and proceeding without the L2 baseline cache.",
            DB_SAVE_GATE_WATCHDOG_MS,
            spec.station_key,
            spec.start_yyyymm,
            spec.end_yyyymm,
        )

        self._cancel_db_level2_watchdog()
        self._end_db_save_gate()

        self.statusBar().showMessage(
            "DB baseline prefetch timed out after 2 minutes; Save has been re-enabled.",
            10000
        )

    def _prefetch_db_overlay_if_allowed(self, spec):
        """Start background DB overlay prefetch for the current request when the span and cache state allow it."""

        if not spec:
            return

        span = month_span_inclusive(spec.start_yyyymm, spec.end_yyyymm)
        if span > DB_OVERLAY_MAX_MONTHS:
            self.statusBar().showMessage(
                "DB overlay skipped: range is {0} months (max {1}).".format(span, DB_OVERLAY_MAX_MONTHS),
                7000
            )
            return

        key = self._db_cache_key(spec)
        if key in self._db_overlay_cache:
            station_obj = self._db_overlay_cache[key]
            self._cache_overlay_as_level2_baseline_if_compatible(spec, station_obj)

            self.statusBar().showMessage(
                "DB overlay cached for {0} {1}-{2}".format(spec.station_key, spec.start_yyyymm, spec.end_yyyymm),
                4000
            )
            return

        self._db_overlay_gen += 1
        gen = self._db_overlay_gen

        # Best-effort stop existing thread; stale results are ignored anyway.
        try:
            if self._db_overlay_thread is not None:
                self._db_overlay_thread.quit()
                self._db_overlay_thread.wait(100)

                # Cancel the watchdog tied to the abandoned attempt.
                self._cancel_db_overlay_watchdog()

                # Best effort: if we are replacing an in-flight overlay prefetch,
                # release one pending gate slot for the abandoned attempt.
                self._end_db_save_gate()

                self._db_overlay_thread = None
                self._db_overlay_worker = None
        except Exception:
            pass

        self._begin_db_save_gate()
        self._arm_db_overlay_watchdog(spec, gen)

        self.statusBar().showMessage(
            "Loading DB overlay in background for {0} {1}-{2}...".format(spec.station_key, spec.start_yyyymm, spec.end_yyyymm),
            0
        )

        self._db_overlay_thread = QtCore.QThread()
        if self._db_overlay_can_supply_l2_baseline(spec):
            self._db_overlay_worker = DbOverlayWorker(
                spec,
                gen,
                force_level_2=True,
                force_base_channel_data=True,
            )
        else:
            self._db_overlay_worker = DbOverlayWorker(spec, gen)
        self._db_overlay_worker.moveToThread(self._db_overlay_thread)

        self._db_overlay_thread.started.connect(self._db_overlay_worker.run)
        self._db_overlay_worker.finished.connect(self._on_db_overlay_prefetch_finished)
        self._db_overlay_worker.failed.connect(self._on_db_overlay_prefetch_failed)

        # cleanup
        self._db_overlay_worker.finished.connect(self._db_overlay_thread.quit)
        self._db_overlay_worker.failed.connect(self._db_overlay_thread.quit)
        self._db_overlay_thread.finished.connect(self._db_overlay_thread.deleteLater)

        self._db_overlay_thread.start()

    def _prefetch_db_level2_baseline_if_allowed(self, spec):
        """Start background level 2 baseline prefetch when the span and cache state allow it."""

        if not spec:
            return

        span = month_span_inclusive(spec.start_yyyymm, spec.end_yyyymm)
        if span > DB_OVERLAY_MAX_MONTHS:
            logging.info(
                "DB baseline prefetch skipped: range is %s months (max %s).",
                span, DB_OVERLAY_MAX_MONTHS
            )
            return

        key = self._db_level2_cache_key(spec)
        if key in self._db_level2_cache:
            return

        self._db_level2_gen += 1
        gen = self._db_level2_gen

        # Stop existing baseline thread if any (stale results ignored anyway).
        try:
            if self._db_level2_thread is not None:
                self._db_level2_thread.quit()
                self._db_level2_thread.wait(100)

                # Cancel the watchdog tied to the abandoned attempt.
                self._cancel_db_level2_watchdog()

                # Best effort: if we are replacing an in-flight level-2 prefetch,
                # release one pending Save-gate slot for the abandoned attempt.
                self._end_db_save_gate()

                self._db_level2_thread = None
                self._db_level2_worker = None
        except Exception:
            pass

        self._begin_db_save_gate()
        self._arm_db_level2_watchdog(spec, gen)

        self._db_level2_thread = QtCore.QThread()
        self._db_level2_worker = DbOverlayWorker(spec, gen, force_level_2=True, force_base_channel_data=True)
        self._db_level2_worker.moveToThread(self._db_level2_thread)

        self._db_level2_thread.started.connect(self._db_level2_worker.run)
        self._db_level2_worker.finished.connect(self._on_db_level2_baseline_finished)
        self._db_level2_worker.failed.connect(self._on_db_level2_baseline_failed)

        # cleanup
        self._db_level2_worker.finished.connect(self._db_level2_thread.quit)
        self._db_level2_worker.failed.connect(self._db_level2_thread.quit)
        self._db_level2_thread.finished.connect(self._db_level2_thread.deleteLater)

        self._db_level2_thread.start()

    def _on_db_overlay_prefetch_finished(self, spec, station_obj, gen):
        """Store completed DB overlay data, release the Save gate, and apply overlay if enabled."""

        if gen != self._db_overlay_gen:
            return

        self._cancel_db_overlay_watchdog()
        self._end_db_save_gate()

        key = self._db_cache_key(spec)
        self._db_overlay_cache[key] = station_obj
        self._cache_overlay_as_level2_baseline_if_compatible(spec, station_obj)

        # A successful prefetch means DB overlay is available again — re-enable the checkbox.
        self._db_overlay_last_prefetch_failed = False
        try:
            self.db_overlay_checkbox.setEnabled(True)
        except Exception:
            pass

        self.statusBar().showMessage(
            "DB overlay ready for {0} {1}-{2}".format(spec.station_key, spec.start_yyyymm, spec.end_yyyymm),
            6000
        )

        # Warn on missing database tide prediction.
        if getattr(station_obj, "load_warning_no_prd", False):
            box = QtWidgets.QMessageBox(self)
            box.setIcon(QtWidgets.QMessageBox.Warning)
            box.setWindowTitle("No Tide Prediction Data")
            box.setText("No database tide prediction data is available for plotting.")
            box.setInformativeText(station_obj.load_warning_no_prd_msg)
            box.setStandardButtons(QtWidgets.QMessageBox.Ok)
            box.exec_()

        # If the user already checked the box, draw as soon as data is ready.
        if self.db_overlay_enabled:
            self._apply_db_overlay_if_ready()

    def _on_db_overlay_prefetch_failed(self, spec, error_str, gen):
        """Handle DB overlay prefetch failure by releasing the Save gate and disabling overlay for the current load."""

        if gen != self._db_overlay_gen:
            return

        self._cancel_db_overlay_watchdog()
        self._end_db_save_gate()

        # Mark failure and disable the checkbox until a future success.
        self._db_overlay_last_prefetch_failed = True

        # Force overlay OFF and disable the checkbox.
        try:
            self.db_overlay_checkbox.blockSignals(True)
            self.db_overlay_checkbox.setChecked(False)   # turn it off
            self.db_overlay_checkbox.setEnabled(False)   # disable it
        finally:
            try:
                self.db_overlay_checkbox.blockSignals(False)
            except Exception:
                pass

        self.db_overlay_enabled = False

        if hasattr(self.start_screen, "set_db_overlay_enabled"):
            self.start_screen.set_db_overlay_enabled(False)

        self._clear_db_overlay_plot()

        self.statusBar().showMessage(
            "DB overlay failed for {0} {1}-{2}".format(spec.station_key, spec.start_yyyymm, spec.end_yyyymm),
            6000
        )

        self.critical_dialog(
            title="DB Overlay Error",
            text="Failed to prefetch DB overlay data",
            info_text=error_str,
            details=error_str
        )

    def _on_db_level2_baseline_finished(self, spec, station_obj, gen):
        """Store completed level 2 baseline data and release the Save gate."""

        if gen != self._db_level2_gen:
            return

        self._cancel_db_level2_watchdog()
        self._end_db_save_gate()

        self._db_level2_cache[self._db_level2_cache_key(spec)] = station_obj

        logging.info(
            "DB baseline (L2) ready for %s %s-%s (used for HF upsert diff)",
            spec.station_key, spec.start_yyyymm, spec.end_yyyymm
        )

        if self._db_debug_enabled():
            try:
                agg = getattr(station_obj, "aggregate_months", None)
                if not isinstance(agg, dict):
                    logging.info("DB baseline (L2) coverage: no aggregate_months dict found")
                else:
                    times = agg.get("time", {})
                    data = agg.get("data", {})
                    keys = [k for k in times.keys() if k in data and k not in ("ALL", "PRD")]
                    if not keys:
                        logging.info("DB baseline (L2) coverage: no sensor keys found in aggregate_months")
                    else:
                        k0 = sorted(keys)[0]
                        t = pd.to_datetime(times[k0])
                        if len(t) == 0:
                            logging.info("DB baseline (L2) coverage %s: empty time vector", k0)
                        else:
                            logging.info(
                                "DB baseline (L2) coverage %s: n=%d tmin=%s tmax=%s",
                                k0, len(t), t.min(), t.max()
                            )
            except Exception as e:
                logging.info("DB baseline (L2) coverage debug failed: %s", e)


    def _on_db_level2_baseline_failed(self, spec, error_str, gen):
        """Handle level 2 baseline prefetch failure and release the Save gate."""

        if gen != self._db_level2_gen:
            return

        self._cancel_db_level2_watchdog()
        self._end_db_save_gate()

        logging.warning(
            "DB baseline (L2) failed for %s %s-%s: %s",
            spec.station_key, spec.start_yyyymm, spec.end_yyyymm, error_str
        )

    def _db_overlay_station_from_cache(self, spec):
        """Return cached DB overlay station data for the given request spec."""

        if not spec:
            return None
        key = self._db_cache_key(spec)

        return self._db_overlay_cache.get(key)

    def _db_level2_station_from_cache(self, spec):
        """Return cached level 2 baseline station data for the given request spec."""

        if not spec:
            return None

        return self._db_level2_cache.get(self._db_level2_cache_key(spec))

    def _cache_overlay_as_level2_baseline_if_compatible(self, spec, station_obj):
        """
        Reuse a base-channel_data TS/L2 overlay station as the save-time L2
        baseline station.

        This avoids reading the same fd-multi/base-channel_data rows twice for
        TS loads. Regular s*.dat loads still need a separate L2 baseline because
        their overlay is raw/L0.
        """

        if not self._db_overlay_can_supply_l2_baseline(spec):
            return False

        self._db_level2_cache[self._db_level2_cache_key(spec)] = station_obj

        logging.info(
            "DB baseline (L2) reused from TS overlay cache for %s %s-%s",
            spec.station_key,
            spec.start_yyyymm,
            spec.end_yyyymm,
        )

        return True

    def _apply_db_overlay_if_ready(self):
        """If overlay is enabled and cached station is ready, tell Start() to draw it."""
        if not self.db_overlay_enabled:
            return False
        if not self.db_overlay_spec:
            return False

        station_db = self._db_overlay_station_from_cache(self.db_overlay_spec)
        if station_db is None:
            # still loading or was skipped
            return False

        # Delegate actual plotting to Start (my_widgets.py).
        try:
            if hasattr(self.start_screen, "set_db_overlay_station"):
                self.start_screen.set_db_overlay_station(station_db)
        except Exception:
            logging.exception("Failed applying DB overlay to plot")
            return False

        return True

    def _clear_db_overlay_plot(self):
        """Remove any DB overlay data currently shown on the plot."""

        try:
            if hasattr(self.start_screen, "clear_db_overlay"):
                self.start_screen.clear_db_overlay()
        except Exception:
            logging.exception("Failed clearing DB overlay from plot")

    def _query_fd_ts_metadata(self, uhslc_id):
        """Query and normalize FD and RQ time series metadata for the given station."""

        FD_QUALITY_ID = self.require_quality_id("fd")
        RQ_QUALITY_ID = self.require_quality_id("rq")
        HOURLY_RESOLUTION_ID = self.require_resolution_id("hourly")
        DAILY_RESOLUTION_ID = self.require_resolution_id("daily")
        UHSLC_SOURCE_PRIORITY = self.require_source_priority(self.fd_source_name)

        try:
            init_pool(minconn=1, maxconn=5)
            with get_conn() as conn:
                with conn.cursor() as cur:
                    sql = DATE_RANGE_BY_TIME_SERIES_QUALITY
                    params = (
                        int(uhslc_id),
                        int(FD_QUALITY_ID),
                        int(RQ_QUALITY_ID),
                        int(HOURLY_RESOLUTION_ID),
                        int(DAILY_RESOLUTION_ID),
                    )
                    _log_sql(
                        cur,
                        sql,
                        params,
                        spec={
                            "query": "date_range_by_time_series_quality",
                            "uhslc_id": int(uhslc_id),
                            "fd_quality_id": int(FD_QUALITY_ID),
                            "rq_quality_id": int(RQ_QUALITY_ID),
                            "resolution_ids": [int(HOURLY_RESOLUTION_ID), int(DAILY_RESOLUTION_ID)],
                            "source_priority": int(UHSLC_SOURCE_PRIORITY),
                        },
                    )
                    cur.execute(sql, params)
                    rows = cur.fetchall()
                    cols = [d[0] for d in cur.description]

            if not rows:
                return pd.DataFrame(
                    columns=[
                        "time_series_id", "quality_id", "resolution_id", "id_from_source",
                        "priority", "date_begin", "date_end", "uhslc_id"
                    ]
                )

            df = pd.DataFrame(rows, columns=cols)
            if not df.empty:
                df["quality_id"] = pd.to_numeric(df["quality_id"], errors="coerce")
                df["resolution_id"] = pd.to_numeric(df["resolution_id"], errors="coerce")
                df["time_series_id"] = pd.to_numeric(df["time_series_id"], errors="coerce")
                df["priority"] = pd.to_numeric(df["priority"], errors="coerce")
                df["date_begin"] = pd.to_datetime(df["date_begin"], errors="coerce")
                df["date_end"] = pd.to_datetime(df["date_end"], errors="coerce")
                df["id_from_source"] = df["id_from_source"].astype(str)

            return df

        except Exception:

            logging.exception(
                "FD metadata lookup failed for uhslc_id=%s while querying date_range_by_time_series_quality. "
                "Because FD reconcile metadata should normally be readable from the database/materialized view, "
                "this suggests a database connectivity, pool, query-execution, permissions, or database-state "
                "problem rather than a normal missing-station setup case. Please verify database access and "
                "connection health; if the issue persists, contact the database administrator to confirm the "
                "FD/RQ metadata path and materialized view are available and healthy. "
                "Select ok and proceed as normal understanding the following for this station:\n\n"
                "1.) fast-delivery products/files can still be generated and saved locally per usual.\n"
                "2.) the interface and non-FD workflows can still proceed as normal.\n"
                "3.) save-time fast-delivery database reconcile/upsert/delete ops will not occur for this run.\n"
                "4.) traceback/details for the underlying failure follow in the log.\n",
                uhslc_id,
            )

            return pd.DataFrame()

    def _upsert_fd_primary_channel_from_saved_products(self, station, is_test_mode=False):
        """
        Upsert monthly primary_channel rows based on the exact reliable_sensor that
        was written into each saved hourly FD header.

        For each saved month:
          - resolve the active connection for the month
          - resolve the Water Level channel on that connection whose name matches
            the saved reliable_sensor
          - upsert (time, channel_id, connection_id) into primary_channel
        """

        try:
            if station is None:
                return

            cached_rows = getattr(station, "_last_saved_fd_primary_channels", None)
            if not cached_rows:
                logging.info("primary_channel upsert skipped: no saved FD primary-channel cache on station.")
                return

            if not getattr(station, "month_collection", None):
                logging.info("primary_channel upsert skipped: station has no month collection.")
                return

            station_db_id = getattr(station, "station_db_id", None)
            uhslc_code = getattr(station, "uhslc_code", None) or "<unknown>"
            uhslc_id = getattr(station, "uhslc_id", None)

            if station_db_id is None:
                logging.warning(
                    "primary_channel upsert skipped for station=%s uhslc_id=%s: missing station_db_id on Station object.",
                    uhslc_code,
                    uhslc_id,
                )
                return

            execute_writes = self._db_live_writes_enabled(
                is_test_mode,
                "primary_channel upsert",
            )
            executed_rows = 0

            init_pool(minconn=1, maxconn=5)
            with get_conn() as conn:
                with conn.cursor() as cur:
                    for row in cached_rows:
                        month_start = pd.to_datetime(row["month_start"], utc=True, errors="coerce")
                        if pd.isna(month_start):
                            logging.warning(
                                "primary_channel upsert skipped for uhslc_code=%s: invalid month_start in cache row=%r",
                                uhslc_code, row
                            )
                            continue

                        month_end = month_start + pd.DateOffset(months=1)
                        sensor_name = str(row["sensor_name"]).strip()

                        # Resolve the connection active for this month.
                        conn_sql = CONNECTION_FOR_DB_STATION_ID_IN_RANGE
                        conn_params = (
                            int(station_db_id),
                            month_start.to_pydatetime(),
                            month_end.to_pydatetime(),
                        )
                        _log_sql(
                            cur,
                            conn_sql,
                            conn_params,
                            spec={
                                "query": "connection_for_db_station_id_in_range",
                                "station_db_id": int(station_db_id),
                                "uhslc_code": uhslc_code,
                                "uhslc_id": uhslc_id,
                                "month_start": str(month_start),
                                "month_end": str(month_end),
                            },
                        )
                        cur.execute(conn_sql, conn_params)
                        conn_row = cur.fetchone()

                        if not conn_row:
                            logging.warning(
                                "primary_channel upsert skipped for uhslc_code=%s month=%s: "
                                "no active connection found in requested range. "
                                "FD files were still saved normally, but primary_channel will not be updated.",
                                uhslc_code,
                                month_start.strftime("%Y-%m"),
                            )
                            continue

                        conn_cols = [d[0] for d in cur.description]
                        conn_map = dict(zip(conn_cols, conn_row))
                        connection_id = conn_map["id"]

                        # Resolve Water Level channels on that connection and match by channel name.
                        ch_sql = CHANNELS_FOR_CONNECTION
                        ch_params = (int(connection_id),)
                        _log_sql(
                            cur,
                            ch_sql,
                            ch_params,
                            spec={
                                "query": "channels_for_connection",
                                "connection_id": int(connection_id),
                            },
                        )
                        cur.execute(ch_sql, ch_params)
                        ch_rows = cur.fetchall()
                        ch_cols = [d[0] for d in cur.description]

                        if not ch_rows:
                            logging.warning(
                                "primary_channel upsert skipped for uhslc_code=%s month=%s connection_id=%s: "
                                "no Water Level channels found for the resolved connection. "
                                "FD files were still saved normally, but primary_channel will not be updated.",
                                uhslc_code,
                                month_start.strftime("%Y-%m"),
                                connection_id,
                            )
                            continue

                        channels_df = pd.DataFrame(ch_rows, columns=ch_cols)
                        channels_df["channel_name_norm"] = (
                            channels_df["channel_name"]
                            .astype(str)
                            .str.strip()
                            .str.lower()
                        )

                        match_df = channels_df.loc[
                            channels_df["channel_name_norm"] == sensor_name.lower()
                        ].copy()

                        if match_df.empty:
                            logging.warning(
                                "primary_channel upsert skipped for uhslc_code=%s month=%s connection_id=%s: "
                                "no Water Level channel matched saved primary sensor '%s'. "
                                "FD files were still saved normally, but primary_channel will not be updated.",
                                uhslc_code,
                                month_start.strftime("%Y-%m"),
                                connection_id,
                                sensor_name,
                            )
                            continue

                        channel_id = int(match_df.iloc[0]["channel_id"])

                        upsert_sql = PRIMARY_CHANNEL_UPSERT
                        upsert_params = (
                            month_start.to_pydatetime(),
                            channel_id,
                            int(connection_id),
                        )
                        _log_sql(
                            cur,
                            upsert_sql,
                            upsert_params,
                            spec={
                                "query": "primary_channel_upsert",
                                "time": str(month_start),
                                "channel_id": int(channel_id),
                                "connection_id": int(connection_id),
                                "sensor_name": sensor_name,
                            },
                        )

                        if execute_writes:
                            cur.execute(upsert_sql, upsert_params)
                            executed_rows += 1
                            action = "upserted"
                        else:
                            action = "logged"

                        logging.info(
                            "primary_channel %s | uhslc_code=%s | month=%s | connection_id=%s | "
                            "channel_id=%s | sensor_name=%s",
                            action,
                            uhslc_code,
                            month_start.strftime("%Y-%m"),
                            connection_id,
                            channel_id,
                            sensor_name,
                        )

                if execute_writes:
                    conn.commit()
                    logging.info("primary_channel upsert committed | rows=%d", executed_rows)

        except Exception:
            logging.exception("primary_channel upsert hook failed")

    def _query_fd_db_df(self, time_series_id, resolution_id, priority, start_time=None, end_time=None):
        """
        Query the current FD rows in time_series_data for the exact target series.
        Returns DataFrame(time, value), normalized the same way the level-3 script uses DB data.
        """

        FD_QUALITY_ID = self.require_quality_id("fd")

        if start_time is None:
            start_time = pd.Timestamp("1800-01-01", tz="UTC")
        else:
            start_time = pd.to_datetime(start_time, utc=True)

        if end_time is None:
            end_time = pd.Timestamp("2100-01-01", tz="UTC")
        else:
            end_time = pd.to_datetime(end_time, utc=True)

        try:
            init_pool(minconn=1, maxconn=5)
            with get_conn() as conn:
                with conn.cursor() as cur:
                    sql = TIME_SERIES_DATA_BY_TARGET_AND_RANGE
                    params = (
                        int(time_series_id),
                        int(FD_QUALITY_ID),
                        int(resolution_id),
                        int(priority),
                        start_time.to_pydatetime(),
                        end_time.to_pydatetime(),
                    )
                    _log_sql(
                        cur,
                        sql,
                        params,
                        spec={
                            "query": "time_series_data_by_target_and_range",
                            "table": "time_series_data",
                            "time_series_id": int(time_series_id),
                            "quality_id": int(FD_QUALITY_ID),
                            "resolution_id": int(resolution_id),
                            "priority": int(priority),
                            "start_time": start_time.to_pydatetime(),
                            "end_time": end_time.to_pydatetime(),
                        },
                    )
                    cur.execute(sql, params)
                    rows = cur.fetchall()
                    cols = [d[0] for d in cur.description]

            if not rows:
                return pd.DataFrame(columns=["time", "value"])

            df = pd.DataFrame(rows, columns=cols)
            df["time"] = pd.to_datetime(df["time"], utc=True)
            df["value"] = pd.to_numeric(df["value"], errors="coerce")

            if resolution_id == self.require_resolution_id("daily") and not df.empty:
                df["time"] = df["time"].dt.floor("D") + pd.Timedelta(hours=12)

            df = (
                df[["time", "value"]]
                .sort_values("time")
                .drop_duplicates("time", keep="last")
                .reset_index(drop=True)
            )

            return df

        except Exception:

            logging.exception(
                "FD DB query failed for time_series_id=%s resolution_id=%s priority=%s",
                time_series_id, resolution_id, priority
            )

            return pd.DataFrame(columns=["time", "value"])

    def _build_fd_local_df(self, station, resolution):
        """Build a normalized local FD dataframe from the most recently saved FD products."""

        cache = getattr(station, "_last_saved_fd_products", None)
        if not cache:
            return pd.DataFrame(columns=["time", "value"])

        pack = cache.get(resolution, {}) or {}
        times = pack.get("time", [])
        vals_mm = pack.get("value_mm", [])

        if len(times) == 0:
            return pd.DataFrame(columns=["time", "value"])

        first_time = times[0]
        if isinstance(first_time, (int, float, np.integer, np.floating)):
            dt_list = [station.datenum_to_datetime(x) for x in times]
        else:
            dt_list = times

        df = pd.DataFrame({
            "time": pd.to_datetime(dt_list, errors="coerce", utc=True),
            "value": pd.to_numeric(vals_mm, errors="coerce") / 1000.0,
        })

        if resolution == "hourly" and not df.empty:
            df["time"] = df["time"].dt.round("h")
        elif resolution == "daily" and not df.empty:
            df["time"] = df["time"].dt.floor("D") + pd.Timedelta(hours=12)

        df = (
            df[["time", "value"]]
            .sort_values("time")
            .drop_duplicates("time", keep="last")
            .reset_index(drop=True)
        )

        return df

    def _build_fd_web_df(self, station, station_num, resolution):
        """Fetch FD data from the web source and return it as a normalized dataframe."""

        try:
            t_web, v_web = self.start_screen.fetch_uh_web_fd_data(station_num, resolution)
        except Exception:
            logging.exception("FD web fetch failed for station=%s resolution=%s", station_num, resolution)
            return pd.DataFrame(columns=["time", "value"])

        if t_web is None or v_web is None or len(t_web) == 0:
            return pd.DataFrame(columns=["time", "value"])

        dt_list = [station.datenum_to_datetime(x) for x in t_web]

        df = pd.DataFrame({
            "time": pd.to_datetime(dt_list, errors="coerce"),
            "value": pd.to_numeric(v_web, errors="coerce") / 1000.0,  # mm -> m
        })

        if resolution == "daily" and not df.empty:
            df["time"] = pd.to_datetime(df["time"]).dt.floor("D") + pd.Timedelta(hours=12)

        df = (
            df[["time", "value"]]
            .sort_values("time")
            .drop_duplicates("time", keep="last")
            .reset_index(drop=True)
        )

        return df

    def _enumerate_fd_versions_and_windows(self, meta_df, resolution_id):
        """
        Return one FD target per id_from_source for this resolution and for the
        configured UHSLC source priority.

        This mirrors the updater script behavior:
        - process every version separately
        - derive FD window from that version's RQ row
        - latest version => [rq_begin, +inf)
        - non-latest version => [rq_begin, rq_end]
        - missing RQ => full FD reconcile for that version
        - only consider FD targets at the configured UHSLC source priority
        """

        FD_QUALITY_ID = self.require_quality_id("fd")
        RQ_QUALITY_ID = self.require_quality_id("rq")
        UHSLC_SOURCE_PRIORITY = self.require_source_priority(self.fd_source_name)

        if meta_df is None or meta_df.empty:
            return []

        meta_res = meta_df[
            (meta_df["resolution_id"] == int(resolution_id)) &
            (meta_df["priority"] == int(UHSLC_SOURCE_PRIORITY))
        ].copy()
        if meta_res.empty:
            logging.info(
                "No FD/RQ metadata rows found for resolution_id=%s source_priority=%s",
                resolution_id,
                UHSLC_SOURCE_PRIORITY,
            )
            return []

        fd_candidates = meta_res[meta_res["quality_id"] == int(FD_QUALITY_ID)].copy()
        if fd_candidates.empty:
            logging.info(
                "No FD metadata candidates found for resolution_id=%s source_priority=%s",
                resolution_id,
                UHSLC_SOURCE_PRIORITY,
            )
            return []

        raw_versions = fd_candidates["id_from_source"].dropna().astype(str).unique()

        versions = []
        for id_from_source in sorted(raw_versions):
            if not id_from_source:
                continue
            if not id_from_source[-1].isalpha():
                logging.warning(
                    "FD id_from_source is unversioned/non-lettered; skipping for UHSLC-source-priority FD reconcile. "
                    "id_from_source=%s resolution_id=%s source_priority=%s",
                    id_from_source,
                    resolution_id,
                    UHSLC_SOURCE_PRIORITY,
                )
                continue
            versions.append(id_from_source)

        if not versions:
            logging.warning(
                "No valid lettered FD versions found after filtering unversioned/non-lettered "
                "UHSLC-source-priority FD id_from_source values. resolution_id=%s source_priority=%s",
                resolution_id,
                UHSLC_SOURCE_PRIORITY,
            )
            return []

        latest_id_from_source = versions[-1]
        choices = []

        for id_from_source in versions:
            is_latest_version = (id_from_source == latest_id_from_source)

            # FD row is required because it contains the exact time_series_id / priority target.
            fd_row = meta_res[
                (meta_res["quality_id"] == int(FD_QUALITY_ID)) &
                (meta_res["id_from_source"] == id_from_source)
            ].copy()

            if fd_row.empty:
                logging.warning(
                    "FD metadata missing for version at UHSLC source priority; skipping. "
                    "id_from_source=%s resolution_id=%s source_priority=%s",
                    id_from_source,
                    resolution_id,
                    UHSLC_SOURCE_PRIORITY,
                )
                continue

            fd_row = fd_row.sort_values(["date_begin", "date_end"]).iloc[0]

            rq_row = meta_res[
                (meta_res["quality_id"] == int(RQ_QUALITY_ID)) &
                (meta_res["id_from_source"] == id_from_source)
            ].copy()

            rq_exists = not rq_row.empty
            rq_begin = None
            rq_end = None

            if rq_exists:
                rq_row = rq_row.sort_values(["date_begin", "date_end"]).iloc[0]
                rq_begin = rq_row["date_begin"]
                rq_end = rq_row["date_end"]
                fd_window_start = rq_begin
                fd_window_end = None if is_latest_version else rq_end
            else:
                logging.warning(
                    "No RQ bounds found for id_from_source=%s resolution_id=%s source_priority=%s. "
                    "Proceeding with FULL FD reconcile.",
                    id_from_source,
                    resolution_id,
                    UHSLC_SOURCE_PRIORITY,
                )
                fd_window_start = None
                fd_window_end = None

            choices.append({
                "id_from_source": id_from_source,
                "latest_id_from_source": latest_id_from_source,
                "is_latest_version": is_latest_version,
                "rq_exists": rq_exists,
                "rq_begin": self._naive(rq_begin),
                "rq_end": self._naive(rq_end),
                "fd_window_start": self._naive(fd_window_start),
                "fd_window_end": self._naive(fd_window_end),
                "time_series_id": int(fd_row["time_series_id"]),
                "priority": int(fd_row["priority"]),
            })

        return choices

    def _fd_current_utc_cutoff(self):
        """Return the current UTC timestamp used as the strict FD future-data cutoff."""

        return pd.Timestamp.now(tz="UTC").floor("s")


    def _filter_fd_delete_params_to_window(self, delete_params, start_time, end_time):
        """Keep only FD delete timestamps inside the effective inclusive save window."""

        start_ts = pd.to_datetime(start_time, utc=True)
        end_ts = pd.to_datetime(end_time, utc=True)
        filtered = []

        for time_series_id, quality_id, resolution_id, priority, times in delete_params:
            kept_times = [
                t for t in times
                if start_ts <= pd.to_datetime(t, utc=True) <= end_ts
            ]
            if kept_times:
                filtered.append((time_series_id, quality_id, resolution_id, priority, kept_times))

        return filtered


    def _filter_fd_upsert_params_to_window(self, upsert_params, start_time, end_time):
        """Keep only FD upsert rows inside the effective inclusive save window."""

        start_ts = pd.to_datetime(start_time, utc=True)
        end_ts = pd.to_datetime(end_time, utc=True)

        return [
            p for p in upsert_params
            if start_ts <= pd.to_datetime(p[0], utc=True) <= end_ts
        ]

    def _clip_fd_df_to_window(self, df, start_time, end_time):
        """Clip an FD dataframe to the requested inclusive time window."""

        if df is None or df.empty:
            return pd.DataFrame(columns=["time", "value"])

        out = df.copy()
        out["time"] = pd.to_datetime(out["time"], errors="coerce")

        start_time = pd.to_datetime(start_time, errors="coerce") if start_time is not None else None
        end_time = pd.to_datetime(end_time, errors="coerce") if end_time is not None else None

        # Normalize any tz-aware timestamps to naive UTC-like timestamps
        if hasattr(out["time"].dt, "tz") and out["time"].dt.tz is not None:
            out["time"] = out["time"].dt.tz_convert(None)

        if start_time is not None and getattr(start_time, "tzinfo", None) is not None:
            start_time = start_time.tz_convert(None) if hasattr(start_time, "tz_convert") else start_time.tz_localize(None)

        if end_time is not None and getattr(end_time, "tzinfo", None) is not None:
            end_time = end_time.tz_convert(None) if hasattr(end_time, "tz_convert") else end_time.tz_localize(None)

        if start_time is not None:
            out = out[out["time"] >= start_time]
        if end_time is not None:
            out = out[out["time"] <= end_time]

        return out.reset_index(drop=True)

    def _fd_save_window_bounds(self, target_start_yyyymm, target_end_yyyymm, resolution):
        """
        Convert the requested save month range into an inclusive timestamp window.

        hourly:
            [YYYY-MM-01 00:00:00, first instant of next month - 1 hour]

        daily:
            [YYYY-MM-01 12:00:00, last day of end month at 12:00:00]
        """

        if target_start_yyyymm is None or target_end_yyyymm is None:
            raise ValueError("Both target_start_yyyymm and target_end_yyyymm must be specified.")

        def yyyymm_to_dt_start(yyyymm: int) -> datetime:
            """Convert a YYYYMM integer into a datetime representing the first day of that month at 00:00:00."""

            y = int(yyyymm) // 100
            m = int(yyyymm) % 100

            return datetime(y, m, 1, 0, 0, 0)

        def next_month(dt: datetime) -> datetime:
            """Return a datetime representing the first day of the month immediately following the given datetime."""

            y, m = dt.year, dt.month

            return datetime(y + 1, 1, 1, 0, 0, 0) if m == 12 else datetime(y, m + 1, 1, 0, 0, 0)

        start_dt = pd.Timestamp(yyyymm_to_dt_start(int(target_start_yyyymm)), tz="UTC")
        end_dt_exclusive = pd.Timestamp(next_month(yyyymm_to_dt_start(int(target_end_yyyymm))), tz="UTC")

        if resolution == "hourly":
            compare_start = start_dt
            compare_end = end_dt_exclusive - pd.Timedelta(hours=1)
        elif resolution == "daily":
            compare_start = start_dt + pd.Timedelta(hours=12)
            compare_end = (end_dt_exclusive - pd.Timedelta(days=1)) + pd.Timedelta(hours=12)
        else:
            raise ValueError(f"Unsupported resolution for FD save window: {resolution}")

        return compare_start, compare_end

    def _build_fd_upsert_params(self, local_df, db_df, time_series_id, priority, resolution_id):
        """
        Build FD UPSERT params by comparing saved FD output to current DB rows,
        matching the level-3 script's DB-driven comparison model.
        """

        FD_QUALITY_ID = self.require_quality_id("fd")
        ATOL_M = 1e-3
        last_update = pd.Timestamp.now(tz="UTC").round("min").tz_localize(None)

        local_df = local_df.copy()
        db_df = db_df.copy()

        if not local_df.empty:
            local_df["time"] = pd.to_datetime(local_df["time"], utc=True)
        if not db_df.empty:
            db_df["time"] = pd.to_datetime(db_df["time"], utc=True)

        local_times = pd.DatetimeIndex(local_df["time"]).unique() if not local_df.empty else pd.DatetimeIndex([])
        db_times = pd.DatetimeIndex(db_df["time"]).unique() if not db_df.empty else pd.DatetimeIndex([])

        added_times = local_times.difference(db_times)
        value_changed_times = pd.DatetimeIndex([])

        if len(local_times) > 0 and len(db_times) > 0:
            intersection_times = local_times.intersection(db_times)
            if len(intersection_times) > 0:
                local_map = local_df.set_index("time").loc[intersection_times, "value"].sort_index()
                db_map = db_df.set_index("time").loc[intersection_times, "value"].sort_index()
                same = np.isclose(local_map.values, db_map.values, atol=ATOL_M, rtol=0.0, equal_nan=True)
                diff_mask = ~same
                if diff_mask.any():
                    value_changed_times = pd.DatetimeIndex(local_map.index[diff_mask])

        upsert_times = added_times.union(value_changed_times)

        params = []
        if len(upsert_times) > 0:
            tsdb_df = (
                local_df.set_index("time")
                .loc[list(upsert_times), ["value"]]
                .sort_index()
                .reset_index()
                .reset_index(drop=True)
            )

            tsdb_df["last_update"] = last_update
            tsdb_df["priority"] = int(priority)
            tsdb_df["data_flag_id"] = None
            tsdb_df["quality_id"] = int(FD_QUALITY_ID)
            tsdb_df["resolution_id"] = int(resolution_id)
            tsdb_df["time_series_id"] = int(time_series_id)

            params = [
                (
                    row["time"].to_pydatetime() if hasattr(row["time"], "to_pydatetime") else row["time"],
                    None if pd.isna(row["value"]) else float(row["value"]),
                    row["last_update"].to_pydatetime() if hasattr(row["last_update"], "to_pydatetime") else row["last_update"],
                    int(row["priority"]),
                    row["data_flag_id"],
                    int(row["quality_id"]),
                    int(row["resolution_id"]),
                    int(row["time_series_id"]),
                )
                for _, row in tsdb_df.iterrows()
            ]

        return {
            "added_count": int(len(added_times)),
            "changed_count": int(len(value_changed_times)),
            "upsert_count": int(len(upsert_times)),
            "params": params,
        }

    def _build_fd_window_clip_delete_params(
        self,
        full_db_df,
        time_series_id,
        priority,
        resolution_id,
        fd_window_start,
        fd_window_end,
        batch_size=10000,
    ):
        """
        Build delete params for existing FD rows that fall OUTSIDE the allowed
        version window. This mirrors the updater script's behavior:

        - delete rows before fd_window_start
        - delete rows after fd_window_end (only for non-latest versions)

        Returns:
            {
                "delete_count": int,
                "delete_stmt_count": int,
                "params": list[tuple]
            }
        """

        if full_db_df is None or full_db_df.empty:

            return {
                "delete_count": 0,
                "delete_stmt_count": 0,
                "params": [],
            }

        db_df = full_db_df.copy()
        db_df["time"] = pd.to_datetime(db_df["time"], utc=True, errors="coerce")
        db_df = db_df.dropna(subset=["time"]).sort_values("time").reset_index(drop=True)

        delete_times = pd.DatetimeIndex([])

        if fd_window_start is not None:
            start_ts = pd.to_datetime(fd_window_start, utc=True)
            delete_times = delete_times.union(db_df.loc[db_df["time"] < start_ts, "time"])

        if fd_window_end is not None:
            end_ts = pd.to_datetime(fd_window_end, utc=True)
            delete_times = delete_times.union(db_df.loc[db_df["time"] > end_ts, "time"])

        delete_times = pd.DatetimeIndex(delete_times).sort_values().unique()

        if len(delete_times) == 0:
            return {
                "delete_count": 0,
                "delete_stmt_count": 0,
                "params": [],
            }

        FD_QUALITY_ID = self.require_quality_id("fd")

        params = []
        for chunk in self._chunk_datetime_index(delete_times, batch_size=batch_size):
            params.append((
                int(time_series_id),
                int(FD_QUALITY_ID),
                int(resolution_id),
                int(priority),
                list(pd.DatetimeIndex(chunk).to_pydatetime()),
            ))

        return {
            "delete_count": int(len(delete_times)),
            "delete_stmt_count": int(len(params)),
            "params": params,
        }


    def _reconcile_fd_db_from_saved_products(self, station, target_start_yyyymm, target_end_yyyymm, is_test_mode=False):
        """
        Save-time FD DB reconcile (small-window mode):
          - use date_range_by_time_series_quality-derived metadata for version/window logic
          - bound the reconcile to the selected save month range
          - compare saved FD output vs current DB FD rows only inside the overlap
            between the save window and the version's allowed FD window
          - preserve full-FD reconcile fallback when RQ bounds are missing
          - do NOT perform full-version window clipping here; the daily updater
            remains the authoritative full reconciler
          - log the DELETE / UPSERT statements and optionally execute them
        """

        if self._db_ops_disabled_for_span or not self._db_ops_allowed_for_spec(self.db_overlay_spec):
            self._show_db_ops_disabled_warning_once()
            logging.info(
                "FD DB reconcile skipped: DB work disabled for loaded span > %s months.",
                DB_OVERLAY_MAX_MONTHS
            )
            return

        try:
            if station is None:
                return

            if not getattr(station, "_last_saved_fd_products", None):
                logging.info("FD DB upsert skipped: no saved fast-delivery products cached on station.")
                return

            if not getattr(station, "month_collection", None):
                logging.info("FD DB upsert skipped: station has no month collection.")
                return

            # First, upsert monthly primary_channel rows using the exact sensor that was
            # written into each hourly FD header. This path is independent of the
            # date_range_by_time_series_quality matview and should proceed whenever the
            # required connection/channel metadata can be resolved.
            self._upsert_fd_primary_channel_from_saved_products(station, is_test_mode=is_test_mode)

            uhslc_id = getattr(station, "uhslc_id", None)
            uhslc_code = getattr(station, "uhslc_code", None) or "<unknown>"

            if uhslc_id is None:
                logging.warning(
                    "FD DB upsert skipped for station=%s: missing explicit uhslc_id on Station object.",
                    uhslc_code,
                )
                return

            meta_df = self._query_fd_ts_metadata(int(uhslc_id))

            if meta_df.empty:
                logging.warning(
                    "No FD/RQ metadata rows were found in date_range_by_time_series_quality for uhslc_id=%s "
                    "(filtered to hourly/daily resolutions). This usually means the station/version/resolution "
                    "has not been fully set up for FD in the database yet, there is no qualifying FD/RQ data for "
                    "the materialized view to summarize yet, or the materialized view needs refresh. "
                    "If FD database storage is needed for this station, request that the appropriate time_series "
                    "record(s) and associated FD/RQ metadata be added/verified in the database for the relevant "
                    "station/version/resolution and that the materialized view be refreshed if needed. "
                    "Select ok and proceed as normal understanding the following for this station:\n\n"
                    "1.) fast-delivery products/files can still be generated and saved per usual.\n"
                    "2.) the interface and non-FD workflows can still proceed as normal.\n"
                    "3.) save-time fast-delivery database reconcile/upsert/delete ops will not occur.\n"
                    "4.) other database features remain unaffected if otherwise configured.\n",
                    uhslc_id,
                )
                return

            execute_writes = self._db_live_writes_enabled(
                is_test_mode,
                "FD DB reconcile",
            )

            for resolution in ("hourly", "daily"):
                resolution_id = self.require_resolution_id(resolution)

                local_df = self._build_fd_local_df(station, resolution)
                if local_df.empty:
                    logging.info(
                        "FD DB upsert skipped for uhslc_id=%s resolution=%s: local dataframe empty",
                        uhslc_id, resolution
                    )
                    continue

                save_window_start, save_window_end = self._fd_save_window_bounds(
                    target_start_yyyymm=target_start_yyyymm,
                    target_end_yyyymm=target_end_yyyymm,
                    resolution=resolution,
                )

                requested_save_window_end = save_window_end
                now_utc = self._fd_current_utc_cutoff()

                # Strict future-data guard for FD time_series_data writes.
                # The requested save range can cover the rest of the current month,
                # but FD rows whose valid time is after the current UTC instant must
                # not be inserted, updated, or deleted.
                if save_window_end > now_utc:
                    save_window_end = now_utc
                    logging.info(
                        "FD DB reconcile future cutoff applied | uhslc_id=%s | resolution=%s | "
                        "requested_save_window_end=%s | effective_save_window_end=%s",
                        uhslc_id,
                        resolution,
                        requested_save_window_end,
                        save_window_end,
                    )

                if save_window_end < save_window_start:
                    logging.info(
                        "FD DB reconcile skipped: selected range is entirely in the future | "
                        "uhslc_id=%s | resolution=%s | save_window_start=%s | "
                        "requested_save_window_end=%s | now_utc=%s",
                        uhslc_id,
                        resolution,
                        save_window_start,
                        requested_save_window_end,
                        now_utc,
                    )
                    continue

                local_df = self._clip_fd_df_to_window(
                    local_df,
                    save_window_start,
                    save_window_end,
                )

                if local_df.empty:
                    logging.info(
                        "FD DB upsert skipped for uhslc_id=%s resolution=%s: "
                        "local dataframe empty after save-window/future clip (%s..%s)",
                        uhslc_id, resolution, save_window_start, save_window_end
                    )
                    continue

                choices = self._enumerate_fd_versions_and_windows(
                    meta_df,
                    resolution_id=resolution_id,
                )
                if not choices:
                    logging.warning(
                        "FD DB upsert skipped for uhslc_id=%s resolution=%s: could not resolve any FD version/window targets",
                        uhslc_id, resolution
                    )
                    continue

                step = pd.Timedelta(hours=1) if resolution == "hourly" else pd.Timedelta(days=1)

                local_min = pd.to_datetime(local_df["time"].min(), utc=True)
                local_max = pd.to_datetime(local_df["time"].max(), utc=True)

                for choice in choices:
                    compare_start = local_min
                    compare_end = local_max

                    if choice["fd_window_start"] is not None:
                        compare_start = max(compare_start, pd.to_datetime(choice["fd_window_start"], utc=True))

                    if choice["fd_window_end"] is not None:
                        compare_end = min(compare_end, pd.to_datetime(choice["fd_window_end"], utc=True))

                    if compare_end < compare_start:
                        logging.info(
                            "FD DB reconcile skipped for uhslc_id=%s resolution=%s id_from_source=%s: "
                            "no overlap between local data and version window",
                            uhslc_id, resolution, choice["id_from_source"]
                        )
                        continue

                    local_df_clip = self._clip_fd_df_to_window(
                        local_df,
                        compare_start,
                        compare_end,
                    )

                    if local_df_clip.empty:
                        logging.info(
                            "FD DB reconcile skipped for uhslc_id=%s resolution=%s id_from_source=%s: "
                            "local dataframe empty after version-window clip",
                            uhslc_id, resolution, choice["id_from_source"]
                        )
                        continue

                    db_df_clip = self._query_fd_db_df(
                        time_series_id=choice["time_series_id"],
                        resolution_id=resolution_id,
                        priority=choice["priority"],
                        start_time=compare_start,
                        end_time=compare_end,
                    )

                    logging.info(
                        "FD version window | uhslc_id=%s | resolution=%s | id_from_source=%s | "
                        "is_latest_version=%s | rq_exists=%s | rq_begin=%s | rq_end=%s | "
                        "fd_window_start=%s | fd_window_end=%s",
                        uhslc_id,
                        resolution,
                        choice["id_from_source"],
                        choice["is_latest_version"],
                        choice["rq_exists"],
                        choice["rq_begin"],
                        choice["rq_end"],
                        choice["fd_window_start"],
                        choice["fd_window_end"],
                    )

                    delete_info = self._build_fd_delete_params(
                        local_df=local_df_clip,
                        db_df=db_df_clip,
                        time_series_id=choice["time_series_id"],
                        priority=choice["priority"],
                        resolution_id=resolution_id,
                    )

                    diff_info = self._build_fd_upsert_params(
                        local_df=local_df_clip,
                        db_df=db_df_clip,
                        time_series_id=choice["time_series_id"],
                        priority=choice["priority"],
                        resolution_id=resolution_id,
                    )

                    original_delete_count = int(delete_info["delete_count"])
                    original_upsert_count = int(diff_info["upsert_count"])

                    all_delete_params = self._filter_fd_delete_params_to_window(
                        delete_info["params"],
                        compare_start,
                        compare_end,
                    )
                    filtered_upsert_params = self._filter_fd_upsert_params_to_window(
                        diff_info["params"],
                        compare_start,
                        compare_end,
                    )

                    total_delete_count = sum(len(p[4]) for p in all_delete_params)
                    total_delete_stmt_count = len(all_delete_params)
                    diff_info["params"] = filtered_upsert_params
                    diff_info["upsert_count"] = len(filtered_upsert_params)

                    if total_delete_count != original_delete_count or diff_info["upsert_count"] != original_upsert_count:
                        logging.info(
                            "FD DB future/window guard filtered mutations | uhslc_id=%s | resolution=%s | "
                            "id_from_source=%s | compare_start=%s | compare_end=%s | "
                            "delete_times_before=%d | delete_times_after=%d | "
                            "upserts_before=%d | upserts_after=%d",
                            uhslc_id,
                            resolution,
                            choice["id_from_source"],
                            compare_start,
                            compare_end,
                            original_delete_count,
                            total_delete_count,
                            original_upsert_count,
                            diff_info["upsert_count"],
                        )

                    logging.info(
                        "FD reconcile spec | uhslc_id=%s | resolution=%s | id_from_source=%s | "
                        "time_series_id=%s | priority=%s | "
                        "save_window_start=%s | save_window_end=%s | "
                        "compare_start=%s | compare_end=%s | "
                        "deletes=%d | inserts=%d | updates=%d | total_upserts=%d",
                        uhslc_id,
                        resolution,
                        choice["id_from_source"],
                        choice["time_series_id"],
                        choice["priority"],
                        save_window_start,
                        save_window_end,
                        compare_start,
                        compare_end,
                        total_delete_count,
                        diff_info["added_count"],
                        diff_info["changed_count"],
                        diff_info["upsert_count"],
                    )

                    if total_delete_count == 0 and diff_info["upsert_count"] == 0:
                        logging.info(
                            "FD reconcile spec | uhslc_id=%s | resolution=%s | id_from_source=%s | "
                            "time_series_id=%s | priority=%s | compare_start=%s | compare_end=%s | no_op=true",
                            uhslc_id,
                            resolution,
                            choice["id_from_source"],
                            choice["time_series_id"],
                            choice["priority"],
                            compare_start,
                            compare_end,
                        )
                        continue

                    if total_delete_count > 0:
                        self._log_rendered_sql_batch(
                            "FD DB delete",
                            TIME_SERIES_DATA_DELETE_EXACT_TIMES,
                            all_delete_params,
                            sample_limit=10,
                        )

                    if diff_info["upsert_count"] > 0:
                        self._log_rendered_sql_batch(
                            "FD DB upsert",
                            TIME_SERIES_DATA_UPSERT,
                            diff_info["params"],
                            sample_limit=10,
                        )

                    if execute_writes:
                        try:
                            init_pool(minconn=1, maxconn=5)
                            with get_conn() as conn:
                                with conn.cursor() as cur:
                                    if total_delete_count > 0:
                                        execute_batch(
                                            cur,
                                            TIME_SERIES_DATA_DELETE_EXACT_TIMES,
                                            all_delete_params,
                                            page_size=1000,
                                        )

                                    if diff_info["upsert_count"] > 0:
                                        execute_batch(
                                            cur,
                                            TIME_SERIES_DATA_UPSERT,
                                            diff_info["params"],
                                            page_size=1000,
                                        )

                                conn.commit()

                            logging.info(
                                "FD DB reconcile committed | uhslc_id=%s | resolution=%s | id_from_source=%s | "
                                "delete_stmts=%d | delete_rows=%d | upsert_rows=%d",
                                uhslc_id,
                                resolution,
                                choice["id_from_source"],
                                total_delete_stmt_count,
                                total_delete_count,
                                diff_info["upsert_count"],
                            )

                        except Exception:
                            logging.exception(
                                "FD DB reconcile execution failed for uhslc_id=%s resolution=%s id_from_source=%s",
                                uhslc_id,
                                resolution,
                                choice["id_from_source"],
                            )
                            raise

        except Exception:
            logging.exception("FD DB upsert hook failed")

    def _log_rendered_execute_batch_sql(self, sql_template, params, sample_limit=10):
        """
        Log a concise DB write spec instead of fully rendered SQL previews.
        """

        self._log_rendered_sql_batch(
            "DB batch write",
            sql_template,
            params,
            sample_limit=sample_limit,
        )

    def _reconcile_hf_db_from_cached_overlay(self, station, target_start_yyyymm, target_end_yyyymm, is_test_mode=False):
        """
        Log and optionally execute a bounded reconcile for high-frequency data.

        Behavior:
        - Baseline comes from the cached save-time L2 station loaded from base
        channel_data using fd-multi quality. This is intentionally separate
        from the visible DB overlay, including for TS loads.
        - Local/save-side data comes from the currently loaded station months inside the selected save range.
        - Within that selected save range:
            * DB-only timestamps are deleted
            * local-only or changed timestamps are upserted
        """

        if self._db_ops_disabled_for_span or not self._db_ops_allowed_for_spec(self.db_overlay_spec):
            self._show_db_ops_disabled_warning_once()
            logging.info(
                "HF DB reconcile skipped: DB work disabled for loaded span > %s months.",
                DB_OVERLAY_MAX_MONTHS
            )
            return

        try:
            if not getattr(self, "db_overlay_checkbox", None):
                return
            if not self.db_overlay_checkbox.isEnabled():
                return
            if not getattr(self, "db_overlay_spec", None):
                return

            spec = self.db_overlay_spec

            # Save-time HF reconcile compares against the authoritative fd-multi/L2
            # baseline from base channel_data.
            #
            # For regular s*.dat loads, this baseline is loaded separately because the
            # visible overlay is raw/L0.
            #
            # For TS t*.dat loads, the visible overlay is already fd-multi/L2 from base
            # channel_data and is aliased into the L2 baseline cache.
            station_db = self._db_level2_station_from_cache(spec)

            if station_db is None:
                logging.info("HF DB reconcile skipped: base channel_data L2 baseline not ready (load station and allow baseline prefetch).")
                return

            logging.info("HF DB reconcile baseline: L2 from base channel_data baseline cache")
        except Exception:
            return

        def yyyymm_to_dt_start(yyyymm: int) -> datetime:
            """Convert a YYYYMM integer into a datetime representing the first day of that month at 00:00:00."""

            y = int(yyyymm) // 100
            m = int(yyyymm) % 100

            return datetime(y, m, 1, 0, 0, 0)

        def next_month(dt: datetime) -> datetime:
            """Return a datetime representing the first day of the month immediately following the given datetime."""

            y, m = dt.year, dt.month

            return datetime(y + 1, 1, 1, 0, 0, 0) if m == 12 else datetime(y, m + 1, 1, 0, 0, 0)

        start_dt = yyyymm_to_dt_start(int(target_start_yyyymm))
        end_dt_exclusive = next_month(yyyymm_to_dt_start(int(target_end_yyyymm)))
        requested_end_dt_exclusive = end_dt_exclusive

        # Strict future-data guard for HF channel_data writes.
        # The save range may include the full current/future month, but HF data
        # valid at or after the current UTC instant must not be inserted, updated,
        # or deleted. Keep timestamps naive because HF channel_data timestamps are
        # handled as naive UTC throughout this code path.
        now_utc = _naive_utc_now()
        if end_dt_exclusive > now_utc:
            end_dt_exclusive = now_utc
            logging.info(
                "HF DB reconcile future cutoff applied | station=%s | requested_range_end=%s | effective_range_end=%s",
                spec.station_key,
                requested_end_dt_exclusive,
                end_dt_exclusive,
            )

        if end_dt_exclusive <= start_dt:
            logging.info(
                "HF DB reconcile skipped: selected range is entirely in the future | station=%s | range_start=%s | requested_range_end=%s | now_utc=%s",
                spec.station_key,
                start_dt,
                requested_end_dt_exclusive,
                now_utc,
            )
            return

        uhslc_code = spec.station_key

        cid_by_sensor = {}
        try:
            # Preferred source:
            # channel metadata attached by TimescaleSource.load_station().
            #
            # This exists even when there are zero existing fd-multi channel_data rows,
            # which is exactly the first-time HF insert case.
            for k, cid in (getattr(station_db, "channel_id_by_sensor", None) or {}).items():
                key = _normalize_sensor_key(k)
                if key and key not in ("ALL", "PRD") and cid is not None:
                    cid_by_sensor[key] = int(cid)

            # Backward-compatible fallback:
            # older station_db objects may only have channel_id attached to Sensor
            # objects created from existing channel_data rows.
            for m in getattr(station_db, "month_collection", []) or []:
                for k, s in m.sensor_collection.items():
                    key = _normalize_sensor_key(k)
                    if key in ("ALL", "PRD"):
                        continue

                    cid = getattr(s, "channel_id", None)
                    if cid is not None:
                        cid_by_sensor[key] = int(cid)

            if not cid_by_sensor:
                logging.info(
                    "HF DB reconcile skipped: no Water Level channel metadata found for station=%s range_start=%s range_end=%s.",
                    uhslc_code,
                    start_dt,
                    end_dt_exclusive,
                )
                return

            if self._db_debug_enabled() and not self._logged_overlay_channel_mapping:
                preview = list(cid_by_sensor.items())[:10]
                logging.info(
                    "Verified HF DB channel mapping from connection/channel metadata (showing first %d): %s",
                    len(preview),
                    preview,
                )
                self._logged_overlay_channel_mapping = True

        except Exception:
            logging.exception("HF DB reconcile skipped: failed to build channel_id map from DB connection/channel metadata.")
            return

        existing_by_sensor = {}
        try:
            db_times = station_db.aggregate_months.get("time", {})
            db_data = station_db.aggregate_months.get("data", {})

            for sens, t_arr in db_times.items():
                key = _normalize_sensor_key(sens)
                if key in ("ALL", "PRD"):
                    continue

                if sens not in db_data:
                    continue

                t_idx = pd.to_datetime(t_arr)
                y = np.array(db_data[sens], dtype=float, copy=True)
                y[y == 9999] = np.nan
                y[y == -131.072] = np.nan

                existing_by_sensor[key] = (pd.DatetimeIndex(t_idx), y)

        except Exception:
            logging.exception("HF DB reconcile skipped: could not build cached DB baseline.")
            return

        # Build local/save-side HF product aggregated across the selected save range.
        local_by_sensor = {}

        for month in getattr(station, "month_collection", []) or []:
            yyyymm = int(month.year) * 100 + int(month.month)
            if yyyymm < int(target_start_yyyymm) or yyyymm > int(target_end_yyyymm):
                continue

            for key, sensor in month.sensor_collection.items():
                sensor_key = _normalize_sensor_key(key)
                if sensor_key in ("ALL", "PRD"):
                    continue

                vals = sensor.get_flat_data().copy()
                vals = utils.remove_9s(vals)
                vals = vals - int(sensor.height)

                new_vals = np.asarray(vals, dtype=float) / 1000.0
                new_idx = pd.to_datetime(sensor.get_time_vector(), errors="coerce")

                valid_time_mask = ~pd.isna(new_idx)
                if not np.any(valid_time_mask):
                    continue

                new_idx = pd.DatetimeIndex(new_idx[valid_time_mask])
                new_vals = new_vals[valid_time_mask]

                pack = local_by_sensor.setdefault(sensor_key, {"time": [], "value": []})
                pack["time"].extend(list(new_idx.to_pydatetime()))
                pack["value"].extend(list(new_vals))

        normalized_local = {}
        for key, pack in local_by_sensor.items():
            df_local = pd.DataFrame({
                "time": pd.to_datetime(pack["time"], errors="coerce"),
                "value": pd.to_numeric(pack["value"], errors="coerce"),
            })

            df_local = (
                df_local
                .dropna(subset=["time"])
                .sort_values("time")
                .drop_duplicates("time", keep="last")
                .reset_index(drop=True)
            )

            # Enforce the effective HF save window, including the future-data
            # cutoff. This is required because loading/saving a month can include
            # timestamps later than the current time.
            df_local = df_local[
                (df_local["time"] >= pd.Timestamp(start_dt)) &
                (df_local["time"] < pd.Timestamp(end_dt_exclusive))
            ].reset_index(drop=True)

            normalized_local[_normalize_sensor_key(key)] = (
                pd.DatetimeIndex(df_local["time"]),
                df_local["value"].to_numpy(dtype=float),
            )

        QUALITY_ID = self.require_quality_id("fd-multi")
        DATA_FLAG_ID = None
        ATOL_M = 1e-3

        delete_params = []
        upsert_params = []
        sensor_debug = {}

        sensor_keys = sorted(
            set(cid_by_sensor.keys()) &
            (set(existing_by_sensor.keys()) | set(normalized_local.keys()))
        )

        logging.info(
            "HF DB reconcile channel/key counts | station=%s | channel_map=%d | db_baseline_sensors=%d | local_sensors=%d | matched_sensors=%d",
            uhslc_code,
            len(cid_by_sensor),
            len(existing_by_sensor),
            len(normalized_local),
            len(sensor_keys),
        )

        if not sensor_keys:
            logging.info(
                "HF reconcile spec | station=%s | range_start=%s | range_end=%s | no_op=true | reason=no matching local/DB sensors for available Water Level channels",
                uhslc_code,
                start_dt,
                end_dt_exclusive,
            )
            return

        for key in sensor_keys:
            cid = cid_by_sensor.get(str(key))
            if cid is None:
                continue

            if key in normalized_local:
                new_idx, new_vals = normalized_local[key]
            else:
                new_idx = pd.DatetimeIndex([])
                new_vals = np.array([], dtype=float)

            base_pack = existing_by_sensor.get(str(key))
            if base_pack is None:
                if len(new_idx) > 0:
                    ts = new_idx.to_pydatetime()
                    upsert_params.extend(
                        (
                            None if pd.isna(v) else float(v),
                            t,
                            cid,
                            QUALITY_ID,
                            DATA_FLAG_ID,
                            QUALITY_ID,
                        )
                        for v, t in zip(new_vals, ts)
                    )

                sensor_debug[str(key)] = {
                    "channel_id": cid,
                    "n_local": int(len(new_idx)),
                    "n_db": 0,
                    "n_removed_from_db": 0,
                    "n_added_to_db": int(len(new_idx)),
                    "n_changed_vs_db": 0,
                    "n_upsert_total": int(len(new_idx)),
                }
                continue

            base_idx, base_vals = base_pack
            base_mask = (base_idx >= pd.Timestamp(start_dt)) & (base_idx < pd.Timestamp(end_dt_exclusive))
            base_idx = pd.DatetimeIndex(base_idx[base_mask])
            base_vals = np.asarray(base_vals[base_mask], dtype=float)

            delete_info = self._build_hf_delete_params(
                channel_id=cid,
                quality_id=QUALITY_ID,
                base_idx=base_idx,
                local_idx=new_idx,
            )
            delete_params.extend(delete_info["params"])

            if len(new_idx) == 0:
                sensor_debug[str(key)] = {
                    "channel_id": cid,
                    "n_local": 0,
                    "n_db": int(len(base_idx)),
                    "n_removed_from_db": delete_info["delete_count"],
                    "n_added_to_db": 0,
                    "n_changed_vs_db": 0,
                    "n_upsert_total": 0,
                }
                continue

            pos = base_idx.get_indexer(new_idx)
            missing_mask = (pos == -1)

            matched_pos = pos[~missing_mask]
            base_aligned_vals = base_vals[matched_pos]
            new_matched_vals = new_vals[~missing_mask]

            changed_matched = ~np.isclose(new_matched_vals, base_aligned_vals, rtol=0.0, atol=ATOL_M, equal_nan=True)

            to_upsert = missing_mask.copy()
            to_upsert[~missing_mask] |= changed_matched

            if np.any(to_upsert):
                ts = new_idx[to_upsert].to_pydatetime()
                vs = new_vals[to_upsert]
                upsert_params.extend(
                    (
                        None if pd.isna(v) else float(v),
                        t,
                        cid,
                        QUALITY_ID,
                        DATA_FLAG_ID,
                        QUALITY_ID,
                    )
                    for v, t in zip(vs, ts)
                )

            sensor_debug[str(key)] = {
                "channel_id": cid,
                "n_local": int(len(new_idx)),
                "n_db": int(len(base_idx)),
                "n_removed_from_db": int(delete_info["delete_count"]),
                "n_added_to_db": int(missing_mask.sum()),
                "n_changed_vs_db": int(changed_matched.sum()),
                "n_upsert_total": int(to_upsert.sum()),
            }

        if sensor_debug and self._db_debug_enabled():
            df_metrics = (
                pd.DataFrame.from_dict(sensor_debug, orient="index")
                .sort_values(["n_removed_from_db", "n_upsert_total", "n_changed_vs_db"], ascending=False)
            )
            logging.info("HF DB reconcile debug metrics (top 10 sensors):\n%s", df_metrics.head(10).to_string())

            tot_removed = int(df_metrics["n_removed_from_db"].sum()) if "n_removed_from_db" in df_metrics else 0
            tot_added = int(df_metrics["n_added_to_db"].sum()) if "n_added_to_db" in df_metrics else 0
            tot_changed = int(df_metrics["n_changed_vs_db"].sum()) if "n_changed_vs_db" in df_metrics else 0
            tot_upsert = int(df_metrics["n_upsert_total"].sum()) if "n_upsert_total" in df_metrics else len(upsert_params)

            logging.info(
                "HF DB reconcile debug totals: sensors=%d removed(deletes)=%d added(inserts)=%d changed(updates)=%d upsert_total=%d",
                len(df_metrics), tot_removed, tot_added, tot_changed, tot_upsert
            )

        # Defensive final guard: no HF DB mutation may target timestamps outside
        # the effective save window. In particular, this prevents future-dated
        # inserts/updates/deletes even if a future code change bypasses the local
        # dataframe filter above.
        window_start_ts = pd.Timestamp(start_dt)
        window_end_ts = pd.Timestamp(end_dt_exclusive)

        original_delete_timestamp_count = sum(len(p[2]) for p in delete_params)
        filtered_delete_params = []

        for channel_id, quality_id, times in delete_params:
            kept_times = [
                t for t in times
                if window_start_ts <= pd.Timestamp(t) < window_end_ts
            ]

            if kept_times:
                filtered_delete_params.append((channel_id, quality_id, kept_times))

        delete_params = filtered_delete_params

        original_upsert_count = len(upsert_params)
        upsert_params = [
            p for p in upsert_params
            if window_start_ts <= pd.Timestamp(p[1]) < window_end_ts
        ]

        filtered_delete_timestamp_count = sum(len(p[2]) for p in delete_params)

        if (
            filtered_delete_timestamp_count != original_delete_timestamp_count or
            len(upsert_params) != original_upsert_count
        ):
            logging.info(
                "HF DB future/window guard filtered mutations | station=%s | range_start=%s | effective_range_end=%s | "
                "delete_times_before=%d | delete_times_after=%d | upserts_before=%d | upserts_after=%d",
                uhslc_code,
                start_dt,
                end_dt_exclusive,
                original_delete_timestamp_count,
                filtered_delete_timestamp_count,
                original_upsert_count,
                len(upsert_params),
            )

        if not delete_params and not upsert_params:
            logging.info(
                "HF reconcile spec | station=%s | range_start=%s | range_end=%s | no_op=true",
                uhslc_code,
                start_dt,
                end_dt_exclusive,
            )
            return

        logging.info(
            "HF reconcile spec | station=%s | range_start=%s | range_end=%s | deletes=%d | upserts=%d",
            uhslc_code,
            start_dt,
            end_dt_exclusive,
            len(delete_params),
            len(upsert_params),
        )

        if delete_params:
            self._log_rendered_sql_batch(
                "HF DB delete",
                CHANNEL_DATA_DELETE_EXACT_TIMES,
                delete_params,
                sample_limit=10,
            )

        if upsert_params:
            self._log_rendered_sql_batch(
                "HF DB upsert",
                CHANNEL_DATA_UPSERT,
                upsert_params,
                sample_limit=10,
            )

        hf_write_result = {}

        if self._db_live_writes_enabled(is_test_mode, "HF DB reconcile"):
            if TSDB_BACKGROUND_HF_WRITES:
                queued = self._queue_hf_db_write_job(
                    station_key=uhslc_code,
                    start_dt=start_dt,
                    end_dt_exclusive=end_dt_exclusive,
                    delete_params=list(delete_params),
                    upsert_params=list(upsert_params),
                    page_size=10000,
                )

                if queued:
                    logging.info(
                        "HF DB reconcile queued for background execution | station=%s | range_start=%s | range_end=%s | "
                        "delete_stmts=%d | upsert_rows=%d",
                        uhslc_code,
                        start_dt,
                        end_dt_exclusive,
                        len(delete_params),
                        len(upsert_params),
                    )
                    return

                # Conservative fallback: if queueing failed because an identical job is
                # already in flight, do not silently continue as if the DB was updated.
                logging.warning(
                    "HF DB reconcile background queue skipped; continuing without starting duplicate DB write | "
                    "station=%s | range_start=%s | range_end=%s",
                    uhslc_code,
                    start_dt,
                    end_dt_exclusive,
                )
                return

            try:
                init_pool(minconn=1, maxconn=5)
                with get_conn() as conn:
                    with conn.cursor() as cur:
                        hf_write_result = _execute_hf_channel_data_staged_write(
                            cur,
                            delete_params,
                            upsert_params,
                        )

                    conn.commit()

                logging.info(
                    "HF DB reconcile committed | station=%s | range_start=%s | range_end=%s | "
                    "execute_mode=%s | delete_stmts=%d | delete_rows_staged=%d | delete_rows_affected=%d | "
                    "upsert_rows=%d | staged_upsert_rows=%d | direct_copy_rows=%d | "
                    "direct_copy_groups=%d | staged_upsert_groups=%d | "
                    "upsert_stmt_count=%d | upsert_rows_affected=%d",
                    uhslc_code,
                    start_dt,
                    end_dt_exclusive,
                    hf_write_result.get("execute_mode", "copy_staging_upsert"),
                    hf_write_result.get("delete_stmt_count", 0),
                    hf_write_result.get("delete_rows_staged", 0),
                    hf_write_result.get("delete_rows_affected", 0),
                    len(upsert_params),
                    hf_write_result.get("staged_upsert_rows", 0),
                    hf_write_result.get("direct_copy_rows_affected", 0),
                    hf_write_result.get("direct_copy_group_count", 0),
                    hf_write_result.get("staged_upsert_group_count", 0),
                    hf_write_result.get("upsert_stmt_count", 0),
                    hf_write_result.get("upsert_rows_affected", 0),
                )

            except Exception:
                logging.exception(
                    "HF DB reconcile execution failed for station=%s range_start=%s range_end=%s",
                    uhslc_code,
                    start_dt,
                    end_dt_exclusive,
                )
                raise

    def _log_rendered_sql_batch(self, label, sql_template, params, sample_limit=10):
        """
        Log a concise DB write spec instead of rendered SQL previews.

        Summarizes:
        - operation
        - target table
        - row count / statement count
        - key identifiers gleaned from params
        - min/max timestamps if present
        """

        if not params:
            logging.info("%s spec | rows=0", label)
            return

        sql_norm = " ".join(str(sql_template).split()).lower()

        if "insert into time_series_data" in sql_norm:
            table = "time_series_data"
            op = "upsert"
        elif "delete from time_series_data" in sql_norm:
            table = "time_series_data"
            op = "delete"
        elif "insert into channel_data" in sql_norm:
            table = "channel_data"
            op = "upsert"
        elif "delete from channel_data" in sql_norm:
            table = "channel_data"
            op = "delete"
        else:
            table = "unknown"
            op = "write"

        def _extract_times_from_param_tuple(p):
            """Extract and return the list of timestamp values from a parameter tuple used in batched DB operations."""

            times = []

            # time_series_data upsert:
            # (time, value, last_update, priority, data_flag_id, quality_id, resolution_id, time_series_id)
            if table == "time_series_data" and op == "upsert":
                if len(p) >= 1:
                    times.append(pd.to_datetime(p[0], errors="coerce"))

            # time_series_data delete:
            # (time_series_id, quality_id, resolution_id, priority, [times])
            elif table == "time_series_data" and op == "delete":
                if len(p) >= 5:
                    for t in p[4] or []:
                        times.append(pd.to_datetime(t, errors="coerce"))

            # channel_data upsert:
            # (data, time, channel_id, quality_id, data_flag_id, quality_id)
            elif table == "channel_data" and op == "upsert":
                if len(p) >= 2:
                    times.append(pd.to_datetime(p[1], errors="coerce"))

            # channel_data delete:
            # (channel_id, quality_id, [times])
            elif table == "channel_data" and op == "delete":
                if len(p) >= 3:
                    for t in p[2] or []:
                        times.append(pd.to_datetime(t, errors="coerce"))

            return [t for t in times if not pd.isna(t)]

        def _first_nonempty(values):
            """Return the first value in the iterable that is not None and not empty, or None if all values are empty."""

            for v in values:
                if v is not None:
                    return v
            return None

        all_times = []
        for p in params:
            all_times.extend(_extract_times_from_param_tuple(p))

        time_min = min(all_times).isoformat() if all_times else None
        time_max = max(all_times).isoformat() if all_times else None

        summary = {
            "op": op,
            "table": table,
            "batch_rows": int(len(params)),
            "stmt_count": int(len(params)),
            "time_min": time_min,
            "time_max": time_max,
        }

        try:
            if table == "time_series_data" and op == "upsert":
                first = params[0]
                summary.update({
                    "quality_id": int(first[5]),
                    "resolution_id": int(first[6]),
                    "time_series_id": int(first[7]),
                    "priority": int(first[3]),
                })
            elif table == "time_series_data" and op == "delete":
                first = params[0]
                summary.update({
                    "time_series_id": int(first[0]),
                    "quality_id": int(first[1]),
                    "resolution_id": int(first[2]),
                    "priority": int(first[3]),
                    "timestamps_targeted": int(sum(len(p[4]) for p in params)),
                })
            elif table == "channel_data" and op == "upsert":
                channel_ids = sorted({int(p[2]) for p in params})
                quality_ids = sorted({int(p[3]) for p in params})

                # HF channel_data upserts are executed through temp staging:
                # COPY into tmp_hf_channel_data_upsert, then one
                # INSERT ... ON CONFLICT DO UPDATE statement per quality_id.
                summary.update({
                    "stmt_count": len(quality_ids),
                    "execute_mode": "copy_staging_upsert",
                    "channel_count": len(channel_ids),
                    "channel_ids_preview": channel_ids[:10],
                    "quality_ids": quality_ids,
                })
            elif table == "channel_data" and op == "delete":
                first = params[0]
                summary.update({
                    "stmt_count": 1,
                    "execute_mode": "copy_staging",
                    "channel_id": int(first[0]),
                    "quality_id": int(first[1]),
                    "timestamps_targeted": int(sum(len(p[2]) for p in params)),
                })
        except Exception:
            pass

        parts = [f"{k}={v}" for k, v in summary.items() if v is not None]
        logging.info("%s spec | %s", label, " | ".join(parts))

    def _chunk_datetime_index(self, dt_index, batch_size=10000):
        """Yield a datetime index in unique sorted chunks for batched database operations."""

        idx = pd.DatetimeIndex(dt_index).sort_values().unique()
        for i in range(0, len(idx), batch_size):
            yield idx[i:i + batch_size]

    def _build_fd_delete_params(self, local_df, db_df, time_series_id, priority, resolution_id, batch_size=10000):
        """
        Build delete params for DB-only timestamps inside the selected FD save scope.
        """

        FD_QUALITY_ID = self.require_quality_id("fd")

        local_df = local_df.copy()
        db_df = db_df.copy()

        if not local_df.empty:
            local_df["time"] = pd.to_datetime(local_df["time"], utc=True)
        if not db_df.empty:
            db_df["time"] = pd.to_datetime(db_df["time"], utc=True)

        local_times = pd.DatetimeIndex(local_df["time"]).unique() if not local_df.empty else pd.DatetimeIndex([])
        db_times = pd.DatetimeIndex(db_df["time"]).unique() if not db_df.empty else pd.DatetimeIndex([])

        delete_times = db_times.difference(local_times)

        params = []
        for chunk in self._chunk_datetime_index(delete_times, batch_size=batch_size):
            params.append((
                int(time_series_id),
                int(FD_QUALITY_ID),
                int(resolution_id),
                int(priority),
                list(pd.DatetimeIndex(chunk).to_pydatetime()),
            ))

        return {
            "delete_count": int(len(delete_times)),
            "delete_stmt_count": int(len(params)),
            "params": params,
        }

    def _build_hf_delete_params(self, channel_id, quality_id, base_idx, local_idx, batch_size=10000):
        """
        Build delete params for DB-only timestamps inside the selected HF save scope.
        """

        delete_times = pd.DatetimeIndex(base_idx).difference(pd.DatetimeIndex(local_idx))

        params = []
        for chunk in self._chunk_datetime_index(delete_times, batch_size=batch_size):
            params.append((
                int(channel_id),
                int(quality_id),
                list(pd.DatetimeIndex(chunk).to_pydatetime()),
            ))

        return {
            "delete_count": int(len(delete_times)),
            "delete_stmt_count": int(len(params)),
            "params": params,
        }

    def _queue_hf_db_write_job(
        self,
        station_key,
        start_dt,
        end_dt_exclusive,
        delete_params,
        upsert_params,
        page_size=10000,
    ):
        """
        Queue HF DB write execution in a background QThread.

        The reconcile/diff has already been computed synchronously. This worker only
        performs DB delete/upsert/commit.
        """

        job_key = "hf:{station}:{start}:{end}".format(
            station=station_key,
            start=pd.Timestamp(start_dt).isoformat(),
            end=pd.Timestamp(end_dt_exclusive).isoformat(),
        )

        if job_key in self._hf_db_write_jobs_inflight:
            logging.warning(
                "HF DB background write not queued because same job is already in flight | job_key=%s",
                job_key,
            )
            self.statusBar().showMessage(
                "HF DB write already in progress for this station/range; not starting a duplicate.",
                8000,
            )
            return False

        self._hf_db_write_jobs_inflight.add(job_key)

        # Reuse the existing Save gate so the user cannot start a second save while
        # an older DB write might still commit later.
        self._set_db_save_gate_pending_count(self._db_save_gate_pending_count)

        thread = QtCore.QThread()
        worker = HfDbWriteWorker(
            job_key=job_key,
            station_key=station_key,
            range_start=start_dt,
            range_end=end_dt_exclusive,
            delete_params=delete_params,
            upsert_params=upsert_params,
            upsert_page_size=page_size,
        )

        def _cleanup_hf_db_write_objects():
            self._hf_db_write_threads.pop(job_key, None)
            self._hf_db_write_workers.pop(job_key, None)

        thread.finished.connect(_cleanup_hf_db_write_objects)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)

        self._hf_db_write_threads[job_key] = thread
        self._hf_db_write_workers[job_key] = worker

        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_hf_db_write_finished)
        worker.failed.connect(self._on_hf_db_write_failed)

        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(thread.deleteLater)

        self.statusBar().showMessage(
            "HF DB write running in background for {0}...".format(station_key),
            0,
        )

        logging.info(
            "HF DB background write queued | job_key=%s | station=%s | range_start=%s | range_end=%s | deletes=%d | upserts=%d",
            job_key,
            station_key,
            start_dt,
            end_dt_exclusive,
            len(delete_params or []),
            len(upsert_params or []),
        )

        thread.start()
        return True


    def _on_hf_db_write_finished(self, job_key, result):
        """Handle successful background HF DB write completion."""

        try:
            self._hf_db_write_jobs_inflight.discard(job_key)

            self._set_db_save_gate_pending_count(self._db_save_gate_pending_count)

            logging.info(
                "HF DB background write committed | job_key=%s | station=%s | range_start=%s | range_end=%s | "
                "execute_mode=%s | delete_stmts=%d | delete_rows_staged=%d | delete_rows_affected=%d | "
                "upsert_rows=%d | staged_upsert_rows=%d | direct_copy_rows=%d | "
                "direct_copy_groups=%d | staged_upsert_groups=%d | "
                "upsert_stmt_count=%d | upsert_rows_affected=%d | timings=%s",
                job_key,
                result.get("station"),
                result.get("range_start"),
                result.get("range_end"),
                result.get("execute_mode", "copy_staging_upsert"),
                result.get("delete_stmts", 0),
                result.get("delete_rows_staged", 0),
                result.get("delete_rows_affected", 0),
                result.get("upsert_rows", 0),
                result.get("staged_upsert_rows", 0),
                result.get("direct_copy_rows", 0),
                result.get("direct_copy_group_count", 0),
                result.get("staged_upsert_group_count", 0),
                result.get("upsert_stmt_count", 0),
                result.get("upsert_rows_affected", 0),
                result.get("timings", {}),
            )

            self.statusBar().showMessage(
                "HF DB write complete for {0}.".format(result.get("station")),
                8000,
            )

        except Exception:
            logging.exception("Failed while handling HF DB background write success | job_key=%s", job_key)


    def _on_hf_db_write_failed(self, job_key, error_text):
        """Handle failed background HF DB write."""

        try:
            self._hf_db_write_jobs_inflight.discard(job_key)

            self._set_db_save_gate_pending_count(self._db_save_gate_pending_count)

            logging.error(
                "HF DB background write failed | job_key=%s\n%s",
                job_key,
                error_text,
            )

            self.statusBar().showMessage(
                "HF DB write failed. Check logs before relying on DB output.",
                12000,
            )

            QtWidgets.QMessageBox.warning(
                self,
                "HF DB Write Failed",
                "The local files were saved, but the background HF database write failed.\n\n"
                "Check the logs before relying on database output.",
            )

        except Exception:
            logging.exception("Failed while handling HF DB background write failure | job_key=%s", job_key)


if __name__ == '__main__':
    appctxt = AppContext()  # 4. Instantiate the subclass
    # apply_stylesheet(appctxt.app, theme='dark_blue.xml')
    exit_code = appctxt.run()  # 5. Invoke run()
    sys.exit(exit_code)
