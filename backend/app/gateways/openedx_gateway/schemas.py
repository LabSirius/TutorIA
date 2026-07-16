"""Pydantic models for the subset of Open edX MongoDB documents we care about.

These describe only the fields the gateway reads, not the full Open edX
document shape. Parsing is deliberately defensive (see sync_service): the exact
field names must be confirmed against the real instance before the pilot.
"""
from pydantic import BaseModel


class OpenEdxCourse(BaseModel):
    """A course in Open edX -> becomes a row in our `subjects` table."""

    course_id: str          # natural key (reconciliation key -> subjects.external_id)
    display_name: str
    description: str | None = None


class OpenEdxModule(BaseModel):
    """A course module/block -> becomes a row in our `modules` table."""

    module_id: str          # natural key (reconciliation key -> modules.external_id)
    course_id: str          # parent course (-> subjects.external_id)
    display_name: str
    order: int = 0
    description: str | None = None
    content_text: str | None = None


class OpenEdxEnrollment(BaseModel):
    """A student enrollment -> becomes/updates a row in our `students` table.

    Reconciled by email, which is already unique in our schema.
    """

    user_id: str
    email: str
    name: str | None = None
    course_id: str | None = None
