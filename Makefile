.PHONY: install test show-config offline headless

install:
	python3 -m pip install -U pip
	python3 -m pip install -e ".[gui,dev]"

test:
	pytest -q

show-config:
	pyoranris show-config -c configs/offline_sim.yaml

offline:
	pyoranris run -c configs/offline_sim.yaml

headless:
	pyoranris run -c configs/offline_sim.yaml --headless
