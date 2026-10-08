from flask_smorest import Blueprint

from app.adapters.http.routes import auth, events, health, sessions

BLUEPRINTS: tuple[Blueprint, ...] = (
    health.blueprint,
    auth.blueprint,
    events.blueprint,
    sessions.blueprint,
)

__all__ = ["BLUEPRINTS"]
