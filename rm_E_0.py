#!/usr/bin/env python3
from ase.io import read, write

input_file = "ase_out.xyz"
output_file = "test_clean.xyz"

# 读取所有帧
traj = read(input_file, index=":")

kept = []
removed = 0

for atoms in traj:
    # 优先从 atoms.info 中读能量
    if "energy" in atoms.info:
        E = atoms.info["energy"]
    else:
        # 否则用 ASE 的能量接口（如果计算过）
        try:
            E = atoms.get_potential_energy()
        except:
            # 如果完全没有能量信息，则默认保留
            E = None

    # 判断能量是否为正
    if E is not None and E > 0:
        removed += 1
        continue

    kept.append(atoms)

# 写回清理后的 xyz
write(output_file, kept)

print(f"总帧数: {len(traj)}")
print(f"保留帧数: {len(kept)}")
print(f"去掉能量为正的帧数: {removed}")
print(f"已写入: {output_file}")
