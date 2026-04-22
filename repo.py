import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


@dataclass
class Measurement:
    id: int
    created_at: str
    posto: str  # FUNDO / ACAB / JAT
    operador: str
    varal: str
    projeto: str | None
    serie: str | None
    values: list[str]  # len 46
    status: str  # PENDING / EXPORTED
    exported_at: str | None


class Repo:
    def __init__(self, db_path: str | Path = "medicoes.db") -> None:
        self.db_path = str(db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    def _init_db(self) -> None:
        # 1. Cria a tabela se não existir (inclui varal desde o início)
        with self._connect() as con:
            cols = ",".join([f"m{i:02d} TEXT" for i in range(1, 47)])
            con.execute(
                f"""
                CREATE TABLE IF NOT EXISTS measurements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    posto TEXT NOT NULL,
                    operador TEXT NOT NULL,
                    varal TEXT NULL,
                    projeto TEXT NULL,
                    serie TEXT NULL,
                    {cols},
                    status TEXT NOT NULL,
                    exported_at TEXT NULL
                )
                """
            )

        # 2. Migração: adiciona varal em bancos antigos que ainda não têm a coluna
        with self._connect() as con:
            existing = [r["name"] for r in con.execute("PRAGMA table_info(measurements)")]
            if "varal" not in existing:
                con.execute("ALTER TABLE measurements ADD COLUMN varal TEXT NULL")

    def create_pending(
        self,
        posto: str,
        operador: str,
        varal: str,
        values: list[str],
        projeto: str | None = None,
        serie: str | None = None,
    ) -> int:
        assert len(values) == 46

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cols = ", ".join([f"m{i:02d}" for i in range(1, 47)])
        placeholders = ", ".join(["?"] * 46)

        with self._connect() as con:
            cur = con.execute(
                f"""
                INSERT INTO measurements
                (created_at, posto, operador, varal, projeto, serie, {cols}, status, exported_at)
                VALUES (?, ?, ?, ?, ?, ?, {placeholders}, 'PENDING', NULL)
                """,
                [
                    now,
                    posto,
                    operador,
                    varal,  
                    projeto,
                    serie,
                    *values,
                ],
            )
            return int(cur.lastrowid)

    def list_pending(self, posto: str) -> list[Measurement]:
        with self._connect() as con:
            rows = con.execute(
                """
                SELECT * FROM measurements
                WHERE status='PENDING' AND posto=?
                ORDER BY id ASC
                """,
                [posto],
            ).fetchall()
        return [self._row_to_measurement(r) for r in rows]

    def list_history(self, limit: int = 200) -> list[Measurement]:
        with self._connect() as con:
            rows = con.execute(
                """
                SELECT * FROM measurements
                WHERE status='EXPORTED'
                ORDER BY exported_at DESC, id DESC
                LIMIT ?
                """,
                [limit],
            ).fetchall()
        return [self._row_to_measurement(r) for r in rows]

    def get_by_ids(self, ids: Iterable[int]) -> list[Measurement]:
        ids = list(ids)
        if not ids:
            return []
        qs = ", ".join(["?"] * len(ids))
        with self._connect() as con:
            rows = con.execute(f"SELECT * FROM measurements WHERE id IN ({qs})", ids).fetchall()
        # mantém uma ordem estável
        by_id = {r["id"]: self._row_to_measurement(r) for r in rows}
        return [by_id[i] for i in ids if i in by_id]

    def update_assignment(self, id_: int, projeto: str, serie: str) -> None:
        with self._connect() as con:
            con.execute(
                "UPDATE measurements SET projeto=?, serie=? WHERE id=?",
                [projeto, serie, id_],
            )

    def mark_exported(self, id_: int) -> None:
        exported_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._connect() as con:
            con.execute(
                "UPDATE measurements SET status='EXPORTED', exported_at=? WHERE id=?",
                [exported_at, id_],
            )

    def _row_to_measurement(self, r: sqlite3.Row) -> Measurement:
        values = [r[f"m{i:02d}"] or "" for i in range(1, 47)]
        return Measurement(
            id=int(r["id"]),
            created_at=r["created_at"],
            posto=r["posto"],
            operador=r["operador"],
            varal=r["varal"],
            projeto=r["projeto"],
            serie=r["serie"],
            values=values,
            status=r["status"],
            exported_at=r["exported_at"],
        )
    
    def delete_measurement(self, id_: int) -> None:
        with self._connect() as con:
            con.execute("DELETE FROM measurements WHERE id=?", [id_])

    def list_pending_all(self) -> list[Measurement]:
        with self._connect() as con:
            rows = con.execute(
                """
                SELECT * FROM measurements
                WHERE status='PENDING'
                ORDER BY posto ASC, datetime(created_at) DESC, id DESC
                """
            ).fetchall()
        return [self._row_to_measurement(r) for r in rows]
    
    def update_measurement(self, id, posto, operador, varal, projeto, serie, values):
        assert len(values) == 46

        cols = [f"m{i:02d}" for i in range(1, 47)]
        set_clause = ", ".join([f"{c}=?" for c in cols])

        with self._connect() as con:
            con.execute(
                f"""
                UPDATE measurements
                SET posto=?, operador=?, varal=?, projeto=?, serie=?, {set_clause}
                WHERE id=?
                """,
                [posto, operador, varal, projeto, serie, *values, id],
            )

    def get_config(self, key: str, default: str = "") -> str:
        with self._connect() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key   TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            row = con.execute(
                "SELECT value FROM config WHERE key = ?", [key]
            ).fetchone()
        return row[0] if row else default
 
    def set_config(self, key: str, value: str) -> None:
        """Grava ou atualiza um valor na tabela de configurações."""
        with self._connect() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key   TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            con.execute(
                "INSERT INTO config (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                [key, value]
            )