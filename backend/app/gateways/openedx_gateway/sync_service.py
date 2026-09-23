"""Open edX MongoDB -> PostgreSQL sync (RF-22).

Pulls courses, modules and enrollments from Open edX's MongoDB and upserts them
into our unified PostgreSQL store. Every upsert reconciles on a natural key from
the source system, so the sync is idempotent and safe to re-run:

    courses     -> subjects.external_id  == course_id
    modules     -> modules.external_id   == module_id
    enrollments -> students.email        == email (already unique)

If Open edX is unreachable the sync logs and returns; it never crashes the app.
"""
import logging

from sqlalchemy import select

from app.db import database
from app.gateways.openedx_gateway.mongo_client import (
    OpenEdxMongoClient,
    OpenEdxMongoUnavailableError,
)
from app.gateways.openedx_gateway.mysql_client import OpenEdxMySQLClient
from app.gateways.openedx_gateway.schemas import (
    OpenEdxCourse,
    OpenEdxEnrollment,
    OpenEdxEnrollmentFromMySQL,
    OpenEdxModule,
)
from app.models.module import Module, Subject
from app.models.student import Student

logger = logging.getLogger(__name__)

# Validated against Tutor 21.0.8 (Open edX Teak) with an imported test course:
# - Courses and structures live in MongoDB (modulestore.*).
# - Enrollments live in MySQL (student_courseenrollment), NOT MongoDB.
# - modulestore.definitions holds per-block content (used by Fase 5 / RAG),
#   not consumed here yet.
COURSES_COLLECTION = "modulestore.active_versions"
MODULES_COLLECTION = "modulestore.structures"
DEFINITIONS_COLLECTION = "modulestore.definitions"  # TODO(fase-5): consume for RAG ingestion


class OpenEdxSyncService:
    def __init__(
        self,
        client: OpenEdxMongoClient | None = None,
        mysql_client: OpenEdxMySQLClient | None = None,
    ):
        self.client = client or OpenEdxMongoClient()
        self.mysql_client = mysql_client or OpenEdxMySQLClient()

    # -- parsing (defensive: skip documents we cannot identify) --------------

    @staticmethod
    def _parse_course(doc: dict) -> OpenEdxCourse | None:
        # active_versions documents carry org/course/run separately, not a
        # combined course_id; reconstruct the opaque key from them.
        org = str(doc.get("org") or "").strip()
        course = str(doc.get("course") or "").strip()
        run = str(doc.get("run") or "").strip()
        if not (org and course and run):
            logger.warning(
                "Skipping course document without org/course/run: %r", doc
            )
            return None
        course_id = f"course-v1:{org}+{course}+{run}"
        return OpenEdxCourse(
            course_id=course_id,
            # TODO(fase-3b): enrich display_name from the structures document
            # (blocks[block_type == "course"].fields.display_name); the opaque
            # key is a placeholder until then.
            display_name=course_id,
            description=None,
        )

    @staticmethod
    def _parse_module(doc: dict) -> OpenEdxModule | None:
        # A modulestore.structures document is a whole course tree (blocks[]),
        # not one module per document, so a single-row parser cannot express the
        # reshape. Returns None until module sync is reimplemented (see the
        # TODO(fase-3b) above sync_modules).
        return None

    @staticmethod
    def _parse_enrollment(doc: dict) -> OpenEdxEnrollment | None:
        email = str(doc.get("email") or "").strip()
        if not email:
            logger.warning("Skipping enrollment document without an email: %r", doc)
            return None
        return OpenEdxEnrollment(
            user_id=str(doc.get("user_id") or doc.get("_id") or email),
            email=email,
            name=doc.get("name"),
            course_id=doc.get("course_id"),
        )

    # -- sync steps ----------------------------------------------------------

    async def sync_courses(self, dry_run: bool = False) -> int:
        docs = await self.client.fetch(COURSES_COLLECTION)
        courses = [c for c in (self._parse_course(d) for d in docs) if c]
        if dry_run:
            logger.info("[dry-run] would upsert %d course(s) into subjects", len(courses))
            return len(courses)

        async with database.async_session() as session:
            async with session.begin():
                for course in courses:
                    existing = (
                        await session.execute(
                            select(Subject).where(
                                Subject.external_id == course.course_id
                            )
                        )
                    ).scalar_one_or_none()
                    if existing is None:
                        session.add(
                            Subject(
                                external_id=course.course_id,
                                name=course.display_name,
                                description=course.description,
                            )
                        )
                    else:
                        existing.name = course.display_name
                        existing.description = course.description
        logger.info("Synced %d course(s) from Open edX", len(courses))
        return len(courses)

    # TODO(fase-3b): reimplement module-level sync against the real structures
    # schema. Each modulestore.structures document is a whole course tree: walk
    # blocks[], resolve children recursively, and filter by block_type to emit
    # one row per module. A single-row _parse_module cannot express this, so it
    # returns None and this method returns 0 until the follow-up lands — the
    # scheduler and admin endpoint keep working, they just get 0 modules.
    async def sync_modules(self, dry_run: bool = False) -> int:
        logger.warning("module-level sync not yet reimplemented against real schema")
        return 0

    # TODO(fase-3b): reconcile Student by an external_user_id column instead of
    # email. Requires an Alembic migration to add students.external_user_id (unique)
    # and backfill from Open edX's auth_user.id. Deferred to keep Fase 3 changes
    # schema-preserving.
    async def sync_enrollments(self, dry_run: bool = False) -> int:
        # The email filters exclude the system users Tutor creates before the
        # first real user (admin is user_id=4): the automated *@openedx and
        # *@fake.email accounts and the edx@example.com superuser.
        query = (
            "SELECT sce.id AS enrollment_id, sce.user_id, sce.course_id, "
            "sce.is_active, sce.mode, au.email, au.username "
            "FROM student_courseenrollment sce "
            "JOIN auth_user au ON au.id = sce.user_id "
            "WHERE sce.is_active = 1 "
            "AND au.email NOT LIKE %s "
            "AND au.email NOT LIKE %s "
            "AND au.email != %s"
        )
        params = ("%@openedx", "%@fake.email", "edx@example.com")
        rows = await self.mysql_client.fetch_all(query, params)

        enrollments: list[OpenEdxEnrollmentFromMySQL] = []
        for row in rows:
            try:
                enrollments.append(OpenEdxEnrollmentFromMySQL(**row))
            except Exception as exc:  # noqa: BLE001 — skip a malformed row, keep the rest
                logger.warning("Skipping malformed enrollment row %r: %s", row, exc)

        if dry_run:
            logger.info(
                "[dry-run] would upsert %d enrollment(s) into students",
                len(enrollments),
            )
            return len(enrollments)

        async with database.async_session() as session:
            async with session.begin():
                for enrollment in enrollments:
                    existing = (
                        await session.execute(
                            select(Student).where(Student.email == enrollment.email)
                        )
                    ).scalar_one_or_none()
                    if existing is None:
                        session.add(
                            Student(
                                name=enrollment.username or enrollment.email,
                                email=enrollment.email,
                            )
                        )
                    elif enrollment.username:
                        existing.name = enrollment.username
        logger.info(
            "Synced %d enrollment(s) from Open edX MySQL", len(enrollments)
        )
        return len(enrollments)

    async def sync_all(self, dry_run: bool = False) -> dict:
        """Run all sync steps in order. Never raises: an unreachable Open edX or
        a failing step is reported in the result, not thrown at the caller."""
        results: dict = {"courses": 0, "modules": 0, "enrollments": 0, "errors": []}

        # Only Mongo reachability is checked up-front (courses/modules come from
        # Mongo). MySQL reachability is validated inside sync_enrollments itself,
        # so a MySQL outage does not block course sync.
        try:
            await self.client.ping()
        except OpenEdxMongoUnavailableError as exc:
            logger.warning("Open edX sync skipped: %s", exc)
            results["errors"].append(str(exc))
            return results

        for name, step in (
            ("courses", self.sync_courses),
            ("modules", self.sync_modules),
            ("enrollments", self.sync_enrollments),
        ):
            try:
                results[name] = await step(dry_run=dry_run)
            except Exception as exc:  # noqa: BLE001 — one bad step must not stop the rest
                logger.exception("Open edX %s sync failed", name)
                results["errors"].append(f"{name}: {exc}")

        return results


# Module-level singleton used by the scheduler and the admin endpoint.
sync_service = OpenEdxSyncService()
