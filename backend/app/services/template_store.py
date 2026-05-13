import json
import sqlite3
from pathlib import Path
from uuid import uuid4

from pydantic import TypeAdapter

from backend.app.schemas import (
    EssayCorrectionInput,
    EssayCorrectionResponse,
    EssayTemplate,
    EssayTemplateCreate,
)


class SQLiteEssayStore:
    def __init__(self, db_path: str | Path = "data/essay_backend.sqlite3") -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def create(self, template: EssayTemplateCreate) -> EssayTemplate:
        created = EssayTemplate(id=f"tpl_{uuid4().hex}", **template.model_dump())
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO essay_templates
                    (id, title, requirements, grade_level, essay_type)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    created.id,
                    created.title,
                    created.requirements,
                    created.grade_level,
                    created.essay_type,
                ),
            )
        return created

    def get(self, template_id: str) -> EssayTemplate | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, title, requirements, grade_level, essay_type
                FROM essay_templates
                WHERE id = ?
                """,
                (template_id,),
            ).fetchone()
        if row is None:
            return None
        return EssayTemplate(
            id=row["id"],
            title=row["title"],
            requirements=row["requirements"],
            grade_level=row["grade_level"],
            essay_type=row["essay_type"],
        )

    def list(self) -> list[EssayTemplate]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, title, requirements, grade_level, essay_type
                FROM essay_templates
                ORDER BY created_at DESC
                """
            ).fetchall()
        return [
            EssayTemplate(
                id=row["id"],
                title=row["title"],
                requirements=row["requirements"],
                grade_level=row["grade_level"],
                essay_type=row["essay_type"],
            )
            for row in rows
        ]

    def to_correction_input(self, template_id: str) -> EssayCorrectionInput | None:
        template = self.get(template_id)
        if template is None:
            return None
        return EssayCorrectionInput(
            title=template.title,
            requirements=template.requirements,
            grade_level=template.grade_level,
            essay_type=template.essay_type,
        )

    def save_correction(self, correction: EssayCorrectionResponse) -> EssayCorrectionResponse:
        payload = correction.model_dump_json(by_alias=True)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO essay_corrections (id, payload)
                VALUES (?, ?)
                """,
                (correction.id, payload),
            )
        return correction

    def get_correction(self, correction_id: str) -> EssayCorrectionResponse | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload
                FROM essay_corrections
                WHERE id = ?
                """,
                (correction_id,),
            ).fetchone()
        if row is None:
            return None
        return TypeAdapter(EssayCorrectionResponse).validate_python(json.loads(row["payload"]))

    def clear(self) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM essay_corrections")
            connection.execute("DELETE FROM essay_templates")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS essay_templates (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    requirements TEXT NOT NULL DEFAULT '',
                    grade_level TEXT NOT NULL,
                    essay_type TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS essay_corrections (
                    id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )


template_store = SQLiteEssayStore()
