# Bundled backends

| Backend | Driver / UAPI | Source | Daemon |
|---|---|---|---|
| KernelSU | 32675 / 5 | [f895b80a](https://github.com/tiann/KernelSU/commit/f895b80a3aad79948ba8074f53cf8f65a314d576) | 3.3.0-74-gf895b80a |
| KernelSU-Next | 33340 / 5 | [02a9e1c5](https://github.com/KernelSU-Next/KernelSU-Next/commit/02a9e1c5fb2c4fd8117429fe004136332788c1b6) | 3.4.1-7-g02a9e1c5 |
| BakaSU | 35226 / 5 | [f6cb7e70](https://github.com/Baka-SU/BakaSU/commit/f6cb7e70c10ebde149f3121ae68b945514fd0801) | 4.2.0-rc3-55-gf6cb7e70 |

Each folder contains the exact driver/daemon hashes and the complete Samsung
compatibility patch for that revision. Keep these records in git: they are used
by the weekly build and by `tools/test_backend_bundle.py`.

Use a UAPI 5 manager. BakaSU retains the internal `resukisu` id.
After installing a new APK, fully reboot and activate root to load its driver.
A manager APK update alone does not replace the running driver.

Build and bundle validation is not phone testing. Firmware support, exploit
algorithms, and Samsung compatibility behavior are not changed by this pipeline.
See [the build workflow](../tools/backend-refresh/README.md).
