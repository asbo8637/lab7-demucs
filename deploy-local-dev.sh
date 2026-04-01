#!/bin/sh
#
# You can use this script to launch Redis and minio on Kubernetes
# and forward their connections to your local computer. That means
# you can then work on your worker-server.py and rest-server.py
# on your local computer rather than pushing to Kubernetes with each change.
#
# To kill the port-forward processes us e.g. "ps augxww | grep port-forward"
# to identify the processes ids
#
kubectl apply -f redis/redis-deployment.yaml
kubectl apply -f redis/redis-service.yaml

kubectl apply -f rest/rest-deployment.yaml
kubectl apply -f rest/rest-service.yaml
kubectl apply -f logs/logs-deployment.yaml
kubectl apply -f worker/worker-deployment.yaml
kubectl apply -f minio/minio-deployment.yaml

# Wait for pods to start
echo "Sleeping for my little pods to start"
sleep 60

kubectl port-forward --address 0.0.0.0 service/redis 6379:6379 &

# Forward minio API and console
kubectl port-forward -n minio-ns --address 0.0.0.0 service/minio-service 9000:9000 &
kubectl port-forward -n minio-ns --address 0.0.0.0 service/minio-service 9001:9001 &

# Forward REST service
kubectl port-forward --address 0.0.0.0 service/rest-service 5000:5000 &