FROM ghcr.io/ishidawataru/xcvr-emu:latest

WORKDIR /sonic_platform_base

RUN --mount=type=bind,source=docker/sonic_py_common,target=/sonic_py_common,rw \
    cd /sonic_py_common && pip install .

RUN mkdir sonic_platform_base && touch sonic_platform_base/__init__.py

COPY docker/pyproject.toml .

RUN pip install '.[dev]'
