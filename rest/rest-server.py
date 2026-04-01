import os
import base64
import hashlib
from flask import Flask, request, jsonify, send_file, Response
import redis
import jsonpickle
from io import BytesIO
from minio import Minio

app = Flask(__name__)


r = redis.Redis(host=os.environ.get('REDIS_HOST', 'localhost'), port=6379, db=0)

minio_host = os.environ.get('MINIO_HOST', 'localhost:9000')
minio_client = Minio(minio_host, access_key='rootuser', secret_key='rootpass123', secure=False)

QUEUE_KEY = 'toWorker'
LOG_KEY = 'logging'

@app.route('/', methods=['GET'])
def hello():
    return '<p>Music Separation Server</p>'

@app.route('/apiv1/separate', methods=['POST'])
def separate():
    #grab json data
    data = request.get_json()
    mp3 = data.get('mp3')
    model = data.get('model')
    callback = data.get('callback')
    if not mp3:
        return jsonify({'error': 'Missing mp3'}), 400
    
    #Hash the song for identifier. 
    songhash = hashlib.sha224(mp3.encode()).hexdigest()
    job = {'songhash': songhash, 'mp3': mp3, 'model': model, 'callback': callback}
    r.lpush(QUEUE_KEY, jsonpickle.encode(job))
    return jsonify({'hash': songhash, 'reason': 'Song enqueued for separation'})

@app.route('/apiv1/queue/', methods=['GET'])
def get_queue():
    queue = r.lrange(QUEUE_KEY, 0, -1)
    #hehe pickle
    hashes = [jsonpickle.decode(item)['songhash'] for item in queue]
    return jsonify({'queue': hashes})

@app.route('/apiv1/track/<songhash>/<track>', methods=['GET'])
def get_track(songhash, track):
    object_name = f'{songhash}-{track}'
    try:
        data = minio_client.get_object('output', object_name)
        return Response(data.read(), mimetype='audio/mpeg')
    except Exception:
        return jsonify({'error': 'Track not found'}), 404

@app.route('/apiv1/remove/<songhash>/<track>', methods=['GET', 'DELETE'])
def remove_track(songhash, track):
    object_name = f'{songhash}-{track}'
    try:
        minio_client.remove_object('output', object_name)
        return jsonify({'status': f'{object_name} removed'})
    except Exception:
        return jsonify({'error': 'Track not found'}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
