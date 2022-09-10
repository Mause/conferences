from flask import Flask

app = Flask(__name__)

@app.route('/schedule.xml')
def schedule():
    return 'hello'

