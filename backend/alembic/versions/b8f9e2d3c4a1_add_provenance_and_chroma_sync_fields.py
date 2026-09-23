"""add provenance, qco, and chroma sync fields to indian_standards and certification_requirements

Revision ID: b8f9e2d3c4a1
Revises: a4c8d2e1f907
Create Date: 2026-09-23 20:25:00.000000

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "b8f9e2d3c4a1"
down_revision: Union[str, Sequence[str], None] = "a4c8d2e1f907"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # IndianStandard columns
    op.add_column("indian_standards", sa.Column("canonical_standard_number", sa.String(length=100), nullable=True))
    op.create_index(op.f("ix_indian_standards_canonical_standard_number"), "indian_standards", ["canonical_standard_number"], unique=True)
    
    op.add_column("indian_standards", sa.Column("base_standard_number", sa.String(length=50), nullable=True))
    op.create_index(op.f("ix_indian_standards_base_standard_number"), "indian_standards", ["base_standard_number"], unique=False)
    
    op.add_column("indian_standards", sa.Column("part_number", sa.String(length=50), nullable=True))
    op.add_column("indian_standards", sa.Column("revision_year", sa.String(length=20), nullable=True))
    op.add_column("indian_standards", sa.Column("source_type", sa.String(length=50), nullable=True, server_default="Local Metadata Index"))
    op.add_column("indian_standards", sa.Column("source_document", sa.String(length=255), nullable=True))
    op.add_column("indian_standards", sa.Column("source_document_hash", sa.String(length=64), nullable=True))
    op.add_column("indian_standards", sa.Column("verified_at", sa.DateTime(), nullable=True))
    op.add_column("indian_standards", sa.Column("verified_by", sa.String(length=100), nullable=True))
    op.add_column("indian_standards", sa.Column("evidence_confidence", sa.String(length=50), nullable=True, server_default="Medium"))
    
    op.add_column("indian_standards", sa.Column("embedding_status", sa.String(length=50), nullable=True, server_default="pending"))
    op.add_column("indian_standards", sa.Column("last_embedded_at", sa.DateTime(), nullable=True))
    op.add_column("indian_standards", sa.Column("indexed_content_hash", sa.String(length=64), nullable=True))
    op.add_column("indian_standards", sa.Column("embedding_error", sa.Text(), nullable=True))
    op.add_column("indian_standards", sa.Column("needs_reindex", sa.Boolean(), nullable=False, server_default=sa.text("true")))
    op.add_column("indian_standards", sa.Column("embedding_version", sa.String(length=20), nullable=True, server_default="v1.0"))

    # CertificationRequirement columns
    op.add_column("certification_requirements", sa.Column("notification_number", sa.String(length=100), nullable=True))
    op.add_column("certification_requirements", sa.Column("issuing_authority", sa.String(length=150), nullable=True))
    op.add_column("certification_requirements", sa.Column("notification_date", sa.String(length=50), nullable=True))
    op.add_column("certification_requirements", sa.Column("effective_date", sa.String(length=50), nullable=True))
    op.add_column("certification_requirements", sa.Column("product_scope", sa.Text(), nullable=True))
    op.add_column("certification_requirements", sa.Column("applicable_standard", sa.String(length=100), nullable=True))
    op.add_column("certification_requirements", sa.Column("official_document_url", sa.String(length=500), nullable=True))
    op.add_column("certification_requirements", sa.Column("evidence_text", sa.Text(), nullable=True))
    op.add_column("certification_requirements", sa.Column("page_or_clause_reference", sa.String(length=100), nullable=True))
    op.add_column("certification_requirements", sa.Column("verified_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("certification_requirements", "verified_at")
    op.drop_column("certification_requirements", "page_or_clause_reference")
    op.drop_column("certification_requirements", "evidence_text")
    op.drop_column("certification_requirements", "official_document_url")
    op.drop_column("certification_requirements", "applicable_standard")
    op.drop_column("certification_requirements", "product_scope")
    op.drop_column("certification_requirements", "effective_date")
    op.drop_column("certification_requirements", "notification_date")
    op.drop_column("certification_requirements", "issuing_authority")
    op.drop_column("certification_requirements", "notification_number")

    op.drop_column("indian_standards", "embedding_version")
    op.drop_column("indian_standards", "needs_reindex")
    op.drop_column("indian_standards", "embedding_error")
    op.drop_column("indian_standards", "indexed_content_hash")
    op.drop_column("indian_standards", "last_embedded_at")
    op.drop_column("indian_standards", "embedding_status")
    op.drop_column("indian_standards", "evidence_confidence")
    op.drop_column("indian_standards", "verified_by")
    op.drop_column("indian_standards", "verified_at")
    op.drop_column("indian_standards", "source_document_hash")
    op.drop_column("indian_standards", "source_document")
    op.drop_column("indian_standards", "source_type")
    op.drop_column("indian_standards", "revision_year")
    op.drop_column("indian_standards", "part_number")
    op.drop_index(op.f("ix_indian_standards_base_standard_number"), table_name="indian_standards")
    op.drop_column("indian_standards", "base_standard_number")
    op.drop_index(op.f("ix_indian_standards_canonical_standard_number"), table_name="indian_standards")
    op.drop_column("indian_standards", "canonical_standard_number")
