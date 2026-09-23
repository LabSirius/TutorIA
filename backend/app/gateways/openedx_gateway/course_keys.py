"""Parse Open edX "opaque keys" for courses.

Open edX identifies a course with an "opaque key" — the string format it has
used since the split-mongo modulestore — of the shape:

    course-v1:ORG+COURSE+RUN

for example ``course-v1:UTP+V001+2026_07_V1``
(org=``UTP``, course=``V001``, run=``2026_07_V1``).

We deliberately do NOT depend on the `opaque-keys` PyPI library: we only need to
split this one well-known format, so a few lines of pure string parsing keep the
gateway lightweight and dependency-free.
"""

_COURSE_KEY_PREFIX = "course-v1:"


class InvalidCourseKeyError(ValueError):
    """Raised when a string is not a valid Open edX opaque course key."""


def parse_course_key(key: str) -> tuple[str, str, str]:
    """Split ``course-v1:ORG+COURSE+RUN`` into ``(org, course, run)``.

    Raises InvalidCourseKeyError if the ``course-v1:`` prefix is missing, the
    three ``+``-separated parts are not all present, or any part is empty.
    """
    if not isinstance(key, str) or not key.startswith(_COURSE_KEY_PREFIX):
        raise InvalidCourseKeyError(
            f"Not an Open edX opaque course key (missing "
            f"'{_COURSE_KEY_PREFIX}' prefix): {key!r}"
        )

    remainder = key[len(_COURSE_KEY_PREFIX):]
    parts = remainder.split("+")
    if len(parts) != 3 or not all(part.strip() for part in parts):
        raise InvalidCourseKeyError(
            f"Malformed opaque course key (expected ORG+COURSE+RUN): {key!r}"
        )

    org, course, run = (part.strip() for part in parts)
    return org, course, run


def is_valid_course_key(key: str) -> bool:
    """Return True if ``key`` is a well-formed opaque course key, else False
    (a convenience for callers that prefer a boolean over exception handling)."""
    try:
        parse_course_key(key)
    except InvalidCourseKeyError:
        return False
    return True
