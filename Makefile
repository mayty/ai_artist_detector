include local.mk
CONTAINER_NAME = api-dev

run_interactive:
	docker compose run --rm --service-ports $(CONTAINER_NAME)

.PHONY: sh
sh:
	docker compose run --rm $(CONTAINER_NAME) sh -c "make ensure_venv && sh"

%:
	docker compose run --rm $(CONTAINER_NAME) make $@