.PHONY: install preprocess backend frontend ai-labels upload clean

CSV ?= ~/Downloads/telegram.csv
ARTIFACTS ?= ./artifacts
TOP_N ?= 30

install:
	pip install -r data_processing/requirements.txt
	pip install -r backend/requirements.txt
	cd frontend && npm install

preprocess:
	python3 -m data_processing.scripts.ingest_and_compute --csv $(CSV) --output $(ARTIFACTS) --top-n $(TOP_N)

ai-labels:
	python3 -m data_processing.scripts.generate_ai_labels --artifacts $(ARTIFACTS)

backend:
	cd backend && ARTIFACTS_LOCAL_PATH=../$(ARTIFACTS) uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

upload:
	python3 -m data_processing.scripts.upload_to_s3 --artifacts $(ARTIFACTS)

clean:
	rm -rf artifacts/ __pycache__ */__pycache__ */*/__pycache__ */*/*/__pycache__
