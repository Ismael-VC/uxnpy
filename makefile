CC = gcc
CFLAGS = -O3 -Wall -fPIC
LDFLAGS = -shared

UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Linux)
	LIB_EXT = so
	LIB_NAME = libuxn.$(LIB_EXT)
	LDFLAGS += -fPIC
endif
ifeq ($(UNAME_S),Darwin)
	LIB_EXT = dylib
	LIB_NAME = libuxn.$(LIB_EXT)
	LDFLAGS = -dynamiclib
endif
ifeq ($(OS),Windows_NT)
	LIB_EXT = dll
	LIB_NAME = uxn.$(LIB_EXT)
	CC = gcc
endif

.PHONY: all clean install test build dist

all: $(LIB_NAME)

$(LIB_NAME): src/uxn/uxn.c src/uxn_wrapper.c
	mkdir -p build
	$(CC) $(CFLAGS) $(LDFLAGS) -Isrc -Ideps/uxn/src -o build/$@ src/uxn/uxn.c src/uxn_wrapper.c

clean:
	rm -rf src/__pycache__
	rm -rf tests/__pycache__
	rm -rf build

install: all
	pip install -e .

venv:
	python -m venv .venv
	source .venv/bin/activate

build: all
	python setup.py build

dist: all
	python setup.py sdist bdist_wheel

test: install
	python -m pytest tests/ -v

upload-test: dist
	python -m twine upload --repository testpypi dist/*

upload: dist
	python -m twine upload dist/*

dev-install:
	pip install -e ".[dev]"

format:
	black pyuxn tests
	isort pyuxn tests
