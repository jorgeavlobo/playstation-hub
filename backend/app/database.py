"""
PS5 Monitoring Service - SQLite Persistence Layer.

Responsibilities:
    - Initialize the persistent database.
    - Apply versioned schema migrations.
    - Store monitoring events.
    - Create and close usage sessions.
    - Retrieve sessions for reporting and recovery.

All database timestamps are stored as UTC Unix epoch values.

The database is intended to reside inside the Home Assistant
application's persistent /data directory.
"""

import json
import sqlite3
import threading

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from models import (
    MonitoringEvent,
    SessionType,
    UsageSession,
    ensure_utc,
)


SCHEMA_VERSION = 3


def to_timestamp(value: datetime) -> float:
    """Convert a timezone-aware datetime into a UTC Unix timestamp."""

    return ensure_utc(value).timestamp()


def from_timestamp(value: float) -> datetime:
    """Convert a Unix timestamp into a timezone-aware UTC datetime."""

    return datetime.fromtimestamp(value, tz=timezone.utc)


class Database:
    """
    Thread-safe SQLite persistence manager.

    A single connection is shared by the application and protected
    by a reentrant lock.

    Database writes use explicit transactions. SQLite WAL mode
    improves resilience and permits concurrent read operations.
    """

    def __init__(self, database_path: Path) -> None:
        """Initialize the database connection and schema."""

        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._lock = threading.RLock()

        self._connection = sqlite3.connect(
            str(self.database_path),
            timeout=30.0,
            check_same_thread=False,
            isolation_level=None,
        )

        self._connection.row_factory = sqlite3.Row

        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA foreign_keys=ON")
        self._connection.execute("PRAGMA busy_timeout=30000")

        self._initialize_schema()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """
        Execute a database transaction with automatic rollback.

        Callers must not manually commit or rollback the connection.
        """

        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")

            try:
                yield self._connection
                self._connection.execute("COMMIT")
            except BaseException:
                self._connection.execute("ROLLBACK")
                raise

    def _initialize_schema(self) -> None:
        """Create the schema and verify its migration version."""

        with self.transaction() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER NOT NULL
                )
                """
            )

            row = connection.execute(
                "SELECT version FROM schema_version LIMIT 1"
            ).fetchone()

            if row is None:
                connection.execute(
                    "INSERT INTO schema_version (version) VALUES (0)"
                )
                current_version = 0
            else:
                current_version = int(row["version"])

            if current_version > SCHEMA_VERSION:
                raise RuntimeError(
                    "Database schema is newer than this application."
                )

            if current_version < 1:
                self._migration_v1(connection)

                connection.execute(
                    "UPDATE schema_version SET version = 1"
                )
                current_version = 1

            if current_version < 2:
                self._migration_v2(connection)

                connection.execute(
                    "UPDATE schema_version SET version = 2"
                )
                current_version = 2

            if current_version < 3:
                self._migration_v3(connection)

                connection.execute(
                    "UPDATE schema_version SET version = 3"
                )

    @staticmethod
    def _migration_v1(connection: sqlite3.Connection) -> None:
        """Create the initial event and session tables."""

        statements = """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                occurred_at REAL NOT NULL,
                payload_json TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_events_occurred_at
                ON events (occurred_at);

            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_type TEXT NOT NULL
                    CHECK (session_type IN ('console', 'gaming')),
                started_at REAL NOT NULL,
                ended_at REAL,
                player_name TEXT,
                title_id TEXT,
                title_name TEXT,
                title_image TEXT,
                CHECK (
                    ended_at IS NULL
                    OR ended_at >= started_at
                ),
                CHECK (
                    session_type != 'gaming'
                    OR player_name IS NOT NULL
                )
            );

            CREATE INDEX IF NOT EXISTS idx_sessions_time
                ON sessions (started_at, ended_at);

            CREATE INDEX IF NOT EXISTS idx_sessions_type
                ON sessions (session_type, started_at);

            CREATE INDEX IF NOT EXISTS idx_sessions_game
                ON sessions (title_id, started_at);

            CREATE UNIQUE INDEX IF NOT EXISTS idx_open_console
                ON sessions (session_type)
                WHERE ended_at IS NULL
                  AND session_type = 'console';

            CREATE UNIQUE INDEX IF NOT EXISTS idx_open_gaming
                ON sessions (session_type, player_name)
                WHERE ended_at IS NULL
                  AND session_type = 'gaming';
            """

        # Execute each SQL statement individually to preserve the
        # surrounding explicit SQLite transaction.
        for statement in statements.split(";"):
            statement = statement.strip()

            if statement:
                connection.execute(statement)


    @staticmethod
    def _migration_v2(connection: sqlite3.Connection) -> None:
        """
        Add persistent observation checkpoints.

        Checkpoints are associated with individual sessions.
        Foreign keys ensure that removing a session also removes
        its associated checkpoint.

        Existing v1 sessions and events remain unchanged.
        """

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS checkpoints (
                session_id INTEGER PRIMARY KEY,
                observed_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                FOREIGN KEY (session_id)
                    REFERENCES sessions(id)
                    ON DELETE CASCADE
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_checkpoints_observed
            ON checkpoints (observed_at)
            """
        )


    @staticmethod
    def _migration_v3(connection: sqlite3.Connection) -> None:
        """
        Create the persistent monitoring state table.

        The table stores the latest accepted observation separately
        from the historical event log.

        Existing events are used to initialize the last observation
        timestamp when migrating an older database.

        Historical sessions, events, and checkpoints are preserved.
        """

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS monitoring_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                last_observation_at REAL,
                last_power TEXT,
                last_activity TEXT,
                last_player TEXT,
                last_title_id TEXT,
                updated_at REAL
            )
            """
        )

        connection.execute(
            """
            INSERT OR IGNORE INTO monitoring_state (id)
            VALUES (1)
            """
        )

        # Preserve ordering information from existing v2 events.
        # This is only used during the migration.
        row = connection.execute(
            """
            SELECT occurred_at, payload_json
            FROM events
            WHERE event_type = 'state_update'
            ORDER BY occurred_at DESC, id DESC
            LIMIT 1
            """
        ).fetchone()

        if row is not None:
            payload = json.loads(row["payload_json"] or "{}")

            connection.execute(
                """
                UPDATE monitoring_state
                SET last_observation_at = ?,
                    last_power = ?,
                    last_activity = ?,
                    last_player = ?,
                    last_title_id = ?,
                    updated_at = ?
                WHERE id = 1
                """,
                (
                    row["occurred_at"],
                    payload.get("power"),
                    payload.get("activity"),
                    json.dumps(payload.get("players", [])),
                    payload.get("title_id"),
                    row["occurred_at"],
                ),
            )

    def get_monitoring_state(self) -> dict:
        """
        Return the latest persisted monitoring state.

        This method is read-only and safe for diagnostics.
        """

        with self._lock:
            row = self._connection.execute(
                """
                SELECT *
                FROM monitoring_state
                WHERE id = 1
                """
            ).fetchone()

        return dict(row) if row is not None else {}

    def save_checkpoint(
        self,
        session_id: int,
        observed_at: datetime,
    ) -> None:
        """
        Persist the last confirmed observation of a session.

        Checkpoints are monotonically increasing: an older
        observation cannot replace a newer checkpoint.

        The session must exist and remain open.
        """

        timestamp = to_timestamp(observed_at)

        with self.transaction() as connection:
            row = connection.execute(
                """
                SELECT started_at
                FROM sessions
                WHERE id = ?
                  AND ended_at IS NULL
                """,
                (session_id,),
            ).fetchone()

            if row is None:
                raise ValueError(
                    f"Session {session_id} does not exist or is closed."
                )

            if timestamp < row["started_at"]:
                raise ValueError(
                    "Checkpoint cannot precede session start."
                )

            connection.execute(
                """
                INSERT INTO checkpoints (
                    session_id,
                    observed_at,
                    updated_at
                )
                VALUES (?, ?, ?)
                ON CONFLICT(session_id)
                DO UPDATE SET
                    observed_at = excluded.observed_at,
                    updated_at = excluded.updated_at
                WHERE excluded.observed_at
                    > checkpoints.observed_at
                """,
                (
                    session_id,
                    timestamp,
                    datetime.now(timezone.utc).timestamp(),
                ),
            )

    def get_checkpoint(
        self,
        session_id: int,
    ) -> datetime | None:
        """
        Return the last confirmed observation of a session.

        Returns None when no checkpoint exists.
        """

        with self._lock:
            row = self._connection.execute(
                """
                SELECT observed_at
                FROM checkpoints
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()

        if row is None:
            return None

        return from_timestamp(row["observed_at"])

    def insert_event(self, event: MonitoringEvent) -> int:
        """Persist an event and return its database identifier."""

        payload_json = (
            json.dumps(
                event.payload,
                ensure_ascii=False,
                separators=(",", ":"),
            )
            if event.payload is not None
            else None
        )

        with self.transaction() as connection:
            cursor = connection.execute(
                """
                INSERT INTO events (
                    event_type,
                    occurred_at,
                    payload_json
                )
                VALUES (?, ?, ?)
                """,
                (
                    event.event_type.value,
                    to_timestamp(event.occurred_at),
                    payload_json,
                ),
            )

            return int(cursor.lastrowid)

    def create_session(self, session: UsageSession) -> int:
        """
        Persist a session and return its database identifier.

        Partial unique indexes prevent duplicate open sessions
        for the same console or monitored player.
        """

        with self.transaction() as connection:
            cursor = connection.execute(
                """
                INSERT INTO sessions (
                    session_type,
                    started_at,
                    ended_at,
                    player_name,
                    title_id,
                    title_name,
                    title_image
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.session_type.value,
                    to_timestamp(session.started_at),
                    (
                        to_timestamp(session.ended_at)
                        if session.ended_at is not None
                        else None
                    ),
                    session.player_name,
                    session.title_id,
                    session.title_name,
                    session.title_image,
                ),
            )

            return int(cursor.lastrowid)

    def close_session(
        self,
        session_id: int,
        ended_at: datetime,
    ) -> bool:
        """
        Close an open session.

        Returns True when a session was closed.

        Returns False when the session was already closed or
        the supplied identifier does not exist.
        """

        with self.transaction() as connection:
            cursor = connection.execute(
                """
                UPDATE sessions
                SET ended_at = ?
                WHERE id = ?
                  AND ended_at IS NULL
                  AND started_at <= ?
                """,
                (
                    to_timestamp(ended_at),
                    session_id,
                    to_timestamp(ended_at),
                ),
            )

            return cursor.rowcount == 1

    def get_open_sessions(self) -> list[UsageSession]:
        """Return all sessions that have not yet been closed."""

        with self._lock:
            rows = self._connection.execute(
                """
                SELECT *
                FROM sessions
                WHERE ended_at IS NULL
                ORDER BY started_at, id
                """
            ).fetchall()

        return [self._row_to_session(row) for row in rows]

    def get_sessions(
        self,
        start: datetime,
        end: datetime,
        session_type: SessionType | None = None,
    ) -> list[UsageSession]:
        """
        Retrieve sessions overlapping a requested UTC interval.

        This includes sessions that started before the interval
        and sessions that remain open.
        """

        start_ts = to_timestamp(start)
        end_ts = to_timestamp(end)

        if end_ts <= start_ts:
            raise ValueError("End must be later than start.")

        query = """
            SELECT *
            FROM sessions
            WHERE started_at < ?
              AND (
                  ended_at IS NULL
                  OR ended_at > ?
              )
        """

        parameters = [end_ts, start_ts]

        if session_type is not None:
            query += " AND session_type = ?"
            parameters.append(session_type.value)

        query += " ORDER BY started_at, id"

        with self._lock:
            rows = self._connection.execute(
                query,
                parameters,
            ).fetchall()

        return [self._row_to_session(row) for row in rows]

    @staticmethod
    def _row_to_session(row: sqlite3.Row) -> UsageSession:
        """Convert a database row into an immutable session model."""

        return UsageSession(
            session_id=row["id"],
            session_type=SessionType(row["session_type"]),
            started_at=from_timestamp(row["started_at"]),
            ended_at=(
                from_timestamp(row["ended_at"])
                if row["ended_at"] is not None
                else None
            ),
            player_name=row["player_name"],
            title_id=row["title_id"],
            title_name=row["title_name"],
            title_image=row["title_image"],
        )


    def apply_observation(
        self,
        state,
        player_name: str,
        max_gap_seconds: float = 90.0,
    ) -> bool:
        """
        Atomically process a confirmed PS5 observation.

        The caller must reject retained MQTT messages.

        Existing sessions are advanced only when the gap between
        observations does not exceed the configured freshness limit.

        Larger gaps are excluded from confirmed usage totals.

        Returns True when the observation was accepted.
        """

        from models import EventType

        if not player_name.strip():
            raise ValueError("Player name cannot be empty.")

        if max_gap_seconds <= 0:
            raise ValueError("Maximum gap must be positive.")

        timestamp = to_timestamp(state.observed_at)

        with self.transaction() as connection:
            previous = connection.execute(
                """
                SELECT *
                FROM monitoring_state
                WHERE id = 1
                """
            ).fetchone()

            if (
                previous["last_observation_at"] is not None
                and timestamp <= previous["last_observation_at"]
            ):
                return False

            console_active = state.console_active
            gaming_active = state.player_is_gaming(player_name)

            open_sessions = connection.execute(
                """
                SELECT *
                FROM sessions
                WHERE ended_at IS NULL
                ORDER BY id
                """
            ).fetchall()

            for session in open_sessions:
                checkpoint = connection.execute(
                    """
                    SELECT observed_at
                    FROM checkpoints
                    WHERE session_id = ?
                    """,
                    (session["id"],),
                ).fetchone()

                last_seen = (
                    checkpoint["observed_at"]
                    if checkpoint is not None
                    else session["started_at"]
                )

                expired = (
                    timestamp - last_seen > max_gap_seconds
                )

                is_console = session["session_type"] == "console"

                is_player = (
                    session["session_type"] == "gaming"
                    and session["player_name"] == player_name
                )

                game_changed = (
                    is_player
                    and gaming_active
                    and (
                        session["title_id"] != state.title_id
                        or session["title_name"] != state.title_name
                    )
                )

                should_close = (
                    expired
                    or (is_console and not console_active)
                    or (
                        is_player
                        and (not gaming_active or game_changed)
                    )
                )

                if should_close:
                    # Close at the last confirmed observation.
                    # The actual transition may have happened
                    # between two MQTT observations.
                    end_timestamp = last_seen

                    connection.execute(
                        """
                        UPDATE sessions
                        SET ended_at = ?
                        WHERE id = ?
                          AND ended_at IS NULL
                        """,
                        (
                            max(
                                end_timestamp,
                                session["started_at"],
                            ),
                            session["id"],
                        ),
                    )
                else:
                    connection.execute(
                        """
                        INSERT INTO checkpoints (
                            session_id,
                            observed_at,
                            updated_at
                        )
                        VALUES (?, ?, ?)
                        ON CONFLICT(session_id)
                        DO UPDATE SET
                            observed_at = excluded.observed_at,
                            updated_at = excluded.updated_at
                        WHERE excluded.observed_at
                            > checkpoints.observed_at
                        """,
                        (
                            session["id"],
                            timestamp,
                            timestamp,
                        ),
                    )

            remaining = connection.execute(
                """
                SELECT session_type, player_name
                FROM sessions
                WHERE ended_at IS NULL
                """
            ).fetchall()

            console_open = any(
                row["session_type"] == "console"
                for row in remaining
            )

            gaming_open = any(
                row["session_type"] == "gaming"
                and row["player_name"] == player_name
                for row in remaining
            )

            if console_active and not console_open:
                cursor = connection.execute(
                    """
                    INSERT INTO sessions (
                        session_type,
                        started_at
                    )
                    VALUES ('console', ?)
                    """,
                    (timestamp,),
                )

                connection.execute(
                    """
                    INSERT INTO checkpoints (
                        session_id,
                        observed_at,
                        updated_at
                    )
                    VALUES (?, ?, ?)
                    """,
                    (
                        cursor.lastrowid,
                        timestamp,
                        timestamp,
                    ),
                )

            if gaming_active and not gaming_open:
                cursor = connection.execute(
                    """
                    INSERT INTO sessions (
                        session_type,
                        started_at,
                        player_name,
                        title_id,
                        title_name,
                        title_image
                    )
                    VALUES ('gaming', ?, ?, ?, ?, ?)
                    """,
                    (
                        timestamp,
                        player_name,
                        state.title_id,
                        state.title_name,
                        state.title_image,
                    ),
                )

                connection.execute(
                    """
                    INSERT INTO checkpoints (
                        session_id,
                        observed_at,
                        updated_at
                    )
                    VALUES (?, ?, ?)
                    """,
                    (
                        cursor.lastrowid,
                        timestamp,
                        timestamp,
                    ),
                )

            # Build the normalized state for change detection.
            # Repeated heartbeat messages update checkpoints but
            # do not create duplicate historical events.
            current_players = json.dumps(
                list(state.players),
                ensure_ascii=False,
                separators=(",", ":"),
            )

            previous_players = previous["last_player"]

            # Normalize legacy player JSON before comparison.
            if previous_players is not None:
                try:
                    previous_players = json.dumps(
                        json.loads(previous_players),
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                except (TypeError, ValueError):
                    pass

            state_changed = (
                previous["last_observation_at"] is None
                or previous["last_power"] != state.power.value
                or previous["last_activity"] != state.activity.value
                or previous_players != current_players
                or previous["last_title_id"] != state.title_id
            )

            if state_changed:
                connection.execute(
                    """
                    INSERT INTO events (
                        event_type,
                        occurred_at,
                        payload_json
                    )
                    VALUES (?, ?, ?)
                    """,
                    (
                        EventType.STATE_UPDATE.value,
                        timestamp,
                        json.dumps(
                            {
                                "power": state.power.value,
                                "device_status": state.device_status,
                                "activity": state.activity.value,
                                "players": list(state.players),
                                "title_id": state.title_id,
                                "title_name": state.title_name,
                            },
                            ensure_ascii=False,
                        ),
                    ),
                )

            # Always persist the latest accepted observation,
            # even when the console state has not changed.
            connection.execute(
                """
                UPDATE monitoring_state
                SET last_observation_at = ?,
                    last_power = ?,
                    last_activity = ?,
                    last_player = ?,
                    last_title_id = ?,
                    updated_at = ?
                WHERE id = 1
                """,
                (
                    timestamp,
                    state.power.value,
                    state.activity.value,
                    current_players,
                    state.title_id,
                    datetime.now(timezone.utc).timestamp(),
                ),
            )

        return True


    def recover_open_sessions(self) -> int:
        """
        Recover sessions left open by an interrupted process.

        Each session is closed at its latest persisted checkpoint.
        If no checkpoint exists, its start timestamp is used.

        The operation is atomic and idempotent.

        Returns:
            Number of sessions recovered.
        """

        with self.transaction() as connection:
            rows = connection.execute(
                """
                SELECT
                    s.id,
                    s.started_at,
                    c.observed_at
                FROM sessions AS s
                LEFT JOIN checkpoints AS c
                    ON c.session_id = s.id
                WHERE s.ended_at IS NULL
                """
            ).fetchall()

            for row in rows:
                end_timestamp = (
                    row["observed_at"]
                    if row["observed_at"] is not None
                    else row["started_at"]
                )

                connection.execute(
                    """
                    UPDATE sessions
                    SET ended_at = ?
                    WHERE id = ?
                      AND ended_at IS NULL
                    """,
                    (
                        max(end_timestamp, row["started_at"]),
                        row["id"],
                    ),
                )

            return len(rows)

    def close(self) -> None:
        """Close the SQLite connection safely."""

        with self._lock:
            self._connection.close()
