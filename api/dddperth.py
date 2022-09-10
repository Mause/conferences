from flask import Flask, request, render_template
import requests
from datetime import date


app = Flask(__name__)


start_date = end_date = date(2022, 9, 10)



@app.route('/api/dddperth/')
def schedule():
    data = requests.get('https://dddperth-functions-prod.azurewebsites.net/api/GetAgenda').json()
    return (
        render_template(
            "schedule.xml",
            days=data,
            to_time=lambda t: '{:02d}:{:02d}'.format(*divmod(t, 60)),
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

