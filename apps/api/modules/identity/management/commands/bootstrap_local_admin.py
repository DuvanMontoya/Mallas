from __future__ import annotations

import argparse
import os
import secrets
import subprocess
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from modules.curriculum.models import CurriculumRevision
from modules.identity.models import User
from modules.imports.application.services import import_curriculum_baseline


class Command(BaseCommand):
    help = "Prepare the local curriculum baseline and create a local-only Django superuser."

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
    def _run_windows_acl_script(script: str, path: Path) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["MALLAS_CREDENTIAL_PATH"] = str(path)
        # pwsh can inject its module path into this process. Windows PowerShell
        # cannot load those PowerShell 7 modules, so let powershell.exe rebuild
        # its own trusted default module path before using Get-Acl/Set-Acl.
        environment.pop("PSModulePath", None)
        return subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )

    @classmethod
    def _restrict_windows_path(cls, path: Path, *, directory: bool) -> None:
        security_type = (
            "System.Security.AccessControl.DirectorySecurity"
            if directory
            else "System.Security.AccessControl.FileSecurity"
        )
        inheritance = (
            "[System.Security.AccessControl.InheritanceFlags]::ContainerInherit -bor "
            "[System.Security.AccessControl.InheritanceFlags]::ObjectInherit"
            if directory
            else "[System.Security.AccessControl.InheritanceFlags]::None"
        )
        script = f"""
$ErrorActionPreference = 'Stop'
$sid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User
$acl = [{security_type}]::new()
$acl.SetAccessRuleProtection($true, $false)
$rule = [System.Security.AccessControl.FileSystemAccessRule]::new(
    $sid,
    [System.Security.AccessControl.FileSystemRights]::FullControl,
    {inheritance},
    [System.Security.AccessControl.PropagationFlags]::None,
    [System.Security.AccessControl.AccessControlType]::Allow
)
$acl.AddAccessRule($rule)
$item = Get-Item -LiteralPath $env:MALLAS_CREDENTIAL_PATH
$item.SetAccessControl($acl)
"""
        result = cls._run_windows_acl_script(script, path)
        if result.returncode:
            raise CommandError("Could not apply an exclusive ACL to local credentials.")

    @classmethod
    def _restrict_credentials_file(cls, path: Path) -> None:
        if os.name != "nt":
            os.chmod(path, 0o600)
            return
        cls._restrict_windows_path(path, directory=False)

    @classmethod
    def _restrict_credentials_directory(cls, path: Path) -> None:
        if os.name != "nt":
            os.chmod(path, 0o700)
            return
        cls._restrict_windows_path(path, directory=True)

    @classmethod
    def _windows_acl_is_private(cls, path: Path) -> bool:
        script = """
$ErrorActionPreference = 'Stop'
$currentSid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$file = [System.IO.FileInfo]::new($env:MALLAS_CREDENTIAL_PATH)
$acl = $file.GetAccessControl()
$rules = @($acl.Access | ForEach-Object {
    $ruleSid = $_.IdentityReference.Translate(
            [System.Security.Principal.SecurityIdentifier]
        ).Value
    $fullControl = (($_.FileSystemRights -band
        [System.Security.AccessControl.FileSystemRights]::FullControl) -eq
        [System.Security.AccessControl.FileSystemRights]::FullControl)
    "$ruleSid`t$($_.AccessControlType)`t$($_.IsInherited)`t$fullControl"
})
Write-Output $currentSid
Write-Output $acl.GetOwner([System.Security.Principal.SecurityIdentifier]).Value
Write-Output $acl.AreAccessRulesProtected
Write-Output $rules.Count
$rules | ForEach-Object { Write-Output $_ }
"""
        result = cls._run_windows_acl_script(script, path)
        if result.returncode:
            return False
        try:
            lines = result.stdout.splitlines()
            current_sid, owner_sid, protected, rule_count = lines[:4]
            rules = [line.split("\t") for line in lines[4:]]
            return bool(
                protected == "True"
                and owner_sid == current_sid
                and rule_count == "1"
                and len(rules) == 1
                and rules[0] == [current_sid, "Allow", "False", "True"]
            )
        except IndexError, ValueError:
            return False

    @classmethod
    def _credentials_file_is_private(cls, path: Path) -> bool:
        if not path.is_file() or path.is_symlink():
            return False
        if os.name == "nt":
            return cls._windows_acl_is_private(path)
        return (path.stat().st_mode & 0o777) == 0o600

    @staticmethod
    def _write_credentials(path: Path, content: str) -> Path:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        Command._restrict_credentials_directory(path.parent)
        temporary = path.with_name(f".{path.name}.{secrets.token_hex(12)}.tmp")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        flags |= getattr(os, "O_NOFOLLOW", 0)
        descriptor: int | None = None
        try:
            descriptor = os.open(temporary, flags, 0o600)
            Command._restrict_credentials_file(temporary)
            stream = os.fdopen(descriptor, "w", encoding="utf-8", newline="\n")
            descriptor = None
            with stream:
                stream.write(content)
            if not Command._credentials_file_is_private(temporary):
                raise CommandError("The local credential file ACL could not be verified.")
            return temporary
        except BaseException:
            if descriptor is not None:
                os.close(descriptor)
            temporary.unlink(missing_ok=True)
            raise

    @staticmethod
    def _ensure_local_curriculum(actor: User) -> bool:
        if CurriculumRevision.objects.filter(plan__code="2514").exists():
            return False
        import_curriculum_baseline(
            report_path=settings.PROJECT_ROOT / "var" / "bootstrap" / "curriculum-import.md",
            created_by=actor,
        )
        return True

    def handle(self, *args: object, **options: object) -> None:
        if not settings.DEBUG:
            raise CommandError("This command is intentionally restricted to DJANGO_DEBUG=true.")

        email = str(options["email"]).strip().lower()
        if not email:
            raise CommandError("--email cannot be empty.")
        credentials_file = self._credentials_path(options["credentials_file"])

        user = User.objects.filter(email__iexact=email).first()
        reset_password = bool(options["reset_password"])
        if user and not user.is_superuser:
            raise CommandError(
                "The existing account is not a superuser and will not be elevated by this command."
            )

        if user is not None and not reset_password:
            curriculum_imported = self._ensure_local_curriculum(user)
            credentials_file_is_private = self._credentials_file_is_private(credentials_file)
            if credentials_file_is_private:
                self.stdout.write(
                    self.style.SUCCESS(
                        "Local superuser is ready. A private credential file was found at "
                        f"{credentials_file}."
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        "Local superuser is ready, but a valid private credentials file was not found. "
                        "Run this command again with --reset-password to create a new local password."
                    )
                )
            if curriculum_imported:
                self.stdout.write(
                    "Verified curriculum baseline imported as a local DRAFT revision."
                )
            self.stdout.write(
                "Sign in at http://localhost:3000/login after starting the web application."
            )
            return

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
                curriculum_imported = self._ensure_local_curriculum(user)
                os.replace(temporary, credentials_file)
                if not self._credentials_file_is_private(credentials_file):
                    raise CommandError("The installed local credential file is not private.")
        finally:
            temporary.unlink(missing_ok=True)
        self.stdout.write(
            self.style.SUCCESS(
                f"Local superuser {action}. Credentials saved to {credentials_file}."
            )
        )
        self.stdout.write(
            "Sign in at http://localhost:3000/login after starting the web application."
        )
        if curriculum_imported:
            self.stdout.write("Verified curriculum baseline imported as a local DRAFT revision.")
