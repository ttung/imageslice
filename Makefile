SHELL := /bin/bash

MODULES=slicedimage tests

lint:
	flake8 $(MODULES)

test_srcs := $(shell find tests -name 'test_*.py')

test: SLICEDIMAGE_COVERAGE := 1
test: $(test_srcs) lint
	coverage combine
	rm -f .coverage.*

$(test_srcs): %.py :
	if [ "$(SLICEDIMAGE_COVERAGE)" == 1 ]; then \
		SLICEDIMAGE_COVERAGE=1 coverage run -p --source=slicedimage -m unittest $(subst /,.,$*); \
	else \
		python -m unittest $(subst /,.,$*); \
	fi

.PHONY : $(test_srcs)
