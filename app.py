# app.py
import asyncio
from math import atan2, cos, radians, sin, sqrt
import math
import random
from flask import Flask, jsonify, request
from flask_restful import Resource, Api
from flask_swagger_ui import get_swaggerui_blueprint
import googlemaps
from datetime import datetime
import polyline
from firebase_admin import firestore, initialize_app, credentials, exceptions
import requests
from config import API_KEY
from flask_cors import CORS, cross_origin
from geopy.distance import geodesic
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

# from apscheduler.schedulers.background import BackgroundScheduler
gmaps = googlemaps.Client(key=API_KEY)

app = Flask(__name__)
CORS(app)
api = Api(app)

# Configure Swagger UI
SWAGGER_URL = '/swagger'
API_URL = "/static/swagger.json"
swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "CoDrive"
    }
)
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

cred = credentials.Certificate("firebase-admin.json")
initialize_app(cred)

db = firestore.client()

userRef = db.collection("Users")
vehicleRef = db.collection("Vehicles")
reviewRef = db.collection("Reviews")
rideRef = db.collection("Rides")

# scheduler = BackgroundScheduler()

def printHello():
    print("Hello")
    
# scheduler.add_job(printHello, 'interval', seconds=10)

# scheduler.start()

@app.route('/hello')
def hello():
    return {"members":["member1","member2","member5"]}

# api.add_resource(hello, '/hello')

def get_vehicle(vehicle_id):
    docRef = vehicleRef.document(vehicle_id)
    doc = docRef.get()
    if doc.exists:
        vehicle = doc.to_dict()
        vehicle["Id"] = vehicle_id
        return vehicle
    else:
        return None
    
def get_reviewer(user_id):
    docRef = userRef.document(user_id)
    doc = docRef.get()
    if doc.exists:
        data = doc.to_dict()
        return {
            "Name": f"{data['FirstName']} {data['LastName']}",
            "ProfileUrl": data['ProfileUrl'],
            "Id": user_id
        }
    else:
        return None 

def get_review(review_id):
    docRef = reviewRef.document(review_id)
    doc = docRef.get()
    if doc.exists:
        data = doc.to_dict()
        data["Id"] = review_id
        data["Reviewer"] = get_reviewer(data["Reviewer"].get().id)
        return data
    else:
        return None
    
def get_driver(user_id):
    docRef = userRef.document(user_id)
    doc = docRef.get()
    if doc.exists:
        data = doc.to_dict()
        return {
            "Name": f"{data['FirstName']} {data['LastName']}",
            "ProfileUrl": data['ProfileUrl'],
            "Id": user_id,
            "PhoneNumber": data["PhoneNumber"],
            "Gender": data["Gender"]
        }
    else:
        return None
    
def get_corider(user_id):
    docRef = userRef.document(user_id)
    doc = docRef.get()
    if doc.exists:
        data = doc.to_dict()
        return {
            "Name": f"{data['FirstName']} {data['LastName']}",
            "ProfileUrl": data['ProfileUrl'],
            "Id": user_id,
            "Gender": data["Gender"],
            "PhoneNumber": data["PhoneNumber"]
        }
    else:
        return None
   

def get_ride(ride_id):
    docRef = rideRef.document(ride_id)
    doc = docRef.get()
    if doc.exists:
        data = doc.to_dict()
        data["Id"] = ride_id
        if "Driver" in data:
            data["Driver"] = get_driver(data["Driver"].get().id)
        if "Vehicle" in data:
            data["Vehicle"] = get_vehicle(data["Vehicle"].get().id)

        coRidersRef = docRef.collection("CoRiders")
        co_riders = coRidersRef.get()
        co_riders_data = []
        for co_rider in co_riders:
            co_rider_data = co_rider.to_dict()
            co_rider_data["Id"] = co_rider.id
            if co_rider_data["CoRider"]:
                co_rider_data["CoRider"] = get_corider(co_rider_data["CoRider"].get().id)
                co_riders_data.append(co_rider_data)
        data["CoRiders"] = co_riders_data
        return data
    else:
        return None
    
def get_corider(corider_id):
    docRef = userRef.document(corider_id)
    doc = docRef.get()
    if doc.exists:
        data = doc.to_dict()
        return {
            "Name": f"{data['FirstName']} {data['LastName']}",
            "ProfileUrl": data['ProfileUrl'],
            "Id": corider_id,
            "PhoneNumber": data['PhoneNumber'],
            "Gender": data["Gender"],
        }
    else:
        return None
    
def calculate_distance(lat1, lon1, lat2, lon2):
    # Radius of the Earth in kilometers
    R = 6371.0

    # Convert latitude and longitude from degrees to radians
    lat1_rad = radians(lat1)
    lon1_rad = radians(lon1)
    lat2_rad = radians(lat2)
    lon2_rad = radians(lon2)

    # Difference in latitude and longitude
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    # Haversine formula
    a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = R * c

    return distance

@app.route('/get_ride', methods=['GET'])
def get_ride_details():
    try:
        rideId = request.args.get('rideId')
        return get_ride(rideId), 200
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500


@app.route('/get_user', methods=['GET'])
def get_user():
    try:
        docRef = userRef.document(request.args.get('userId'))
        doc = docRef.get()
        if doc.exists:
            user_data = doc.to_dict()
            user_data["Id"] = doc.id
            if "Reviews" in user_data:
                user_data["Reviews"] = [get_review(ref.get().id) for ref in user_data["Reviews"]]
            if "Vehicles" in user_data:
                user_data["Vehicles"] = [get_vehicle(ref.get().id) for ref in user_data["Vehicles"]]
            if "History"in user_data:
                del user_data["History"]
            return jsonify(user_data), 200
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500

    
@app.route('/get_history', methods=['GET'])
def get_history():
    try:
        docRef = userRef.document(request.args.get('userId'))
        doc = docRef.get()
        if doc.exists:
            user_data = doc.to_dict()
            if "History" in user_data:
                user_data["History"] = [get_ride(ref.get().id) for ref in user_data["History"]]
            
            history_data = user_data["History"]

            return jsonify(history_data), 200
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_directions')
def get_directions():
    try:
        # Get source and destination
        source_lat = float(request.args.get('s1'))
        source_lng = float(request.args.get('s2'))
        destination_lat = float(request.args.get('d1'))
        destination_lng = float(request.args.get('d2'))

        source_str = f"{source_lat},{source_lng}"
        destination_str = f"{destination_lat},{destination_lng}"

        print("Hello", source_str, destination_str)

        # Request directions from Google Maps API
        directions_result = gmaps.directions(
            source_str,
            destination_str,
            mode="driving",  # You can change the mode based on your requirements
            departure_time=datetime.now(),
        )

        # Extract relevant information from the directions result
        route = directions_result[0]['legs'][0]
        steps = route['steps']

        total_distance = route['distance']['text']
        total_duration = route['duration']['text']
        
        # Use arrival_time if available, otherwise, use duration_in_traffic
        eta = route['arrival_time']['text'] if 'arrival_time' in route else route['duration_in_traffic']['text']

        # Extract polyline coordinates
        encoded_polyline = directions_result[0]['overview_polyline']['points']
        decoded_polyline = polyline.decode(encoded_polyline)

        # Additional information
        total_steps = len(steps)

        response_data = {
            'status': 'success',
            'total_distance': total_distance,
            'total_duration': total_duration,
            'eta': eta,
            'polyline_coordinates': decoded_polyline,
            'total_steps': total_steps,
            'steps': [{
                'instruction': step['html_instructions'],
                'distance': step['distance']['text'],
                'duration': step['duration']['text'],
                'start_location': step['start_location'],
                'end_location': step['end_location'],
            } for step in steps],
        }

        return jsonify(response_data)

    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500

@app.route('/add_vehicle', methods=['POST'])
def add_vehicle():
    try:
        data = request.json
        userId = data.get('userId')

        vehicle_data = {
            "FuelType": data.get('fuelType'),
            "SeatingCapcity": data.get('seatingCapacity'),
            "VehicleName": data.get('vehicleName'),
            "VehicleNumber": data.get('vehicleNumber')  
        }

        doc_ref = vehicleRef.document()
        doc_ref.set(vehicle_data)
        doc_id = doc_ref.id


        user_doc = userRef.document(userId)
        user_doc.update({"Vehicles": firestore.ArrayUnion([doc_ref])})

        return jsonify({"message": "Vehicle added successfully", "document_id": doc_id, "data": vehicle_data}), 200
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_places', methods=['GET'])
def get_places():
    query = request.args.get('query')
    src_lat = float(request.args.get('src_lat'))
    src_lng = float(request.args.get('src_lng'))
    location = f'{src_lat}, {src_lng}'
    radius = 50000
    url = f'https://maps.googleapis.com/maps/api/place/textsearch/json?query={query}&location={location}&radius={radius}&key={API_KEY}'


    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = response.json()
        places = data.get('results', [])

        if not places:
            return jsonify({'error': 'No places found.'}), 404

        results = []
        for place in places:
            place_lat = place['geometry']['location']['lat']
            place_lon = place['geometry']['location']['lng']
            distance = calculate_distance(src_lat, src_lng, place_lat, place_lon)
            place['distance'] = distance
            results.append(place)

        sorted_places = sorted(places, key=lambda x: x["distance"])
        if(len(sorted_places) > 0):
            return jsonify({'places': sorted_places}), 200
        else:
            return jsonify({'places': []}), 201
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_is_on_ride', methods=['GET'])
def get_is_on_ride():
    userId = request.args.get('userId')
    userDocRef = userRef.document(userId)
    userDoc = userDocRef.get()
    try:
        if(userDoc.exists):
            data = userDoc.to_dict()
            if "IsOnRide" in data:
                return data["IsOnRide"], 200
            else:
                return [False, ""], 200
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500

@app.route('/start_ride', methods=['GET'])
def start_ride():
    try:
        userId = request.args.get('userId')
        vehicleId = request.args.get('vehicleId')
        distance = request.args.get('totalDistance')
        s_lat = float(request.args.get('s_lat'))
        s_lng = float(request.args.get('s_lng'))
        s_str = request.args.get('s_str')
        d_lat = float(request.args.get('d_lat'))
        d_lng = float(request.args.get('d_lng'))
        d_str = request.args.get('d_str')
        seatingCapacity = int(request.args.get('seatingCapacity'))
        isNow = request.args.get('isNow')
        startTime = 0
        if(isNow):
            startTime = SERVER_TIMESTAMP
        else:
            startTime = request.args.get('startTime')

        source = [s_lat, s_lng, s_str]
        destination = [d_lat, d_lng, d_str]

        driver_ref = userRef.document(userId)

        ride_data = {
            "Source": source,
            "Destination": destination,
            "Status": "Started",
            "StartTime": startTime,
            "Driver": driver_ref,
            "JoinedRiders": 0,
            "SeatingCapacity": seatingCapacity,
            # "TotalDistance": distance,
            "Vehicle": vehicleRef.document(vehicleId),
            "Updated": 0,
        }

        doc_ref = rideRef.document()
        doc_ref.set(ride_data)
        doc_id = doc_ref.id

        user_doc = userRef.document(userId)
        user_doc.update({"History": firestore.ArrayUnion([doc_ref]), "IsOnRide": [True, doc_id]})

        return jsonify({"message": "Ride started successfully", "document_id": doc_id}), 200
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500

@app.route('/join_ride', methods=['GET'])
def join_ride():
    try:
        userId = request.args.get('userId')
        rideId = request.args.get('rideId')
        amount = float(request.args.get('amount'))

        # Pickup Latitude, Longitude & String
        p_lat = float(request.args.get('p_lat'))
        p_lng = float(request.args.get('p_lng'))
        p_str = request.args.get('p_str')

        # Drop Latitude, Longitude & String
        d_lat = float(request.args.get('d_lat'))
        d_lng = float(request.args.get('d_lng'))
        d_str = request.args.get('d_str')

        pickup = [p_lat, p_lng, p_str]
        drop = [d_lat, d_lng, d_str]

        corider_ref = userRef.document(userId)

        ride_doc_ref = rideRef.document(rideId)
        ride_doc = rideRef.document(rideId).get()
        if(ride_doc.exists):
            data = ride_doc.to_dict()
            if(data["JoinedRiders"] == data["SeatingCapacity"]):
                return jsonify({"error": "Ride is full, please try joining another ride."}), 500

        doc_ref = rideRef.document(rideId).collection("CoRiders").document()
        
        ride_data = {
            "Pickup": pickup,
            "Drop": drop,
            "PickupTime": SERVER_TIMESTAMP,
            "DropTime": SERVER_TIMESTAMP,
            "Distance": 1,
            "CoRider": corider_ref,
            "Amount": amount,
            "Status": "Requested",
            "CompletionCode": random.randint(10000, 99999),
        }

        doc_ref.set(ride_data)
        doc_id = doc_ref.id

        user_doc = userRef.document(userId)
        user_doc.update({"History": firestore.ArrayUnion([doc_ref])})
        ride_doc_ref.update({"Updated": ride_doc.to_dict()["Updated"] + 1})

        return jsonify({"message": "Ride joined successfully", "document_id": doc_id}), 200
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/accept_join_request', methods=['GET'])
def accept_join_request():
    rideId  = request.args.get('rideId')
    coriderId  = request.args.get('coriderId')

    rideDocRef = rideRef.document(rideId)
    rideDoc = rideDocRef.get()
    coriders = rideDocRef.collection("CoRiders")
    coriderRef = coriders.document(coriderId)

    corider = coriderRef.get()
    try:
        if rideDoc.to_dict()["JoinedRiders"] < rideDoc.to_dict()["SeatingCapacity"]:
            if corider.exists:
                data = corider.to_dict()
                data["CoRider"] = get_corider(data["CoRider"].get().id)
                coRiderMainDocRef = userRef.document(data["CoRider"]["Id"])
                corider_main_data = coRiderMainDocRef.get().to_dict()
                if "IsOnRide" in corider_main_data:
                    if(corider_main_data["IsOnRide"][0]):
                        return jsonify({"message": "User has already joined another ride."}), 201
                coriderRef.update({"Status": "Joined"})
                ride_data = rideDoc.to_dict()
                rideDocRef.update({"Updated": ride_data["Updated"] + 1})
                coRiderMainDocRef.update({"History": firestore.ArrayUnion([rideDocRef]), "IsOnRide": [True, rideId]})
                return jsonify({"message": "Joining request has been accepted."}), 200
            else:
                return jsonify({"err": "Corider doesn't exist"}), 500
        else:
            return jsonify({"err": "Ride is full"}), 500

    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500

@app.route('/reject_join_request', methods=['GET'])
def reject_join_request():
    rideId  = request.args.get('rideId')
    coriderId  = request.args.get('coriderId')

    rideDocRef = rideRef.document(rideId)
    rideDoc = rideDocRef.get()
    coriders = rideDocRef.collection("CoRiders")
    coriderRef = coriders.document(coriderId)

    corider = coriderRef.get()
    if corider.exists:
        data = corider.to_dict()
        data["CoRider"] = get_corider(data["CoRider"].get().id)
        coRiderMainDocRef = userRef.document(data["CoRider"]["Id"])
        coriderRef.update({"Status": "Rejected"})
        ride_data = rideDoc.to_dict()
        rideDocRef.update({"Updated": ride_data["Updated"] + 1})
        coRiderMainDocRef.update({"History": firestore.ArrayUnion([rideDocRef]), "IsOnRide": [False, rideId]})
        return jsonify({"message": "Joining request has been accepted."}), 200
    else:
        return jsonify({"err": "corider doesn't exist"}), 500
    
@app.route('/complete_corider_ride', methods=['GET'])
def complete_corider_ride():
    rideId  = request.args.get('rideId')
    coriderId  = request.args.get('coriderId')
    completionCode  = int(request.args.get('completionCode'))

    rideDoc = rideRef.document(rideId)
    coriders = rideDoc.collection("CoRiders")
    coriderRef = coriders.document(coriderId)
    corider = coriderRef.get()
    rideDocGet = rideDoc.get()
    if corider.exists:
        data = corider.to_dict()
        if data["CompletionCode"] == completionCode and data["Status"] == "Joined":
            if rideDocGet.exists:
                ride_data = rideDocGet.to_dict()
                coRiderMainDocRef = userRef.document(data["CoRider"].id)
                balance = coRiderMainDocRef.get().to_dict()["Balance"]
                payableAmount = data["Amount"]
                updatedBalance = balance - payableAmount
                transactionRef = coRiderMainDocRef.collection("Transactions").doc()
                transactionRef.set({
                    "Message": "Paid for Ride", 
                    "Amount": payableAmount,
                    "RideId": rideId,
                    "Time": SERVER_TIMESTAMP
                })
                rideDoc.update({"Updated": ride_data["Updated"] + 1})
                coRiderMainDocRef.update({"IsOnRide": [False, rideId], "Balance": updatedBalance})
            coriderRef.update({"Status": "Completed", "DropTime": SERVER_TIMESTAMP})
            return jsonify({"message": "Ride is completed"}), 200
        else:
            return jsonify({"error": "Error in ride completion"}), 500
    return None

@app.route('/complete_driver_ride', methods=['GET'])
def complete_driver_ride():
    rideId = request.args.get('rideId')
    rideDocRef = rideRef.document(rideId)
    ride = rideDocRef.get()
    if(ride.exists):
        data = ride.to_dict()
        if "Driver" in data:
            user_doc = data["Driver"]
            rideDocRef.update({"Status": "Completed"})
            user_doc.update({"IsOnRide": [False, rideId]})
            return jsonify({"message": "Ride completed successfully"}), 200
        else:
            return jsonify({"err": "Ride is not started"}), 500
    return jsonify({"error": "Error on ride completion."}), 500

    
def fetch_route_coordinates(source_lat, source_lng, destination_lat, destination_lng):
    source_str = f"{source_lat},{source_lng}"
    destination_str = f"{destination_lat},{destination_lng}"
    directions_result = gmaps.directions(
        source_str,
        destination_str,
        mode="driving",  # You can change the mode based on your requirements
        departure_time=datetime.now(),
    )

    # Extract relevant information from the directions result
    if len(directions_result) > 0:
        route = directions_result[0]['legs'][0]
        steps = route['steps']
        encoded_polyline = directions_result[0]['overview_polyline']['points']
        decoded_polyline = polyline.decode(encoded_polyline)
        if len(decoded_polyline) > 0:
            # Insert source coordinates at the beginning
            decoded_polyline.insert(0, (source_lat, source_lng))
            # Append destination coordinates at the end
            decoded_polyline.append((destination_lat, destination_lng))
            return decoded_polyline 
        else:
            return []
    else:
        return []

def calculate_bearing(lat1, lon1, lat2, lon2):
    """
    Calculate the bearing angle between two sets of coordinates.
    """
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    delta_lon = lon2_rad - lon1_rad

    y = math.sin(delta_lon) * math.cos(lat2_rad)
    x = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon)

    bearing = math.atan2(y, x)
    bearing = math.degrees(bearing)
    bearing = (bearing + 360) % 360

    return bearing
    

@app.route('/search_rides', methods=['GET'])
def search_rides():
    # Get user's source and destination coordinates from the request
    user_source_lat = float(request.args.get('s_lat'))
    user_source_lng = float(request.args.get('s_lng'))
    user_destination_lat = float(request.args.get('d_lat'))
    user_destination_lng = float(request.args.get('d_lng'))

    query = rideRef.where("Status", "==", "Started")
    rides = query.stream()

    user_route_coordinates = fetch_route_coordinates(user_source_lat, user_source_lng, user_destination_lat, user_destination_lng)

    filtered_rides = []
    count = 0

    bearing1 = calculate_bearing(user_source_lat,user_source_lng, user_destination_lat, user_destination_lng)
    results = []
    for ride in rides:
        ride_data = ride.to_dict()
        if(ride_data["JoinedRiders"] == ride_data["SeatingCapacity"]):
            continue
        ride_data["Id"] = ride.id

        document_route_coordinates = fetch_route_coordinates(ride_data["Source"][0], ride_data["Source"][1], ride_data["Destination"][0], ride_data["Destination"][1])

        bearing2 = calculate_bearing(ride_data["Source"][0], ride_data["Source"][1], ride_data["Destination"][0], ride_data["Destination"][1])
        angle_difference = abs(bearing1 - bearing2)
        threshold = 50

        print("angle diff", angle_difference)
        if(angle_difference > threshold):
            continue

        source_proximity = False
        for lat, lng in document_route_coordinates:
            distance = geodesic((user_source_lat, user_source_lng), (lat, lng)).meters
            if distance <= 700:
                source_proximity = True
                break

        destination_proximity = False
        for lat, lng in document_route_coordinates:
            distance = geodesic((user_destination_lat, user_destination_lng), (lat, lng)).meters
            if distance <= 700:
                destination_proximity = True
                break
        if source_proximity and destination_proximity:
            ride_data = get_ride(ride.id)
            results.append({
                "Source": ride_data["Source"], 
                "Destination": ride_data["Destination"], 
                "Status": ride_data["Status"],
                "Id": ride_data["Id"],
                "Driver": ride_data["Driver"],
                "Vehicle":ride_data["Vehicle"],
                "JoinedRiders": ride_data["JoinedRiders"],
                "SeatingCapacity": ride_data["SeatingCapacity"],
                "CoRiders": ride_data["CoRiders"], 
            })
            count = count + 1
    
        if(count > 4):
            break
    
            

    return jsonify({'rides': results})

if __name__ == "__main__":
    app.run(debug=True)

