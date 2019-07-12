SHELL := /bin/bash

MODULES=slicedimage tests

test_srcs := $(shell find tests -name 'test_*.py')

test: lint
	pytest -v -n 8 --cov slicedimage

$(test_srcs): %.py :
	python -m unittest $(subst /,.,$*); \

lint:   lint-non-init lint-init

lint-non-init:
	flake8 --ignore 'E252, E301, E302, E305, E401, W503, E731, F811' --exclude='*__init__.py' $(MODULES)

lint-init:
	flake8 --ignore 'E252, E301, E302, E305, E401, F401, W503, E731, F811' --filename='*__init__.py' $(MODULES)

.PHONY : $(test_srcs)
