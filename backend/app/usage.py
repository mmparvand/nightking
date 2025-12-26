from __future__ import annotations

from sqlalchemy.orm import Session

from .models import Service
from .crud import update_usage


class TrafficCollector:
    """
    Stub interface for traffic accounting. A future node agent can call `record_usage`
    with byte deltas collected from gateways. This implementation simply persists to the DB.
    """

    def __init__(self, db: Session):
        self.db = db

    def record_usage(self, service: Service, *, bytes_used: int) -> Service:
        service.traffic_used_bytes = (service.traffic_used_bytes or 0) + max(bytes_used, 0)
        return update_usage(self.db, service, traffic_used_bytes=service.traffic_used_bytes)

    def reset_usage(self, service: Service) -> Service:
        return update_usage(self.db, service, traffic_used_bytes=0)
