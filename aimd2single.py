import os
import shutil
from ase.io import read, write

# === 参数设置 ===
traj_file = "XDATCAR"        # 或 "XDATCAR" ／ "OUTCAR"（若 ASE 支持）  
frame_prefix = "frame_"          # 生成文件夹前缀  
step_interval = 3                # 每隔此步提取一帧（1 = 每帧）  
copy_input_files = ["INCAR",  "POTCAR"]  # 要复制/链接到每个子文件夹的输入文件  
# === 结束参数设置 ===

print(f"Reading trajectory from {traj_file} …")
# 读取所有帧
atoms_list = read(traj_file, index=":", format=None)  # format=None 试让 ASE 自动识别

print(f"Total frames read: {len(atoms_list)}")
for i, atoms in enumerate(atoms_list):
    if i % step_interval != 0:
        continue
    dirname = f"{frame_prefix}{i:05d}"
    os.makedirs(dirname, exist_ok=True)
    poscar_path = os.path.join(dirname, "POSCAR")
    write(poscar_path, atoms, format="vasp")
    # 复制或软链接输入文件
    for fname in copy_input_files:
        if os.path.exists(fname):
            dst = os.path.join(dirname, fname)
            # 可选择软链接：
            try:
                os.symlink(os.path.abspath(fname), dst)
            except Exception:
                shutil.copy(fname, dst)
    print(f"Frame {i} → {dirname}/POSCAR")

print("Frame extraction done.")

