from flask import Flask, request, render_template
import requests
from datetime import datetime


app = Flask(__name__)


start_date = end_date = datetime(2022, 9, 10, 0, 0, 0)


def to_time(t):
    fmt = t['Format']
    if not (fmt and fmt[0].isdigit()):
        return '00:00'
    return '{:02d}:{:02d}'.format(*divmod(int(fmt.split()[0]), 60))

@app.route('/api/dddperth/')
def schedule():
    data = requests.get('https://dddperth-functions-prod.azurewebsites.net/api/GetAgenda', verify=False).json()
    return (
        render_template(
            "schedule.xml",
            days={start_date: {'room': [{'start': start_date, 'end': end_date, **talk} for talk in data]}},
            to_time=to_time,
            start_date=start_date,
            end_date=end_date,
        ),
        200,
        {"content-type": "application/xml"},
    )


@app.errorhandler(404)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return request.url + ' not found'

