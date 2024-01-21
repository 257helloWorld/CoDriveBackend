# app.py
import asyncio
from flask import Flask, jsonify, request
import googlemaps
from datetime import datetime
import polyline
from firebase_admin import firestore, initialize_app, credentials
from config import API_KEY

# from apscheduler.schedulers.background import BackgroundScheduler
gmaps = googlemaps.Client(key=API_KEY)

app = Flask(__name__)
cred = credentials.Certificate("firebase-admin.json")
initialize_app(cred)
db = firestore.client()
userRef = db.collection("Users")
vehicleRef = db.collection("Vehicles")
reviewRef = db.collection("Reviews")

# scheduler = BackgroundScheduler()


def printHello():
	print("Hello")
	
# scheduler.add_job(printHello, 'interval', seconds=10)

# scheduler.start()

@app.route('/')
def hello():
    return {"members":["member1","member2","member3"]}

def get_vehicle(vehicle_id):
    docRef = vehicleRef.document(vehicle_id)
    doc = docRef.get()
    if doc.exists:
         vehicle = doc.to_dict()
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
               "ProfileUrl": data['ProfileUrl']
          }
     else:
          return None

def get_review(review_id):
    docRef = reviewRef.document(review_id)
    doc = docRef.get()
    if doc.exists:
        data = doc.to_dict()
        data["Reviewer"] = get_reviewer(data["Reviewer"].get().id)
        return data
    else:
         return None


@app.route('/get_user', methods=['GET'])
def get_user():
    docRef = userRef.document(request.args.get('userId'))
    doc = docRef.get()
    if doc.exists:
        user_data = doc.to_dict()
        if user_data["Reviews"]:
            user_data["Reviews"] = [get_review(ref.get().id) for ref in user_data["Reviews"]]
        if user_data["Vehicles"]:
            user_data["Vehicles"] = [get_vehicle(ref.get().id) for ref in user_data["Vehicles"]]
        return jsonify(user_data)
    else:
        print("No such document!")
        return None

@app.route('/get_directions')
def get_directions():
    try:
        # Get source and destination
        source_lat = float(request.args.get('s1'))
        source_lng = float(request.args.get('s2'))
        destination_lat = float(request.args.get('d1'))
        destination_lng = float(request.args.get('d2 '))

        source_str = f"{source_lat},{source_lng}"
        destination_str = f"{destination_lat},{destination_lng}"

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

    except Exception as e:
        # Handle error
        return jsonify({'status': 'error', 'message': str(e)})
    
if __name__ == "__main__":
	app.run(debug=True)

