from flask import Flask, render_template
import requests
from datetime import datetime
from lxml.html import fromstring, tostring
from collections import defaultdict
from dateutil.parser import parse
from unidecode import unidecode

app = Flask(__name__)


start_date = end_date = datetime(2022, 9, 10, 0, 0, 0)


def to_time(t):
    fmt = t.get("Format")
    if fmt == "Keynote":
        return "00:50"
    elif not fmt:
        return "00:15"
    return "{:02d}:{:02d}".format(*divmod(int(fmt.split()[0]), 60))


def get_times_and_locations():
    html = fromstring(requests.get("https://dddperth.com/agenda").content)
    sections = html.xpath(".//section")
    for section in sections:
        times = section.xpath(".//time/@datetime")
        if not times:
            continue
        time = parse(str(times[0]))
        for talk in section:
            rooms = talk.xpath(".//span/text()")
            titles = talk.xpath(".//h2/text()")

            for title in titles:
                yield unidecode(title), {
                    "room": rooms[0] if rooms else "Elsewhere",
                    "start": time,
                }


@app.route("/api/dddperth/")
def schedule():
    locos = dict(get_times_and_locations())
    data = requests.get(
        "https://dddperth-functions-prod.azurewebsites.net/api/GetAgenda", verify=False
    ).json()
    talks = [
        {**talk, **locos.pop(" ".join(unidecode(talk["Title"]).split("  ")))}
        for talk in data
    ] + [
        {"Title": name, "Id": name, **meta}
        for name, meta in locos.items()
    ]

    rtalks = defaultdict(list)
    for talk in talks:
        rtalks[talk["room"]].append(talk)

    return (
        render_template(
            "schedule.xml",
            days={start_date: rtalks},
            to_time=to_time,
            start_date=start_date,
            end_date=end_date,
        ),
        200,
        {"content-type": "application/xml"},
    )

