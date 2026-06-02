import os
import math
from PIL import Image

def merge_images_in_folder(folder_path, output_path="merged_result.png", cols=2):
    """
    将指定文件夹下的所有图片拼接成一张大图。
    
    :param folder_path: 存放图片的文件夹路径
    :param output_path: 拼接后输出的大图路径
    :param cols: 每行排几张图片 (例如 cols=2 时，6张图会排成 3行 x 2列)
    """
    # 1. 查找文件夹下所有的图片文件
    valid_extensions = {'.png', '.jpg', '.jpeg', '.bmp'}
    
    if not os.path.exists(folder_path):
        print(f"[错误] 找不到文件夹: {folder_path}")
        return

    image_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) 
                   if os.path.splitext(f)[1].lower() in valid_extensions]
    
    if not image_files:
        print(f"[提示] 文件夹 {folder_path} 中没有找到任何图片。")
        return

    # 为了保证每次拼接的顺序一致，按文件名排个序
    image_files.sort()

    # 2. 打开所有图片
    images = [Image.open(img_path) for img_path in image_files]
    
    # 3. 计算统一的网格尺寸
    # 获取单张图片的最大宽度和高度（以最大的为准，防止不同大小的图排版错乱）
    cell_width = max(img.width for img in images)
    cell_height = max(img.height for img in images)
    
    # 4. 计算网格的行数
    rows = math.ceil(len(images) / cols)
    
    # 计算大画布的总尺寸
    canvas_width = cols * cell_width
    canvas_height = rows * cell_height
    
    # 5. 创建纯白背景的新画布
    canvas = Image.new('RGB', (canvas_width, canvas_height), 'white')
    
    # 6. 将图片一张张贴进对应的网格位置
    for index, img in enumerate(images):
        row = index // cols
        col = index % cols
        
        # 计算当前图片应该粘贴的左上角 (x, y) 坐标
        x = col * cell_width
        y = row * cell_height
        
        # 粘贴图片
        canvas.paste(img, (x, y))
        
    # 7. 保存最终结果
    canvas.save(output_path)
    print(f"✅ 成功将 {len(images)} 张图片拼接为 1 张！")
    print(f"📁 已保存至: {os.path.abspath(output_path)}")


if __name__ == "__main__":
    # 替换为你刚才生成图表的那个文件夹路径
    # 例如：r"outputs\metrics\plots_0509_120000"
    target_folder = r"outputs\waterrandomtest\random_0514_005030\metrics"  
    
    # 输出的文件名，直接存在当前目录下
    output_filename = target_folder + "\..\\" + "all_metrics_merged.png"
    
    # cols=2 表示每行放2张图。如果有6张图，就会生成一个 3行2列 的大图
    # 如果图太多，你想每行放3张，改成 cols=3 即可
    merge_images_in_folder(target_folder, output_filename, cols=2)