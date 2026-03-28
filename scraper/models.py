from dataclasses import dataclass, asdict


@dataclass
class HotelData:
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
    def from_dict(cls, data: dict) -> 'HotelData':
        return cls(**data)
