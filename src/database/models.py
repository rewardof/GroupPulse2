"""
GroupPulse Database Models

SQLAlchemy ORM models for PostgreSQL database.
All models use async sessions and are optimized for high concurrency.
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, BIGINT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import enum


# Base class for all models
class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


# Enums
class GroupType(str, enum.Enum):
    """Group type enumeration."""
    SOURCE = "source"
    DESTINATION = "destination"


class RuleAction(str, enum.Enum):
    """Forwarding rule action enumeration."""
    FORWARD = "forward"
    FORWARD_NO_CAPTION = "forward_no_caption"
    NOTIFY_ONLY = "notify_only"
    IGNORE = "ignore"


# =============================================================================
# Users & Authentication
# =============================================================================

class User(Base):
    """
    User model - represents a Telegram user using the bot.

    One user can have exactly one Telegram account.
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    telegram_account: Mapped[Optional["TelegramAccount"]] = relationship(
        "TelegramAccount", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    keywords: Mapped[List["Keyword"]] = relationship(
        "Keyword", back_populates="user", cascade="all, delete-orphan"
    )
    forwarding_rules: Mapped[List["ForwardingRule"]] = relationship(
        "ForwardingRule", back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_users_telegram_id", "telegram_id"),
        Index("idx_users_is_active", "is_active", postgresql_where=(Column("is_active") == True)),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} telegram_id={self.telegram_id} username={self.username}>"


# =============================================================================
# Telegram Accounts (One per user)
# =============================================================================

class TelegramAccount(Base):
    """
    Telegram account model - stores encrypted session strings.

    Each user has exactly ONE Telegram account.
    Session strings are encrypted with AES-256-GCM.
    """
    __tablename__ = "telegram_accounts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    phone_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    api_id: Mapped[int] = mapped_column(Integer, nullable=False)
    api_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Encrypted session string (AES-256-GCM)
    session_string_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    session_encryption_key_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    is_authorized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Rate limiting state
    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    messages_sent_today: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    flood_wait_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Metadata
    account_created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    dc_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Telegram data center

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="telegram_account")
    groups: Mapped[List["Group"]] = relationship(
        "Group", back_populates="account", cascade="all, delete-orphan"
    )
    message_logs: Mapped[List["MessageLog"]] = relationship(
        "MessageLog", back_populates="account", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_accounts_user_id", "user_id"),
        Index("idx_accounts_is_active", "is_active", postgresql_where=(Column("is_active") == True)),
        Index("idx_accounts_flood_wait", "flood_wait_until",
              postgresql_where=(Column("flood_wait_until") > func.now())),
    )

    def __repr__(self) -> str:
        return f"<TelegramAccount id={self.id} user_id={self.user_id} phone={self.phone_number}>"


# =============================================================================
# Groups (Source & Destination)
# =============================================================================

class Group(Base):
    """
    Telegram group/channel model.

    Groups can be either SOURCE (listen to) or DESTINATION (forward to).
    """
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("telegram_accounts.id", ondelete="CASCADE"), nullable=False
    )

    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    access_hash: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    group_type: Mapped[GroupType] = mapped_column(Enum(GroupType), nullable=False)

    # Monitoring
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    total_messages_received: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    total_messages_forwarded: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    # Metadata
    member_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_scam: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    account: Mapped["TelegramAccount"] = relationship("TelegramAccount", back_populates="groups")
    message_logs: Mapped[List["MessageLog"]] = relationship(
        "MessageLog", back_populates="source_group", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_groups_account_id", "account_id"),
        Index("idx_groups_telegram_id", "telegram_id"),
        Index("idx_groups_type", "group_type"),
        Index("idx_groups_is_active", "is_active", postgresql_where=(Column("is_active") == True)),
        Index("idx_groups_unique_account_telegram", "account_id", "telegram_id", unique=True),
    )

    def __repr__(self) -> str:
        return f"<Group id={self.id} title={self.title} type={self.group_type}>"


# =============================================================================
# Keywords (For filtering)
# =============================================================================

class Keyword(Base):
    """
    Keyword model for message filtering.

    Supports both literal strings and regex patterns.
    """
    __tablename__ = "keywords"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    keyword: Mapped[str] = mapped_column(String(255), nullable=False)
    is_regex: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_case_sensitive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Statistics
    match_count: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    last_matched_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="keywords")

    __table_args__ = (
        Index("idx_keywords_user_id", "user_id"),
        Index("idx_keywords_is_active", "is_active", postgresql_where=(Column("is_active") == True)),
    )

    def __repr__(self) -> str:
        return f"<Keyword id={self.id} keyword={self.keyword} regex={self.is_regex}>"


# =============================================================================
# Forwarding Rules
# =============================================================================

class ForwardingRule(Base):
    """
    Forwarding rule model - defines message forwarding logic.

    Uses PostgreSQL arrays for many-to-many relationships with groups and keywords.
    """
    __tablename__ = "forwarding_rules"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Sources and destinations (array of IDs)
    source_group_ids: Mapped[List[int]] = mapped_column(ARRAY(BIGINT), nullable=False)
    destination_group_ids: Mapped[List[int]] = mapped_column(ARRAY(BIGINT), nullable=False)

    # Filtering (keyword IDs)
    keyword_ids: Mapped[List[int]] = mapped_column(ARRAY(BIGINT), nullable=False, default=list)
    require_all_keywords: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    exclude_keyword_ids: Mapped[List[int]] = mapped_column(ARRAY(BIGINT), nullable=False, default=list)

    # Action
    action: Mapped[RuleAction] = mapped_column(
        Enum(RuleAction), default=RuleAction.FORWARD, nullable=False
    )

    # Conditions
    only_media: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    only_text: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    min_text_length: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_text_length: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Rate limiting (per rule)
    max_forwards_per_minute: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_forwards_per_hour: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_forwards_per_day: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Humanization
    add_random_delay_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Priority (higher = processed first)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Statistics
    total_processed: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    total_forwarded: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    total_skipped: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="forwarding_rules")

    __table_args__ = (
        Index("idx_rules_user_id", "user_id"),
        Index("idx_rules_is_active", "is_active", postgresql_where=(Column("is_active") == True)),
        Index("idx_rules_priority", "priority"),
        # GIN indexes for array searches
        Index("idx_rules_source_groups", "source_group_ids", postgresql_using="gin"),
        Index("idx_rules_dest_groups", "destination_group_ids", postgresql_using="gin"),
        Index("idx_rules_keywords", "keyword_ids", postgresql_using="gin"),
    )

    def __repr__(self) -> str:
        return f"<ForwardingRule id={self.id} name={self.name} priority={self.priority}>"


# =============================================================================
# Message Log (Deduplication & Audit)
# =============================================================================

class MessageLog(Base):
    """
    Message log model - tracks processed messages for deduplication and auditing.

    Includes automatic cleanup after retention period.
    """
    __tablename__ = "message_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("telegram_accounts.id", ondelete="CASCADE"), nullable=False
    )
    source_group_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False
    )

    # Message identifiers
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    message_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # SHA-256

    # Content preview (for debugging)
    text_preview: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    has_media: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    media_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # Forwarding info
    was_forwarded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    destination_group_ids: Mapped[Optional[List[int]]] = mapped_column(ARRAY(BIGINT), nullable=True)
    forwarding_rule_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("forwarding_rules.id", ondelete="SET NULL"), nullable=True
    )

    # Timing
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    forwarded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    account: Mapped["TelegramAccount"] = relationship("TelegramAccount", back_populates="message_logs")
    source_group: Mapped["Group"] = relationship("Group", back_populates="message_logs")

    __table_args__ = (
        Index("idx_msg_log_account_id", "account_id"),
        Index("idx_msg_log_source_group", "source_group_id"),
        Index("idx_msg_log_message_hash", "message_hash"),
        Index("idx_msg_log_received_at", "received_at"),
        # Unique constraint for deduplication (1 hour window)
        Index(
            "idx_msg_log_dedup",
            "account_id", "source_group_id", "message_id",
            unique=True,
            postgresql_where=(Column("received_at") > func.now() - func.make_interval(0, 0, 0, 0, 1))
        ),
    )

    def __repr__(self) -> str:
        return f"<MessageLog id={self.id} message_id={self.message_id} forwarded={self.was_forwarded}>"
