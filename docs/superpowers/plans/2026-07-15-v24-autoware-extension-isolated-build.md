# v24 Autoware Lanelet2 extension isolated-build plan

## Objective

Decide, before compiling, whether the frozen official
`autoware_lanelet2_extension` 1.2.0 source can be built and loaded against the
existing Lanelet2 1.2.2 runtime entirely under
`/root/autodl-tmp/camp_v24_autoware_lanelet2_extension`. The original OSM is
read-only. Diffusion Planner code, configuration, weights, checkpoint,
request, candidate tensors, and trajectories remain unchanged.

## Frozen inputs

- Extension commit: `4a3420d8cc19906e7739618f8a1686400f79b4ac`.
- Extension tree: `76ba5b7b3b74bc5539b6ea55dcfb205538ad5362`.
- Clean source: isolated-prefix `source_full`; upstream CMake and package
  manifests are authoritative.
- Existing runtime: Lanelet2 Python package `1.2.2`, Python `3.9.25`, GCC
  `11.4.0`, CMake `3.22.1`, and glibc `2.35`.
- Map SHA256:
  `cda848e3d440aaf48e532f8ab33afdff0bf8b8f1a45abd3d7724637a287ed660`.

## Build authorization predicate

A build may start only if one read-only preflight proves all of the following:

1. The frozen checkout and key file hashes still match the qualification
   artifact, and free space remains above the 10 GiB floor.
2. Lanelet2 1.2.2 headers, libraries, and CMake package files already exist in
   the current environment or isolated prefix and resolve to one consistent
   ABI.
3. Every dependency required by the unmodified official CMake targets already
   exists and is discoverable without network acquisition or machine-global
   change.
4. Configure, build, and install outputs can remain wholly in isolated
   `build` and `install` directories.

No system package operation, global Python install, Lanelet2/ROS upgrade, or
environment-wide mutation is authorized. No additional source checkout is
authorized: the extension is the sole new dependency source. The preflight
must not start a compiler when any predicate is false.

Compiling only `detection_area.cpp`, editing upstream CMake, supplying a local
handwritten registrar, copying headers from an unfrozen checkout, or dropping
the official Python/C++ dependency chain would not prove the frozen official
extension and is prohibited.

## TDD and static preflight

1. Contract-test this plan before its implementation record exists.
2. Rehash the clean source, archive, license, and registration-chain files.
3. Inventory compiler, Python SOABI, glibc, Lanelet2 package/library exports,
   headers, CMake configs, ROS/ament/Autoware packages, and every upstream
   `find_package`/package-manifest dependency.
4. Run read-only CMake/package discovery probes only. Record commands, stdout,
   stderr, return codes, HEADS, environment, disk, and the authorization
   predicate as JSON and Markdown.
5. Seal the artifact with file SHA256 values plus `ROOT_SHA256SUMS`.
6. Independently recompute the predicate from the sealed inventory.

## Decision and continuation

- Predicate true: run the unmodified official CMake targets in the isolated
  prefix, then prove library provenance/ABI, process-local factory
  registration, 15/15 regulatory preservation, 9/9 lanelet-reference
  preservation, source-byte identity, stock-map before/after invariance, and
  fixed-DP immutability.
- Predicate false: do not build. Branch A becomes source-ineligible with the
  exact missing prerequisites and immutable receipt. This is source-local;
  Branch B raw census remains mandatory and the global stop remains false.

Any later corrected attempt receives a new artifact path. Failed evidence is
never overwritten.
