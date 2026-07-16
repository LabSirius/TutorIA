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
from app.gateways.openedx_gateway.schemas import (
    OpenEdxCourse,
    OpenEdxEnrollment,
    OpenEdxModule,
)
from app.models.module import Module, Subject
from app.models.student import Student

logger = logging.getLogger(__name__)

# TODO: confirm these collection names against the real Open edX instance before
# the pilot. Open edX's split modulestore keeps course content in MongoDB; some
# deployments keep enrollments in MySQL instead, in which case sync_enrollments
# will need a different source.
COURSES_COLLECTION = "modulestore.active_versions"
MODULES_COLLECTION = "modulestore.structures"
ENROLLMENTS_COLLECTION = "student_courseenrollment"


class OpenEdxSyncService:
    def __init__(self, client: OpenEdxMongoClient | None = None):
        self.client = client or OpenEdxMongoClient()

    # -- parsing (defensive: skip documents we cannot identify) --------------

    @staticmethod
    def _parse_course(doc: dict) -> OpenEdxCourse | None:
        course_id = str(doc.get("course_id") or doc.get("_id") or "").strip()
        if not course_id:
            logger.warning("Skipping course document without a course_id: %r", doc)
            return None
        return OpenEdxCourse(
            course_id=course_id,
            display_name=str(doc.get("display_name") or doc.get("name") or course_id),
            description=doc.get("description"),
        )

    @staticmethod
    def _parse_module(doc: dict) -> OpenEdxModule | None:
        module_id = str(doc.get("module_id") or doc.get("_id") or "").strip()
        course_id = str(doc.get("course_id") or "").strip()
        if not module_id or not course_id:
            logger.warning(
                "Skipping module document without module_id/course_id: %r", doc
            )
            return None
        return OpenEdxModule(
            module_id=module_id,
            course_id=course_id,
            display_name=str(doc.get("display_name") or doc.get("name") or module_id),
            order=int(doc.get("order") or 0),
            description=doc.get("description"),
            content_text=doc.get("content_text"),
        )

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

    async def sync_modules(self, dry_run: bool = False) -> int:
        docs = await self.client.fetch(MODULES_COLLECTION)
        modules = [m for m in (self._parse_module(d) for d in docs) if m]
        if dry_run:
            logger.info("[dry-run] would upsert %d module(s) into modules", len(modules))
            return len(modules)

        synced = 0
        async with database.async_session() as session:
            async with session.begin():
                for module in modules:
                    subject = (
                        await session.execute(
                            select(Subject).where(
                                Subject.external_id == module.course_id
                            )
                        )
                    ).scalar_one_or_none()
                    if subject is None:
                        logger.warning(
                            "Skipping module %s: course %s has not been synced yet",
                            module.module_id, module.course_id,
                        )
                        continue
                    existing = (
                        await session.execute(
                            select(Module).where(
                                Module.external_id == module.module_id
                            )
                        )
                    ).scalar_one_or_none()
                    if existing is None:
                        session.add(
                            Module(
                                external_id=module.module_id,
                                subject_id=subject.id,
                                name=module.display_name,
                                order=module.order,
                                description=module.description,
                                content_text=module.content_text,
                            )
                        )
                    else:
                        existing.subject_id = subject.id
                        existing.name = module.display_name
                        existing.order = module.order
                        existing.description = module.description
                        if module.content_text is not None:
                            existing.content_text = module.content_text
                    synced += 1
        logger.info("Synced %d module(s) from Open edX", synced)
        return synced

    async def sync_enrollments(self, dry_run: bool = False) -> int:
        docs = await self.client.fetch(ENROLLMENTS_COLLECTION)
        enrollments = [e for e in (self._parse_enrollment(d) for d in docs) if e]
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
                                name=enrollment.name or enrollment.email,
                                email=enrollment.email,
                            )
                        )
                    elif enrollment.name:
                        existing.name = enrollment.name
        logger.info("Synced %d enrollment(s) from Open edX", len(enrollments))
        return len(enrollments)

    async def sync_all(self, dry_run: bool = False) -> dict:
        """Run all sync steps in order. Never raises: an unreachable Open edX or
        a failing step is reported in the result, not thrown at the caller."""
        results: dict = {"courses": 0, "modules": 0, "enrollments": 0, "errors": []}

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
