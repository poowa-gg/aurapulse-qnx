# Codelab: Building Mixed-Criticality Safety Systems on QNX 8.0
**From Zero to Deterministic Microkernel Isolation in QEMU**

* **Duration**: ~35 minutes
* **Target Audience**: Robotics, Automotive, and Embedded AI Engineers
* **Prerequisites**: Free [QNX Everywhere](https://blackberry.qnx.com/en/developers/qnx-everywhere) account, QNX SDP 8.0, and QEMU

---

## Module 1: Why Mixed-Criticality Matters
When deploying neural networks onto surgical robots or autonomous vehicles, engineers face a fundamental conflict:
* **AI Perception** requires dynamic memory allocation, multi-threading, and variable inference times.
* **Actuator Control** requires strict real-time deadlines (sub-millisecond jitter) and zero tolerance for crashes.

In this codelab, you will build `/dev/aurasentry`, a user-space QNX 8.0 Resource Manager that acts as a deterministic firewall between an untrusted AI process and physical motor commands.

---

## Module 2: Setting Up QNX SDP 8.0 & QEMU
1. Install **QNX SDP 8.0** via the QNX Software Center.
2. Source your toolchain environment (`qnxsdp-env.bat` on Windows or `qnxsdp-env.sh` on Linux).
3. Generate an `x86_64` QNX 8.0 virtual image using `mkqnximage --type=qemu --arch=x86_64 --clean --noprompt`.

---

## Module 3: Writing a QNX Resource Manager (`/dev/aurasentry`)
Unlike monolithic kernels where custom device drivers run in kernel space (where a single pointer bug crashes the entire OS), QNX drivers are isolated user-space processes.

Key QNX APIs used in `src/aurasentry/aurasentry.c`:
1. **`dispatch_create()`**: Allocates a unified message/pulse dispatch context.
2. **`iofunc_func_init()` & `iofunc_attr_init()`**: Initializes default POSIX file operations (`open`, `read`, `write`, `close`).
3. **`resmgr_attach()`**: Registers `/dev/aurasentry` in the QNX pathname manager so any process can interact with it using standard `open()`, `read()`, and `write()` calls.

---

## Module 4: Deterministic Timing with Kernel Pulses
Instead of polling or using heavy condition variables, QNX provides **Pulses**—fixed-size, non-blocking notifications delivered directly into the dispatch loop via `pulse_attach()`, `message_connect()`, `SIGEV_PULSE_INIT()`, and `timer_create(CLOCK_MONOTONIC, ...)`. By setting `SCHED_FIFO` at priority `50`, the kernel guarantees our safety handler preempts standard priority `10` AI threads immediately when the timer pulse fires.

---

## Module 5: Hands-On Fault Injection Lab
1. Cross-compile both binaries using `qcc -Vgcc_ntox86_64`.
2. **Test Kinematic Clamping**: Write `echo "0.850 0.600" > /dev/aurasentry` and read `cat /dev/aurasentry` to observe `"OVERRIDE_CLAMPED"` capping the output vector to `0.050 mm/cycle`.
3. **Test Watchdog Failsafe**: Run `/tmp/ai_sim --duration 3` and wait for it to exit. Within 50 ms, `/dev/aurasentry` transitions to `"FAILSAFE_HOLD"` and zeroes actuator velocity.

---

## Summary
You have built a fault-isolated, deterministic safety layer on QNX 8.0 that protects physical hardware from AI hallucinations, CPU starvation, and process crashes.
