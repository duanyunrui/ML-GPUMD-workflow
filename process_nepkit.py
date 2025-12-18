#!/usr/bin/env python3
import argparse
import os
import re

def parse_args():
    parser = argparse.ArgumentParser(
        description="移除 .xyz（ExtXYZ）文件中每帧第二行的 Config_type=\"\" 字段"
    )
    parser.add_argument("input_file", help="输入 .xyz 文件路径")
    parser.add_argument("--output", default="clean_no_config_type.xyz",
                        help="输出文件路径（移除后的）")
    return parser.parse_args()

def process_file(input_file, output_file):
    with open(input_file, 'r') as fin, open(output_file, 'w') as fout:
        while True:
            # 读第一行（原子数）
            first = fin.readline()
            if not first:
                break
            fout.write(first)
            # 读第二行（注释行）
            second = fin.readline()
            if not second:
                # 如果文件在奇数行结束，跳出
                break
            # 移除 Config_type="" 或类似 Config_type=<anything> 项
            # 使用正则替换
            new_second = re.sub(r'\bConfig_type=\"[^\"]*\"', '', second)
            # 还可以移除多余空格
            new_second = re.sub(r'\s{2,}', ' ', new_second).strip() + '\n'
            fout.write(new_second)
            # 接着读接下来的原子数据行
            # 从第一行我们知道原子数
            try:
                nat = int(first.strip())
            except ValueError:
                # 如果第一行不能转换成整数，则跳至下一帧
                nat = None
            if nat is not None:
                for _ in range(nat):
                    line = fin.readline()
                    if not line:
                        break
                    fout.write(line)
    print(f"处理完成。输入文件：{input_file}")
    print(f"输出文件：{output_file}")

def main():
    args = parse_args()
    if os.path.exists(args.output):
        os.remove(args.output)
    process_file(args.input_file, args.output)

if __name__ == "__main__":
    main()
