# ConCon MuJoCo maintenance

Maintenance branch: `concon/3.16.0-sdf-sign-pr3689` in
[5o1/mujoco](https://github.com/5o1/mujoco).

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

## Build and install

Use the normal upstream CMake dependency pins. Network access in the ConCon
workspace must use real-IP direct connections first. Set the environment's
`LD_LIBRARY_PATH` to its `lib` directory when the official Python extensions need
the conda C++ runtime.

```sh
cmake -S . -B build/concon -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DMUJOCO_BUILD_EXAMPLES=OFF -DMUJOCO_BUILD_SIMULATE=OFF \
  -DMUJOCO_BUILD_TESTS=ON -DMUJOCO_TEST_PYTHON_UTIL=OFF
cmake --build build/concon --target mujoco user_objects_test user_mesh_test -j 4
(cd test && ../build/concon/bin/user_objects_test && ../build/concon/bin/user_mesh_test)
python -m pip download --only-binary=:all: --no-deps -d wheelhouse mujoco==3.16.0
python tools/concon/repack_wheel.py \
  --official-wheel wheelhouse/mujoco-3.16.0-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl \
  --library build/concon/lib/libmujoco.so.3.16.0 --output-dir wheelhouse
python -m pip install --no-deps --force-reinstall \
  wheelhouse/mujoco-3.16.0+concon.sdf3689.1-cp312-cp312-linux_x86_64.whl
```

The local wheel retains the official 3.16.0 Python bindings and plugins, replacing
only the ABI-compatible engine library. It is tagged `linux_x86_64`, without a
manylinux portability claim. Distribution metadata reports
`3.16.0+concon.sdf3689.1`; `mujoco.__version__` and `mj_versionString()` still report
the native API version `3.16.0`. `mujoco/CONCON_PATCH.json` records source commits,
upstream wheel hash and installed library hash. All meshes must be recompiled;
old `.mjb` files still contain their previously generated SDF coefficients.

Inspect the installed variant with:

```sh
python -c 'import importlib.metadata; print(importlib.metadata.version("mujoco"))'
python -c 'import mujoco,pathlib; print((pathlib.Path(mujoco.__file__).parent/"CONCON_PATCH.json").read_text())'
```

To roll back, reinstall the retained official wheel with `--no-deps
--force-reinstall`, then recompile models. This affects the selected Python
environment only.

## Validation record

The gamepad project's Chinese installation and validation report is maintained in
`build/experiments/mb_m2/pr3689_install/REPORT.md` of
`xbox_gamepad_physics-mujoco`. It distinguishes the independent tetrahedron
reproducer, gamepad-specific static SDF queries, contact experiments and the
remaining M2 acceptance gates. This fork does not claim that installing the patch
alone completes gamepad acceptance.
