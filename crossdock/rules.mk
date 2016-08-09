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

.PHONY: crossdock_install_ci
crossdock_install_ci:
ifeq ($(TOX_ENV), crossdock)
	docker version
	@echo "Installing docker-compose $${DOCKER_COMPOSE_VERSION:?'DOCKER_COMPOSE_VERSION env not set'}"
	sudo rm -f /usr/local/bin/docker-compose
	curl -L https://github.com/docker/compose/releases/download/$${DOCKER_COMPOSE_VERSION}/docker-compose-`uname -s`-`uname -m` > docker-compose
	chmod +x docker-compose
	sudo mv docker-compose /usr/local/bin
	docker-compose version
else
	@echo Skipping installation of Docker
endif

.PHONY: crossdock_logs_ci
crossdock_logs_ci:
ifdef SHOULD_XDOCK
	docker-compose -f $(XDOCK_YAML) logs
endif
