DOCKER_CMD ?= docker
SONIC_XCVR_IMAGE ?= sonic-xcvr

.PHONY: test_sonic_xcvr_with_emu
test_sonic_xcvr_with_emu:
	$(DOCKER_CMD) build -f docker/Dockerfile -t $(SONIC_XCVR_IMAGE) .
	$(DOCKER_CMD) run -it \
	-v `pwd`/docker/pyproject.toml:/sonic_platform_base/pyproject.toml \
	-v `pwd`/sonic_platform_base:/sonic_platform_base/sonic_platform_base \
	-v `pwd`/docker/tests:/sonic_platform_base/tests \
	-w /sonic_platform_base \
	$(SONIC_XCVR_IMAGE) \
	python -m pytest -v .
