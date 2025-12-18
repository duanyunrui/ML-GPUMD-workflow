#!/usr/bin/env python3
from ase.io import read
import sys
# 读取 train.xyz 的所有帧
frames = read(sys.argv[1],index=":")

print("Number of frames in train.xyz:", len(frames))
