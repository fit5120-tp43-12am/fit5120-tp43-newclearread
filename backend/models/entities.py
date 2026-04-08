from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


_MYSQL_TABLE_ARGS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}


class User(Base):
    __tablename__ = "USER"
    __table_args__ = (_MYSQL_TABLE_ARGS,)

    user_id: Mapped[int] = mapped_column(mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    preferences: Mapped[Optional[Dict[str, Any]]] = mapped_column(mysql.JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        mysql.DATETIME(fsp=3),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(3)"),
    )
    last_active_at: Mapped[Optional[datetime]] = mapped_column(mysql.DATETIME(fsp=3), nullable=True)

    documents: Mapped[List["Document"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    audio_sessions: Mapped[List["AudioSession"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    reading_processes: Mapped[List["ReadingProcess"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    focus_mode_settings: Mapped[List["FocusModeSetting"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    voice_recordings: Mapped[List["VoiceRecording"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    user_communities: Mapped[List["UserCommunity"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Document(Base):
    __tablename__ = "DOCUMENT"
    __table_args__ = (
        Index("idx_document_user_id", "user_id"),
        _MYSQL_TABLE_ARGS,
    )

    document_id: Mapped[int] = mapped_column(mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey("USER.user_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    parsed_text: Mapped[Optional[str]] = mapped_column(mysql.LONGTEXT, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        mysql.DATETIME(fsp=3),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(3)"),
    )

    user: Mapped["User"] = relationship(back_populates="documents")
    processed_contents: Mapped[List["ProcessedContent"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    glossary_terms: Mapped[List["Glossary"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    task_steps: Mapped[List["TaskStep"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="TaskStep.step_order",
    )
    audio_sessions: Mapped[List["AudioSession"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    reading_processes: Mapped[List["ReadingProcess"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ProcessedContent(Base):
    __tablename__ = "PROCESSED_CONTENT"
    __table_args__ = (
        Index("idx_processed_content_document_id", "document_id"),
        Index("idx_processed_content_document_type", "document_id", "content_type"),
        _MYSQL_TABLE_ARGS,
    )

    content_id: Mapped[int] = mapped_column(mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey("DOCUMENT.document_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(mysql.LONGTEXT, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        mysql.DATETIME(fsp=3),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(3)"),
    )

    document: Mapped["Document"] = relationship(back_populates="processed_contents")


class Glossary(Base):
    __tablename__ = "GLOSSARY"
    __table_args__ = (
        UniqueConstraint("document_id", "term", name="uk_glossary_document_term"),
        Index("idx_glossary_document_id", "document_id"),
        _MYSQL_TABLE_ARGS,
    )

    term_id: Mapped[int] = mapped_column(mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey("DOCUMENT.document_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    term: Mapped[str] = mapped_column(String(255), nullable=False)
    simple_definition: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    context_example: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    document: Mapped["Document"] = relationship(back_populates="glossary_terms")


class TaskStep(Base):
    __tablename__ = "TASK_STEP"
    __table_args__ = (
        UniqueConstraint("document_id", "step_order", name="uk_task_step_document_order"),
        Index("idx_task_step_document_id", "document_id"),
        _MYSQL_TABLE_ARGS,
    )

    step_id: Mapped[int] = mapped_column(mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey("DOCUMENT.document_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    step_order: Mapped[int] = mapped_column(mysql.INTEGER(unsigned=True), nullable=False)
    instruction_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_completed: Mapped[bool] = mapped_column(
        mysql.TINYINT(1),
        nullable=False,
        server_default=text("0"),
    )

    document: Mapped["Document"] = relationship(back_populates="task_steps")


class AudioSession(Base):
    __tablename__ = "AUDIO_SESSION"
    __table_args__ = (
        Index("idx_audio_session_user_id", "user_id"),
        Index("idx_audio_session_document_id", "document_id"),
        _MYSQL_TABLE_ARGS,
    )

    session_id: Mapped[int] = mapped_column(mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey("USER.user_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey("DOCUMENT.document_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    playback_speed: Mapped[Decimal] = mapped_column(
        mysql.DECIMAL(3, 2),
        nullable=False,
        server_default=text("1.00"),
    )
    last_position_seconds: Mapped[int] = mapped_column(mysql.INTEGER(unsigned=True), nullable=False, server_default=text("0"))
    started_at: Mapped[datetime] = mapped_column(
        mysql.DATETIME(fsp=3),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(3)"),
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(mysql.DATETIME(fsp=3), nullable=True)

    user: Mapped["User"] = relationship(back_populates="audio_sessions")
    document: Mapped["Document"] = relationship(back_populates="audio_sessions")


class ReadingProcess(Base):
    __tablename__ = "READING_PROCESS"
    __table_args__ = (
        UniqueConstraint("user_id", "document_id", name="uk_reading_process_user_document"),
        Index("idx_reading_process_document_id", "document_id"),
        _MYSQL_TABLE_ARGS,
    )

    process_id: Mapped[int] = mapped_column(mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey("USER.user_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey("DOCUMENT.document_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    last_position: Mapped[int] = mapped_column(mysql.INTEGER(unsigned=True), nullable=False, server_default=text("0"))
    last_accessed_at: Mapped[datetime] = mapped_column(
        mysql.DATETIME(fsp=3),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(3)"),
    )

    user: Mapped["User"] = relationship(back_populates="reading_processes")
    document: Mapped["Document"] = relationship(back_populates="reading_processes")


class FocusModeSetting(Base):
    __tablename__ = "FOCUS_MODE_SETTING"
    __table_args__ = (
        UniqueConstraint("user_id", name="uk_focus_mode_setting_user_id"),
        _MYSQL_TABLE_ARGS,
    )

    setting_id: Mapped[int] = mapped_column(mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey("USER.user_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    is_enabled: Mapped[bool] = mapped_column(mysql.TINYINT(1), nullable=False, server_default=text("0"))
    ruler_width: Mapped[int] = mapped_column(mysql.INTEGER(unsigned=True), nullable=False, server_default=text("80"))

    user: Mapped["User"] = relationship(back_populates="focus_mode_settings")


class VoiceRecording(Base):
    __tablename__ = "VOICE_RECORDING"
    __table_args__ = (
        Index("idx_voice_recording_user_id", "user_id"),
        _MYSQL_TABLE_ARGS,
    )

    recording_id: Mapped[int] = mapped_column(mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey("USER.user_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    audio_file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    transcribed_text: Mapped[Optional[str]] = mapped_column(mysql.LONGTEXT, nullable=True)
    structured_notes: Mapped[Optional[str]] = mapped_column(mysql.LONGTEXT, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        mysql.DATETIME(fsp=3),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(3)"),
    )

    user: Mapped["User"] = relationship(back_populates="voice_recordings")


class CommunityResource(Base):
    __tablename__ = "COMMUNITY_RESOURCE"
    __table_args__ = (
        Index("idx_community_resource_type", "type"),
        Index("idx_community_resource_state", "state"),
        _MYSQL_TABLE_ARGS,
    )

    resource_id: Mapped[int] = mapped_column(mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    user_communities: Mapped[List["UserCommunity"]] = relationship(
        back_populates="resource",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class UserCommunity(Base):
    __tablename__ = "USER_COMMUNITY"
    __table_args__ = (
        Index("idx_user_community_resource_id", "resource_id"),
        _MYSQL_TABLE_ARGS,
    )

    user_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey("USER.user_id", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    )
    resource_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey("COMMUNITY_RESOURCE.resource_id", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        mysql.DATETIME(fsp=3),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(3)"),
    )

    user: Mapped["User"] = relationship(back_populates="user_communities")
    resource: Mapped["CommunityResource"] = relationship(back_populates="user_communities")

