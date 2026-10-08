from http import HTTPStatus

from flask_smorest import Blueprint

from app.adapters.http.schemas.health import HealthSchema

blueprint = Blueprint("health", __name__, description="Service health")


@blueprint.route("/health")
@blueprint.response(HTTPStatus.OK, HealthSchema)
def health() -> dict[str, str]:
    return {"status": "ok"}
