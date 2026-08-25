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
SPEC_STDIN ?=
SPEC_EMBED_INPUTS ?= 1

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
SPEC_BARE_IO_OBJ := $(SPEC_RUNTIME_DIR)/bare_io.o
SPEC_INPUT_BIN := $(SPEC_RUNTIME_DIR)/spec-inputs.bin
SPEC_INPUT_OBJ := $(SPEC_RUNTIME_DIR)/spec-inputs.o

export SPEC_ARGS
export SPEC_STDIN

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

ifeq ($(BAREMETAL),1)
SPEC_COMMON_FLAGS += -DSPEC_BAREMETAL
SPEC_PLATFORM_CFLAGS := $(BARE_CFLAGS)
SPEC_PLATFORM_CXXFLAGS := $(BARE_CXXFLAGS)
SPEC_PLATFORM_FFLAGS := $(filter-out -ffreestanding,$(BARE_CFLAGS))
ifneq ($(filter -mcpu=%,$(SPEC_EXTRA_CFLAGS)),)
SPEC_PLATFORM_CFLAGS := $(filter-out -march=%,$(SPEC_PLATFORM_CFLAGS))
endif
ifneq ($(filter -mcpu=%,$(SPEC_EXTRA_CXXFLAGS)),)
SPEC_PLATFORM_CXXFLAGS := $(filter-out -march=%,$(SPEC_PLATFORM_CXXFLAGS))
endif
ifneq ($(filter -mcpu=%,$(SPEC_EXTRA_FFLAGS)),)
SPEC_PLATFORM_FFLAGS := $(filter-out -march=%,$(SPEC_PLATFORM_FFLAGS))
endif
SPEC_PLATFORM_LDFLAGS := $(BARE_LDFLAGS)
SPEC_CXX_RUNTIME_LIBS := -lstdc++ -lsupc++
SPEC_FORTRAN_RUNTIME_LIBS := -lgfortran
SPEC_RUNTIME_OBJS := $(SPEC_RUNTIME_CONFIG_OBJ) $(SPEC_BARE_IO_OBJ) \
	$(SPEC_INPUT_OBJ)
SPEC_RUNTIME_LDFLAGS := -Wl,--wrap=main -Wl,--wrap=_open \
	-Wl,--wrap=_read -Wl,--wrap=_write -Wl,--wrap=_lseek \
	-Wl,--wrap=_fstat -Wl,--wrap=_stat -Wl,--wrap=_unlink \
	-Wl,--wrap=_close
else
SPEC_PLATFORM_CFLAGS := $(SPEC_OPTIMIZE)
SPEC_PLATFORM_CXXFLAGS := $(SPEC_OPTIMIZE)
SPEC_PLATFORM_FFLAGS := $(SPEC_OPTIMIZE)
SPEC_PLATFORM_LDFLAGS := -static
endif

CFLAGS := $(SPEC_PLATFORM_CFLAGS) $(SPEC_COMMON_FLAGS) $(SPEC_COMMON_CFLAGS) \
	$(SPEC_COMPAT_CFLAGS) \
	$(SPEC_BENCH_FLAGS) $(SPEC_EXTRA_CFLAGS) $(SPEC_BENCH_CFLAGS)
CXXFLAGS := $(SPEC_PLATFORM_CXXFLAGS) $(SPEC_COMMON_FLAGS) \
	$(SPEC_COMMON_CXXFLAGS) \
	$(SPEC_BENCH_FLAGS) $(SPEC_EXTRA_CXXFLAGS) $(SPEC_BENCH_CXXFLAGS)
FFLAGS := $(SPEC_PLATFORM_FFLAGS) $(SPEC_COMMON_FLAGS) -fno-strict-aliasing \
	-J$(SPEC_MOD_DIR) -I$(SPEC_MOD_DIR) $(SPEC_BENCH_FFLAGS) \
	$(SPEC_EXTRA_FFLAGS)
LDFLAGS := $(SPEC_PLATFORM_LDFLAGS) $(SPEC_RUNTIME_LDFLAGS) \
	$(SPEC_BENCH_LDFLAGS) \
	$(SPEC_EXTRA_LDFLAGS)

ifeq ($(SPEC_LINK_LANGUAGE),CXX)
SPEC_LD := $(CXX)
SPEC_LANGUAGE_LIBS := $(SPEC_CXX_RUNTIME_LIBS)
else ifeq ($(SPEC_LINK_LANGUAGE),FC)
SPEC_LD := $(FC)
SPEC_LANGUAGE_LIBS := $(SPEC_FORTRAN_RUNTIME_LIBS)
else
SPEC_LD := $(CC)
endif

SPEC_OBJS := $(addprefix $(SPEC_OBJ_DIR)/,$(addsuffix .o,$(basename $(SPEC_SOURCES))))
SPEC_STAGED_SOURCES := $(addprefix $(SPEC_STAGE_DIR)/,$(SPEC_SOURCES))
SPEC_DEPS := $(SPEC_OBJS:.o=.d)

ifneq ($(findstring F,$(SPEC_BENCH_LANGUAGE)),)
.NOTPARALLEL:
endif

.PHONY: all spec-stage spec-runtime clean
all: $(APP)

spec-stage:
	@python3 sync_source.py --source $(SPEC_SOURCE_DIR) --destination $(SPEC_STAGE_DIR)

$(SPEC_STAGED_SOURCES): | spec-stage
	@test -f $@

spec-runtime:
	@python3 prepare_runtime.py \
		--executable $(SPEC_EXE_NAME) \
		$(foreach dir,$(SPEC_INPUT_DIRS),--input-dir $(dir)) \
		--embed-inputs $(SPEC_EMBED_INPUTS) \
		--binary-output $(SPEC_INPUT_BIN) \
		--c-output $(SPEC_RUNTIME_CONFIG_C)

$(SPEC_RUNTIME_CONFIG_C) $(SPEC_INPUT_BIN): | spec-runtime
	@test -f $@

$(SPEC_RUNTIME_CONFIG_OBJ): $(SPEC_RUNTIME_CONFIG_C)
	@echo + CC $<
	@mkdir -p $(dir $@)
	@$(CC) $(SPEC_PLATFORM_CFLAGS) $(SPEC_COMMON_FLAGS) -c -o $@ $<

$(SPEC_BARE_IO_OBJ): bare_io.c
	@echo + CC $<
	@mkdir -p $(dir $@)
	@$(CC) $(SPEC_PLATFORM_CFLAGS) $(SPEC_COMMON_FLAGS) -c -o $@ $<

$(SPEC_INPUT_OBJ): $(SPEC_INPUT_BIN)
	@echo + OBJCOPY $<
	@cd $(SPEC_RUNTIME_DIR) && $(CROSS_COMPILE)objcopy \
		-I binary -O elf64-littleaarch64 -B aarch64 \
		--rename-section .data=.rodata.spec_inputs,alloc,load,readonly,data,contents \
		spec-inputs.bin spec-inputs.o

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

$(SPEC_OBJ_DIR)/%.o: $(SPEC_STAGE_DIR)/%.F
	@echo + FC $<
	@mkdir -p $(dir $@) $(SPEC_MOD_DIR)
ifeq ($(SPEC_SUITE_RESOLVED),2017)
	@cd $(SPEC_STAGE_DIR) && $(FC) $(FFLAGS) $(SPEC_BENCH_FPPFLAGS) \
		-c -o $(abspath $@) $(abspath $<)
else
	@echo + SPECPP $<
	@mkdir -p $(dir $(SPEC_PREP_DIR)/$*)
	@cd $(SPEC_STAGE_DIR) && $(SPEC_ROOT)/bin/specperl $(SPEC_ROOT)/bin/specpp \
		$(SPEC_BENCH_FPPFLAGS) -o $(abspath $(SPEC_PREP_DIR)/$*.f) $*.F
	@cd $(SPEC_STAGE_DIR) && $(FC) $(FFLAGS) -c -o $(abspath $@) \
		$(abspath $(SPEC_PREP_DIR)/$*.f)
endif

$(SPEC_OBJ_DIR)/%.o: $(SPEC_STAGE_DIR)/%.F90
	@echo + FC $<
	@mkdir -p $(dir $@) $(SPEC_MOD_DIR)
ifeq ($(SPEC_SUITE_RESOLVED),2017)
	@cd $(SPEC_STAGE_DIR) && $(FC) $(FFLAGS) $(SPEC_BENCH_FPPFLAGS) \
		-c -o $(abspath $@) $(abspath $<)
else
	@echo + SPECPP $<
	@mkdir -p $(dir $(SPEC_PREP_DIR)/$*)
	@cd $(SPEC_STAGE_DIR) && $(SPEC_ROOT)/bin/specperl $(SPEC_ROOT)/bin/specpp \
		$(SPEC_BENCH_FPPFLAGS) -o $(abspath $(SPEC_PREP_DIR)/$*.f90) $*.F90
	@cd $(SPEC_STAGE_DIR) && $(FC) $(FFLAGS) -c -o $(abspath $@) \
		$(abspath $(SPEC_PREP_DIR)/$*.f90)
endif

$(APP): $(SPEC_OBJS) $(SPEC_RUNTIME_OBJS) $(EXTRA_OBJS)
	@echo + LD $@
	@mkdir -p $(dir $@)
	@$(SPEC_LD) $(LDFLAGS) -o $@ $(EXTRA_OBJS) $(SPEC_RUNTIME_OBJS) \
		$(SPEC_OBJS) \
		$(SPEC_BENCH_LIBS) $(SPEC_LANGUAGE_LIBS) $(LDLIBS)

clean:
	@rm -rf $(SPEC_WORK_DIR) $(APP)

-include $(SPEC_DEPS)
