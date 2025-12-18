#!/bin/bash
#SBATCH -J c4-scp
#SBATCH -N 1
#SBATCH -n 28
#SBATCH --ntasks-per-node=28
#SBATCH --partition=sciences
#SBATCH --output=%j.out
#SBATCH --error=%j.err

# 软件路径
export vasp_path="/data/app/vasp6.3.2/vasp.6.3.2"

# 环境变量
source /data/app/intel2022.3.1/setvars.sh > /dev/null 2>&1
export PATH="${vasp_path}/bin:${PATH}"

# 错误状态：脚本默认遇到错误就退出，这里我们稍改逻辑
set -u
# 注：我们先不启用 set -e，因为希望在子目录出错时继续
ulimit -s unlimited
ulimit -l unlimited

# 用 srun 或 mpirun 执行 VASP（根据你的集群环境可选）
run_vasp() {
  mpirun -np "${SLURM_NTASKS}" "${vasp_path}/bin/vasp_std" | tee vasp.out
}

progress_file="progress.log"
: > "$progress_file"   # 清空旧记录

for step in $(seq 2365 1 3040); do
  d=$(printf "frame_%05d" "$step")
  if [ ! -d "$d" ]; then
    echo "目录不存在：$d，跳过" | tee -a "$progress_file"
    continue
  fi

  echo ">>> [$d] 开始：$(date)" | tee -a "$progress_file"
  cd "$d" || { echo "无法进入目录 $d, 跳过" | tee -a "../$progress_file"; cd ..; continue; }

  if [ -s OUTCAR ] || [ -f DONE ]; then
    echo "    已存在 OUTCAR/DONE，跳过" | tee -a "../$progress_file"
    cd ..
    continue
  fi

  : > vasp.out

  # 运行 VASP，并捕捉退出代码
  run_vasp 2>&1 | tee -a vasp.out
  exit_code=$?
  
  if [ $exit_code -ne 0 ]; then
    # 出错情况
    echo "    [$d] 出错，退出码 = $exit_code" | tee -a "../$progress_file"
    echo "ERROR: $d failed with exit code $exit_code" >> "../$progress_file"
    cd ..
    # 跳过去，不创建 DONE，不影响其它目录
    continue
  fi

  # 成功时才创建标志文件
  touch DONE
  echo "    [$d] 完成：$(date)" | tee -a "../$progress_file"
  echo "$step" >> "../$progress_file"
  cd ..
done

echo "✅ 全部单点能顺序完成（含跳过出错项） $(date)" | tee -a "$progress_file"
