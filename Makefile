SHELL := /bin/bash

MODULES=slicedimage tests

test_srcs := $(shell find tests -name 'test_*.py')

test: lint
	pytest -v -n 8 --cov slicedimage

$(test_srcs): %.py :
	python -m unittest $(subst /,.,$*); \

lint:
	flake8 $(MODULES)

.PHONY : $(test_srcs)
