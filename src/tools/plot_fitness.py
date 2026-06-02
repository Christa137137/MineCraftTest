import json
import os
import matplotlib.pyplot as plt
from collections import defaultdict
from datetime import datetime

def plot_fitness_over_time(file_path, base_output_dir="outputs/metrics"):
    """
    读取评估追踪数据，取同一时间点的平均值，并生成每个维度的随时间变化图。
    图片将保存在 outputs/metrics/plots_时间戳/ 目录下。
    """
    # 1. 动态生成带时间戳的输出文件夹
    timestamp = datetime.now().strftime("%m%d_%H%M%S")
    output_folder = os.path.join(base_output_dir, f"plots_{timestamp}")
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"已创建输出文件夹: {output_folder}")

    # 数据结构: data[指标名称][时间点] = [值1, 值2, ...]
    data = defaultdict(lambda: defaultdict(list))

    # 2. 读取并解析文件
    if not os.path.exists(file_path):
        print(f"错误：找不到文件 {file_path}")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            try:
                record = json.loads(line)
                time_val = record.get("time")
                fitness_dict = record.get("fitness", {})
                
                # 将每个 fitness 的值追加到对应时间点的列表中
                for key, val in fitness_dict.items():
                    data[key][time_val].append(val)
            except json.JSONDecodeError:
                print(f"跳过无效的 JSON 行: {line}")

    # 3. 对每个 fitness 指标进行平均值计算并绘图
    for fit_key, time_dict in data.items():
        # 获取排序后的时间点列表，保证 X 轴顺序正确
        sorted_times = sorted(time_dict.keys())
        
        # 计算每个时间点的平均值
        averages = [sum(time_dict[t]) / len(time_dict[t]) for t in sorted_times]

        # 4. 开始绘制图表
        plt.figure(figsize=(10, 6))
        plt.plot(sorted_times, averages, marker='o', linestyle='-', linewidth=2, markersize=5)
        
        # [修改点]：强制将 Y 轴的显示范围固定为最低 0，最高 1
        plt.ylim(0, 1)
        
        # 设置图表标题和坐标轴标签
        plt.title(f"{fit_key} over Time", fontsize=14, pad=15)
        plt.xlabel("Time (s)", fontsize=12)
        plt.ylabel(f"Average {fit_key}", fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.7)
        
        # 5. 保存图片
        output_file_path = os.path.join(output_folder, f"{fit_key}.png")
        plt.savefig(output_file_path, bbox_inches='tight')
        plt.close() # 关闭当前画布以释放内存
        
        print(f"已生成并保存图表: {output_file_path}")

if __name__ == "__main__":
    # 替换为你实际的 jsonl 文件相对路径
    target_file = "outputs\\waterrandomtest\\random_0507_172514\\inconsistent_seeds\\eval_trace.jsonl" 
    
    plot_fitness_over_time(target_file)