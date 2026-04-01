import os
import base64
import redis
import jsonpickle
import time
import subprocess
import glob
import shutil
from minio import Minio

QUEUE_KEY = 'toWorker'
LOG_KEY = 'logging'
OUTPUT_DIR = 'output'

os.makedirs(OUTPUT_DIR, exist_ok=True)

r = redis.Redis(host=os.environ.get('REDIS_HOST', 'localhost'), port=6379, db=0)

minio_host = os.environ.get('MINIO_HOST', 'localhost:9000')
minio_client = Minio(minio_host, access_key='rootuser', secret_key='rootpass123', secure=False)

# set up buckets if they dont already exist
for bucket in ['queue', 'output']:
    if not minio_client.bucket_exists(bucket):
        minio_client.make_bucket(bucket)

r.lpush(LOG_KEY, 'worker is up, waiting for stuff to do')

while True:
    job_data = r.brpop(QUEUE_KEY, timeout=5)
    if not job_data:
        time.sleep(1)
        continue
    _, job_raw = job_data
    job = jsonpickle.decode(job_raw)
    songhash = job['songhash']
    mp3_b64 = job['mp3']
    model = job.get('model') or 'htdemucs'
    r.lpush(LOG_KEY, f'Processing job {songhash} with model {model}')
    mp3_bytes = base64.b64decode(mp3_b64)
    mp3_path = os.path.join(OUTPUT_DIR, f'{songhash}.mp3')
    with open(mp3_path, 'wb') as f:
        f.write(mp3_bytes)
    demucs_cmd = [
        'demucs',
        '-n', model,
        '-d', 'cpu',
        '-o', os.path.abspath(OUTPUT_DIR),
        os.path.abspath(mp3_path)
    ]
    try:
        r.lpush(LOG_KEY, f'running demucs on {songhash}')
        subprocess.run(demucs_cmd, check=True)


        # grab the separated tracks and throw them in minio
        track_dir = os.path.join(OUTPUT_DIR, model, songhash)
        for track_file in glob.glob(os.path.join(track_dir, '*.wav')):
            track_name = os.path.basename(track_file).replace('.wav', '.mp3')
            object_name = f'{songhash}-{track_name}'
            minio_client.fput_object('output', object_name, track_file)
            r.lpush(LOG_KEY, f'uploaded {object_name}')
        
        # cleanup so we dont fill up disk
        os.remove(mp3_path)
        shutil.rmtree(track_dir, ignore_errors=True)
        r.lpush(LOG_KEY, f'done with {songhash}')
    except Exception as e:
        r.lpush(LOG_KEY, f'something went wrong with {songhash}: {e}')
