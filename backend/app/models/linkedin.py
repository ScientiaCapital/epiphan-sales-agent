"""LinkedIn workflow and tracking models."""

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class PostStatus(str, Enum):
    """LinkedIn post status."""

    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"


class PostType(str, Enum):
    """Type of LinkedIn content."""

    TEXT = "text"
    IMAGE = "image"
    CAROUSEL = "carousel"
    VIDEO = "video"
    ARTICLE = "article"
    POLL = "poll"


class LinkedInPost(Base, TimestampMixin):
    """
    LinkedIn post tracking for thought leadership content.

    Schedule: Tuesday & Thursday
    - Tuesday: Fresh week, high engagement
    - Thursday: Pre-weekend planning mode
    """

    __tablename__ = "linkedin_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Content
    title: Mapped[str | None] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    post_type: Mapped[PostType] = mapped_column(String(20), default=PostType.TEXT)

    # Media (if applicable)
    media_urls: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    media_alt_text: Mapped[str | None] = mapped_column(Text)

    # Scheduling
    status: Mapped[PostStatus] = mapped_column(
        String(20), default=PostStatus.DRAFT, index=True
    )
    scheduled_for: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # LinkedIn Reference
    linkedin_post_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(500))

    # Categorization
    topic: Mapped[str | None] = mapped_column(String(100), index=True)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    campaign: Mapped[str | None] = mapped_column(String(100))

    # Engagement Metrics (updated after publish)
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    shares: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    engagement_rate: Mapped[float | None] = mapped_column(Integer)

    # Performance Notes
    performance_notes: Mapped[str | None] = mapped_column(Text)
    what_worked: Mapped[str | None] = mapped_column(Text)

    # Epiphan Context
    related_product: Mapped[str | None] = mapped_column(
        String(100)
    )  # Pearl, Webcaster, etc.
    target_persona: Mapped[str | None] = mapped_column(
        String(100)
    )  # Education, Broadcast, etc.

    __table_args__ = (
        Index("ix_linkedin_scheduled", "status", "scheduled_for"),
    )


class LinkedInCadence(Base, TimestampMixin):
    """
    LinkedIn posting cadence configuration.

    Default: Tuesday & Thursday
    Optimal times: 7-8am, 12pm, 5-6pm
    """

    __tablename__ = "linkedin_cadence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Cadence Settings
    name: Mapped[str] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Days (0=Monday, 6=Sunday)
    posting_days: Mapped[list[int]] = mapped_column(
        ARRAY(Integer), default=[1, 3]  # Tuesday, Thursday
    )

    # Times (24-hour format)
    posting_times: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=["08:00", "12:00"]
    )

    # Timezone
    timezone: Mapped[str] = mapped_column(String(50), default="America/New_York")

    # Content Queue Settings
    min_queue_size: Mapped[int] = mapped_column(
        Integer, default=4
    )  # Alert if queue low
    auto_schedule: Mapped[bool] = mapped_column(Boolean, default=False)

    # Analytics
    total_posts: Mapped[int] = mapped_column(Integer, default=0)
    avg_engagement_rate: Mapped[float | None] = mapped_column(Integer)

    __table_args__ = (Index("ix_cadence_active", "is_active"),)


class LinkedInEngagement(Base, TimestampMixin):
    """
    Track engagement activities on LinkedIn.

    For BDR prospecting and relationship building.
    """

    __tablename__ = "linkedin_engagements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Engagement Type
    engagement_type: Mapped[str] = mapped_column(
        String(30), index=True
    )  # like, comment, share, connect, message

    # Target
    target_linkedin_url: Mapped[str | None] = mapped_column(String(500))
    target_name: Mapped[str | None] = mapped_column(String(255))
    target_company: Mapped[str | None] = mapped_column(String(255))
    target_title: Mapped[str | None] = mapped_column(String(255))

    # Content (for comments/messages)
    content: Mapped[str | None] = mapped_column(Text)

    # Related Lead
    lead_id: Mapped[int | None] = mapped_column(Integer, index=True)

    # Outcome
    response_received: Mapped[bool] = mapped_column(Boolean, default=False)
    response_content: Mapped[str | None] = mapped_column(Text)
    response_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Metrics
    resulted_in_meeting: Mapped[bool] = mapped_column(Boolean, default=False)
    resulted_in_opportunity: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        Index("ix_engagement_type_date", "engagement_type", "created_at"),
    )


class LinkedInTemplate(Base, TimestampMixin):
    """
    Templates for LinkedIn content and outreach.

    Includes post templates and connection message templates.
    """

    __tablename__ = "linkedin_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Template Info
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    template_type: Mapped[str] = mapped_column(
        String(30), index=True
    )  # post, connection_request, inmail, comment

    # Content
    content: Mapped[str] = mapped_column(Text)
    # Variables: {{first_name}}, {{company}}, {{product}}, etc.

    # Categorization
    persona: Mapped[str | None] = mapped_column(String(100))  # Target audience
    use_case: Mapped[str | None] = mapped_column(String(100))
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String))

    # Performance
    times_used: Mapped[int] = mapped_column(Integer, default=0)
    avg_response_rate: Mapped[float | None] = mapped_column(Integer)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (Index("ix_template_type_active", "template_type", "is_active"),)
