NAME = coremark

COREMARK_DIR ?= coremark
COREMARK_SOURCE_DIR := $(abspath $(COREMARK_DIR))
COREMARK_GIT_URL ?= https://github.com/eembc/coremark.git
COREMARK_GIT_REF ?= main
ifeq ($(BAREMETAL),1)
COREMARK_ITERATIONS ?= 30000
COREMARK_CHECKPOINT ?= 0
COREMARK_FLAGS_STR ?= -O3 -march=armv9-a -DITERATIONS=$(COREMARK_ITERATIONS)
COREMARK_MEM_LOCATION ?= Static
COREMARK_PORTABLE_DIR := portable-bare
else
COREMARK_ITERATIONS ?= 0
COREMARK_FLAGS_STR ?= -O2 -static -DITERATIONS=$(COREMARK_ITERATIONS)
COREMARK_MEM_LOCATION ?= Heap
COREMARK_PORTABLE_DIR := portable
endif

COREMARK_UPSTREAM_SRCS = \
	$(COREMARK_DIR)/core_list_join.c \
	$(COREMARK_DIR)/core_main.c \
	$(COREMARK_DIR)/core_matrix.c \
	$(COREMARK_DIR)/core_state.c \
	$(COREMARK_DIR)/core_util.c
COREMARK_CORE_SRCS = \
	$(COREMARK_DIR)/core_list_join.c \
	$(COREMARK_DIR)/core_matrix.c \
	$(COREMARK_DIR)/core_state.c \
	$(COREMARK_DIR)/core_util.c
ifeq ($(BAREMETAL),1)
COREMARK_MAIN_PATCH := $(CURDIR)/portable-bare/core_main.patch
COREMARK_PATCHED_MAIN := $(DST_DIR)/generated/core_main.c
COREMARK_PATCHED_MAIN_OBJ := $(DST_DIR)/generated/core_main.o
EXTRA_OBJS += $(COREMARK_PATCHED_MAIN_OBJ)
else
COREMARK_CORE_SRCS += $(COREMARK_DIR)/core_main.c
endif
COREMARK_REQUIRED = $(COREMARK_UPSTREAM_SRCS) $(COREMARK_DIR)/coremark.h

SRCS = \
	$(COREMARK_CORE_SRCS) \
	$(COREMARK_PORTABLE_DIR)/core_portme.c

CFLAGS += \
	-I$(APP_DIR)/$(COREMARK_DIR) \
	-I$(APP_DIR)/$(COREMARK_PORTABLE_DIR) \
	-DFLAGS_STR='"$(COREMARK_FLAGS_STR)"' \
	-DMEM_LOCATION='"$(COREMARK_MEM_LOCATION)"' \
	-DITERATIONS=$(COREMARK_ITERATIONS) \
	-DCOREMARK_CHECKPOINT=$(COREMARK_CHECKPOINT)
ifneq ($(BAREMETAL),1)
LDFLAGS += -static
endif

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

ifeq ($(BAREMETAL),1)
$(COREMARK_PATCHED_MAIN): $(COREMARK_DIR)/core_main.c $(COREMARK_MAIN_PATCH)
	@mkdir -p $(dir $@)
	@cp $< $@
	@patch --silent $@ < $(COREMARK_MAIN_PATCH)

$(COREMARK_PATCHED_MAIN_OBJ): $(COREMARK_PATCHED_MAIN) check-coremark-source
	@echo + CC $<
	@$(CC) $(CFLAGS) -c -o $@ $<
endif
endif
