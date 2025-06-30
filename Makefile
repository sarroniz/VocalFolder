SHELL := /bin/bash

run:
	@source /opt/homebrew/Caskroom/miniforge/base/etc/profile.d/conda.sh && \
	conda activate vocalfolder && \
	PYTHONPATH=. python app/main.py

lint:
	@ruff check app

format:
	@ruff format app

clean:
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete

debug:
	@source /opt/homebrew/Caskroom/miniforge/base/etc/profile.d/conda.sh && \
	conda activate vocalfolder && \
	PYTHONPATH=. PYTHONDEBUG=1 python app/main.py --debug