import pytest

from app.application.dto import Actor
from app.application.services import AuthorizationService, EventAccessPolicy
from app.domain.enums import EventStatus, UserRole
from app.domain.exceptions import AuthorizationError
from app.domain.ports import EventVisibility
from tests.factories import build_event

OWNER_ID = 10
ADMIN = Actor(user_id=1, role=UserRole.ADMIN)
OWNER = Actor(user_id=OWNER_ID, role=UserRole.ORGANIZER)
OTHER_ORGANIZER = Actor(user_id=20, role=UserRole.ORGANIZER)
ATTENDEE = Actor(user_id=OWNER_ID, role=UserRole.ATTENDEE)


@pytest.fixture
def policy() -> EventAccessPolicy:
    return EventAccessPolicy(AuthorizationService())


@pytest.mark.parametrize(
    ("actor", "allowed"),
    [(ADMIN, True), (OWNER, True), (OTHER_ORGANIZER, False), (ATTENDEE, False)],
)
def test_management_requires_ownership_unless_admin(
    policy: EventAccessPolicy, actor: Actor, allowed: bool
) -> None:
    event = build_event(created_by=OWNER_ID)

    assert policy.can_manage(actor, event) is allowed


def test_ensure_can_manage_raises_for_foreign_event(policy: EventAccessPolicy) -> None:
    with pytest.raises(AuthorizationError, match="own events"):
        policy.ensure_can_manage(OTHER_ORGANIZER, build_event(created_by=OWNER_ID))


@pytest.mark.parametrize(("actor", "allowed"), [(ADMIN, True), (OWNER, True), (ATTENDEE, False)])
def test_creating_events_requires_manage_permission(
    policy: EventAccessPolicy, actor: Actor, allowed: bool
) -> None:
    if allowed:
        policy.ensure_can_manage_events(actor)
    else:
        with pytest.raises(AuthorizationError):
            policy.ensure_can_manage_events(actor)


@pytest.mark.parametrize(
    ("actor", "visible"),
    [(None, False), (ATTENDEE, False), (OTHER_ORGANIZER, False), (OWNER, True), (ADMIN, True)],
)
def test_unpublished_events_are_only_visible_to_managers(
    policy: EventAccessPolicy, actor: Actor | None, visible: bool
) -> None:
    draft = build_event(created_by=OWNER_ID, status=EventStatus.DRAFT)

    assert policy.can_view(actor, draft) is visible
    assert policy.can_view(actor, build_event(status=EventStatus.PUBLISHED))


@pytest.mark.parametrize(
    ("actor", "expected"),
    [
        (None, EventVisibility.public()),
        (ATTENDEE, EventVisibility.public()),
        (OWNER, EventVisibility.public_or_owned_by(OWNER_ID)),
        (ADMIN, EventVisibility.unrestricted()),
    ],
)
def test_listing_visibility_depends_on_role(
    policy: EventAccessPolicy, actor: Actor | None, expected: EventVisibility
) -> None:
    assert policy.visibility_for(actor) == expected
