"""CST channel_data schema using RI's existing ordered asynchronous writer."""
import sqlite3
from contextlib import closing
from .async_writer import AsyncSQLiteWriter, Statement
from .cst_schema import ALL_BASE_COLS, TABLE_NAME, _ensure_table, _row_from_pkt


class SimulationRecorder:
    def __init__(self, path):
        self.writer = AsyncSQLiteWriter(path, self._initialize, name="simulation-sqlite-writer")
        columns = ",".join(ALL_BASE_COLS)
        placeholders = ",".join("?" for _ in ALL_BASE_COLS)
        self._table = '"' + TABLE_NAME.replace('"', '""') + '"'
        self._insert = f"INSERT INTO {self._table} ({columns}) VALUES ({placeholders})"

    @staticmethod
    def _initialize(connection):
        _ensure_table(connection, ALL_BASE_COLS)

    def record(self, packets):
        rows = [_row_from_pkt(packet) for packet in packets]
        if not rows:
            return True
        return self.writer.submit([Statement(self._insert, tuple(tuple(row.get(key) for key in ALL_BASE_COLS) for row in rows))])

    def latest(self, limit=100):
        """Independent reader connection; call from a worker for UI queries."""
        if not self.writer.path.exists():
            return []
        with closing(sqlite3.connect(self.writer.path.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
            connection.row_factory = sqlite3.Row
            query = f"SELECT * FROM {self._table} ORDER BY timestamp DESC LIMIT ?"
            return [dict(row) for row in connection.execute(query, (max(1, min(10000, int(limit))),))]

    def close(self, timeout=10):
        self.writer.close(timeout=timeout)
        if not self.writer.done.wait(timeout + 1):
            raise RuntimeError("Simulation database writer did not finish before shutdown")
        status = self.writer.status()
        if status["error"] or status["queue_depth"] or status["in_flight"]:
            raise RuntimeError(f"Simulation records were not fully committed: {status}")
