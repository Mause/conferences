from collections.abc import Callable, Generator, Iterable
from datetime import date, datetime, timedelta
from functools import cache
from itertools import groupby as _groupby
from pathlib import Path
from tempfile import mkdtemp
from typing import TypedDict, cast

import frontmatter
from dulwich.porcelain import clone, pull
from dulwich.repo import Repo
from flask import Flask, Response, render_template, request
from pydantic import BaseModel

app = Flask(__name__)

TWO_DAYS = timedelta(days=3)


class Person(BaseModel):
    name: str


class Session(BaseModel):
    code: str
    title: str
    speakers: list[str]
    start: str | None
    end: str | None
    room: str
    track: str | None
    type: str
    abstract: str | None = None


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
    metadata = Person.validate(
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
    twitter_ids: list[str] =[]

    @property
    def id(self) -> int:
        return abs(hash(self.code))

    def __getattr__(self, name):
        breakpoint()


def get_talks(root: Path) -> Generator[ReSession]:
    for talk in (root / "src/content/sessions").glob("*.md"):
        talk = Session.model_validate(frontmatter.load(talk).metadata)
        if not (talk.start and talk.end):
            print(talk.title, "has no start time")
            continue
        start = datetime.fromisoformat(talk.start)
        end = datetime.fromisoformat(talk.end)
        duration = end - start

        yield ReSession(
            title=talk.title,
            room=talk.room,
            code=talk.code,
            track=talk.track or "no track",
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


if __name__ == "__main__":
    with app.app_context():
        body, status, hedaers = get_schedule()
        with open("out.xml", "w") as fh:
            fh.write(body)
        # print(body)
    app.run(debug=True, host="0.0.0.0")
