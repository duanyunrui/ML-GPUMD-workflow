#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import glob

# ======================
# 1. 根目录配置
# ======================

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
root_dirs += ["purega", "pureC"]

# 输出文件
ERROR_FILE = "error.out"


# ======================
# 2. 工具函数
# ======================

def get_nelm(incar_path: str, default_nelm: int = 60) -> int:
    """从 INCAR 中读取 NELM；如果没有则返回默认值"""
    nelm = default_nelm
    if not os.path.isfile(incar_path):
        return nelm

    with open(incar_path, "r") as f:
        for line in f:
            # 去掉注释（! 或 # 后面）
            raw = line.split("!")[0].split("#")[0]
            if "NELM" in raw.upper():
                try:
                    nelm = int(raw.split("=")[1].split()[0])
                except Exception:
                    pass
    return nelm


def check_convergence(frame_dir: str) -> bool:
    """
    根据 OUTCAR 判断单点能是否收敛：

    1）如果 OUTCAR 中包含 "aborting loop because EDIFF is reached" -> 收敛
    2）否则，统计 DAV:/RMM: 行数 = NELEC，读取 INCAR 中 NELM（默认 60）：
        - 若 NELEC == NELM -> 电子在最大步数内未收敛 -> 不收敛
        - 其它情况 -> 视为不收敛/异常
    """
    outcar = os.path.join(frame_dir, "OUTCAR")
    incar = os.path.join(frame_dir, "INCAR")

    if not os.path.isfile(outcar):
        # 没有 OUTCAR，肯定不收敛
        return False

    nelm = get_nelm(incar)

    converged = False
    nelec = 0

    # 按行扫描，避免一次性读入特别大的 OUTCAR
    with open(outcar, "r", errors="ignore") as f:
        for line in f:
            if "aborting loop because EDIFF is reached" in line:
                converged = True
            if "DAV:" in line or "RMM:" in line:
                nelec += 1

    if converged:
        return True

    # 没有收敛语句，且电子步数达到 NELM -> 明确不收敛
    if nelec >= nelm:
        return False

    # 步数没跑满 NELM 又没有收敛语句，多半是异常终止，也算不收敛
    return False


# ======================
# 3. 主逻辑
# ======================

def main():
    # 清空上一轮 error.out
    with open(ERROR_FILE, "w") as f:
        pass

    total_frames = 0
    conv_frames = 0
    unconv_frames = 0

    for root in root_dirs:
        if not os.path.isdir(root):
            print(f"[跳过] 根目录不存在: {root}")
            continue

        print(f"\n=== 检查根目录: {root} ===")

        # 找到 root 下所有 frame* 子目录
        frame_dirs = sorted(
            d for d in glob.glob(os.path.join(root, "frame*"))
            if os.path.isdir(d)
        )

        if not frame_dirs:
            print("  (无 frame* 目录)")
            continue

        for frame in frame_dirs:
            total_frames += 1
            abs_path = os.path.abspath(frame)

            if check_convergence(frame):
                conv_frames += 1
                print(f"  [OK] 收敛:   {abs_path}")
            else:
                unconv_frames += 1
                print(f"  [FAILED] 不收敛: {abs_path}")
                with open(ERROR_FILE, "a") as f:
                    f.write(abs_path + "\n")

    print("\n===== 统计 =====")
    print(f"总计 frame 目录数:    {total_frames}")
    print(f"收敛:                 {conv_frames}")
    print(f"不收敛/异常:          {unconv_frames}")
    print(f"不收敛路径已写入:     {os.path.abspath(ERROR_FILE)}")


if __name__ == "__main__":
    main()
