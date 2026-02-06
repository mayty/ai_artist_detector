include local.mk
CONTAINER_NAME = api-dev
COMMANDS_CONTAINER_NAME = commands

run_interactive:
	docker compose run --rm --service-ports $(CONTAINER_NAME)

.PHONY: sh
sh:
	docker compose run --rm $(COMMANDS_CONTAINER_NAME) sh -c sh

%:
	docker compose run --rm $(COMMANDS_CONTAINER_NAME) make $@
