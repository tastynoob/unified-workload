OUTFLAG = -o
CC ?= cc
PORT_CFLAGS ?= -O2
COREMARK_ITERATIONS ?= 0
COREMARK_MEM_LOCATION ?= Heap

FLAGS_STR = "$(PORT_CFLAGS) $(XCFLAGS) -DITERATIONS=$(COREMARK_ITERATIONS) $(XLFLAGS) $(LFLAGS_END)"
CFLAGS = $(PORT_CFLAGS) -I$(PORT_DIR) -I. -DFLAGS_STR=\"$(FLAGS_STR)\" -DMEM_LOCATION=\"$(COREMARK_MEM_LOCATION)\" -DITERATIONS=$(COREMARK_ITERATIONS)
LFLAGS_END += -static

PORT_SRCS = $(PORT_DIR)/core_portme.c
vpath %.c $(PORT_DIR)
vpath %.h $(PORT_DIR)
vpath %.mak $(PORT_DIR)
EXTRA_DEPENDS += $(PORT_DIR)/core_portme.mak

LOAD = echo Loading done
RUN =

OEXT = .o
EXE =
OPATH = ./
MKDIR = mkdir -p

.PHONY: port_prebuild port_postbuild port_prerun port_postrun port_preload port_postload
port_prebuild port_postbuild port_prerun port_postrun port_preload port_postload:
