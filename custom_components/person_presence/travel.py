"""Travel context derived exclusively from accepted GPS measurements."""

from dataclasses import dataclass
from math import asin, atan2, cos, degrees, isfinite, radians, sin, sqrt

from .engine import fresh


def distance_m(lat1, lon1, lat2, lon2):
    a = (
        sin(radians(lat2 - lat1) / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(radians(lon2 - lon1) / 2) ** 2
    )
    return 6371000 * 2 * asin(sqrt(min(1, max(0, a))))


@dataclass(frozen=True)
class TravelResult:
    distance_m: float | None = None
    direction: str = "unknown"
    bearing: str | None = None
    observed_at: float | None = None


class TravelContext:
    def __init__(self):
        self.baseline = None
        self.result = TravelResult()

    def update(self, result, now, gps_age, home):
        lat, lon = result.latitude, result.longitude
        valid = (
            not result.pending
            and result.selected is not None
            and home is not None
            and lat is not None
            and lon is not None
            and isfinite(lat)
            and isfinite(lon)
            and -90 <= lat <= 90
            and -180 <= lon <= 180
            and fresh(result.gps_observed_at, now, gps_age)
        )
        if not valid:
            self.baseline = None
            self.result = TravelResult()
            return self.result
        home_key = (home.latitude, home.longitude)
        identity = (result.selected, result.gps_source_entity_id, home_key)
        fix = (identity, result.gps_observed_at, lat, lon, result.accuracy)
        if self.baseline == fix:
            return self.result
        metres = distance_m(home.latitude, home.longitude, lat, lon)
        direction = "unknown"
        old = self.baseline
        if old and old[0] == identity and fix[1] <= old[1]:
            self.baseline = None
            self.result = TravelResult()
            return self.result
        if old and old[0] == identity and 0 < fix[1] - old[1] <= gps_age:
            delta = metres - distance_m(home.latitude, home.longitude, old[2], old[3])
            threshold = max(50, (old[4] or 0) + (result.accuracy or 0))
            direction = (
                "stationary"
                if abs(delta) < threshold
                else "towards_home"
                if delta < 0
                else "away_from_home"
            )
        lat1, lat2, dl = (
            radians(home.latitude),
            radians(lat),
            radians(lon - home.longitude),
        )
        bearing = (
            degrees(
                atan2(
                    sin(dl) * cos(lat2),
                    cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(dl),
                )
            )
            + 360
        ) % 360
        compass = (
            ("N", "NE", "E", "SE", "S", "SW", "W", "NW")[
                int((bearing + 22.5) // 45) % 8
            ]
            if metres > 0
            else None
        )
        self.baseline = fix
        self.result = TravelResult(
            round(metres, 1), direction, compass, result.gps_observed_at
        )
        return self.result
