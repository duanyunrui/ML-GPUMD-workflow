#!/usr/bin/env python3
import os
import shutil
from ase.io import read, write
from ase import Atoms

# 参数区 —— 根据你的情况修改
xyz_file = "Ga-total.xyz"      # 包含4800帧的 XYZ 文件
incar_file = "INCAR"
potcar_file = "POTCAR"

total_frames = 4800
num_groups = 8
frames_per_group = total_frames // num_groups   # 600

# 输出主目录（可修改）
output_root = "single_point_runs"

# 检查 INCAR & POTCAR 存在
if not os.path.isfile(incar_file):
    raise FileNotFoundError(f"INCAR 文件 {incar_file} 未找到")
if not os.path.isfile(potcar_file):
    raise FileNotFoundError(f"POTCAR 文件 {potcar_file} 未找到")

# 创建输出根目录
os.makedirs(output_root, exist_ok=True)

# 使用 ASE 读取所有帧 （index=":" 读取所有帧）  
# 注意：如果文件极大、在内存受限情况下，可能需要分批读取。
atoms_list = read(xyz_file, index=":")  # 生成一个 list of Atoms 对象 :contentReference[oaicite:1]{index=1}

if len(atoms_list) != total_frames:
    print(f"警告：读取到的帧数为 {len(atoms_list)}，但你期望 {total_frames}。请确认。")

for frame_idx, atoms in enumerate(atoms_list):
    group_idx = frame_idx // frames_per_group
    if group_idx >= num_groups:
        group_idx = num_groups - 1    # 最后一组可能多余
    
    group_folder = os.path.join(output_root, f"group_{group_idx+1:02d}")
    os.makedirs(group_folder, exist_ok=True)
    
    frame_folder = os.path.join(group_folder, f"frame_{frame_idx+1:05d}")
    os.makedirs(frame_folder, exist_ok=True)
    
    # 输出为 VASP POSCAR 格式
    poscar_path = os.path.join(frame_folder, "POSCAR")
    write(poscar_path, atoms, format="vasp", direct=True, vasp5=True)
    
    # 复制 INCAR 和 POTCAR
    shutil.copy(incar_file, frame_folder)
    shutil.copy(potcar_file, frame_folder)
    
    if (frame_idx+1) % 100 == 0 or frame_idx == total_frames-1:
        print(f"已处理帧 {frame_idx+1}/{total_frames}")

print("✅ 完成：所有帧转换并分类完毕。")
