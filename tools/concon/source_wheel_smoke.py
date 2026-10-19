"""Exercise SDF signs and MjSpec force-actuator compilation without gamepad assets."""
import argparse
import importlib.metadata
import json
from pathlib import Path

import mujoco as mj
import numpy as np


def force_probe():
    spec = mj.MjSpec.from_string('<mujoco/>')
    spec.option.timestep = .0005
    spec.option.integrator = mj.mjtIntegrator.mjINT_IMPLICITFAST
    body = spec.worldbody.add_body(name='probe', pos=[0, 0, .1])
    mass, radius = .05, .004
    body.mass = mass
    body.ipos = [0, 0, 0]
    body.iquat = [1, 0, 0, 0]
    body.inertia = [2 * mass * radius ** 2 / 5] * 3
    body.explicitinertial = True
    body.add_freejoint(name='probe_free')
    for i, axis in enumerate(np.eye(3)):
        spec.add_actuator(name=f'force_{i}', target='probe_free',
                          trntype=mj.mjtTrn.mjTRN_JOINT, gear=[*axis, 0, 0, 0],
                          gainprm=[1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                          ctrllimited=False, forcelimited=False)
    body.add_geom(name='probe', type=mj.mjtGeom.mjGEOM_SPHERE, size=[radius, 0, 0])
    model = spec.compile()
    data = mj.MjData(model)
    data.ctrl[:] = [1., 0., mass * 9.81]
    for _ in range(8):
        mj.mj_step(model, data)
    np.testing.assert_allclose(data.qvel[:3], [.004 / mass, 0., 0.], atol=1e-12)
    assert not any(w.number for w in data.warning)
    return {'compiled': True, 'step_seconds': float(data.time), 'velocity': data.qvel[:3].tolist()}


def tetrahedron():
    vertices = np.array([[1, 1, 1], [-1, -1, 1], [-1, 1, -1], [1, -1, -1]], dtype=float) * .01
    faces = []
    for omitted in range(4):
        face = [i for i in range(4) if i != omitted]
        normal = np.cross(vertices[face[1]] - vertices[face[0]], vertices[face[2]] - vertices[face[0]])
        if normal @ vertices[face].mean(axis=0) < 0:
            face[1], face[2] = face[2], face[1]
        faces.append(face)
    faces = np.array(faces)
    spec = mj.MjSpec()
    mesh = spec.add_mesh(name='tetra', uservert=vertices.ravel(), userface=faces.ravel())
    spec.worldbody.add_geom(type=mj.mjtGeom.mjGEOM_SDF, meshname=mesh.name)
    model = spec.compile()
    data = mj.MjData(model)
    mj.mj_forward(model, data)
    root, count = int(model.mesh_octadr[0]), int(model.mesh_octnum[0])
    leaves = np.flatnonzero((model.oct_child[root:root + count] == -1).all(axis=1))
    neg = np.argwhere(model.oct_coeff[root + leaves] < -1e-6)
    node, corner = leaves[neg[:, 0]], neg[:, 1]
    box = model.oct_aabb[root + node]
    bits = np.column_stack([corner & 1, (corner >> 1) & 1, (corner >> 2) & 1])
    local = box[:, :3] + (2 * bits - 1) * box[:, 3:]
    world = local @ data.geom_xmat[0].reshape(3, 3).T + data.geom_xpos[0]
    normals = np.cross(vertices[faces[:, 1]] - vertices[faces[:, 0]], vertices[faces[:, 2]] - vertices[faces[:, 0]])
    normals /= np.linalg.norm(normals, axis=1)[:, None]
    violation = (world @ normals.T - np.einsum('ij,ij->i', vertices[faces[:, 0]], normals)).max(axis=1)
    return int((violation > 1e-6).sum())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--variant', choices=['patched', 'control'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = {'distribution': importlib.metadata.version('mujoco'), 'force_probe': force_probe(),
              'tetra_wrong_sign_corner_records': tetrahedron(), 'variant': args.variant}
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    if args.variant == 'patched':
        assert result['tetra_wrong_sign_corner_records'] == 0, result
    else:
        assert result['tetra_wrong_sign_corner_records'] > 0, result
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
