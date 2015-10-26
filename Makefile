project := tchannel

flake8 := flake8
pytest := PYTHONDONTWRITEBYTECODE=1 py.test --tb short \
	--cov-config .coveragerc --cov $(project) \
	--async-test-timeout=1 --timeout=30 tests

html_report := --cov-report html
test_args := --cov-report term-missing

TEST_HOST=127.0.0.1
TEST_PORT=0
TEST_LOG_FILE=test-server.log

.DEFAULT_GOAL := test-lint


env/bin/activate:
	virtualenv env

env_install: env/bin/activate
	./env/bin/pip install -r requirements-test.txt
	./env/bin/python setup.py develop

.PHONY: tox_install
tox_install:
	pip install -r requirements-test.txt
	python setup.py develop

.PHONY: install
install: clean
ifdef TOX_ENV
	make tox_install
else
	make env_install
endif

.PHONY: test_server
test_server:
	# TODO: use ${TEST_LOG_FILE}
	./env/bin/python examples/tchannel_server.py --host ${TEST_HOST} --port ${TEST_PORT}

.PHONY: test
test: clean
	$(pytest) $(test_args)

.PHONY: test_ci
test_ci: clean
	tox -e $(TOX_ENV) -- tests

.PHONY: testhtml
testhtml: clean
	$(pytest) $(html_report) && open htmlcov/index.html

.PHONY: clean
clean:
	rm -rf dist/
	rm -rf build/
	@find $(project) tests -name "*.pyc" -delete

.PHONY: lint
lint:
	@$(flake8) $(project) tests examples setup.py

.PHONY: test-lint
test-lint: test lint

.PHONY: docs
docs:
	make -C docs html

.PHONY: docsopen
docsopen: docs
	open docs/_build/html/index.html

.PHONY: vcr-thrift
vcr-thrift:
	make -C ./tchannel/testing/vcr all

.PHONY: gen_thrift
gen_thrift:
    thrift --gen py:new_style,slots,dynamic -out tests/data/generated tests/data/idls/ThriftTest.thrift
