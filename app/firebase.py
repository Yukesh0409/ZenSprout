import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase
cred = credentials.Certificate("firebase-key.json")  # Download the service account key from Firebase
firebase_admin.initialize_app(cred)

# Get Firestore client
db = firestore.client()