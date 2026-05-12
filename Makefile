.PHONY: test coverage coverage-html lint clean

test:
	python3 -m unittest discover tests -v || test $$? -eq 5

coverage:
	coverage run -m unittest discover tests
	coverage report -m

coverage-html:
	coverage run -m unittest discover tests
	coverage html
	@echo "Open htmlcov/index.html"

lint:
	python3 -m compileall -q scripts tests

clean:
	rm -rf .coverage htmlcov tests/__pycache__ scripts/__pycache__ scripts/kanban_zone/__pycache__
