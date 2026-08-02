"""Static regression guards for the production deployment configuration.

These read backend/Dockerfile, backend/.dockerignore, and
docker-compose.prod.yml as plain text and assert on their content - no
Docker daemon required, so they run in the normal `pytest` gate and catch:

- a future edit that silently drops Alembic from the production image (the
  class of bug that caused "FAILED: No 'script_location' key found in
  configuration." in the migrate service);
- a future edit that drops the storage-init service or its ownership/
  permission fix (the class of bug that caused "PermissionError: [Errno 13]
  Permission denied" writing to /app/storage/uploads/... - a freshly
  created Compose named volume starts out root-owned, and the backend
  container runs as non-root UID 10001, so something has to chown it once).

Both fail loudly in this test suite well before anyone has to notice them
from a failed/crash-looping container.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = REPO_ROOT / "backend" / "Dockerfile"
DOCKERIGNORE = REPO_ROOT / "backend" / ".dockerignore"
COMPOSE_PROD = REPO_ROOT / "docker-compose.prod.yml"


def _lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


# docker-compose.prod.yml's top-level `services:` keys, in file order. Used
# to slice out one service's block as plain text without a full YAML parser
# (PyYAML is only a transitive test-env dependency, not a declared one -
# see pyproject.toml - so these tests deliberately avoid relying on it).
_COMPOSE_SERVICE_ORDER = (
    "postgres",
    "chromadb",
    "migrate",
    "storage-init",
    "backend",
    "frontend",
    "reverse-proxy",
)


def _compose_service_section(contents: str, service_name: str) -> str:
    start_marker = f"\n  {service_name}:"
    start = contents.index(start_marker)
    remaining = _COMPOSE_SERVICE_ORDER[_COMPOSE_SERVICE_ORDER.index(service_name) + 1 :]
    end = len(contents)
    for later_service in remaining:
        marker = f"\n  {later_service}:"
        if marker in contents[start:]:
            end = start + contents[start:].index(marker)
            break
    else:
        # Last service in the file: ends at the top-level `volumes:` block.
        if "\nvolumes:" in contents[start:]:
            end = start + contents[start:].index("\nvolumes:")
    return contents[start:end]


def test_dockerfile_copies_alembic_config_and_migrations_before_the_production_stage() -> None:
    lines = _lines(DOCKERFILE)

    def index_of(predicate: Callable[[str], bool], label: str) -> int:
        for i, line in enumerate(lines):
            if predicate(line):
                return i
        raise AssertionError(f"backend/Dockerfile has no line matching: {label}")

    copy_ini_index = index_of(
        lambda line: line.strip().startswith("COPY") and "alembic.ini" in line,
        "COPY alembic.ini ...",
    )
    copy_dir_index = index_of(
        lambda line: (
            line.strip().startswith("COPY") and "alembic" in line and "alembic.ini" not in line
        ),
        "COPY alembic ./alembic (the migrations directory, not alembic.ini)",
    )
    production_stage_index = index_of(
        lambda line: line.strip().startswith("FROM") and "AS production" in line,
        "FROM base AS production",
    )
    pip_install_index = index_of(
        lambda line: "pip install" in line and "-e ." in line,
        "RUN pip install --no-cache-dir -e .",
    )

    # Both COPY instructions must precede the production stage (i.e. live in
    # the shared base stage, not be dev-only) so the production image
    # actually contains them - not just the dev target, which would mask
    # this in local testing (dev's docker-compose.yml bind-mounts over
    # everything, hiding a base-stage gap that only breaks the built,
    # unmounted production image).
    assert copy_ini_index < production_stage_index, (
        "COPY alembic.ini must be in the shared base stage, before `FROM base AS production`."
    )
    assert copy_dir_index < production_stage_index, (
        "COPY alembic ./alembic must be in the shared base stage, before `FROM base AS production`."
    )
    # And before the package install, matching this Dockerfile's existing
    # ordering convention (source copied in, then installed).
    assert copy_ini_index < pip_install_index
    assert copy_dir_index < pip_install_index


def test_dockerfile_has_a_build_time_alembic_presence_check() -> None:
    """A `RUN test -f alembic.ini ...` guard that fails `docker build`
    immediately if a future edit ever drops these files again, rather than
    only surfacing as a runtime failure in the migrate container."""
    contents = DOCKERFILE.read_text(encoding="utf-8")
    assert "alembic.ini" in contents and "alembic/env.py" in contents
    assert "RUN test -f alembic.ini" in contents


def test_dockerignore_does_not_exclude_alembic_files() -> None:
    excluded_patterns = {
        line.strip()
        for line in _lines(DOCKERIGNORE)
        if line.strip() and not line.strip().startswith("#")
    }
    blocking_patterns = {
        pattern
        for pattern in excluded_patterns
        if not pattern.startswith("!") and "alembic" in pattern.casefold()
    }
    assert not blocking_patterns, (
        f"backend/.dockerignore excludes alembic-related paths, which would break "
        f"`alembic upgrade head` in the built image: {blocking_patterns}"
    )


def test_compose_prod_migrate_service_runs_alembic_upgrade_head_in_backend_workdir() -> None:
    contents = COMPOSE_PROD.read_text(encoding="utf-8")
    migrate_section = contents.split("\n  migrate:", 1)[1].split("\n  backend:", 1)[0]

    assert "working_dir: /app/backend" in migrate_section
    assert 'command: ["alembic", "upgrade", "head"]' in migrate_section
    # Must build the same production target as the backend service, not a
    # separate image that could drift out of sync with it.
    assert "target: production" in migrate_section


def test_compose_prod_has_a_storage_init_service_using_the_backend_image() -> None:
    contents = COMPOSE_PROD.read_text(encoding="utf-8")
    assert "\n  storage-init:" in contents
    section = _compose_service_section(contents, "storage-init")
    assert "target: production" in section
    assert "image: exam-quality-backend:prod" in section


def test_storage_init_runs_as_root_only_for_this_one_service() -> None:
    contents = COMPOSE_PROD.read_text(encoding="utf-8")
    storage_init_section = _compose_service_section(contents, "storage-init")
    backend_section = _compose_service_section(contents, "backend")
    migrate_section = _compose_service_section(contents, "migrate")

    assert 'user: "0:0"' in storage_init_section
    # The root override is scoped to storage-init alone - backend and
    # migrate must still run as the image's own non-root USER (see
    # backend/Dockerfile's production stage), not inherit/duplicate a root
    # override.
    assert "user:" not in backend_section
    assert "user:" not in migrate_section


def test_storage_init_mounts_the_same_upload_and_report_volumes_as_backend() -> None:
    contents = COMPOSE_PROD.read_text(encoding="utf-8")
    storage_init_section = _compose_service_section(contents, "storage-init")
    backend_section = _compose_service_section(contents, "backend")

    for mount in (
        "backend_uploads:/app/storage/uploads",
        "backend_reports:/app/storage/reports",
    ):
        assert mount in storage_init_section, f"storage-init is missing volume mount: {mount}"
        assert mount in backend_section, f"backend is missing volume mount: {mount}"


def test_storage_init_chowns_to_the_backend_uid_and_never_uses_chmod_777() -> None:
    contents = COMPOSE_PROD.read_text(encoding="utf-8")
    storage_init_section = _compose_service_section(contents, "storage-init")

    assert "chown -R 10001:10001" in storage_init_section
    assert "/app/storage/uploads" in storage_init_section
    assert "/app/storage/reports" in storage_init_section
    # A secure, non-world-writable mode - not 777. Checked against the
    # actual command string only (not the whole YAML block, which is free
    # to *mention* "0777" in an explanatory comment contrasting the two).
    command_line = next(
        line
        for line in storage_init_section.splitlines()
        if "chown -R" in line and not line.strip().startswith("#")
    )
    assert "0750" in command_line
    assert "777" not in command_line
    # Never the application server.
    assert "uvicorn" not in storage_init_section


def test_storage_init_never_prints_environment_values() -> None:
    """storage-init's command is pure filesystem plumbing (mkdir/chown/
    chmod) - it must not be given an `environment:` block (nothing to leak)
    or contain any command that echoes environment/secret values."""
    contents = COMPOSE_PROD.read_text(encoding="utf-8")
    storage_init_section = _compose_service_section(contents, "storage-init")

    assert "environment:" not in storage_init_section
    for leaky_command in ("env", "printenv", "echo $", 'echo "$'):
        assert leaky_command not in storage_init_section


def test_backend_depends_on_storage_init_completing_successfully() -> None:
    contents = COMPOSE_PROD.read_text(encoding="utf-8")
    backend_section = _compose_service_section(contents, "backend")
    depends_on_section = backend_section.split("depends_on:", 1)[1]

    storage_init_dependency = depends_on_section.split("storage-init:", 1)[1][:80]
    assert "condition: service_completed_successfully" in storage_init_dependency
    migrate_dependency = depends_on_section.split("migrate:", 1)[1][:80]
    assert "condition: service_completed_successfully" in migrate_dependency


def test_backend_production_image_still_runs_as_non_root() -> None:
    """docker-compose.prod.yml's backend service has no `user:` override
    (checked above), so it runs as whatever backend/Dockerfile's production
    stage sets - confirm that is still the non-root UID, not root."""
    dockerfile_contents = DOCKERFILE.read_text(encoding="utf-8")
    production_section = dockerfile_contents.split("FROM base AS production", 1)[1]
    assert "USER 10001:10001" in production_section
