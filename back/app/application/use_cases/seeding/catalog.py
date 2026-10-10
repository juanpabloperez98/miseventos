"""Demo data created by the initial data seeder.

Every item has a stable ``key`` stored in ``seed_records``; changing a key makes the seeder
treat the item as new. Dates are relative to the day the item is first created, so upcoming
events stay in the future for a freshly seeded database.
"""

from dataclasses import dataclass
from datetime import timedelta

from app.domain.enums import EventStatus


@dataclass(frozen=True, slots=True)
class SpeakerSeed:
    key: str
    name: str
    email: str
    bio: str


@dataclass(frozen=True, slots=True)
class EventSeed:
    key: str
    name: str
    description: str
    location: str
    days_from_today: int
    duration: timedelta
    capacity: int
    # Statuses applied in order starting from DRAFT, so only allowed transitions are used.
    status_path: tuple[EventStatus, ...] = ()


@dataclass(frozen=True, slots=True)
class SessionSeed:
    key: str
    event_key: str
    speaker_key: str | None
    title: str
    description: str
    offset_from_event_start: timedelta
    duration: timedelta
    capacity: int


@dataclass(frozen=True, slots=True)
class SeedCatalog:
    speakers: tuple[SpeakerSeed, ...]
    events: tuple[EventSeed, ...]
    sessions: tuple[SessionSeed, ...]


EVENT_START_TIME = timedelta(hours=14)

DEFAULT_CATALOG = SeedCatalog(
    speakers=(
        SpeakerSeed(
            key="speaker:laura-gomez",
            name="Laura Gómez",
            email="laura.gomez@example.com",
            bio="Backend engineer focused on Python and distributed systems.",
        ),
        SpeakerSeed(
            key="speaker:andres-rojas",
            name="Andrés Rojas",
            email="andres.rojas@example.com",
            bio="Frontend architect specialized in Angular and design systems.",
        ),
        SpeakerSeed(
            key="speaker:camila-torres",
            name="Camila Torres",
            email="camila.torres@example.com",
            bio="Data engineer building streaming pipelines and analytics platforms.",
        ),
    ),
    events=(
        EventSeed(
            key="event:bogota-python-summit",
            name="Bogotá Python Summit",
            description="Two days of talks about Python, web backends and data.",
            location="Ágora Bogotá Convention Center, Bogotá",
            days_from_today=30,
            duration=timedelta(days=1, hours=9),
            capacity=150,
            status_path=(EventStatus.PUBLISHED,),
        ),
        EventSeed(
            key="event:angular-frontend-day",
            name="Angular Frontend Day",
            description="A full day about modern Angular applications.",
            location="Ruta N, Medellín",
            days_from_today=45,
            duration=timedelta(hours=8),
            capacity=80,
            status_path=(EventStatus.PUBLISHED,),
        ),
        EventSeed(
            key="event:cloud-devops-meetup",
            name="Cloud & DevOps Meetup",
            description="Evening meetup about containers and continuous delivery.",
            location="Universidad del Valle, Cali",
            days_from_today=60,
            duration=timedelta(hours=4),
            capacity=40,
        ),
        EventSeed(
            key="event:data-engineering-forum",
            name="Data Engineering Forum",
            description="Case studies about data platforms in Latin America.",
            location="Centro de Convenciones, Cartagena",
            days_from_today=-30,
            duration=timedelta(hours=8),
            capacity=60,
            status_path=(EventStatus.PUBLISHED, EventStatus.COMPLETED),
        ),
    ),
    sessions=(
        SessionSeed(
            key="session:bogota-python-summit:opening-keynote",
            event_key="event:bogota-python-summit",
            speaker_key="speaker:laura-gomez",
            title="Opening keynote: the state of Python",
            description="Where the language and its ecosystem are heading.",
            offset_from_event_start=timedelta(0),
            duration=timedelta(hours=1),
            capacity=150,
        ),
        SessionSeed(
            key="session:bogota-python-summit:hexagonal-architecture",
            event_key="event:bogota-python-summit",
            speaker_key="speaker:laura-gomez",
            title="Hexagonal architecture with Flask",
            description="Keeping business rules independent from frameworks.",
            offset_from_event_start=timedelta(hours=2),
            duration=timedelta(hours=1, minutes=30),
            capacity=60,
        ),
        SessionSeed(
            key="session:bogota-python-summit:data-pipelines",
            event_key="event:bogota-python-summit",
            speaker_key="speaker:camila-torres",
            title="Building data pipelines with Python",
            description="From batch jobs to streaming with open source tools.",
            offset_from_event_start=timedelta(days=1),
            duration=timedelta(hours=2),
            capacity=60,
        ),
        SessionSeed(
            key="session:angular-frontend-day:signals",
            event_key="event:angular-frontend-day",
            speaker_key="speaker:andres-rojas",
            title="Reactive state with Angular signals",
            description="Managing application state without boilerplate.",
            offset_from_event_start=timedelta(hours=1),
            duration=timedelta(hours=1, minutes=30),
            capacity=80,
        ),
        SessionSeed(
            key="session:angular-frontend-day:testing",
            event_key="event:angular-frontend-day",
            speaker_key="speaker:andres-rojas",
            title="Testing Angular applications",
            description="Unit and end-to-end testing strategies.",
            offset_from_event_start=timedelta(hours=4),
            duration=timedelta(hours=1),
            capacity=40,
        ),
        SessionSeed(
            key="session:cloud-devops-meetup:containers",
            event_key="event:cloud-devops-meetup",
            speaker_key="speaker:laura-gomez",
            title="Containers in production with Docker",
            description="Images, health checks and zero-downtime deployments.",
            offset_from_event_start=timedelta(minutes=30),
            duration=timedelta(hours=1),
            capacity=40,
        ),
        SessionSeed(
            key="session:data-engineering-forum:streaming",
            event_key="event:data-engineering-forum",
            speaker_key="speaker:camila-torres",
            title="Streaming data at scale",
            description="Lessons learned running real-time pipelines.",
            offset_from_event_start=timedelta(hours=1),
            duration=timedelta(hours=2),
            capacity=60,
        ),
    ),
)
