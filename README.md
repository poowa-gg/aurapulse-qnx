# AuraPulse QNX 8.0
**Deterministic Mixed-Criticality Surgical & Cobot Safety Sentinel**

> Built on **QNX Software Development Platform (SDP) 8.0** | Category: **Robotics & Medical** | Bonus Tracks: **Best Use of QNX-Specific Technologies** & **Best Codelab / Tutorial**

---

## 1. The Problem: The Mixed-Criticality AI Paradox
Edge AI perception models are transforming surgical robotics and collaborative industrial robots (cobots). However, deep learning inference is **stochastic**: execution times fluctuate between 15 ms and 180+ ms, processes can suffer memory leaks or segmentation faults, and inference hallucinations can output sudden, hazardous trajectory spikes.

On a general-purpose OS, an AI thread spike or driver crash can starve the physical motor control loop—causing actuator overshoot or collision with human tissue.

## 2. The Solution: Microkernel Isolation on QNX 8.0
**AuraPulse** decouples non-deterministic Edge AI from hard real-time physical actuation using native **QNX Neutrino 8.0 microkernel primitives**:

1. **Custom User-Space POSIX Resource Manager (`/dev/aurasentry`)**:
   * Implemented in `src/aurasentry/aurasentry.c` using `dispatch_create()`, `resmgr_attach()`, `iofunc_func_init()`, and `resmgr_msgread()`.
   * Exposes a standard character device interface where AI models stream trajectory deltas (`dx dy`) and monitoring tools read live JSON telemetry.
2. **Asynchronous Kernel Pulse Loop (`SIGEV_PULSE_INIT` & `SCHED_FIFO` Priority 50)**:
   * Driven by `CLOCK_MONOTONIC` periodic timers delivering non-blocking pulses via `pulse_attach()` and `message_connect()`, eliminating mutex contention and thread wake-up overhead.
3. **Kinematic Safety Envelope Clamping**:
   * Every 2.0 ms (500 Hz), `/dev/aurasentry` validates incoming AI vectors against a strict physical velocity bound (`0.050 mm/cycle`). Hazardous AI spikes trigger `OVERRIDE_CLAMPED`, scaling the vector safely onto the perimeter.
4. **50 ms AI Heartbeat Watchdog (`FAILSAFE_HOLD`)**:
   * If the AI process crashes, hangs, or gets starved by CPU load for >50 ms, `/dev/aurasentry` immediately zeroes actuator velocity (`[0.0000, 0.0000]`) and transitions to `FAILSAFE_HOLD`.

---

## 3. Empirical Verification & Benchmarks (QNX 8.0 x86_64)

| Scenario | Injected Fault | QNX `/dev/aurasentry` Response | Outcome |
| :--- | :--- | :--- | :--- |
| **Nominal Operation** | 50 Hz circular AI trajectory (`r = 0.025 mm`) | `SAFE_TRACKING` (`68.56 us` jitter) | 1:1 smooth tracking |
| **AI Hallucination** | Sudden `10x` jump (`[0.7500, -0.6200]`) | `OVERRIDE_CLAMPED` (`1,628` spikes blocked) | Clamped to `0.050 mm` envelope |
| **100% CPU Saturation** | 4x `SCHED_RR` Prio 10 stress threads | `SCHED_FIFO` Prio 50 preempts AI threads | Zero missed safety deadlines |
| **AI Process Crash** | `slay -f ai_sim` (`SIGKILL`) | `FAILSAFE_HOLD` within `50 ms` | Velocity locked to `[0.0000, 0.0000]` |

---

## 4. Repository Structure & QNX Evidence Map

* `src/aurasentry/aurasentry.c` — Native QNX Resource Manager (`/dev/aurasentry`), 500 Hz pulse timer, kinematic clamp, and 50 ms watchdog.
* `src/ai_sim/ai_sim.c` — Edge AI trajectory generator and multi-threaded 100% CPU stress injector.
* `host-dashboard/bridge.py` — Persistent SSH-to-HTTP telemetry and fault-injection bridge.
* `host-dashboard/index.html` — Real-time X/Y actuator envelope visualizer and kernel jitter oscilloscope.
* `codelab/README.md` — Step-by-step developer tutorial (Best Codelab / Tutorial bonus entry).
* `Makefile` — Reproducible cross-compilation rules targeting QNX SDP 8.0 (`qcc`).
* `LICENSE` — Apache 2.0 Open Source License.

---

## 5. Build & Run Instructions

### Prerequisites
* **Host OS**: Windows 10/11 or Ubuntu Linux 22.04+
* **Toolchain**: QNX Software Development Platform **8.0** (`qcc` 12.2.0, `gcc_ntox86_64` or `gcc_ntoaarch64le`)
* **Target**: QEMU `x86_64` virtual machine (generated via `mkqnximage`) or Raspberry Pi 5

### Step 1: Initialize QNX SDP 8.0 Environment & Compile
* **Windows (PowerShell):**
  * Load environment: `cmd /c "`"$env:USERPROFILE\qnx800\qnxsdp-env.bat`" && set"`
  * Compile sentry: `qcc -Vgcc_ntox86_64 -Wall -O2 -lm -o aurasentry src/aurasentry/aurasentry.c`
  * Compile AI sim: `qcc -Vgcc_ntox86_64 -Wall -O2 -lm -pthread -o ai_sim src/ai_sim/ai_sim.c`
* **Linux:**
  * Run `source ~/qnx800/qnxsdp-env.sh && make`

### Step 2: Boot QNX 8.0 Target in QEMU
* Generate image: `mkqnximage --type=qemu --arch=x86_64 --clean --noprompt --ssh-ident=~/.ssh/id_ed25519.pub`
* Run QEMU: `qemu-system-x86_64 -smp 2 --cpu max -m 1G -drive file=output/disk-qemu.vmdk,if=ide,id=drv0 -kernel output/ifs.bin -netdev user,id=net0,hostfwd=tcp::2222-:22 -device virtio-net-pci,netdev=net0 -serial mon:stdio -nographic`

### Step 3: Deploy & Launch on QNX 8.0
* Transfer binaries: `scp -P 2222 -o MACs=hmac-sha2-256 aurasentry ai_sim root@localhost:/tmp/`
* Start resource manager: `ssh -p 2222 -o MACs=hmac-sha2-256 root@localhost "chmod +x /tmp/aurasentry /tmp/ai_sim && /tmp/aurasentry &"`

### Step 4: Launch the Live Host Dashboard
* Start bridge: `python host-dashboard/bridge.py`
* Open `http://localhost:8080` in your browser.
