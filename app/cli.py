"""Command-line tools for the person running MySpott.

They are only available on the server's command line, never from the website.
Run them like this:   flask --app run create-admin
"""

import click

from app.services import auth_service
from app.services.validation import ValidationError


def register_commands(app):
    @app.cli.command("create-admin")
    @click.option("--name", prompt="Full name")
    @click.option("--email", prompt="Email address")
    @click.password_option()
    def create_admin_command(name, email, password):
        """Create a new administrator account."""
        try:
            user = auth_service.create_admin(name, email, password)
        except ValidationError as error:
            _report(error)
            raise SystemExit(1) from None
        click.echo(f"Administrator account created for {user.email}.")

    @app.cli.command("promote-admin")
    @click.option("--email", prompt="Email address of the existing account")
    def promote_admin_command(email):
        """Make an existing account an administrator."""
        try:
            user = auth_service.promote_to_admin(email)
        except ValidationError as error:
            _report(error)
            raise SystemExit(1) from None
        click.echo(f"{user.email} is now an administrator.")


def _report(error):
    for message in error.errors.values():
        click.echo(f"Error: {message}", err=True)