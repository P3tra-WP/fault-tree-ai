"""Durable SQL storage for analyses and their computed minimal cut sets."""

from __future__ import annotations

import threading
import uuid
from pathlib import Path

from sqlalchemy import JSON, ForeignKey, Integer, String, create_engine, delete
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

from app.config import settings
from app.domain.models import AnalysisResult


class Base(DeclarativeBase):
    pass


class AnalysisRecord(Base):
    __tablename__ = "analyses"

    analysis_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    result: Mapped[dict] = mapped_column(JSON, nullable=False)
    import_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)
    cut_sets: Mapped[list["AnalysisCutSetRecord"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )


class AnalysisCutSetRecord(Base):
    __tablename__ = "analysis_cut_sets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.analysis_id"), nullable=False, index=True)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    event_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    event_descriptions: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    baseline_probability: Mapped[float | None] = mapped_column(nullable=True)
    residual_probability: Mapped[float | None] = mapped_column(nullable=True)
    analysis: Mapped[AnalysisRecord] = relationship(back_populates="cut_sets")


class DatabaseStore:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._engine: Engine | None = None
        self._sessions: sessionmaker[Session] | None = None
        self._lock = threading.Lock()

    def _session_factory(self) -> sessionmaker[Session]:
        if self._sessions is not None:
            return self._sessions

        with self._lock:
            if self._sessions is None:
                if self._database_url.startswith("sqlite:///"):
                    database_path = self._database_url.removeprefix("sqlite:///")
                    if database_path and database_path != ":memory:":
                        Path(database_path).parent.mkdir(parents=True, exist_ok=True)
                self._engine = create_engine(
                    self._database_url,
                    connect_args={"check_same_thread": False} if self._database_url.startswith("sqlite") else {},
                )
                Base.metadata.create_all(self._engine)
                self._sessions = sessionmaker(self._engine, expire_on_commit=False)

        return self._sessions

    def new_id(self) -> str:
        return uuid.uuid4().hex

    def save(self, result: AnalysisResult) -> None:
        with self._session_factory()() as session:
            record = session.get(AnalysisRecord, result.analysis_id)
            if record is None:
                record = AnalysisRecord(
                    analysis_id=result.analysis_id,
                    result=result.model_dump(mode="json"),
                    created_at=result.created_at,
                    updated_at=result.updated_at,
                )
                session.add(record)
            else:
                record.result = result.model_dump(mode="json")
                record.updated_at = result.updated_at

            session.execute(
                delete(AnalysisCutSetRecord).where(AnalysisCutSetRecord.analysis_id == result.analysis_id)
            )
            session.add_all(
                AnalysisCutSetRecord(
                    analysis_id=result.analysis_id,
                    ordinal=ordinal,
                    event_ids=cut_set.event_ids,
                    event_descriptions=cut_set.event_descriptions,
                    baseline_probability=cut_set.baseline_probability,
                    residual_probability=cut_set.residual_probability,
                )
                for ordinal, cut_set in enumerate(result.minimal_cut_sets)
            )
            session.commit()

    def get(self, analysis_id: str) -> AnalysisResult | None:
        with self._session_factory()() as session:
            record = session.get(AnalysisRecord, analysis_id)
            return AnalysisResult.model_validate(record.result) if record else None

    def next_import_sequence(self, analysis_id: str) -> int:
        with self._session_factory()() as session:
            record = session.get(AnalysisRecord, analysis_id)
            if record is None:
                return 1
            record.import_sequence += 1
            session.commit()
            return record.import_sequence


store = DatabaseStore(settings.database_url)
