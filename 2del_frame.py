from ase.io import read, write

images = read("train.xyz", ":")

#frames_to_delete = list(range(10, 21)) + [1, 3, 4]  # 0-based 索引
frames_to_delete =  [8241]

for i in sorted(frames_to_delete, reverse=True):
    del images[i]

write("train_new.xyz", images)
