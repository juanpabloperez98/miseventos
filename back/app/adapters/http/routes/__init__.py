from flask_smorest import Blueprint

from app.adapters.http.routes import auth, events, health, registrations, sessions, speakers

BLUEPRINTS: tuple[Blueprint, ...] = (
    health.blueprint,
    auth.blueprint,
    events.blueprint,
    sessions.blueprint,
    registrations.blueprint,
    speakers.blueprint,
)

__all__ = ["BLUEPRINTS"]
