from app.functions.clusterer import *
from app.utils.decorators import *
from config import BASE_DIR, googleapi
from flask import Blueprint, request, jsonify
import requests

# Geo 블루프린트 작성
geo_routes = Blueprint('geo', __name__)

@geo_routes.route('/get_center_addr', methods=['GET'])
def get_center_addr():
    latlng = request.args.get('latlng')
    language = request.args.get('language')
    try:
        response = requests.get(f'https://maps.googleapis.com/maps/api/geocode/json?latlng={latlng}&language={language}&key={googleapi.GOOGLEMAPS_KEY}').json()
    except Exception as e:
        print("Exception:", e)
        return jsonify({
            'success': False,
            'msg': str(e)
        }), 400
    
    return jsonify(response), 200

@geo_routes.route("/load_addr_csv", methods=["GET"])
def load_addr_csv():
    """Load address data from a CSV file.

    Returns:
        result `str`:
            Response success or error status ("success" or "error").
        msg `str`:
            Response message.
        err_code `str`:
            Error code (refer to API_GUIDE.md)
        data `dict`:
            Address data loaded from the CSV file
    """
    f = open(BASE_DIR + "/data/csv_data/pnu_code.csv", "r", encoding="utf-8")
    lines = f.readlines()
    data = {}
    for line in lines:
        if line.split(",")[1] == "sido":
            continue
        if line.split(",")[1] not in data:
            data[line.split(",")[1]] = {}
        else:
            if line.split(",")[2] != "" and line.split(",")[2] not in data[line.split(",")[1]]:
                data[line.split(",")[1]][line.split(",")[2]] = []
            else:
                if line.split(",")[3] != "" and line.split(",")[3] not in data[line.split(",")[1]][line.split(",")[2]]:
                    data[line.split(",")[1]][line.split(",")[2]].append(line.split(",")[3])
    f.close()
    return jsonify({
        "success": True, 
        "msg": "주소 CSV 데이터를 불러왔습니다.",
        "data": data
    }), 200