NAME = coremark

COREMARK_DIR ?= coremark
COREMARK_SOURCE_DIR := $(abspath $(COREMARK_DIR))
COREMARK_GIT_URL ?= https://github.com/eembc/coremark.git
COREMARK_GIT_REF ?= main
COREMARK_ITERATIONS ?= 0
COREMARK_FLAGS_STR ?= -O2 -static -DITERATIONS=$(COREMARK_ITERATIONS)
COREMARK_MEM_LOCATION ?= Heap

COREMARK_CORE_SRCS = \
	$(COREMARK_DIR)/core_list_join.c \
	$(COREMARK_DIR)/core_main.c \
	$(COREMARK_DIR)/core_matrix.c \
	$(COREMARK_DIR)/core_state.c \
	$(COREMARK_DIR)/core_util.c
COREMARK_REQUIRED = $(COREMARK_CORE_SRCS) $(COREMARK_DIR)/coremark.h

SRCS = \
	$(COREMARK_CORE_SRCS) \
	portable/core_portme.c

CFLAGS += \
	-I$(APP_DIR)/$(COREMARK_DIR) \
	-I$(APP_DIR)/portable \
	-DFLAGS_STR='"$(COREMARK_FLAGS_STR)"' \
	-DMEM_LOCATION='"$(COREMARK_MEM_LOCATION)"' \
	-DITERATIONS=$(COREMARK_ITERATIONS)
LDFLAGS += -static

.PHONY: init check-coremark-source

init:
	@if [ -d "$(COREMARK_DIR)" ]; then \
		echo "$(COREMARK_DIR) already exists"; \
	elif [ -e "$(COREMARK_DIR)" ]; then \
		echo "$(COREMARK_DIR) exists but is not a directory" >&2; \
		exit 1; \
	else \
		git clone --depth 1 --single-branch --branch "$(COREMARK_GIT_REF)" "$(COREMARK_GIT_URL)" "$(COREMARK_DIR)"; \
	fi

check-coremark-source:
	@for file in $(COREMARK_REQUIRED); do \
		if [ ! -f "$$file" ]; then \
			echo "CoreMark source is missing under $(COREMARK_SOURCE_DIR)." >&2; \
			echo "Run: make -C $(APP_DIR) init" >&2; \
			exit 1; \
		fi; \
	done

UNIFIED_WORKLOAD_HOME ?= ../..
ifneq ($(filter init,$(MAKECMDGOALS)),init)
include $(UNIFIED_WORKLOAD_HOME)/Makefile.compile

$(OBJS): check-coremark-source
endif
