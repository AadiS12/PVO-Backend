from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_restful import Api, Resource


app = Flask(__name__)
CORS(app, supports_credentials=True, origins=[ "https://pvo.opencodingsociety.com" ])

api = Api(app)


class InfoModel:
    def __init__(self):
        self.data = [
            {
                "FirstName": "John",
                "LastName": "Mortensen",
                "DOB": "October 21",
                "Residence": "San Diego",
                "Email": "jmortensen@powayusd.com",
                "Owns_Cars": ["2015-Fusion", "2011-Ranger", "2003-Excursion", "1997-F350", "1969-Cadillac", "2015-Kuboto-3301"]
            },
            {
                "FirstName": "Shane",
                "LastName": "Lopez",
                "DOB": "February 27",
                "Residence": "San Diego",
                "Email": "slopez@powayusd.com",
                "Owns_Cars": ["2021-Insight"]
            }
        ]

    def read(self):
        return self.data

    def create(self, entry):
        self.data.append(entry)

info_model = InfoModel()

class DataAPI(Resource):
    def get(self):
        return jsonify(info_model.read())

    def post(self):
        entry = request.get_json()
        if not entry:
            return {"error": "No data provided"}, 400
        info_model.create(entry)
        return {"message": "Entry added successfully", "entry": entry}, 201

api.add_resource(DataAPI, '/api/data')

@app.route('/')
def say_hello():
    return "<html><body><h2>Hello, World!</h2></body></html>"

if __name__ == '__main__':
    app.run(port=8426, debug=True)  # ← match config.js