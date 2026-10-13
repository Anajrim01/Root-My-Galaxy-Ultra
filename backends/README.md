# Bundled backends

| Backend | Driver / UAPI | Source | Daemon |
|---|---|---|---|
| KernelSU | 32680 / 5 | [0c0fdb96](https://github.com/tiann/KernelSU/commit/0c0fdb960178fa12d80d6cbcfdcb6ad8be6a865d) | 3.3.0-79-g0c0fdb96 |
| KernelSU-Next | 33354 / 5 | [3157e782](https://github.com/KernelSU-Next/KernelSU-Next/commit/3157e7822190eba628ca6796242db970405e440a) | 3.4.1-21-g3157e782 |
| BakaSU | 35229 / 5 | [d7260ca1](https://github.com/Baka-SU/BakaSU/commit/d7260ca1e5c128061122924d0d48754e361e135c) | 4.2.0-rc3-58-gd7260ca1 |

Each folder contains the exact driver/daemon hashes and the complete Samsung
compatibility patch for that revision. Keep these records in git: they are used
by the weekly build and by `tools/test_backend_bundle.py`.

Use a UAPI 5 manager. BakaSU retains the internal `resukisu` id.
After installing a new APK, fully reboot and activate root to load its driver.
A manager APK update alone does not replace the running driver.

Build and bundle validation is not phone testing. Firmware support, exploit
algorithms, and Samsung compatibility behavior are not changed by this pipeline.
See [the build workflow](../tools/backend-refresh/README.md).
