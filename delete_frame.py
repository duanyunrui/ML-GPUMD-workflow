#!/usr/bin/env python3
from ase.io import read, write
import argparse


def parse_frame_list(s, one_based=False):
    """
    将用户输入的帧序列文本解析为需要删除的索引列表。
    支持格式：
        5           (单帧)
        3,7,10      (多帧)
        20-50       (范围)
        1,5,10-20   (混合)
    """
    to_delete = set()
    parts = s.split(",")

    for p in parts:
        p = p.strip()
        if "-" in p:
            # 范围
            a, b = p.split("-")
            a, b = int(a), int(b)
            if one_based:
                a -= 1
                b -= 1
            to_delete.update(range(a, b + 1))
        else:
            # 单帧
            idx = int(p)
            if one_based:
                idx -= 1
            to_delete.add(idx)

    return sorted(to_delete)


def main():
    parser = argparse.ArgumentParser(
        description="Delete specific frames or frame ranges from a train.xyz file."
    )
    parser.add_argument("input", help="输入文件，例如 train.xyz")
    parser.add_argument("output", help="输出文件，例如 new_train.xyz")
    parser.add_argument(
        "frames",
        help="要删除的帧编号，例如：5 或 3,7,10 或 20-50 或 1,5,10-20"
    )
    parser.add_argument(
        "--one-based", action="store_true",
        help="使用从 1 开始的帧编号（例如 OUTCAR 习惯）"
    )

    args = parser.parse_args()

    images = read(args.input, ":")
    total = len(images)
    print(f"共有 {total} 帧")

    # 解析用户输入
    del_list = parse_frame_list(args.frames, one_based=args.one_based)
    print(f"准备删除帧索引: {del_list}")

    # 越界检查
    for idx in del_list:
        if idx < 0 or idx >= total:
            raise IndexError(f"帧号 {idx} 越界（共有 {total} 帧）")

    # 删除帧（按降序删除避免索引变化）
    for idx in sorted(del_list, reverse=True):
        del images[idx]

    write(args.output, images)
    print(f"已删除 {len(del_list)} 个帧，输出文件: {args.output}")


if __name__ == "__main__":
    main()
