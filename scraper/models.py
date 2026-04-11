from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any


TRACKED_FIELDS = (
    'name', 'stars', 'rating', 'number_of_reviews',
    'district', 'city', 'new_mark', 'link', 'foto',
)


@dataclass
class HotelDataParsed:
    """Flat snapshot of a hotel as scraped from the page right now."""
    id: str
    name: str | None
    stars: int
    rating: float
    number_of_reviews: int
    district: str | None
    city: str | None
    new_mark: bool
    date_parsed: str
    link: str
    foto: str | None

    def to_dict(self) -> dict:
        return asdict(self)

    def to_list(self) -> list:
        return list(asdict(self).values())

    @classmethod
    def from_dict(cls, data: dict) -> 'HotelDataParsed':
        return cls(**data)


@dataclass
class HotelRecord:
    """Stored hotel record with full change history for each field.

    id and date_parsed are immutable identifiers.
    All other fields are {date_str: value} dicts tracking every observed value.
    """
    id: str
    date_parsed: str  # first-seen date — never changes
    name: dict[str, Any] = field(default_factory=dict)
    stars: dict[str, Any] = field(default_factory=dict)
    rating: dict[str, Any] = field(default_factory=dict)
    number_of_reviews: dict[str, Any] = field(default_factory=dict)
    district: dict[str, Any] = field(default_factory=dict)
    city: dict[str, Any] = field(default_factory=dict)
    new_mark: dict[str, Any] = field(default_factory=dict)
    link: dict[str, Any] = field(default_factory=dict)
    foto: dict[str, Any] = field(default_factory=dict)

    def latest(self, field_name: str) -> Any:
        """Return the most recent value for a tracked field."""
        history: dict = getattr(self, field_name, {})
        if not history:
            return None
        last_date = max(
            history.keys(),
            key=lambda d: datetime.strptime(d, "%d.%m.%Y"),
        )
        return history[last_date]

    def to_dict(self) -> dict:
        return asdict(self)

    def to_sheets_row(self) -> list:
        """Return flat list of latest values for Google Sheets (same column order as before)."""
        return [
            self.id,
            self.latest('name'),
            self.latest('stars'),
            self.latest('rating'),
            self.latest('number_of_reviews'),
            self.latest('district'),
            self.latest('city'),
            self.latest('new_mark'),
            self.date_parsed,
            self.latest('link'),
            self.latest('foto'),
        ]

    @classmethod
    def from_dict(cls, data: dict) -> 'HotelRecord':
        return cls(**data)

    @classmethod
    def from_parsed(cls, parsed: HotelDataParsed) -> 'HotelRecord':
        """Create a brand-new HotelRecord from a freshly parsed snapshot."""
        date = parsed.date_parsed
        return cls(
            id=parsed.id,
            date_parsed=date,
            name={date: parsed.name},
            stars={date: parsed.stars},
            rating={date: parsed.rating},
            number_of_reviews={date: parsed.number_of_reviews},
            district={date: parsed.district},
            city={date: parsed.city},
            new_mark={date: parsed.new_mark},
            link={date: parsed.link},
            foto={date: parsed.foto},
        )
