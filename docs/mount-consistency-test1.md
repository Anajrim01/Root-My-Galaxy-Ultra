# Mount consistency test 1

This candidate is based on RMGU 1.2.5 with the same three backend revisions.

## What's new

- Require all three mount-table hooks for SusFS mount hiding. If a hook fails,
  activation rolls back and reports the failing hook instead of leaving partial
  coverage enabled.
- Recognize additional bind and overlay backing paths using a shared mount
  classifier, including mounts with ordinary-looking source names.
- Match absolute mount rules at path-component boundaries to avoid hiding
  similarly named neighbouring paths.
- Add backing-helper availability to the mount diagnostics.

## Validation and current limits

- 43 native host cases pass normally and with ASan/UBSan; seven regressions fail
  against the previous 1.2.5 source.
- The ARM64 module builds with the same pinned DDK. Kernel imports and module
  metadata match the released payload; removing debug sections preserves all
  allocated sections.
- Android unit tests, APK packaging and signature checks run in the candidate
  workflow. A successful workflow is required before distributing its APK.
- Phone testing remains pending. Reader scope remains the existing non-su
  SELinux-domain policy; this candidate does not add per-app profile integration.
- Backing-path recognition is bounded and does not inspect every overlay lower
  layer. Existing module rules and namespace-identity tracking remain active.

## Testing

1. Install the signed release APK from the candidate build over 1.2.5.
2. Fully reboot, then activate root and SusFS normally. A soft reboot keeps the
   previous kernel module loaded.
3. Keep backend, module and detector settings unchanged from your baseline.
4. Export a detector report and collect the following in Termux:

   ```sh
   su -c 'cat /sys/module/susfs_guard_lkm/parameters/mount_stat'
   ```

Successful mount hiding reports `hide=1` and `show_probes=3/3`. The `backing` line
shows whether the new helper paths are available. Check ordinary apps and repeat
the detector check after a soft reboot.

This branch uploads build artifacts; a push does not publish a release or merge
into `main`.
