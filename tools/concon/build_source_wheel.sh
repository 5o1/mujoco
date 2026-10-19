#!/usr/bin/env bash
# Build all native components from one source checkout, using upstream packaging.
set -euo pipefail
source_dir=$(realpath "$1")
mkdir -p "$2"
output_dir=$(realpath "$2")
driver_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec > >(tee "$output_dir/build.log") 2>&1
python -m venv "$output_dir/venv"
source "$output_dir/venv/bin/activate"
python -m pip install --require-hashes -r "$source_dir/python/build_requirements.txt"
if [[ "$VARIANT" == patched ]]; then
  export CONCON_WHEEL_VERSION=3.16.0+concon.sdf3689.2
else
  export CONCON_WHEEL_VERSION=3.16.0+concon.control.1
fi
export CONCON_SOURCE_DIR="$source_dir"
python - <<'PY'
import json,os,subprocess,sys
from pathlib import Path
root=Path(os.environ['CONCON_SOURCE_DIR'])
meta=root/'python/pyproject.toml'
s=meta.read_text().replace('version = "3.16.0"',f'version = "{os.environ["CONCON_WHEEL_VERSION"]}"',1)
s=s.replace('mujoco = [\n','mujoco = [\n    "CONCON_BUILD.json",\n',1)
meta.write_text(s)
with (root/'python/MANIFEST.in').open('a') as manifest:
    manifest.write('\ninclude mujoco/CONCON_BUILD.json\n')
record={'distribution_version':os.environ['CONCON_WHEEL_VERSION'],
        'variant':os.environ['VARIANT'],
        'source_commit':subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip(),
        'source_repository':'https://github.com/5o1/mujoco',
        'python':sys.version,'github_run_url':f'https://github.com/{os.environ["GITHUB_REPOSITORY"]}/actions/runs/{os.environ["GITHUB_RUN_ID"]}',
        'packaging':'Engine, plugins, generated headers and Python extensions built from this same source checkout. No binary replacement or repacking.',
        'compiler':'Ubuntu 22.04 default GCC; Release, double precision; native default LTO on, Python binding LTO off.'}
(root/'python/mujoco/CONCON_BUILD.json').write_text(json.dumps(record,indent=2)+'\n')
PY
cmake -S "$source_dir" -B "$output_dir/native" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=ON \
  -DMUJOCO_BUILD_EXAMPLES=OFF -DMUJOCO_BUILD_SIMULATE=OFF \
  -DMUJOCO_BUILD_TESTS=ON -DMUJOCO_TEST_PYTHON_UTIL=OFF \
  -DCMAKE_INSTALL_PREFIX="$output_dir/install"
cmake --build "$output_dir/native" --target mujoco actuator elasticity sensor sdf_plugin user_objects_test user_mesh_test --parallel 2
(cd "$source_dir/test" && "$output_dir/native/bin/user_objects_test") | tee "$output_dir/user_objects_test.log"
(cd "$source_dir/test" && "$output_dir/native/bin/user_mesh_test") | tee "$output_dir/user_mesh_test.log"
cmake --install "$output_dir/native"
mkdir -p "$output_dir/install/mujoco_plugin"
cp "$output_dir/native/lib/"lib{actuator,elasticity,sensor,sdf_plugin}.so "$output_dir/install/mujoco_plugin/"
(cd "$source_dir/python" && PYTHONPATH="$source_dir/python/mujoco" bash make_sdist.sh) > "$output_dir/sdist.log" 2>&1
export MUJOCO_PATH="$output_dir/install"
export MUJOCO_PLUGIN_PATH="$output_dir/install/mujoco_plugin"
export MUJOCO_CMAKE_ARGS='-DCMAKE_INTERPROCEDURAL_OPTIMIZATION=OFF'
mkdir -p "$output_dir/wheels"
python -m pip wheel --no-deps --no-build-isolation "$source_dir"/python/dist/mujoco-*.tar.gz --wheel-dir "$output_dir/wheels" > "$output_dir/wheel.log" 2>&1
python -m pip install --no-deps "$output_dir"/wheels/*.whl
python -m pip check
python "$driver_dir/source_wheel_smoke.py" --variant "$VARIANT" --output "$output_dir/smoke.json"
(cd "$output_dir" && python -m pytest --pyargs mujoco.specs_test -q) | tee "$output_dir/specs_test.log"
python -m pip freeze > "$output_dir/requirements.txt"
cp "$source_dir/python/mujoco/CONCON_BUILD.json" "$output_dir/provenance.json"
# Only retained deliverables are uploaded, not transient source/build environments.
rm -rf "$output_dir/venv" "$output_dir/native" "$output_dir/install"
