from flask import render_template,jsonify
from app import app
from app.firebase import db

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/test-firebase')
def test_firebase():
    # Write data to Firestore
    doc_ref = db.collection('test').document('example')
    doc_ref.set({
        'name': 'Zensprout',
        'message': 'Firebase is working!'
    })

    # Read data from Firestore
    doc = doc_ref.get()
    if doc.exists:
        return jsonify(doc.to_dict())
    else:
        return jsonify({'error': 'Document not found'}), 404