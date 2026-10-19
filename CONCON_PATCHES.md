# ConCon MuJoCo maintenance

Maintenance branch: `concon/3.16.0-sdf-sign-pr3689` in
[5o1/mujoco](https://github.com/5o1/mujoco).

## Integration status (2026-10-19)

The adopted method builds the engine, plugins and Python bindings together in
[Actions run 39195476197](https://github.com/5o1/mujoco/actions/runs/39195476197),
from source commit `ac1bfe32700667d98b0eea412900beef5d98cbc2`.
The Python 3.12 source-built wheel passes the force-actuator model compilation
that previously segfaulted and the gamepad project's full local fast regression:
324 unittest cases (268 passed, 56 skipped), 20 backend tests and 35 Node tests.

The upstream control reproduces 1,248 exterior-negative tetrahedron corner
records, while the patched build has zero. Both control and patched source
builds compile and step the same force-driven free sphere successfully. The
patched build also passes 103 `user_objects_test` cases, 84 `user_mesh_test`
cases and 80 Python `specs_test` cases (plus 9 subtests).

The previous mixed-binary candidate `.1` is rejected. Its exact crash cause has
not been isolated; successful same-source builds establish a working packaging
method, not proof of a particular ABI defect. Full gamepad acceptance is tracked
separately in the gamepad project, including contact and visual gates.

## SDF sign correction

The base is the unchanged upstream 3.16.0 release commit
`a892750516336d8358949f4518fcc4fbbd85beae`. The only engine change is
[upstream PR #3689](https://github.com/google-deepmind/mujoco/pull/3689), pinned to
`89733a51f207c7fedafc855d22ffd4c38caa793a` and applied with `git am` to preserve
its authorship. This is a downstream patch; the PR was unmerged when adopted on
2026-10-19. See [upstream issue #3686](https://github.com/google-deepmind/mujoco/issues/3686).

The original compiler classifies an SDF sample using the normal of one nearest
triangle. At shared edges and vertices that can give an exterior point a negative
distance and produce contacts in empty space. The patch uses incident face
normals for edges and angle-weighted incident normals for vertices. Unsigned
distance and the runtime contact solver remain unchanged. No gamepad mesh,
physical parameter, contact policy, timestep, or acceptance fixture is changed.

## GitHub Actions source builds

Workflow: `.github/workflows/concon-sdf-wheel.yml`, named **ConCon SDF wheels**.
It builds the engine, plugins, generated binding sources and Python extensions
from the same checkout. No official binary wheel is repacked. The matrix builds
patched CPython 3.10/3.11/3.12 wheels and an unpatched 3.16.0 CPython 3.12 control.
The control uses release commit `a892750516336d8358949f4518fcc4fbbd85beae`.

The Linux runner uses Ubuntu 22.04 GCC, Release and double precision. The native
library retains its default LTO setting; Python extensions use the upstream CI
LTO-off setting. Native LTO-off failed in both control and patched builds because
GCC 11 promoted an upstream `mjc_BoxBox` uninitialized-variable warning to an
error. This was addressed by restoring native default LTO, without changing
collision code or suppressing warnings.

Builds run on pushes affecting the workflow or its two driver scripts. Use `gh`
to inspect, rerun, and download a completed build:

```sh
gh run list --repo 5o1/mujoco --workflow concon-sdf-wheel.yml \
  --branch concon/3.16.0-sdf-sign-pr3689
gh run view RUN_ID --repo 5o1/mujoco
gh run rerun RUN_ID --repo 5o1/mujoco
gh run download RUN_ID --repo 5o1/mujoco \
  --name concon-patched-py3.12 --dir wheelhouse
python -m pip install --no-deps --force-reinstall wheelhouse/wheels/*.whl
```

Only use a build that completed successfully and passed the project's local
checks. Actions artifacts are retained for 30 days; keep adopted wheels in the
project's archive. The source-build distribution is
`3.16.0+concon.sdf3689.2`; its `mujoco/CONCON_BUILD.json` identifies the exact source
commit and Actions run. Native API strings still report `3.16.0`. The wheels are
Linux x86_64 builds, without a manylinux portability claim. Existing `.mjb` files
must be recompiled to replace previously generated SDF coefficients.

The previous binary-replacement candidate `3.16.0+concon.sdf3689.1` failed
integration and must not be installed. Its build history is retained in Git.

## Validation record

The gamepad project's Chinese installation and validation report is maintained in
`build/experiments/mb_m2/pr3689_install/REPORT.md` of
`xbox_gamepad_physics-mujoco`. It distinguishes the independent tetrahedron
reproducer, gamepad-specific static SDF queries, contact experiments and the
remaining M2 acceptance gates. This fork does not claim that installing the patch
alone completes gamepad acceptance.
