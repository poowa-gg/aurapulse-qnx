# AuraPulse QNX 8.0 Makefile
# Target: QNX Neutrino RTOS 8.0 (x86_64 / aarch64)
# Toolchain: QNX SDP 8.0 (qcc)

CC      ?= qcc
ARCH    ?= gcc_ntox86_64
CFLAGS  := -V$(ARCH) -Wall -O2
LDFLAGS := -lm

TARGET_HOST ?= qnx-qemu

all: aurasentry ai_sim

aurasentry: src/aurasentry/aurasentry.c
	$(CC) $(CFLAGS) -o aurasentry src/aurasentry/aurasentry.c $(LDFLAGS)

ai_sim: src/ai_sim/ai_sim.c
	$(CC) $(CFLAGS) -pthread -o ai_sim src/ai_sim/ai_sim.c $(LDFLAGS)

deploy: all
	scp aurasentry ai_sim $(TARGET_HOST):/tmp/
	ssh $(TARGET_HOST) "chmod +x /tmp/aurasentry /tmp/ai_sim"

clean:
	rm -f aurasentry ai_sim test_jitter *.o

.PHONY: all deploy clean
