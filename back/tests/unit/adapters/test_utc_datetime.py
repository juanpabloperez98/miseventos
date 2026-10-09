from datetime import UTC, datetime, timedelta, timezone

import pytest
from marshmallow import Schema, ValidationError

from app.adapters.http.schemas.common import UtcDateTime

BOGOTA = timezone(timedelta(hours=-5))


class _Schema(Schema):
    value = UtcDateTime(allow_none=True)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # 2:30 PM in Colombia.
        ("2030-10-10T14:30:00-05:00", datetime(2030, 10, 10, 19, 30, tzinfo=UTC)),
        ("2030-10-10T19:30:00Z", datetime(2030, 10, 10, 19, 30, tzinfo=UTC)),
        ("2030-10-10T19:30:00+00:00", datetime(2030, 10, 10, 19, 30, tzinfo=UTC)),
        # 11:30 PM in Colombia is already the next day in UTC.
        ("2030-10-10T23:30:00-05:00", datetime(2030, 10, 11, 4, 30, tzinfo=UTC)),
    ],
)
def test_loads_instants_with_offset_as_utc(raw: str, expected: datetime) -> None:
    loaded = _Schema().load({"value": raw})["value"]

    assert loaded == expected
    assert loaded.utcoffset() == timedelta(0)


def test_rejects_dates_without_timezone() -> None:
    with pytest.raises(ValidationError) as error:
        _Schema().load({"value": "2030-10-10T14:30:00"})

    assert "value" in error.value.messages


def test_dumps_aware_values_in_utc_whatever_their_offset() -> None:
    value = datetime(2030, 10, 10, 14, 30, tzinfo=BOGOTA)

    assert _Schema().dump({"value": value}) == {"value": "2030-10-10T19:30:00+00:00"}


def test_dumps_utc_values_unchanged() -> None:
    value = datetime(2030, 10, 11, 4, 30, tzinfo=UTC)

    assert _Schema().dump({"value": value}) == {"value": "2030-10-11T04:30:00+00:00"}


def test_dumps_null_values() -> None:
    assert _Schema().dump({"value": None}) == {"value": None}


def test_round_trip_does_not_shift_the_instant() -> None:
    schema = _Schema()
    raw = "2030-10-10T19:30:00+00:00"

    for _ in range(3):
        raw = schema.dump(schema.load({"value": raw}))["value"]

    assert raw == "2030-10-10T19:30:00+00:00"
