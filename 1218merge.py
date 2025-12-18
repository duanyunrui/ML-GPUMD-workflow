#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
prepare_train_test_with_ase_final.py

功能：
1) 用户只给若干 root 目录；程序递归遍历所有层级，寻找 basename 以 frame 开头的目录；
2) frame 目录下若无可用 OUTCAR 或 OUTCAR 解析失败 -> 忽略并输出，写 ignored_frames.txt；
3) 仅从 OUTCAR 提取结构/能量/力/virial(stress*vol)；不再使用 CONTCAR/POSCAR 作为 fallback；
4) 按“每个 root 单独抽 test_fraction”划分 train/test（抽样随机，但写入顺序保持原排序）。
输出：
- train.xyz / test.xyz (extxyz)
- mapping_log.csv
- ignored_frames.txt
"""

import os
import glob
import random
import argparse
import numpy as np
from ase import io

DEFAULT_OUTCAR_GLOBS = ("OUTCAR", "OUTCAR_*")


def find_frame_dirs_under_root(root: str, prefix: str = "frame") -> list[str]:
    """在单个 root 下递归查找 basename 以 prefix 开头的目录。"""
    root = os.path.abspath(root)
    frame_dirs: list[str] = []
    if not os.path.isdir(root):
        return frame_dirs
    for dirpath, dirnames, _ in os.walk(root):
        if os.path.basename(dirpath).startswith(prefix):
            frame_dirs.append(dirpath)
    return sorted(set(frame_dirs))


def choose_outcar(frame_dir: str) -> str | None:
    """
    在 frame_dir 下选一个 OUTCAR：
    - 优先 OUTCAR
    - 否则在 OUTCAR_* 中选“最新修改时间”的一个
    """
    exact = os.path.join(frame_dir, "OUTCAR")
    if os.path.exists(exact):
        return exact

    candidates = []
    for pat in DEFAULT_OUTCAR_GLOBS:
        candidates.extend(glob.glob(os.path.join(frame_dir, pat)))
    candidates = [c for c in candidates if os.path.isfile(c)]
    if not candidates:
        return None

    candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return candidates[0]



def parse_last_virial_from_outcar(outcar_path: str) -> np.ndarray | None:
    """
    从 OUTCAR 中解析最后一个“FORCE on cell =-STRESS”块的 Total 行（单位通常是 eV）。
    VASP 常见顺序：XX YY ZZ XY YZ ZX
    映射为对称 3x3：
      [[xx, xy, zx],
       [xy, yy, yz],
       [zx, yz, zz]]
    解析失败返回 None。
    """
    try:
        with open(outcar_path, "r", errors="ignore") as f:
            lines = f.readlines()
    except Exception:
        return None

    starts = [i for i, l in enumerate(lines) if "FORCE on cell =-STRESS" in l]
    if not starts:
        return None

    vir = None
    for s in starts:
        for j in range(s, min(s + 40, len(lines))):
            l = lines[j].strip()
            if l.startswith("Total"):
                nums = []
                for tok in l.split():
                    try:
                        nums.append(float(tok))
                    except ValueError:
                        pass
                if len(nums) >= 6:
                    xx, yy, zz, xy, yz, zx = nums[:6]
                    vir = np.array(
                        [[xx, xy, zx],
                         [xy, yy, yz],
                         [zx, yz, zz]],
                        dtype=float
                    )
                break

    return vir


def read_frame_prefer_outcar(frame_dir: str):
    """
    只从 OUTCAR（ASE vasp-out, index=-1 取最后一步）读取结构/能量/力；
    并从 OUTCAR 解析 virial（FORCE on cell =-STRESS 的 Total）。
    若 OUTCAR 不存在或解析失败，抛异常，由上层忽略该 frame_dir。
    返回：(atoms, source_tag)。
    """
    outcar = choose_outcar(frame_dir)
    if outcar is None:
        raise FileNotFoundError("OUTCAR not found")

    try:
        atoms = io.read(outcar, format="vasp-out", index=-1)

        # 尽量从 atoms.calc 取能量/力；取不到则置零
        try:
            energy = float(atoms.get_potential_energy())
        except Exception:
            energy = 0.0
        try:
            forces = np.array(atoms.get_forces(), dtype=float)
        except Exception:
            forces = np.zeros((len(atoms), 3), dtype=float)

        atoms.info["energy"] = energy
        atoms.arrays["forces"] = forces

        vir = parse_last_virial_from_outcar(outcar)
        atoms.info["virial"] = vir if vir is not None else np.zeros((3, 3), dtype=float)

        return atoms, f"OUTCAR:{os.path.basename(outcar)}"
    except Exception as e:
        raise RuntimeError(f"OUTCAR parse failed: {type(e).__name__}: {e}") from e


def write_extended_xyz(atoms_list, filename: str):
    """
    写 extxyz（Properties=species,pos,forces），并写入 energy、Virial、pbc、root/frame/source。
    注意：这里的 Virial 直接写 OUTCAR 的 “FORCE on cell =-STRESS ... units (eV)” Total（通常已是应力*体积形式）。
    """
    with open(filename, "w") as f:
        for atoms in atoms_list:
            n = len(atoms)
            f.write(f"{n}\n")

            cell = atoms.get_cell()
            a, b, c = cell[0], cell[1], cell[2]
            lattice_flat = [a[0], a[1], a[2], b[0], b[1], b[2], c[0], c[1], c[2]]
            lattice_str = " ".join(f"{x:.14g}" for x in lattice_flat)

            energy = float(atoms.info.get("energy", 0.0))
            vir = atoms.info.get("virial", np.zeros((3, 3), dtype=float))
            vir_flat = [vir[i, j] for i in range(3) for j in range(3)]
            vir_str = " ".join(f"{x:.14g}" for x in vir_flat)

            pbc = atoms.get_pbc()
            pbc_str = " ".join("T" if v else "F" for v in pbc)

            root_folder = atoms.info.get("root_folder", "")
            frame_folder = atoms.info.get("frame_folder", "")
            frame_dir = atoms.info.get("frame_dir", "")
            source = atoms.info.get("source", "")

            second_line = (
                f'Lattice="{lattice_str}" '
                f'Properties=species:S:1:pos:R:3:forces:R:3 '
                f'energy={energy:.8f} '
                f'Virial="{vir_str}" '
                f'pbc="{pbc_str}" '
                f'root="{root_folder}" '
                f'frame="{frame_folder}" '
                f'frame_dir="{frame_dir}" '
                f'source="{source}"'
            )
            f.write(second_line + "\n")

            positions = atoms.get_positions()
            forces = atoms.arrays.get("forces", np.zeros((n, 3), dtype=float))
            symbols = atoms.get_chemical_symbols()

            for sym, pos, frc in zip(symbols, positions, forces):
                f.write(
                    f"{sym} {pos[0]:.8f} {pos[1]:.8f} {pos[2]:.8f} "
                    f"{frc[0]:.8f} {frc[1]:.8f} {frc[2]:.8f}\n"
                )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("roots", nargs="+", help="若干 root 目录；程序将递归寻找 frame* 文件夹")
    ap.add_argument("--prefix", type=str, default="frame", help="frame 目录前缀（默认 frame）")
    ap.add_argument("--test_fraction", type=float, default=0.05, help="每个 root 抽 test 的比例")
    ap.add_argument("--seed", type=int, default=1234, help="随机种子（保证可复现）")
    ap.add_argument("--out_train", type=str, default="train.xyz")
    ap.add_argument("--out_test", type=str, default="test.xyz")
    args = ap.parse_args()

    rng = random.Random(args.seed)

    train_structs, test_structs = [], []
    mapping_log = []
    ignored = []

    roots_sorted = [os.path.abspath(r) for r in args.roots]
    roots_sorted.sort()

    for root in roots_sorted:
        frame_dirs = find_frame_dirs_under_root(root, prefix=args.prefix)
        if not frame_dirs:
            print(f"[WARN] No {args.prefix}* directories under root: {root}")
            continue

        # 预筛：只接受存在可用 OUTCAR 的 frame 目录
        valid_dirs = []
        for d in frame_dirs:
            if choose_outcar(d) is None:
                print(f"[IGNORED] (no OUTCAR) {d}")
                ignored.append(d)
            else:
                valid_dirs.append(d)

        if not valid_dirs:
            print(f"[WARN] No valid frames under root: {root}")
            continue

        n_total = len(valid_dirs)
        n_test = max(1, int(n_total * args.test_fraction))
        test_idx = set(rng.sample(range(n_total), n_test))

        # 按原排序遍历，保持顺序
        for i, frame_dir in enumerate(valid_dirs):
            try:
                atoms, source = read_frame_prefer_outcar(frame_dir)
                atoms.info["root_folder"] = root
                atoms.info["frame_folder"] = os.path.basename(frame_dir)
                atoms.info["frame_dir"] = frame_dir
                atoms.info["source"] = source
            except Exception as e:
                print(f"[IGNORED] (OUTCAR missing/unusable) {frame_dir} :: {e}")
                ignored.append(frame_dir)
                continue

            if i in test_idx:
                test_structs.append(atoms)
                mapping_log.append(f"test,{root},{frame_dir},{source}")
            else:
                train_structs.append(atoms)
                mapping_log.append(f"train,{root},{frame_dir},{source}")

        print(f"[ROOT DONE] {root} : frames={n_total}, test={n_test}")

    print(f"Read total: train={len(train_structs)}, test={len(test_structs)}")

    write_extended_xyz(train_structs, args.out_train)
    write_extended_xyz(test_structs, args.out_test)

    with open("mapping_log.csv", "w") as mf:
        mf.write("split,root,frame_dir,source\n")
        for line in mapping_log:
            mf.write(line + "\n")

    with open("ignored_frames.txt", "w") as f:
        for d in ignored:
            f.write(d + "\n")

    print(f"Wrote: {args.out_train}, {args.out_test}, mapping_log.csv")
    print(f"Ignored frames: {len(ignored)} (see ignored_frames.txt)")


if __name__ == "__main__":
    main()
