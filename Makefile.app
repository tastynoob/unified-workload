UNIFIED_WORKLOAD_HOME ?= $(abspath $(dir $(lastword $(MAKEFILE_LIST))))

ifeq ($(NAME),)
$(error NAME is not defined)
endif

APP_DIR ?= $(shell pwd)
INC_DIR += $(APP_DIR)/include/
DST_DIR ?= $(APP_DIR)/build/
APP ?= $(DST_DIR)/$(NAME)

.DEFAULT_GOAL = $(APP)

.PHONY: clean

clean:
	rm -rf $(DST_DIR)
