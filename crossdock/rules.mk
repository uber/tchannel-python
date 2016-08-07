XDOCK_YAML=crossdock/docker-compose.yml

.PHONY: clean-compile
clean-compile:
	find . -name '*.pyc' -exec rm {} \;

.PHONY: docker
docker: clean-compile
	docker build -f crossdock/Dockerfile -t jaeger-client-python .

.PHONY: crossdock
crossdock:
	docker-compose -f $(XDOCK_YAML) kill python
	docker-compose -f $(XDOCK_YAML) rm -f python
	docker-compose -f $(XDOCK_YAML) build python
	docker-compose -f $(XDOCK_YAML) run crossdock

.PHONY: crossdock-fresh
crossdock-fresh:
	docker-compose -f $(XDOCK_YAML) kill
	docker-compose -f $(XDOCK_YAML) rm --force
	docker-compose -f $(XDOCK_YAML) pull
	docker-compose -f $(XDOCK_YAML) build
	docker-compose -f $(XDOCK_YAML) run crossdock

.PHONY: crossdock-logs
crossdock-logs:
	docker-compose -f $(XDOCK_YAML) logs
