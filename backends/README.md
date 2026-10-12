# Bundled backends

| Backend | Driver / UAPI | Source | Daemon |
|---|---|---|---|
| KernelSU | 32680 / 5 | [0c0fdb96](https://github.com/tiann/KernelSU/commit/0c0fdb960178fa12d80d6cbcfdcb6ad8be6a865d) | 3.3.0-79-g0c0fdb96 |
| KernelSU-Next | 33342 / 5 | [0a77550c](https://github.com/KernelSU-Next/KernelSU-Next/commit/0a77550cce8118d64528a2e7313e4b855914a452) | 3.4.1-9-g0a77550c |
| BakaSU | 35227 / 5 | [6200478d](https://github.com/Baka-SU/BakaSU/commit/6200478dd76fc63093a8226d360f5072c46aea26) | 4.2.0-rc3-56-g6200478d |

Each folder contains the exact driver/daemon hashes and the complete Samsung
compatibility patch for that revision. Keep these records in git: they are used
by the weekly build and by `tools/test_backend_bundle.py`.

Use a UAPI 5 manager. BakaSU retains the internal `resukisu` id.
After installing a new APK, fully reboot and activate root to load its driver.
A manager APK update alone does not replace the running driver.

Build and bundle validation is not phone testing. Firmware support, exploit
algorithms, and Samsung compatibility behavior are not changed by this pipeline.
See [the build workflow](../tools/backend-refresh/README.md).
