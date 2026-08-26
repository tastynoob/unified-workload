NAME := spec

UNIFIED_WORKLOAD_HOME ?= ../..
DST_DIR ?= $(CURDIR)/build
APP ?= $(DST_DIR)/$(NAME)

SPEC_BENCHMARK ?= 401.bzip2
SPEC_BENCHSPEC ?=
SPEC_ROOT ?= $(abspath $(SPEC_BENCHSPEC)/..)
SPEC_SUITE ?= auto
SPEC_SIZE ?= test
SPEC_ARGS ?=

ifeq ($(strip $(CROSS_COMPILE)),)
$(error CROSS_COMPILE is not defined)
endif
ifeq ($(strip $(SPEC_BENCHSPEC)),)
$(error SPEC_BENCHSPEC must point to a CPU2006 or CPU2017 benchspec directory)
endif

SPEC_CPU2006_BENCH_DIR := $(abspath $(SPEC_BENCHSPEC)/CPU2006/$(SPEC_BENCHMARK))
SPEC_CPU2017_BENCH_DIR := $(abspath $(SPEC_BENCHSPEC)/CPU/$(SPEC_BENCHMARK))

ifeq ($(SPEC_SUITE),auto)
ifneq ($(wildcard $(SPEC_CPU2017_BENCH_DIR)/Spec/object.pm),)
SPEC_SUITE_RESOLVED := 2017
else ifneq ($(wildcard $(SPEC_CPU2006_BENCH_DIR)/Spec/object.pm),)
SPEC_SUITE_RESOLVED := 2006
else
$(error benchmark $(SPEC_BENCHMARK) was not found under CPU/ or CPU2006/)
endif
else ifeq ($(SPEC_SUITE),2017)
SPEC_SUITE_RESOLVED := 2017
else ifeq ($(SPEC_SUITE),2006)
SPEC_SUITE_RESOLVED := 2006
else
$(error SPEC_SUITE must be auto, 2006, or 2017)
endif

ifeq ($(SPEC_SUITE_RESOLVED),2017)
SPEC_BENCH_DIR := $(SPEC_CPU2017_BENCH_DIR)
else
SPEC_BENCH_DIR := $(SPEC_CPU2006_BENCH_DIR)
endif

SPEC_OBJECT_PM := $(SPEC_BENCH_DIR)/Spec/object.pm
SPEC_SOURCE_DIR := $(SPEC_BENCH_DIR)/src
SPEC_WORK_DIR := $(abspath $(DST_DIR)/spec/$(SPEC_BENCHMARK))
SPEC_STAGE_DIR := $(SPEC_WORK_DIR)/src
SPEC_OBJ_DIR := $(SPEC_WORK_DIR)/obj
SPEC_PREP_DIR := $(SPEC_WORK_DIR)/preprocessed
SPEC_MOD_DIR := $(SPEC_WORK_DIR)/modules
SPEC_METADATA_MK := $(SPEC_WORK_DIR)/metadata.mk
SPEC_RUNTIME_DIR := $(SPEC_WORK_DIR)/runtime
SPEC_RUNTIME_CONFIG_C := $(SPEC_RUNTIME_DIR)/spec_runtime_config.c
SPEC_RUNTIME_CONFIG_OBJ := $(SPEC_RUNTIME_DIR)/spec_runtime_config.o
SPEC_PROFILE_OBJ := $(SPEC_RUNTIME_DIR)/profile_runtime.o
SPEC_INPUT_STAGE_DIR := $(SPEC_WORK_DIR)/inputs

export SPEC_ARGS

ifeq ($(wildcard $(SPEC_OBJECT_PM)),)
$(error CPU$(SPEC_SUITE_RESOLVED) benchmark metadata does not exist: $(SPEC_OBJECT_PM))
endif

.DEFAULT_GOAL := all

$(SPEC_METADATA_MK): metadata.py $(SPEC_OBJECT_PM)
	@mkdir -p $(dir $@)
	@python3 metadata.py \
		--suite $(SPEC_SUITE_RESOLVED) \
		--benchmark $(SPEC_BENCHMARK) \
		--bench-dir $(SPEC_BENCH_DIR) \
		--object-pm $(SPEC_OBJECT_PM) \
		--source-dir $(SPEC_SOURCE_DIR) \
		--output $@

include $(SPEC_METADATA_MK)

ifneq ($(origin SPEC_INPUT_DIR),undefined)
SPEC_INPUT_DIRS ?= $(SPEC_INPUT_DIR)
else
SPEC_INPUT_BENCH_DIR := $(if \
	$(wildcard $(SPEC_BENCH_DIR)/data/$(SPEC_SIZE)/input),\
	$(SPEC_BENCH_DIR),$(SPEC_SOURCE_BENCH_DIR))
SPEC_INPUT_DIRS ?= $(wildcard $(SPEC_INPUT_BENCH_DIR)/data/all/input) \
	$(SPEC_INPUT_BENCH_DIR)/data/$(SPEC_SIZE)/input
endif

CC := $(CROSS_COMPILE)gcc
CXX := $(CROSS_COMPILE)g++
FC := $(CROSS_COMPILE)gfortran

SPEC_OPTIMIZE ?= -O3
ifeq ($(SPEC_SUITE_RESOLVED),2017)
SPEC_COMMON_FLAGS := -MMD -MP -DSPEC -DNDEBUG -D_FILE_OFFSET_BITS=64 \
	-fno-strict-aliasing -DSPEC_LP64 -DSPEC_AUTO_SUPPRESS_OPENMP
SPEC_COMMON_CFLAGS := -std=c99
SPEC_COMMON_CXXFLAGS := -std=c++03
else
SPEC_COMMON_FLAGS := -MMD -MP -DSPEC_CPU -DNDEBUG -D_FILE_OFFSET_BITS=64 \
	-fno-strict-aliasing -DSPEC_CPU_LP64
endif
SPEC_COMPAT_CFLAGS := -Wno-implicit-int -Wno-int-conversion \
	-Wno-incompatible-pointer-types -Wno-implicit-function-declaration

SPEC_PLATFORM_CFLAGS := $(SPEC_OPTIMIZE)
SPEC_PLATFORM_CXXFLAGS := $(SPEC_OPTIMIZE)
SPEC_PLATFORM_FFLAGS := $(SPEC_OPTIMIZE)
SPEC_PLATFORM_LDFLAGS := -static
SPEC_SIMTRAP_INCLUDE := $(abspath $(UNIFIED_WORKLOAD_HOME)/plat/qemu-minivirt-aarch64-gcpt/include)

CFLAGS := $(SPEC_PLATFORM_CFLAGS) $(SPEC_COMMON_FLAGS) $(SPEC_COMMON_CFLAGS) \
	$(SPEC_COMPAT_CFLAGS) \
	$(SPEC_BENCH_FLAGS) $(SPEC_EXTRA_CFLAGS) $(SPEC_BENCH_CFLAGS)
CXXFLAGS := $(SPEC_PLATFORM_CXXFLAGS) $(SPEC_COMMON_FLAGS) \
	$(SPEC_COMMON_CXXFLAGS) \
	$(SPEC_BENCH_FLAGS) $(SPEC_EXTRA_CXXFLAGS) $(SPEC_BENCH_CXXFLAGS)
FFLAGS := $(SPEC_PLATFORM_FFLAGS) $(SPEC_COMMON_FLAGS) -fno-strict-aliasing \
	-J$(SPEC_MOD_DIR) -I$(SPEC_MOD_DIR) $(SPEC_BENCH_FFLAGS) \
	$(SPEC_EXTRA_FFLAGS)
LDFLAGS := $(SPEC_PLATFORM_LDFLAGS) \
	$(SPEC_BENCH_LDFLAGS) $(SPEC_EXTRA_LDFLAGS)

ifeq ($(SPEC_LINK_LANGUAGE),CXX)
SPEC_LD := $(CXX)
else ifeq ($(SPEC_LINK_LANGUAGE),FC)
SPEC_LD := $(FC)
else
SPEC_LD := $(CC)
endif

SPEC_OBJS := $(addprefix $(SPEC_OBJ_DIR)/,$(addsuffix .o,$(basename $(SPEC_SOURCES))))
SPEC_STAGED_SOURCES := $(addprefix $(SPEC_STAGE_DIR)/,$(SPEC_SOURCES))
SPEC_DEPS := $(SPEC_OBJS:.o=.d)

.PHONY: all spec-stage spec-runtime spec-inputs clean FORCE
all: $(APP) spec-inputs

spec-stage:
	@python3 sync_source.py --source $(SPEC_SOURCE_DIR) --destination $(SPEC_STAGE_DIR)

$(SPEC_STAGED_SOURCES): | spec-stage
	@test -f $@

spec-runtime:
	@python3 prepare_runtime.py \
		--executable $(SPEC_EXE_NAME) \
		--output $(SPEC_RUNTIME_CONFIG_C)

$(SPEC_RUNTIME_CONFIG_C): FORCE | spec-runtime
	@test -f $@

$(SPEC_RUNTIME_CONFIG_OBJ): $(SPEC_RUNTIME_CONFIG_C)
	@echo + CC $<
	@mkdir -p $(dir $@)
	@$(CC) $(SPEC_PLATFORM_CFLAGS) $(SPEC_COMMON_FLAGS) -c -o $@ $<

$(SPEC_PROFILE_OBJ): profile_runtime.c
	@echo + CC $<
	@mkdir -p $(dir $@)
	@$(CC) $(SPEC_PLATFORM_CFLAGS) $(SPEC_COMMON_FLAGS) \
		-I$(SPEC_SIMTRAP_INCLUDE) -fno-lto -c -o $@ $<

spec-inputs:
	@rm -rf $(SPEC_INPUT_STAGE_DIR)
	@mkdir -p $(SPEC_INPUT_STAGE_DIR)
	@for input_dir in $(SPEC_INPUT_DIRS); do \
		if [ -d "$$input_dir" ]; then \
			cp -a "$$input_dir"/. "$(SPEC_INPUT_STAGE_DIR)/"; \
		fi; \
	done

$(SPEC_OBJ_DIR)/%.o: $(SPEC_STAGE_DIR)/%.c
	@echo + CC $<
	@mkdir -p $(dir $@)
	@cd $(SPEC_STAGE_DIR) && $(CC) $(CFLAGS) -c -o $(abspath $@) $(abspath $<)

$(SPEC_OBJ_DIR)/%.o: $(SPEC_STAGE_DIR)/%.C
	@echo + CXX $<
	@mkdir -p $(dir $@)
	@cd $(SPEC_STAGE_DIR) && $(CXX) $(CXXFLAGS) -c -o $(abspath $@) $(abspath $<)

$(SPEC_OBJ_DIR)/%.o: $(SPEC_STAGE_DIR)/%.cc
	@echo + CXX $<
	@mkdir -p $(dir $@)
	@cd $(SPEC_STAGE_DIR) && $(CXX) $(CXXFLAGS) -c -o $(abspath $@) $(abspath $<)

$(SPEC_OBJ_DIR)/%.o: $(SPEC_STAGE_DIR)/%.cpp
	@echo + CXX $<
	@mkdir -p $(dir $@)
	@cd $(SPEC_STAGE_DIR) && $(CXX) $(CXXFLAGS) -c -o $(abspath $@) $(abspath $<)

$(SPEC_OBJ_DIR)/%.o: $(SPEC_STAGE_DIR)/%.cxx
	@echo + CXX $<
	@mkdir -p $(dir $@)
	@cd $(SPEC_STAGE_DIR) && $(CXX) $(CXXFLAGS) -c -o $(abspath $@) $(abspath $<)

$(SPEC_OBJ_DIR)/%.o: $(SPEC_STAGE_DIR)/%.f
	@echo + FC $<
	@mkdir -p $(dir $@) $(SPEC_MOD_DIR)
	@cd $(SPEC_STAGE_DIR) && $(FC) $(FFLAGS) -c -o $(abspath $@) $(abspath $<)

$(SPEC_OBJ_DIR)/%.o: $(SPEC_STAGE_DIR)/%.f90
	@echo + FC $<
	@mkdir -p $(dir $@) $(SPEC_MOD_DIR)
	@cd $(SPEC_STAGE_DIR) && $(FC) $(FFLAGS) -c -o $(abspath $@) $(abspath $<)

$(APP): $(SPEC_OBJS) $(SPEC_RUNTIME_CONFIG_OBJ) $(SPEC_PROFILE_OBJ)
	@echo + LD $@
	@mkdir -p $(dir $@)
	@$(SPEC_LD) $(LDFLAGS) -Wl,--wrap=main -o $@ \
		$(SPEC_PROFILE_OBJ) $(SPEC_RUNTIME_CONFIG_OBJ) \
		$(SPEC_OBJS) $(SPEC_BENCH_LIBS)

clean:
	@rm -rf $(SPEC_WORK_DIR) $(APP)

FORCE:

-include $(SPEC_DEPS)
