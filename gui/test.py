def analyze_file(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    # 统计原始数据的总行数
    total_lines = len(lines)

    # 统计去重处理后的行数及重复的行
    unique_lines = set()
    duplicate_lines = set()

    for line in lines:
        if line in unique_lines:
            duplicate_lines.add(line)
        else:
            unique_lines.add(line)

    # 去重后的行数
    unique_line_count = len(unique_lines)

    return total_lines, unique_line_count, duplicate_lines

# 假设文件名为 'data.txt'
file_path = 'results/20231125234854/每个.txt'
total, unique, duplicates = analyze_file(file_path)


print("重复的行有：")
for line in duplicates:
    print(line.strip())
print(f"原始数据总行数: {total}")
print(f"去重处理后的行数: {unique}")