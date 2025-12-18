merge.py：用于将多个文件夹下的单点能计算结果整合为train.xyz文件
22merge.py: 提取virial方法略不同
rm_F_100.py：用于筛选train.xyz中原子力大于100的构型
rm_E_0.py：用于筛选train.xyz中能量大于0的构型
filter_E&F.py：用于同时筛去原子力大于100以及能量大于0的构型
count_zhen.py：用于统计train.xyz文件包含多少帧
process_nepkit.py：用于处理neptrainkit软件输出的train.xyz,其中包含Config_type=""字段，需去掉。否则该train.xyz不适配filter_E&F.py
C_density_filter.py: 用于筛选碳密度位于石墨与金刚石之间的帧。
extract.py: 用于提取train.xyz或者test.xyz中的指定几帧，一般用于删除某些帧，用法：extract.py -i train.xyz -o out.xyz -f 8241

delete_frame.py与2del_frame.py: 删除某些帧，2del_frame.py 是简化版，delete_frame.py是精细版，用法为：python delete_frames.py train.xyz new.xyz 1,5,7,20 --one-based      如果帧数以1开头，需要加one-based。