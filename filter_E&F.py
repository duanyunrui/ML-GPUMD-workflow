#!/usr/bin/env python3
import sys
import os
import argparse
from ase.io import iread, write

def parse_args():
    parser = argparse.ArgumentParser(
        description="单遍读取轨迹即可：按力 + 能量筛选；输出保留帧、删除帧、筛选报告写入日志文件。"
    )
    parser.add_argument("input_file", help="输入轨迹文件 (ASE 支持格式)")
    parser.add_argument("--output", default="clean.xyz",
                        help="保留帧输出文件名")
    parser.add_argument("--deleted", default="deleted_frames.xyz",
                        help="删除帧输出文件名")
    parser.add_argument("--log", default="filter_report.log",
                        help="报告输出日志文件名")
    parser.add_argument("--force_max", type=float, default=100.0,
                        help="最大力阈值（帧中最大力必须 < 此值）")
    parser.add_argument("--force_min", type=float, default=-100.0,
                        help="最小力阈值（帧中最小力必须 > 此值）")
    parser.add_argument("--energy_max", type=float, default=0.0,
                        help="能量阈值，若 E > energy_max 则删除该帧")
    return parser.parse_args()

def main():
    args = parse_args()
    inp = args.input_file
    output_file = args.output
    deleted_file = args.deleted
    log_file = args.log
    fmax = args.force_max
    fmin = args.force_min
    emax = args.energy_max

    # 删除旧输出文件，防止追加混乱
    for fname in (output_file, deleted_file, log_file):
        if os.path.exists(fname):
            os.remove(fname)

    total_frames = 0
    kept_count = 0
    deleted_count = 0

    # 流式逐帧读取并筛选
    for atoms in iread(inp, index=":"):
        total_frames += 1

        # 力筛选
        try:
            forces = atoms.get_forces()
        except Exception:
            # 无法获取力 → 视为删除
            write(deleted_file, atoms, append=True)
            deleted_count += 1
            continue

        if not ((forces.max() < fmax) and (forces.min() > fmin)):
            write(deleted_file, atoms, append=True)
            deleted_count += 1
            continue

        # 能量筛选
        E = None
        if "energy" in atoms.info:
            E = atoms.info["energy"]
        else:
            try:
                E = atoms.get_potential_energy()
            except Exception:
                E = None

        if (E is not None) and (E >= emax):
            write(deleted_file, atoms, append=True)
            deleted_count += 1
            continue

        # 通过筛选
        write(output_file, atoms, append=True)
        kept_count += 1

    # 写报告到日志文件
    with open(log_file, "w", encoding="utf-8") as f_log:
        f_log.write(f"输入轨迹: {inp}\n")
        f_log.write(f"总帧数: {total_frames}\n")
        f_log.write(f"保留帧数: {kept_count}\n")
        f_log.write(f"删除帧数: {deleted_count}\n")
        f_log.write(f"保留帧已写入: {output_file}\n")
        f_log.write(f"删除帧已写入: {deleted_file}\n")
        f_log.write(f"日志文件: {log_file}\n")

    # 也在终端输出简短报告
    print(f"筛选完成 — 总帧 {total_frames}, 保留 {kept_count}, 删除 {deleted_count}")
    print(f"详细报告已写入: {log_file}")

if __name__ == "__main__":
    main()
