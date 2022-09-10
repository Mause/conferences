from flask import Flask, jsonify, request
import requests

app = Flask(__name__)

@app.route('/api/dddperth/')
def schedule():
    data = requests.get('https://dddperth-functions-prod.azurewebsites.net/api/GetAgenda').json()
    return jsonify(data)

@app.errorhandler(404)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return request.url + ' not found'

