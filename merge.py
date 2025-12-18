#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prepare_train_test_with_ase.py

从多个根目录下 “frame_*” 文件夹读取结构（CONTCAR + OUTCAR）；
保留帧-目录映射，不打乱顺序；
按指定比例抽取 test，其余为 train；
分别输出 train.xyz 和 test.xyz。
"""

import os
import glob
import random
import numpy as np
from ase import io

# ——— 用户参数 ———
#root_dirs = [
#    "dg/100",
#    # … 请添加你的所有根目录
#]
root_dirs = []
# growth
root_dirs += [os.path.join("growth", name) for name in
              ["2c", "3c", "4-1c", "4-2c", "5c", "6c", "20c", "dissolve"]]

# interface
root_dirs += [os.path.join("interface", name) for name in
              ["g1", "g2", "g3", "d1", "d2", "d3"]]

# ratio: 1c ~ 22c
root_dirs += [os.path.join("ratio", f"{i}c") for i in range(1, 23)]

# surface
root_dirs += [os.path.join("surface", name) for name in
              ["d100", "d110", "d111", "ga", "gb", "gc"]]

# 单独根目录
root_dirs += ["purega"]

#dg
root_dirs += [os.path.join("dg", name) for name in
              [ "311", "100", "110", "111"]]
#plus_c
root_dirs += [os.path.join("plus_c", name) for name in
              ["v-d100-g", "v-d110-g", "v-d111-g"]]


out_train_xyz = "train.xyz"
out_test_xyz  = "test.xyz"
test_fraction = 0.00   # 每个根目录抽取 test_fraction 作测试
seed = 1234            # 随机种子，保证可重复
factor = 6.2415e-4      # 单位转化 eV/Å³ per kB
contcar_name = "CONTCAR"
outcar_name = "OUTCAR"

# ——— 辅助函数 ———

def read_frame_folder(frame_folder, root_folder_name=None, frame_folder_name=None):
    """
    读取一个 frame 文件夹：读取结构 + 解析 OUTCAR；
    返回 ASE Atoms 对象 （附加 metadata root_folder & frame_folder）。
    """
    contcar_path = os.path.join(frame_folder, contcar_name)
    if not os.path.exists(contcar_path):
        contcar_path = os.path.join(frame_folder, "POSCAR")
        if not os.path.exists(contcar_path):
            raise FileNotFoundError(f"No {contcar_name} or POSCAR in {frame_folder}")

    atoms = io.read(contcar_path)

    N = len(atoms)
    forces = np.zeros((N,3), dtype=float)
    energy = None
    stress_tensor = None

    outcar_path = os.path.join(frame_folder, outcar_name)
    if os.path.exists(outcar_path):
        with open(outcar_path, 'r') as f:
            lines = f.readlines()
        # 能量
        for line in reversed(lines):
            if "free  energy   TOTEN" in line:
                parts = line.split()
                try:
                    energy = float(parts[4])
                except:
                    pass
                break
        if energy is None:
            energy = 0.0

        # 应力 — 从 “vdW” 行开始，在其下五行范围内寻找 “total” 行
        stress_tensor = None
        for i, line in enumerate(lines):
            if "vdW" in line:
                # 从该行下一行开始，最多往下5行
                for j in range(i+1, min(i+6, len(lines))):
                    l2 = lines[j].rstrip('\n')
                    if l2.lstrip().startswith("Total"):
                    #if "Total" in l2.lower():  # 支持大小写
                        vals = l2.split()
                        # 假设该行末 6 个数值为应力张量分量（xx yy zz xy xz yz）
                        if len(vals) >= 6:
                            try:
                                fvals = list(map(float, vals[-6:]))
                                stress_tensor = np.array([
                                    [fvals[0], fvals[3], fvals[5]],
                                    [fvals[3], fvals[1], fvals[4]],
                                    [fvals[5], fvals[4], fvals[2]]
                                ], dtype=float)
                            except ValueError:
                                stress_tensor = None
                        break
                break
        if stress_tensor is not None:
            stress_tensor = stress_tensor
        else:
            print(f"Warning: Could not locate 'vdW' -> 'total' lines for stress in {outcar_path}")
            stress_tensor = np.zeros((3,3), dtype=float)

        # 原子力
        for i, line in enumerate(lines):
            if "POSITION" in line and "TOTAL-FORCE" in line:
                start = i + 2
                k = 0
                for j in range(start, len(lines)):
                    parts = lines[j].split()
                    if len(parts) < 4:
                        break
                    try:
                        fx = float(parts[-3])
                        fy = float(parts[-2])
                        fz = float(parts[-1])
                        forces[k,:] = [fx, fy, fz]
                        k += 1
                        if k >= N:
                            break
                    except:
                        break
                break
    else:
        print(f"Warning: {outcar_name} not found in {frame_folder}")
        energy = 0.0
        stress_tensor = np.zeros((3,3), dtype=float)

    atoms.info["energy"] = energy
    atoms.arrays["forces"] = forces
    atoms.info["stress"] = stress_tensor
    atoms.info["root_folder"] = root_folder_name
    atoms.info["frame_folder"] = frame_folder_name

    return atoms

def write_extended_xyz(atoms_list, filename):
    """
    将多个 ASE Atoms 对象写入 *.xyz 文件；
    每条结构第二行加入 metadata root & frame。
    """
    with open(filename, "w") as f:
        for atoms in atoms_list:
            N = len(atoms)
            f.write(f"{N}\n")
            cell = atoms.get_cell()
            a = cell[0]; b = cell[1]; c = cell[2]
            lattice_flat = [a[0], a[1], a[2],
                            b[0], b[1], b[2],
                            c[0], c[1], c[2]]
            lattice_str = " ".join(f"{x:.14g}" for x in lattice_flat)
            energy = atoms.info.get("energy", 0.0)
            free_energy = energy
            stress = atoms.info.get("stress", np.zeros((3,3), dtype=float))
            stress_flat = [stress[i,j] for i in range(3) for j in range(3)]
            stress_str = " ".join(f"{x:.14g}" for x in stress_flat)
            pbc = atoms.get_pbc()
            pbc_str = " ".join("T" if v else "F" for v in pbc)

            root_folder = atoms.info.get("root_folder", "")
            frame_folder = atoms.info.get("frame_folder", "")

            second_line = (
                f'Lattice="{lattice_str}" '
                f'Properties=species:S:1:pos:R:3:forces:R:3 '
                f'energy={energy:.8f} '
                f'Virial="{stress_str}" '
                f'free_energy={free_energy:.8f} '
                f'pbc="{pbc_str}" '
                f'root="{root_folder}" '
                f'frame="{frame_folder}"'
            )
            f.write(second_line + "\n")

            positions = atoms.get_positions()
            forces = atoms.arrays["forces"]
            symbols = atoms.get_chemical_symbols()
            for sym, pos, force in zip(symbols, positions, forces):
                x,y,z = pos
                fx,fy,fz = force
                f.write(f"{sym} {x:.8f} {y:.8f} {z:.8f} {fx:.8f} {fy:.8f} {fz:.8f}\n")

def main():
    random.seed(seed)

    train_structs = []
    test_structs = []
    mapping_log = []

    for root in root_dirs:
        frame_dirs = sorted(glob.glob(os.path.join(root, "frame*")))
        if not frame_dirs:
            print(f"WARNING: No frame folders found in {root}")
            continue

        n_total = len(frame_dirs)
        n_test = max(1, int(n_total * test_fraction))
        # 随机抽取但保持顺序：选取随机但然后排序帧索引
        selected_idx = sorted(random.sample(range(n_total), n_test))
        test_dirs = [ frame_dirs[i] for i in selected_idx ]
        train_dirs = [ frame_dirs[i] for i in range(n_total) if i not in selected_idx ]

        for d in train_dirs:
            atoms = read_frame_folder(d,
                                      root_folder_name=root,
                                      frame_folder_name=os.path.basename(d))
            train_structs.append(atoms)
            mapping_log.append(f"train,{root},{os.path.basename(d)}")
        for d in test_dirs:
            atoms = read_frame_folder(d,
                                      root_folder_name=root,
                                      frame_folder_name=os.path.basename(d))
            test_structs.append(atoms)
            mapping_log.append(f"test,{root},{os.path.basename(d)}")

    print(f"Read total: train = {len(train_structs)}, test = {len(test_structs)}")

    write_extended_xyz(train_structs, out_train_xyz)
    write_extended_xyz(test_structs, out_test_xyz)

    # 写映射日志
    with open("mapping_log.csv", "w") as mf:
        mf.write("split,root,frame\n")
        for line in mapping_log:
            mf.write(line + "\n")

    print(f"Wrote train file: {out_train_xyz} ({len(train_structs)} frames)")
    print(f"Wrote test  file: {out_test_xyz}  ({len(test_structs)} frames)")

if __name__ == "__main__":
    main()
