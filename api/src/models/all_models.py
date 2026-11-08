import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    CheckConstraint,
    UniqueConstraint,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from api.src.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Payee(Base):
    __tablename__ = "payees"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    legal_name = Column(String(255), nullable=False)
    registration_id = Column(String(100), nullable=False, unique=True, index=True)
    paypal_email = Column(String(255), nullable=False, index=True)
    category = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default="PENDING")  # PENDING, VERIFIED, BLOCKED
    verified_by = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    campaigns = relationship("Campaign", back_populates="payee")


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    story = Column(Text, nullable=False)
    purpose_category = Column(String(100), nullable=False)
    goal = Column(Float, nullable=False)
    currency = Column(String(10), default="USD", nullable=False)
    organizer = Column(String(255), nullable=False)
    payee_id = Column(UUID(as_uuid=True), ForeignKey("payees.id"), nullable=False)
    status = Column(String(50), default="DRAFT", nullable=False)  # DRAFT, ACTIVE, CLOSED
    proof_deadline = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    payee = relationship("Payee", back_populates="campaigns")
    milestones = relationship("Milestone", back_populates="campaign", cascade="all, delete-orphan")
    donations = relationship("Donation", back_populates="campaign")
    evidence_items = relationship("Evidence", back_populates="campaign")
    ledger_entries = relationship("LedgerEntry", back_populates="campaign")


class Milestone(Base):
    __tablename__ = "milestones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False)
    title = Column(String(255), nullable=False)
    target_amount = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    campaign = relationship("Campaign", back_populates="milestones")


class Donation(Base):
    __tablename__ = "donations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False)
    donor_name = Column(String(255), nullable=False)
    donor_email = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)
    paypal_order_id = Column(String(100), nullable=True, unique=True, index=True)
    paypal_capture_id = Column(String(100), nullable=True, unique=True, index=True)
    status = Column(String(50), default="INITIATED", nullable=False)  # INITIATED, CAPTURED, REFUNDED
    request_id = Column(String(100), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    campaign = relationship("Campaign", back_populates="donations")
    refund = relationship("Refund", back_populates="donation", uselist=False)


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False)
    file_path = Column(String(500), nullable=False)
    sha256 = Column(String(64), nullable=False, index=True)
    phash = Column(String(64), nullable=True, index=True)
    requested_amount = Column(Float, nullable=False)
    extracted_json = Column(JSON, nullable=True)
    status = Column(String(50), default="PENDING", nullable=False)  # PENDING, AUDITED, VERIFIED, REJECTED
    
    # Add-on 1: Payee independent confirmation
    confirmation_token = Column(String(100), nullable=False, unique=True, index=True, default=lambda: uuid.uuid4().hex)
    payee_confirmed = Column(Boolean, default=False, nullable=False)
    payee_confirmed_at = Column(DateTime(timezone=True), nullable=True)
    payee_notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    campaign = relationship("Campaign", back_populates="evidence_items")
    audit = relationship("Audit", back_populates="evidence", uselist=False)


class Audit(Base):
    __tablename__ = "audits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_id = Column(UUID(as_uuid=True), ForeignKey("evidence.id"), nullable=False, unique=True)
    checks_json = Column(JSON, nullable=False)
    risk_score = Column(Integer, nullable=False)
    decision = Column(String(50), nullable=False)  # RELEASE, REQUEST_MORE, HUMAN_REVIEW, REJECT
    explanation = Column(Text, nullable=False)
    model_info = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    evidence = relationship("Evidence", back_populates="audit")
    reviews = relationship("Review", back_populates="audit")


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_ledger_positive_amount"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False)
    type = Column(String(50), nullable=False)  # DONATION, RELEASE, REFUND
    amount = Column(Float, nullable=False)
    paypal_ref = Column(String(100), nullable=False)
    audit_id = Column(UUID(as_uuid=True), ForeignKey("audits.id"), nullable=True)
    status = Column(String(50), default="CONFIRMED", nullable=False)  # SUBMITTED, CONFIRMED, FAILED
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    campaign = relationship("Campaign", back_populates="ledger_entries")


class Refund(Base):
    __tablename__ = "refunds"
    __table_args__ = (
        UniqueConstraint("donation_id", name="uq_refunds_donation_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    donation_id = Column(UUID(as_uuid=True), ForeignKey("donations.id"), nullable=False)
    amount = Column(Float, nullable=False)
    paypal_refund_id = Column(String(100), nullable=False, unique=True)
    reason = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    donation = relationship("Donation", back_populates="refund")


class Release(Base):
    __tablename__ = "releases"
    __table_args__ = (
        UniqueConstraint("release_id", name="uq_releases_release_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    release_id = Column(String(100), nullable=False, index=True)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False)
    payee_id = Column(UUID(as_uuid=True), ForeignKey("payees.id"), nullable=False)
    audit_id = Column(UUID(as_uuid=True), ForeignKey("audits.id"), nullable=False)
    amount = Column(Float, nullable=False)
    paypal_batch_id = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class Fingerprint(Base):
    __tablename__ = "fingerprints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kind = Column(String(50), nullable=False, index=True)  # invoice, image, text
    value = Column(String(255), nullable=False, index=True)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False)
    evidence_id = Column(UUID(as_uuid=True), ForeignKey("evidence.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class Review(Base):
    __tablename__ = "reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(UUID(as_uuid=True), ForeignKey("audits.id"), nullable=False)
    reviewer = Column(String(100), nullable=False)
    action = Column(String(50), nullable=False)  # APPROVE, REJECT, REQUEST_MORE
    reason = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    audit = relationship("Audit", back_populates="reviews")


class AuditLog(Base):
    __tablename__ = "audit_log"

    seq = Column(Integer, primary_key=True, autoincrement=True)
    prev_hash = Column(String(64), nullable=False)
    hash = Column(String(64), nullable=False, unique=True, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    payload_json = Column(JSON, nullable=False)
    ts = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    signature = Column(String(255), nullable=True)


class AgentTrace(Base):
    __tablename__ = "agent_traces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    step = Column(Integer, nullable=False)
    tool = Column(String(100), nullable=False)
    input_json = Column(JSON, nullable=True)
    output_json = Column(JSON, nullable=True)
    ts = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    __table_args__ = (
        UniqueConstraint("paypal_event_id", name="uq_webhook_event_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paypal_event_id = Column(String(100), nullable=False, index=True)
    event_type = Column(String(100), nullable=False)
    payload_json = Column(JSON, nullable=False)
    status = Column(String(50), default="PROCESSED", nullable=False)
    received_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class ReferencePrice(Base):
    __tablename__ = "reference_prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_key = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=False)
    hcpcs = Column(String(20), nullable=True, index=True)
    low = Column(Float, nullable=False)
    median = Column(Float, nullable=False)
    high = Column(Float, nullable=False)  # Medicare ceiling or public vendor high
    source = Column(String(255), nullable=False)
    source_url = Column(Text, nullable=False)
    effective_date = Column(DateTime(timezone=True), nullable=False)
    retrieved_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class PayeeVerification(Base):
    __tablename__ = "payee_verifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    payee_id = Column(UUID(as_uuid=True), ForeignKey("payees.id", ondelete="CASCADE"), nullable=False, index=True)
    ein = Column(String(50), nullable=True, index=True)
    npi = Column(String(50), nullable=True, index=True)
    source = Column(String(100), nullable=False)  # "PROPUBLICA_IRS_990", "CMS_NPPES_NPI"
    result = Column(JSON, nullable=False)
    checked_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    payee = relationship("Payee", backref="verifications")


