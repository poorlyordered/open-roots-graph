from pydantic import BaseModel


class TimelineEvent(BaseModel):
    individual_id: str
    name: str
    surname: str | None = None
    sex: str | None = None
    event_type: str  # birth, death, marriage, residence
    year: int | None = None
    date_raw: str | None = None
    place: str | None = None
