from flask import Flask, jsonify
import requests

app = Flask(__name__)

@app.route('/')
def schedule():
    data = requests.get('https://dddperth-functions-prod.azurewebsites.net/api/GetAgenda').json()
    return jsonify(data)

