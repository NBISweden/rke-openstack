
PROJECT_NAME := $(shell python setup.py --name)
PROJECT_VERSION := $(shell python setup.py --version)

SHELL := /bin/bash
DIM := \033[2m
RESET := \033[0m

.PHONY: all
all: lint uninstall install clean

.PHONY: install
install:
	@echo -e "installing $(PROJECT_NAME) $(PROJECT_VERSION)$(RESET)"
	@echo -e -n "$(DIM)"
	@pip install .
	@echo -e -n "$(RESET)"

.PHONY: uninstall
uninstall:
	@echo -e "uninstalling '$(PROJECT_NAME)'$(RESET)"
	-@pip uninstall -y $(PROJECT_NAME) 2> /dev/null

.PHONY: dist
dist:
	@echo -e "packaging $(PROJECT_NAME) $(PROJECT_VERSION)$(RESET)"
	@echo -e -n "$(DIM)"
	@python setup.py sdist --formats=zip --dist-dir=dist
	@echo -e -n "$(RESET)"

.PHONY: clean
clean:
	@echo -e "cleaning $(PROJECT_NAME) $(PROJECT_VERSION) repository$(RESET)"
	@rm -rf build dist $(PROJECT_NAME).egg-info

.PHONY: lint
lint:
	flake8 --ignore E226,D203,D212,D213,D404,D100,D104 rega.py setup.py
