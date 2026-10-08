from flask_smorest import Blueprint

from app.adapters.http.routes import auth, events, health

BLUEPRINTS: tuple[Blueprint, ...] = (health.blueprint, auth.blueprint, events.blueprint)

__all__ = ["BLUEPRINTS"]
