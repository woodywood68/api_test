from flask import Flask, jsonify, make_response, render_template, redirect, url_for, g
import pickle
import json
import os
import requests
import sqlite3

PROJECT_ROOT = os.path.dirname(os.path.realpath(__file__))

DATABASE = os.path.join(PROJECT_ROOT, 'sequences.db')
    
app = Flask(__name__)

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def duplicate(sequence):
    try:
        db = get_db()
        cur = db.execute('INSERT INTO sequences VALUES(?)', [sequence])
        db.commit()
        cur.close()
        return False
    except sqlite3.IntegrityError:
        return True
    
@app.route("/sequences/")
def registered_sequences():
    return "Sequences: " + ", ".join([sequence['sequence'] for sequence in query_db('select * from sequences')])

@app.route("/sequence/<sequence>", methods=['POST'])
def check_sequence_exists(sequence):
    if duplicate(sequence):
        return make_response(response_generator("true", sequence),f"200 Message recieved {sequence}")
    else:
        return make_response(response_generator("false", sequence),f"200 Message recieved {sequence}")

@app.route("/clear/", methods=['PUT'])
def clear():
    db = get_db()
    cur = db.execute('DROP TABLE sequences')
    db.commit()
    cur.close()
    init_db()
    return make_response("200 Deduplication history cleared")

@app.route("/")
def register_sequence():
    return render_template('sequence_input.html')
    
@app.route("/clear_on_click/")
def clear_on_click():
    resp = requests.put('http://127.0.0.1:5000/clear/')
    return redirect(url_for('registered_sequences'))
    
def response_generator(exists, sequence):
    return jsonify({"body": {"duplicate": f"{exists}, {sequence}"}})
    
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)