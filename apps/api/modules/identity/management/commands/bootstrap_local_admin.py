from __future__ import annotations

import argparse
import os
import secrets
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from modules.identity.models import User


class Command(BaseCommand):
    help = "Create a local-only Django superuser and save its credentials outside Git."

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--email", default="admin@localhost")
        parser.add_argument(
            "--credentials-file",
            default=str(settings.PROJECT_ROOT / "var" / "local-admin-credentials.txt"),
        )
        parser.add_argument(
            "--reset-password",
            action="store_true",
            help="Rotate the password of the specified existing local superuser.",
        )

    @staticmethod
    def _credentials_path(value: object) -> Path:
        credentials_file = Path(str(value)).expanduser().resolve(strict=False)
        credentials_root = (settings.PROJECT_ROOT / "var").resolve()
        if not credentials_file.is_relative_to(credentials_root):
            raise CommandError("--credentials-file must stay inside the project's var directory.")
        if credentials_file.exists() and credentials_file.is_symlink():
            raise CommandError("--credentials-file cannot be a symbolic link.")
        return credentials_file

    @staticmethod
    def _write_credentials(path: Path, content: str) -> Path:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if os.name != "nt":
            os.chmod(path.parent, 0o700)
        temporary = path.with_name(f".{path.name}.{secrets.token_hex(12)}.tmp")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        flags |= getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(temporary, flags, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(content)
            if os.name != "nt":
                os.chmod(temporary, 0o600)
            return temporary
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise

    def handle(self, *args: object, **options: object) -> None:
        if not settings.DEBUG:
            raise CommandError("This command is intentionally restricted to DJANGO_DEBUG=true.")

        email = str(options["email"]).strip().lower()
        if not email:
            raise CommandError("--email cannot be empty.")
        credentials_file = self._credentials_path(options["credentials_file"])

        user = User.objects.filter(email__iexact=email).first()
        reset_password = bool(options["reset_password"])
        if user and not reset_password:
            raise CommandError(
                "The account already exists. Use --reset-password to rotate its local password."
            )
        if user and not user.is_superuser:
            raise CommandError(
                "The existing account is not a superuser and will not be elevated by this command."
            )

        password = secrets.token_urlsafe(24)
        credential_content = (
            "# Local development credentials — never commit or reuse outside localhost.\n"
            f"URL=http://localhost:8000/admin/\n"
            f"EMAIL={email}\n"
            f"PASSWORD={password}\n"
        )
        temporary = self._write_credentials(credentials_file, credential_content)
        try:
            with transaction.atomic():
                if user is None:
                    user = User.objects.create_superuser(email=email, password=password)
                    action = "created"
                else:
                    user.set_password(password)
                    user.save(update_fields=["password"])
                    action = "rotated"
                os.replace(temporary, credentials_file)
        finally:
            temporary.unlink(missing_ok=True)
        self.stdout.write(
            self.style.SUCCESS(
                f"Local superuser {action}. Credentials saved to {credentials_file}."
            )
        )
