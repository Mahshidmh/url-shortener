from config import settings
from sqlmodel import create_engine, Session, Field, SQLModel
from datetime import datetime , UTC

engine = create_engine(settings.database_url, echo=True)

def get_session():
    with Session(engine) as session:
        yield session
class URL(SQLModel, table=True):
    id : int | None = Field(default=None, primary_key=True)
    short_code: str = Field(unique=True, max_length=10)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None
    owner_id: int | None = None
    original_url : str
    click_count : int = Field(default=0)
