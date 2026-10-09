import logging

import click
from flask.cli import with_appcontext

from app.adapters.http.dependencies import get_container
from app.domain.exceptions import DomainError
from app.infrastructure.config import ConfigurationError, Environment, load_seed_settings

logger = logging.getLogger(__name__)


@click.command("seed-initial-data")
@with_appcontext
def seed_initial_data_command() -> None:
    """Create the missing seed users and demo data. Refuses to run in production."""
    container = get_container()
    if container.settings.environment is Environment.PRODUCTION:
        raise click.ClickException(
            "Refusing to seed initial data because FLASK_ENV is 'production'. No changes were made."
        )
    try:
        command = load_seed_settings().to_command()
    except ConfigurationError as error:
        raise click.ClickException(f"Invalid seed configuration: {error}") from error

    scope = container.create_request_scope()
    try:
        report = scope.seed_initial_data().execute(command)
    except DomainError as error:
        raise click.ClickException(
            f"Initial data seeding failed: {error.message}. No changes were saved."
        ) from error
    except Exception as error:
        logger.exception("seed_failed")
        raise click.ClickException(
            "Initial data seeding failed unexpectedly. No changes were saved; see the logs."
        ) from error
    finally:
        scope.close()

    click.echo(
        f"Initial data ready: users created={report.users_created} "
        f"existing={report.users_existing}; demo records created={report.records_created} "
        f"existing={report.records_existing} skipped={report.records_skipped}"
        + ("; demo data skipped" if report.demo_data_skipped else "")
    )
