# @Version : 1.00
# @Author : Senyan
# @File : calc_h_index.py
# @Time : 2025/4/1 14:17

import pandas as pd
from collections import defaultdict

# 读取 Excel 文件
file_path = r"D:\pythoncode\PythonProject\papers_data_arXiv4400.xlsx"
df = pd.read_excel(file_path)

# 提取作者和引用次数列
df_filtered = df[["authors", "citations"]].dropna()

# 确保 citations 是整数型
df_filtered["citations"] = df_filtered["citations"].astype(int)

# 构建 作者 → [引用次数列表] 映射
author_citations = defaultdict(list)

for _, row in df_filtered.iterrows():
    authors = [a.strip() for a in row["authors"].split(",")]
    for author in authors:
        author_citations[author].append(row["citations"])

#  计算 h-index
def calculate_h_index(citations):
    sorted_cits = sorted(citations, reverse=True)
    h = sum(c >= i + 1 for i, c in enumerate(sorted_cits))
    return h

# 构建结果表格
h_index_data = []

for author, cites in author_citations.items():
    h = calculate_h_index(cites)
    h_index_data.append({
        "author": author,
        "h_index": h,
        "total_citations": sum(cites),
        "paper_count": len(cites)
    })

h_index_df = pd.DataFrame(h_index_data)
h_index_df = h_index_df.sort_values(by="h_index", ascending=False).reset_index(drop=True)

# === 6. 保存结果 ===
h_index_df.to_csv("h_index_by_author4400.csv", index=False, encoding="utf-8-sig")
print("h-index ，结果保存为 h_index_by_author.csv")
