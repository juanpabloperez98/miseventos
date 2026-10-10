from flask_smorest import Blueprint

from app.adapters.http.routes import (
    auth,
    event_images,
    events,
    health,
    registrations,
    sessions,
    speakers,
)

BLUEPRINTS: tuple[Blueprint, ...] = (
    health.blueprint,
    auth.blueprint,
    events.blueprint,
    event_images.blueprint,
    sessions.blueprint,
    registrations.blueprint,
    speakers.blueprint,
)

__all__ = ["BLUEPRINTS"]
