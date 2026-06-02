import os
import re
import matplotlib.pyplot as plt
from datetime import datetime

def plot_new_bugs_from_log(log_file_path, output_dir="outputs/metrics"):
    """
    解析日志文件，以第一条日志的时间为起点 (0秒)，
    统计并绘制 "New Unique" 不一致性随相对时间变化的累积图。
    """
    if not os.path.exists(log_file_path):
        print(f"[错误] 找不到日志文件: {log_file_path}")
        return

    # 用于匹配日志行首时间戳的正则表达式，例如: [2026-05-07 23:23:16]
    time_pattern = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]")
    
    first_time = None
    times = [0.0]      # X轴：相对时间（秒），初始为0
    counts = [0]       # Y轴：累积发现数量，初始为0
    current_count = 0

    print("正在解析日志文件...")
    with open(log_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            # 尝试提取时间戳
            match = time_pattern.search(line)
            if not match:
                continue
                
            time_str = match.group(1)
            try:
                current_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
                
            # 锁定第一条日志的时间作为 T=0 起点
            if first_time is None:
                first_time = current_time
                print(f"日志起始时间已锁定: {first_time}")

            # 寻找新增的独特漏洞记录 (忽略 Redundant)
            if "[Duplicate Checker] New Unique:" in line:
                current_count += 1
                rel_seconds = (current_time - first_time).total_seconds()
                
                times.append(rel_seconds)
                counts.append(current_count)

    if current_count == 0:
        print("[提示] 日志中没有发现任何 'New Unique' 的记录，无法绘图。")
        return

    # 准备输出文件夹
    timestamp_str = datetime.now().strftime("%m%d_%H%M%S")
    output_folder = os.path.join(output_dir, f"log_plots_{timestamp_str}")
    os.makedirs(output_folder, exist_ok=True)

    # 开始绘图
    plt.figure(figsize=(10, 6))
    
    # 使用阶梯图 (step plot) 最适合展示这种离散的累积触发事件
    plt.step(times, counts, where='post', color='red', linewidth=2, marker='o', markersize=4)
    
    plt.title("Cumulative New Inconsistencies Discovered (From Log)", fontsize=14, pad=15)
    plt.xlabel("Relative Time (Seconds)", fontsize=12)
    plt.ylabel("Total Unique Bugs Found", fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # 强制 Y 轴显示整数刻度 (因为 Bug 数量只能是整数)
    from matplotlib.ticker import MaxNLocator
    plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))
    
    # 保存图片
    output_file_path = os.path.join(output_folder, "new_bugs_from_log.png")
    plt.savefig(output_file_path, bbox_inches='tight')
    plt.close()
    
    print(f"解析完成！共发现 {current_count} 个新漏洞。")
    print(f"图表已成功保存至: {output_file_path}")


if __name__ == "__main__":
    # 请将这里的路径替换为你实际运行产生的 .log 文件路径
    # 例如: "outputs/watertest/proposed_0507_232316/run.log"
    target_log_file = "outputs\watertest\proposed_0510_013259" 
    
    plot_new_bugs_from_log(target_log_file)