from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.network import IngestionStatus, SourceType


class IngestionJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    traffic_source_id: UUID
    original_filename: str
    status: IngestionStatus
    total_rows: int
    accepted_rows: int
    skipped_rows: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class LiveFlow(BaseModel):
    """One normalized connection event emitted by a permitted local sensor."""

    timestamp: datetime
    src_ip: str
    dst_ip: str
    protocol: str
    packets: int
    bytes: int
    src_port: int | None = None
    dst_port: int | None = None
    duration_ms: int | None = None
    flags: str | None = None
    failed_conn_info: str | None = None


class LiveFlowBatch(BaseModel):
    source_name: str = "zeek-live"
    flows: list[LiveFlow]


class TrafficSourceResponse(BaseModel):
    """A selectable traffic source for the analyst dashboard."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    source_type: SourceType
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
