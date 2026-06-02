import os
import json
import re
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

def evaluate_results(target_dir, threshold=0.9, gap_limit_min=20):
    """
    清理不达标文件并绘制发现随时间积累的曲线图
    """
    if not os.path.exists(target_dir):
        print(f"Error: Path {target_dir} not found.")
        return

    relevant_data = []
    files = [f for f in os.listdir(target_dir) if f.endswith('.json')]

    # 1. 筛选、审计与物理清理
    for file_name in files:
        file_path = os.path.join(target_dir, file_name)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 判断是否为相关的 evaluation 文件（检查指标是否存在）
            fit_obj = data.get("fitness", {}).get("buoyancy_inconsistency", {})
            if "fitness" not in fit_obj:
                continue # 无关文件，跳过

            score = fit_obj.get("fitness", 0)

            # 判定删除逻辑
            if score < threshold:
                print(f"[Cleanup]: Deleting low-score seed: {file_name} (Score: {score})")
                os.remove(file_path)
            else:
                # 提取文件名中的时间戳
                # 格式: evaluation_0203_180119526846_9379.json
                # 匹配 0203 (MMDD) 和 180119526846 (HHMMSS + 微秒)
                match = re.search(r'evaluation_(\d{4})_(\d{12})_', file_name)
                if match:
                    time_str = match.group(1) + match.group(2)
                    dt = datetime.strptime(time_str, "%m%d%H%M%S%f")
                    relevant_data.append(dt)
        except Exception as e:
            print(f"Error processing {file_name}: {e}")

    if not relevant_data:
        print("No valid data found to plot.")
        return

    # 2. 时间排序与间隔平滑处理
    relevant_data.sort()
    
    accumulated_minutes = [0]
    bug_counts = [1]
    
    total_effective_time = 0
    
    for i in range(1, len(relevant_data)):
        delta = (relevant_data[i] - relevant_data[i-1]).total_seconds() / 60.0
        
        # 如果间隔大于 20 分钟，视为实验中断，将增量设为极小值（如 1 分钟）或 0
        if delta > gap_limit_min:
            delta = 10.0 # 移除长跳跃，只保留一个逻辑间隔
            
        total_effective_time += delta
        accumulated_minutes.append(total_effective_time)
        bug_counts.append(i + 1)

    # 3. 绘图
    plt.figure(figsize=(10, 6))
    plt.step(accumulated_minutes, bug_counts, where='post', color='#2c3e50', linewidth=2)
    plt.fill_between(accumulated_minutes, bug_counts, step="post", alpha=0.2, color='#3498db')
    
    plt.title(f"Cumulative Inconsistencies Discovered (Score >= {threshold})", fontsize=14)
    plt.xlabel("Effective Accumulated Time (Minutes, Gaps Removed)", fontsize=12)
    plt.ylabel("Number of Unique Bugs", fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.6)
    
    # 保存并展示
    save_path = os.path.join(target_dir, "analysis_plot.png")
    plt.savefig(save_path)
    print(f"\n[Analysis Complete]:")
    print(f"- Total valid seeds: {len(relevant_data)}")
    print(f"- Final plot saved to: {save_path}")
    plt.show()

if __name__ == "__main__":
    # 使用你刚才提供的路径示例
    target_path = r"src\result_evaluation\watertest"
    evaluate_results(target_path)


# 第一段是1753-1830  第二段2023-2051 第三段2100-2129   2219---