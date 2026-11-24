import json
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Text
from app.database import Base

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Text, nullable=False, index=True)
    role = Column(Text, nullable=False) # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    metadata_ = Column("metadata", Text, nullable=True) # JSON string, assistant messages only
    created_at = Column(Text, nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def parsed_metadata(self):
        if self.metadata_:
            try:
                return json.loads(self.metadata_)
            except Exception:
                return None
        return None
