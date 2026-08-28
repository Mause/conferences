from collections.abc import Callable, Generator, Iterable
from datetime import date, datetime, timedelta
from functools import cache
from itertools import groupby as _groupby
from pathlib import Path
from tempfile import mkdtemp
from uuid import UUID

import frontmatter
from dulwich.porcelain import clone, pull
from dulwich.repo import Repo
from flask import Flask, Response, render_template, request
from lxml import etree
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

app = Flask(__name__)

TWO_DAYS = timedelta(days=3)


class NoExtraModel(BaseModel):
    model_config = ConfigDict(extra="forbid", alias_generator=to_camel)


class Person(NoExtraModel):
    name: str
    code: str
    has_avatar: bool


class Session(NoExtraModel):
    code: str
    title: str
    speakers: list[str]
    start: str | None
    end: str | None
    room: str
    track: str | None
    track_name: str | None = None
    type: str
    abstract: str | None = None
    tags: list[str] = Field(default_factory=list)
    sponsor: str | None = None


def groupby[K: str | date, V](
    iterable: Iterable[V], key: Callable[[V], K]
) -> _groupby[K, V]:
    return _groupby(sorted(iterable, key=key), key)


def to_time(minutes: int) -> str:
    hours, minutes = divmod(minutes, 60)
    return f"{int(hours):02d}:{int(minutes):02d}"


@app.route("/api/pycon2026/<int:year>")
def schedule_year_xml(year):
    return get_schedule()


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def catch_all(path):
    return Response(f"Hello from {path} || {request.url}", status=200)


@cache
def get_author(root: Path, code: str) -> str:
    metadata = Person.model_validate(
        frontmatter.load(root / f"src/content/people/{code}.md").metadata,
    )
    return metadata.name


class ReSession(BaseModel):
    code: str
    track: str
    title: str
    start: datetime
    end: datetime
    room: str
    duration: float
    authors: list[str]
    type: str
    abstract: str
    video_url: None = None
    twitter_ids: list[str] = []

    @property
    def id(self) -> int:
        return abs(hash(self.code))

    @property
    def guid(self) -> UUID:
        return UUID(int=self.id)

    def __getattr__(self, name):
        breakpoint()


def get_talks(root: Path) -> Generator[ReSession]:
    for talk in (root / "src/content/sessions").glob("*.md"):
        talk = Session.model_validate(frontmatter.load(talk).metadata)
        if not (talk.start and talk.end):
            print(talk.title, "has no start time")
            continue
        if talk.code.startswith("BREAK"):
            print(talk.title, "is a break")
            continue
        start = datetime.fromisoformat(talk.start)
        end = datetime.fromisoformat(talk.end)
        duration = end - start

        yield ReSession(
            title=talk.title,
            room=talk.room,
            code=talk.code,
            track=talk.track_name or "no track",
            # **talk,
            type=talk.type,
            abstract=talk.abstract or "No abstract provided",
            start=start,
            end=end,
            duration=duration.total_seconds() / 60,
            authors=[get_author(root, speaker) for speaker in talk.speakers],
        )


def get_schedule() -> tuple[str, int, dict[str, str]]:
    path = Path(mkdtemp()) / "2026-website"
    if not path.exists():
        clone(
            "https://github.com/pyconau/2026-website.git",
            path,
            depth=1,
        )
    else:
        pull(Repo(path))

    schedule = list(get_talks(path))
    print(schedule[0])

    days = groupby(schedule, lambda talk: talk.start.date())
    days = {
        date: [
            (room, sorted(room_talks, key=lambda talk: talk.start))
            for room, room_talks in groupby(talks, lambda talk: talk.room)
        ]
        for date, talks in days
    }

    start_date = date.fromisoformat("2026-08-26")
    end_date = date.fromisoformat("2026-08-30")
    return (
        render_template(
            "schedule.xml",
            days=days,
            to_time=to_time,
            start_date=start_date,
            end_date=end_date,
        ),
        200,
        {"content-type": "application/xml"},
    )


def validate_schedule(
    xml_path: str = "out.xml", xsd_path: str = "schedule.xsd"
) -> bool:
    schema = etree.XMLSchema(etree.parse(xsd_path))
    doc = etree.parse(xml_path)
    is_valid = schema.validate(doc)
    if is_valid:
        print("schedule.xml valid against c3voc schema")
    else:
        for err in schema.error_log:
            print(f"  Line {err.line}: {err.message}")
    return is_valid


if __name__ == "__main__":
    with app.app_context():
        body, status, hedaers = get_schedule()
        with open("out.xml", "w") as fh:
            fh.write(body)
        validate_schedule()
    app.run(debug=True, host="0.0.0.0")
