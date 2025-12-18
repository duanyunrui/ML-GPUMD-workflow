#!/usr/bin/env python3
import argparse
import sys
from ase.io import read, write, iread
from ase import Atoms

def parse_args():
    parser = argparse.ArgumentParser(
        description="逐帧读取 .xyz (或 extended-xyz) 文件，从中提取指定帧写入新的 .xyz 文件。节省内存。"
    )
    parser.add_argument("--input", "-i", required=True,
                        help="输入 xyz 文件路径 (e.g. train.xyz)")
    parser.add_argument("--output", "-o", required=True,
                        help="输出 xyz 文件路径 (e.g. subset.xyz)")
    parser.add_argument("--frames", "-f", required=True,
                        help="要提取的帧索引列表，用逗号分隔 (例如 0,5,10)")
    return parser.parse_args()

def main():
    args = parse_args()

    try:
        frames_to_extract = sorted(set(int(x) for x in args.frames.split(",")))
    except ValueError:
        print("Error: frames 列表格式错误 — 请输入整数索引, 用逗号分隔 (例如 0,5,10)", file=sys.stderr)
        sys.exit(1)

    # 用 iread() 逐帧读取 — 返回一个 generator / iterator
    try:
        traj_iter = iread(args.input, index=":")  # 全帧
    except Exception as e:
        print(f"Error: 无法读取输入文件 {args.input} (iread): {e}", file=sys.stderr)
        sys.exit(1)

    # 输出之前，先确保 output 文件是空/新建的
    # 我们用一个 flag 判断是否写过 header，以便 append 或 overwrite
    first_write = True

    current = 0
    extracted = []

    for atoms in traj_iter:
        # 如果当前帧是我们想提取的
        if current in frames_to_extract:
            extracted.append(atoms.copy())  # 先保存起来

        current += 1
        # 如果已经把所有希望的帧都找到，可以提前跳出
        if len(extracted) >= len(frames_to_extract):
            break

    if not extracted:
        print(f"Warning: 未提取到任何帧 — 检查索引 {frames_to_extract} 是否合理？", file=sys.stderr)
        sys.exit(1)

    # 写入 output
    try:
        write(args.output, extracted, format="xyz", append=False)
    except Exception as e:
        print(f"Error: 无法写入输出文件 {args.output}: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"成功: 从 {args.input} 中提取帧 {frames_to_extract} → {args.output}")

if __name__ == "__main__":
    main()
