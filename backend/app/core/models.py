"""
SQLAlchemy database models for QueryNest.

Models:
- User
- Conversation
- ConversationMessage
- KnowledgeBaseDocument
"""

from __future__ import annotations

import uuid

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Boolean,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class User(Base):
    """
    Represents an authenticated QueryNest user.
    """

    __tablename__ = "users"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    full_name = Column(
        String(100),
        nullable=False,
    )

    email = Column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    password_hash = Column(
        String(255),
        nullable=False,
    )

    role = Column(
        String(50),
        nullable=False,
        default="User",
    )

    # Account access can be disabled by an administrator without deleting
    # the user's data. Existing accounts are active after the migration.
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    avatar = Column(
        String(500),
        nullable=True,
    )

    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    conversations = relationship(
        "Conversation",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # User-specific knowledge base documents
    knowledge_base_documents = relationship(
        "KnowledgeBaseDocument",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    procurement_requests = relationship(
        "ProcurementRequest",
        back_populates="user",
        cascade="all, delete-orphan",
    )



class Conversation(Base):
    """
    Represents one user's persistent conversation.
    """

    __tablename__ = "conversations"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    user_id = Column(
        String(36),
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user = relationship(
        "User",
        back_populates="conversations",
    )

    messages = relationship(
        "ConversationMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )


class ConversationMessage(Base):
    """
    Represents a single user or assistant message.

    message_metadata stores optional JSON-encoded information
    associated with the message, such as:
    - sources
    - retrieval results
    - confidence
    - speech text
    """

    __tablename__ = "conversation_messages"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    conversation_id = Column(
        String(36),
        ForeignKey(
            "conversations.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    role = Column(
        String(20),
        nullable=False,
    )

    content = Column(
        Text,
        nullable=False,
    )

    message_metadata = Column(
        "message_metadata",
        Text,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    conversation = relationship(
        "Conversation",
        back_populates="messages",
    )


class KnowledgeBaseDocument(Base):
    """
    Represents a document uploaded by a specific user
    to their personal knowledge base.
    """

    __tablename__ = "knowledge_base_documents"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    user_id = Column(
        String(36),
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    filename = Column(
        String(255),
        nullable=False,
    )

    original_filename = Column(
        String(255),
        nullable=True,
    )

    file_type = Column(
        String(50),
        nullable=True,
    )

    file_size = Column(
        Integer,
        nullable=True,
    )

    status = Column(
        String(50),
        nullable=False,
        default="processing",
    )

    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user = relationship(
        "User",
        back_populates="knowledge_base_documents",
    )


class ProcurementRequest(Base):
    """
    Represents a procurement specification analysis request submitted by a user.
    """

    __tablename__ = "procurement_requests"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    user_id = Column(
        String(36),
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    input_text = Column(
        Text,
        nullable=True,
    )

    uploaded_file_path = Column(
        String(500),
        nullable=True,
    )

    extracted_text = Column(
        Text,
        nullable=True,
    )

    product_category = Column(
        String(150),
        nullable=True,
    )

    procurement_purpose = Column(
        Text,
        nullable=True,
    )

    processing_status = Column(
        String(50),
        nullable=False,
        default="completed",
    )

    result_json = Column(
        Text,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    user = relationship(
        "User",
        back_populates="procurement_requests",
    )

    recommendations = relationship(
        "Recommendation",
        back_populates="procurement_request",
        cascade="all, delete-orphan",
    )


class IndianStandard(Base):
    """
    Represents an Indian Standard (BIS) entry in the reference catalog.
    """

    __tablename__ = "indian_standards"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    standard_number = Column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )

    title = Column(
        String(500),
        nullable=False,
    )

    scope = Column(
        Text,
        nullable=True,
    )

    category = Column(
        String(150),
        nullable=True,
        index=True,
    )

    sector = Column(
        String(150),
        nullable=True,
    )

    publication_date = Column(
        String(50),
        nullable=True,
    )

    revision = Column(
        String(100),
        nullable=True,
    )

    amendment_details = Column(
        Text,
        nullable=True,
    )

    status = Column(
        String(50),
        nullable=False,
        default="Active",
    )

    source_url = Column(
        String(500),
        nullable=True,
    )

    evidence_text = Column(
        Text,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    certifications = relationship(
        "CertificationRequirement",
        back_populates="standard",
        cascade="all, delete-orphan",
    )


class StandardRelationship(Base):
    """
    Represents a directional relationship between two Indian Standards (e.g. normative_reference, test_method, safety).
    """

    __tablename__ = "standard_relationships"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    standard_id = Column(
        String(36),
        ForeignKey(
            "indian_standards.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    related_standard_id = Column(
        String(36),
        ForeignKey(
            "indian_standards.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    relationship_type = Column(
        String(50),
        nullable=False,
    )

    description = Column(
        Text,
        nullable=True,
    )


class Recommendation(Base):
    """
    Represents a recommended Indian Standard generated for a procurement request.
    """

    __tablename__ = "recommendations"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    procurement_request_id = Column(
        String(36),
        ForeignKey(
            "procurement_requests.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    standard_id = Column(
        String(36),
        ForeignKey(
            "indian_standards.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    applicability_status = Column(
        String(50),
        nullable=False,
    )

    relevance_score = Column(
        Integer,
        nullable=False,
        default=0,
    )

    reasoning = Column(
        Text,
        nullable=True,
    )

    evidence = Column(
        Text,
        nullable=True,
    )

    verification_required = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    procurement_request = relationship(
        "ProcurementRequest",
        back_populates="recommendations",
    )

    standard = relationship("IndianStandard")


class CertificationRequirement(Base):
    """
    Represents a certification requirement linked to an Indian Standard (e.g. ISI, CRS, Hallmarking).
    """

    __tablename__ = "certification_requirements"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    standard_id = Column(
        String(36),
        ForeignKey(
            "indian_standards.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    certification_type = Column(
        String(100),
        nullable=False,
    )

    applicability = Column(
        String(100),
        nullable=False,
        default="Mandatory",
    )

    source_url = Column(
        String(500),
        nullable=True,
    )

    verification_status = Column(
        String(100),
        nullable=True,
    )

    standard = relationship(
        "IndianStandard",
        back_populates="certifications",
    )