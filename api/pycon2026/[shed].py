import json
from collections.abc import Callable, Iterable
from datetime import date, datetime, timedelta
from itertools import groupby as _groupby
from typing import Literal

import requests
from flask import Flask, Response, render_template, request
from lxml.html import fromstring
from pydantic import BaseModel

app = Flask(__name__)

TWO_DAYS = timedelta(days=3)


class Session(BaseModel):
    code: str
    title: str
    type: Literal[
        "workshop",
        "talk",
        "break",
        "plenary",
        "other",
    ]
    rooms: list[
        Literal[
            "Lyon",
            "Ballroom 1",
            "Ballroom 2",
            "Ballroom 3",
        ]
    ]
    start: datetime
    end: datetime
    who: str

    @property
    def duration(self) -> int | float:
        return (self.end - self.start).total_seconds()


class Day(BaseModel):
    key: str
    sessions: list[Session]


class Schedule(BaseModel):
    tz: str
    days: list[Day]


def groupby[K: str | date, V](
    iterable: Iterable[V], key: Callable[[V], K]
) -> _groupby[K, V]:
    return _groupby(sorted(iterable, key=key), key)


def to_time(seconds: int) -> str:
    hours, minutes = divmod(seconds // 60, 60)
    return f"{int(hours):02d}:{int(minutes):02d}"


@app.route("/api/pycon2026/<int:year>")
def schedule_year_xml(year):
    return get_schedule()


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def catch_all(path):
    return Response(f"Hello from {path} || {request.url}", status=200)


def one[T](t: list[T]) -> T:
    # if len(t) != 1:
    # raise ValueError(f"Expected one item, got {len(t)}")
    return t[0]


def get_schedule() -> tuple[str, int, dict[str, str]]:
    r = requests.get("https://2026.pycon.org.au/schedule/now")
    r.raise_for_status()
    (js,) = fromstring(r.content).xpath('//script[@id="board-data"]/text()')
    days = Schedule.validate(json.loads(js))

    days = {
        day.key: [
            (room, sorted(room_talks, key=lambda talk: talk.start))
            for room, room_talks in groupby(day.sessions, lambda talk: one(talk.rooms))
        ]
        for day in days.days
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
