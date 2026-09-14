build-ApiFunction:
	mkdir -p $(ARTIFACTS_DIR)/backend
	cp *.py rds-ca.pem $(ARTIFACTS_DIR)/backend/
	python -m pip install -r requirements.lock.txt --target $(ARTIFACTS_DIR)

build-FreshnessFunction: build-ApiFunction
