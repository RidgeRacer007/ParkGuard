.PHONY: demo kind-up deploy
demo:
	docker compose up --build -d
	python -m simulator.run --scenario vehicle_fire
kind-up:
	kind create cluster --name parkguard
	docker build -t parkguard-api:local .
	kind load docker-image parkguard-api:local --name parkguard
deploy:
	kubectl apply -k k8s/overlays/local
