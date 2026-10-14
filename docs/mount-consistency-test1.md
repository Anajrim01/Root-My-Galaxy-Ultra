# Mount consistency test 1

This candidate was based on RMGU 1.2.5 with the same three backend revisions.
The tested SusFS payload is included in RMGU 1.2.6.

## Changes

- Require all three mount-table hooks for SusFS mount hiding. If a hook fails,
  activation rolls back and reports the failing hook instead of leaving partial
  coverage enabled.
- Recognize additional bind and overlay backing paths using a shared mount
  classifier, including mounts with ordinary-looking source names.
- Match absolute mount rules at path-component boundaries to avoid hiding
  similarly named neighbouring paths.
- Add backing-helper availability to the mount diagnostics.

## Validation and current limits

- 43 native host cases passed normally and with ASan/UBSan; seven regressions
  failed against the previous 1.2.5 source.
- The ARM64 module built with the same pinned DDK. Kernel imports and module
  metadata matched the released baseline; removing debug sections preserved all
  allocated sections.
- The signed candidate build passed Android unit tests, APK packaging and
  signature checks:
  https://github.com/xorpix/Root-My-Galaxy-Ultra/actions/runs/38558350186
- Device diagnostics on SM-S948B / BZIG reported hide=1, show_probes=3/3 and all
  backing helpers available. A normal Termux reader saw 209 records compared
  with 216 root-visible records, with seven module-mount records removed.
- A timed root capture during a fresh Duck scan found 212 records in regular
  app processes and 204 in the app zygote and isolated processes. Their eight
  differences were four app-data binds, two runtime-profile binds and two
  shared-storage mounts. Removing those eight entries reproduced the same
  normalized table. No module-mount markers occurred in those captured views.
- These foreign-process captures were root controls, not Duck's exact isolated
  reader output. The remaining cross-process warning is not confirmed resolved.
- Reader scope remains the existing non-su SELinux-domain policy; this change
  does not add per-app profile integration.
- Backing-path recognition is bounded and does not inspect every overlay lower
  layer. Existing module rules and namespace-identity tracking remain active.
- BZID and other device variants still need device testing.

## Updating

Install the production APK, fully reboot and activate root and SusFS normally.
A soft reboot keeps the previous kernel module loaded.

The release notes are in [1.2.6.md](release-notes/1.2.6.md).
