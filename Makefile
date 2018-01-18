#!/usr/bin/make -f
# -*- makefile -*-
#
# Signal Protocol Python library
# Makefile - Build system
#
# Copyright (c) 2017 Catalyst.net Ltd
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


##############################


#
# Makefile arguments
# ------------------
#
# Any of the parameters in this Makefile can be overridden on the command line.
# Some variables are designed to be used like this, to provide optional
# parameters.
#
# Use them like so:
#   $ make install <KEY>=<VALUE>
#
# Examples:
# - install pysignal to a virtualenv and configuration in /opt,
#   with a systemd unit installed to standard directories:
#     $ make install systemd-install \
#       VIRTUALENV="/opt/venv/pysignal" CONFIG_DIR="/opt/pysignal"
#


##############################


#
## Build system parameters.
#

# Parameters that can be changed.
ifdef VIRTUALENV
PREFIX = $(VIRTUALENV)
else
PREFIX = /usr/local
endif

TEST_PRESERVE_TMP_DIR = 0


##############################


#
## setup.py parameters.
#

ifdef PREFIX
SETUP_PY_PREFIX = --prefix=$(PREFIX)
endif

ifdef INSTALL_LIB
SETUP_PY_INSTALL_LIB = --install-lib=$(INSTALL_LIB)
endif


##############################


#
## Build system files and directories.
#

SETUP_PY = setup.py

SRC_DIR = src

TEST_SRC_DIR = tests
TEST_TMP_DIR = .tests


##############################


#
## Commands.
#

# Detect usable Python command, if not defined by the user.
ifndef PYTHON
PYTHON_MAJOR_VER = $(shell python3 -V | sed 's:^Python \([0-9][0-9]*\)\..*$$:\1:')
PYTHON_MINOR_VER = $(shell python3 -V | sed 's:^Python [0-9][0-9]*\.\([0-9][0-9]*\)\..*$$:\1:')
ifeq ($(shell test $(PYTHON_MAJOR_VER) -eq 3 -a $(PYTHON_MINOR_VER) -ge 4 && echo true), true)
PYTHON = $(shell which python3)
endif
endif

ifndef PYTHON
PYTHON = $(shell which python3.5)
endif

ifndef PYTHON
PYTHON = $(shell which python3.4)
endif

ifndef PYTHON
$(error pysignal only supports Python >= 3.4.0)
endif

# Python tools.
PYLINT = pylint
PIP = pip3
# An alternative to this if the default doesn't work:
# PIP = $(PYTHON) -m pip

# System commands.
FIND    = find
INSTALL = install
RM      = rm -f
RMDIR   = rm -rf


##############################


#
## Targets.
#

all:
	@echo "pysignal make targets:"
	@echo "  lint - run pylint code quality check"
	@echo "  test - run unit tests"
	@echo
	@echo "  sdist - build Python source distribution"
	@echo "  bdist_wheel - build Python binary wheel distribution"
	@echo
	@echo "  install - build and install to local system"
	@echo
	@echo "  uninstall - uninstall from local system"
	@echo "  clean - clean build files"
	@echo "See 'Makefile' for more details."


lint:
	$(PYLINT) $(SRC_DIR)/pysignal --disable=duplicate-code 2>&1 | tee make-lint.log
	@echo "pylint output written to make-lint.log"


test:
	$(PYTHON) $(TEST_SRC_DIR)/tests/__init__.py
	test -z $(TEST_PRESERVE_TMP_DIR) && rm -rf $(TEST_TMP_DIR) || true


test-lint:
	$(PYLINT) $(TEST_SRC_DIR)/tests --disable=duplicate-code 2>&1 | tee make-test-lint.log
	@echo "pylint output written to make-test-lint.log"


sdist:
	$(PYTHON) $(SETUP_PY) sdist


bdist_wheel:
	$(PYTHON) $(SETUP_PY) bdist_wheel


install:
	$(PYTHON) $(SETUP_PY) install $(SETUP_PY_PREFIX) $(SETUP_PY_INSTALL_LIB) $(SETUP_PY_INSTALL_SCRIPTS) $(SETUP_PY_INSTALL_DATA)


%: %.in .FORCE
	$(PYTHON) $(TEMPLATE_PROCESS_PY) $< $@ $(foreach KEY,$(PARAMS),$(KEY)=$($(KEY)))


uninstall:
	$(PIP) uninstall -y pysignal


clean:
	$(RM) make-lint.log
	$(RMDIR) .tests
	$(RMDIR) build
	$(RMDIR) dist
	$(RMDIR) src/pysignal.egg-info
	for d in $(shell $(FIND) -name '__pycache__'); do \
		$(RMDIR) $$d; \
	done


.FORCE:

.PHONY: all lint test sdist bdist_wheel install uninstall clean .FORCE
