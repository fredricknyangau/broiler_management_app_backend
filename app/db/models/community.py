from sqlalchemy import JSON, Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class CommunityCategory(Base, UUIDMixin, TimestampMixin):
    """
    Discussion topics/categories for categorization (Marketplace, Health, General).
    """

    __tablename__ = "community_categories"

    name = Column(String(100), nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True)
    description = Column(String(255))
    color = Column(String(20), default="#4CAF50")  # Default green
    icon = Column(String(50))  # Lucide icon name

    posts = relationship("CommunityPost", back_populates="category")


class CommunityPost(Base, UUIDMixin, TimestampMixin):
    """
    User-generated posts in the farm community feed.
    """

    __tablename__ = "community_posts"

    author_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id = Column(
        UUID(as_uuid=True),
        ForeignKey("community_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)

    # Simple image support (Local/External URL)
    image_url = Column(String(500), nullable=True)
    images = Column(JSON, default=[], doc="List of complementary image URLs")

    is_pinned = Column(Boolean, default=False)
    is_closed = Column(Boolean, default=False)

    # Metrics (De-normalized for performance, or updated via triggers/app logic)
    likes_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)

    # Relationships
    author = relationship("User", backref="community_posts")
    category = relationship("CommunityCategory", back_populates="posts")
    comments = relationship(
        "CommunityComment", back_populates="post", cascade="all, delete-orphan"
    )
    likes = relationship(
        "CommunityLike", back_populates="post", cascade="all, delete-orphan"
    )


class CommunityComment(Base, UUIDMixin, TimestampMixin):
    """
    Replies to posts.
    """

    __tablename__ = "community_comments"

    post_id = Column(
        UUID(as_uuid=True),
        ForeignKey("community_posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    content = Column(Text, nullable=False)

    # Relationships
    post = relationship("CommunityPost", back_populates="comments")
    author = relationship("User", backref="community_comments")


class CommunityLike(Base, UUIDMixin, TimestampMixin):
    """
    Tracks likes on posts to prevent duplicates.
    """

    __tablename__ = "community_likes"

    post_id = Column(
        UUID(as_uuid=True),
        ForeignKey("community_posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Relationships
    post = relationship("CommunityPost", back_populates="likes")
    user = relationship("User", backref="community_liked_posts")
