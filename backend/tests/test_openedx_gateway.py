from sqlalchemy import func, select

from app.config import settings
from app.gateways.openedx_gateway.mongo_client import OpenEdxMongoUnavailableError
from app.gateways.openedx_gateway.sync_service import (
    COURSES_COLLECTION,
    ENROLLMENTS_COLLECTION,
    MODULES_COLLECTION,
    OpenEdxSyncService,
)
from app.models.module import Module, Subject
from app.models.student import Student

COURSE_KEY = "course-v1:UTP+PROG1+2026"


class FakeMongoClient:
    """In-memory stand-in for OpenEdxMongoClient."""

    def __init__(self, docs=None, reachable=True):
        self.docs = docs if docs is not None else {}
        self.reachable = reachable

    async def ping(self) -> bool:
        if not self.reachable:
            raise OpenEdxMongoUnavailableError("Open edX MongoDB unreachable (test)")
        return True

    async def fetch(self, collection, query=None):
        if not self.reachable:
            raise OpenEdxMongoUnavailableError("Open edX MongoDB unreachable (test)")
        return self.docs.get(collection, [])


# ---------------------------------------------------------------------------
# sync_courses
# ---------------------------------------------------------------------------

async def test_sync_courses_upserts_and_is_idempotent(db):
    docs = {
        COURSES_COLLECTION: [
            {"course_id": COURSE_KEY, "display_name": "Programacion I", "description": "Intro"}
        ]
    }
    service = OpenEdxSyncService(client=FakeMongoClient(docs))

    assert await service.sync_courses() == 1
    db.expire_all()
    subject = (
        await db.execute(select(Subject).where(Subject.external_id == COURSE_KEY))
    ).scalar_one()
    assert subject.name == "Programacion I"

    # Re-running with an updated name UPDATES the same row (no duplicate).
    docs[COURSES_COLLECTION][0]["display_name"] = "Programacion I (2026-2)"
    assert await service.sync_courses() == 1
    db.expire_all()
    assert (await db.execute(select(func.count()).select_from(Subject))).scalar() == 1
    subject = (
        await db.execute(select(Subject).where(Subject.external_id == COURSE_KEY))
    ).scalar_one()
    assert subject.name == "Programacion I (2026-2)"


async def test_sync_courses_skips_documents_without_course_id(db):
    service = OpenEdxSyncService(
        client=FakeMongoClient({COURSES_COLLECTION: [{"display_name": "Sin id"}]})
    )
    assert await service.sync_courses() == 0
    assert (await db.execute(select(func.count()).select_from(Subject))).scalar() == 0


# ---------------------------------------------------------------------------
# sync_modules
# ---------------------------------------------------------------------------

async def test_sync_modules_links_to_subject_and_is_idempotent(db):
    docs = {
        COURSES_COLLECTION: [{"course_id": COURSE_KEY, "display_name": "Programacion I"}],
        MODULES_COLLECTION: [
            {
                "module_id": "block-v1:UTP+PROG1+2026+type@chapter+block@vars",
                "course_id": COURSE_KEY,
                "display_name": "Variables",
                "order": 1,
            }
        ],
    }
    service = OpenEdxSyncService(client=FakeMongoClient(docs))
    await service.sync_courses()
    assert await service.sync_modules() == 1

    db.expire_all()
    module = (await db.execute(select(Module))).scalar_one()
    assert module.name == "Variables"
    assert module.order == 1
    subject = (await db.execute(select(Subject))).scalar_one()
    assert module.subject_id == subject.id

    # Idempotent re-run.
    assert await service.sync_modules() == 1
    db.expire_all()
    assert (await db.execute(select(func.count()).select_from(Module))).scalar() == 1


async def test_sync_modules_skips_module_whose_course_is_not_synced(db):
    docs = {
        MODULES_COLLECTION: [
            {"module_id": "block-1", "course_id": "course-unknown", "display_name": "Huerfano"}
        ]
    }
    service = OpenEdxSyncService(client=FakeMongoClient(docs))
    assert await service.sync_modules() == 0
    assert (await db.execute(select(func.count()).select_from(Module))).scalar() == 0


# ---------------------------------------------------------------------------
# sync_enrollments
# ---------------------------------------------------------------------------

async def test_sync_enrollments_creates_and_updates_students(db):
    docs = {
        ENROLLMENTS_COLLECTION: [
            {"user_id": "1", "email": "ana@utp.edu.co", "name": "Ana Soto"}
        ]
    }
    service = OpenEdxSyncService(client=FakeMongoClient(docs))
    assert await service.sync_enrollments() == 1

    db.expire_all()
    student = (
        await db.execute(select(Student).where(Student.email == "ana@utp.edu.co"))
    ).scalar_one()
    assert student.name == "Ana Soto"

    # Re-running with a changed name updates in place (reconciled by email).
    docs[ENROLLMENTS_COLLECTION][0]["name"] = "Ana Soto Parra"
    assert await service.sync_enrollments() == 1
    db.expire_all()
    assert (await db.execute(select(func.count()).select_from(Student))).scalar() == 1
    student = (
        await db.execute(select(Student).where(Student.email == "ana@utp.edu.co"))
    ).scalar_one()
    assert student.name == "Ana Soto Parra"


# ---------------------------------------------------------------------------
# sync_all — safety
# ---------------------------------------------------------------------------

async def test_sync_all_handles_unreachable_mongo_without_raising(db):
    service = OpenEdxSyncService(client=FakeMongoClient(reachable=False))
    results = await service.sync_all()  # must not raise
    assert results["courses"] == 0
    assert results["errors"]
    assert "unreachable" in results["errors"][0].lower()


async def test_sync_all_dry_run_writes_nothing(db):
    docs = {
        COURSES_COLLECTION: [{"course_id": COURSE_KEY, "display_name": "Programacion I"}],
        ENROLLMENTS_COLLECTION: [{"user_id": "1", "email": "ana@utp.edu.co", "name": "Ana"}],
    }
    service = OpenEdxSyncService(client=FakeMongoClient(docs))
    results = await service.sync_all(dry_run=True)

    assert results["courses"] == 1
    assert results["enrollments"] == 1
    assert results["errors"] == []
    # Nothing was written.
    assert (await db.execute(select(func.count()).select_from(Subject))).scalar() == 0
    assert (await db.execute(select(func.count()).select_from(Student))).scalar() == 0


# ---------------------------------------------------------------------------
# Admin trigger endpoint
# ---------------------------------------------------------------------------

async def test_admin_sync_endpoint_rejects_missing_token(client):
    resp = await client.post("/api/admin/sync-openedx")
    assert resp.status_code == 422  # header required


async def test_admin_sync_endpoint_rejects_invalid_token(client, monkeypatch):
    monkeypatch.setattr(settings, "admin_token", "secreto")
    resp = await client.post(
        "/api/admin/sync-openedx", headers={"X-Admin-Token": "equivocado"}
    )
    assert resp.status_code == 403


async def test_admin_sync_endpoint_fails_closed_when_token_not_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "admin_token", None)
    resp = await client.post(
        "/api/admin/sync-openedx", headers={"X-Admin-Token": "cualquiera"}
    )
    assert resp.status_code == 403


async def test_admin_sync_endpoint_accepts_valid_token(client, monkeypatch):
    monkeypatch.setattr(settings, "admin_token", "secreto")
    resp = await client.post(
        "/api/admin/sync-openedx",
        params={"dry_run": True},
        headers={"X-Admin-Token": "secreto"},
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "accepted"
    assert body["dry_run"] is True
    assert body["task_id"]
