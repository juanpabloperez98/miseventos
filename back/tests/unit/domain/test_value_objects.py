from datetime import UTC, datetime, timedelta

import pytest

from app.domain.exceptions import InvalidValueError
from app.domain.value_objects import MAX_PER_PAGE, Email, Page, PageRequest, TimeRange

START = datetime(2030, 1, 1, 10, 0, tzinfo=UTC)


class TestEmail:
    def test_normalizes_case_and_whitespace(self) -> None:
        assert Email("  Ada@Example.COM ").value == "ada@example.com"

    @pytest.mark.parametrize(
        "value", ["", "ada", "ada@", "@example.com", "ada@example", "a b@x.io"]
    )
    def test_rejects_invalid_addresses(self, value: str) -> None:
        with pytest.raises(InvalidValueError):
            Email(value)


class TestTimeRange:
    def test_rejects_end_before_or_equal_to_start(self) -> None:
        with pytest.raises(InvalidValueError, match="Start must be before end"):
            TimeRange(START, START)

    def test_rejects_naive_datetimes(self) -> None:
        with pytest.raises(InvalidValueError, match="timezone"):
            TimeRange(datetime(2030, 1, 1, 10), datetime(2030, 1, 1, 11))

    def test_contains_inner_range_including_boundaries(self) -> None:
        outer = TimeRange(START, START + timedelta(hours=8))

        assert outer.contains(TimeRange(START, START + timedelta(hours=8)))
        assert outer.contains(TimeRange(START + timedelta(hours=1), START + timedelta(hours=2)))
        assert not outer.contains(
            TimeRange(START - timedelta(minutes=1), START + timedelta(hours=1))
        )
        assert not outer.contains(TimeRange(START + timedelta(hours=7), START + timedelta(hours=9)))


class TestPagination:
    def test_offset_is_derived_from_page_and_size(self) -> None:
        assert PageRequest(page=3, per_page=20).offset == 40

    @pytest.mark.parametrize(
        ("page", "per_page"), [(0, 10), (1, 0), (1, MAX_PER_PAGE + 1), (-1, 10)]
    )
    def test_rejects_out_of_range_values(self, page: int, per_page: int) -> None:
        with pytest.raises(InvalidValueError):
            PageRequest(page=page, per_page=per_page)

    @pytest.mark.parametrize(("total", "expected_pages"), [(0, 0), (10, 1), (11, 2), (25, 3)])
    def test_page_count_rounds_up(self, total: int, expected_pages: int) -> None:
        page = Page(items=[], total=total, request=PageRequest(page=1, per_page=10))

        assert page.pages == expected_pages
        assert (page.page, page.per_page) == (1, 10)
