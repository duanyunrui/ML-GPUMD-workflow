import numpy as np
from ase.io import read, write
from ase import Atoms

# 密度阈值 (g/cm^3)
DENSITY_MIN = 2.2   # 石墨 ~2.26
DENSITY_MAX = 3.5   # 金刚石 ~3.51
AMU_TO_G = 1.66054e-24

in_xyz = "train.xyz"
out_xyz = "filtered.xyz"

filtered = []
densities = []

all_atoms = read(in_xyz, index=":")  # 读取所有帧

for i, atoms in enumerate(all_atoms):
    # 只考虑 C 原子？
    # 如果包含其他原子，可适当过滤
    masses = atoms.get_masses()
    total_mass_g = masses.sum() * AMU_TO_G  # 转为 g

    cell = atoms.get_cell()
    vol_ang3 = abs(np.linalg.det(cell))
    if vol_ang3 == 0:
        continue
    vol_cm3 = vol_ang3 * 1e-24
    density = total_mass_g / vol_cm3

    densities.append(density)
    if DENSITY_MIN <= density <= DENSITY_MAX:
        filtered.append(atoms)

        print(f"Frame {i} density = {density:.3f} g/cm^3 → keep")

print(f"Kept {len(filtered)} / {len(all_atoms)} frames")

if filtered:
    # write 会输出 ext-xyz (包含 lattice / cell 信息) —— 保留原格式
    write(out_xyz, filtered)
    print(f"Wrote filtered frames into {out_xyz}")
