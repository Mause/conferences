from dulwich.porcelain import pull
from dulwich.repo import Repo
from functools import cache
from pathlib import Path
import frontmatter
from itertools import groupby as _groupby
from datetime import datetime, date, timedelta
from flask import Flask, render_template, redirect, url_for


app = Flask(__name__)

TWO_DAYS = timedelta(days=3)
DATES = {
    str(date.year): (date, date + TWO_DAYS)
    for date in (date(2018, 8, 24), date(2019, 8, 1))
}


def groupby(iterable, key):
    return _groupby(sorted(iterable, key=key), key)


def to_time(minutes: int) -> str:
    return "%02d:%02d" % divmod(minutes, 60)


@app.route("/schedule.xml")
def schedule_xml():
    return redirect(url_for("schedule_year_xml", year="2019"))


@app.route("/api/pycon/<year>")
def schedule_year_xml(year):
    return get_schedule()


@cache
def get_author(code: str) -> str:
    return frontmatter.load(
        Path(f"./2026-website/src/content/people/{code}.md")
    ).metadata["name"]


def get_talks():
    for talk in Path("./2026-website/src/content/sessions").glob("*.md"):
        talk = frontmatter.load(talk).metadata
        start = datetime.fromisoformat(talk["start"])
        end = datetime.fromisoformat(talk["end"])
        duration = end - start

        yield {
            **talk,
            "start": start,
            "end": end,
            "duration": duration.total_seconds() / 60,
            "authors": [get_author(speaker) for speaker in talk["speakers"]],
        }


def get_schedule():
    pull(Repo("./2026-website/"))

    schedule = list(get_talks())
    print(schedule[0])

    days = groupby(schedule, lambda talk: talk["start"].date())
    days = {date: groupby(talks, lambda talk: talk["room"]) for date, talks in days}

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
    # app.run(debug=True, host="0.0.0.0")
    with app.app_context():
        body, status, hedaers = get_schedule()
        with open("out.xml", "w") as fh:
            fh.write(body)
        # print(body)
