import os
import fitz  # PyMuPDF
import re
import csv
from collections import defaultdict

pdf_folder = r"D:\pythoncode\page4400edge\pdfs2500"
output_csv = 'author_citation_adjlist.csv'
fail_log = 'failed_files.txt'

# 黑名单关键词
blacklist = {
    "Engineering", "Mathematics", "Learning", "Deep Learning", "Gradient",
    "Computer", "Abstract", "Theory", "Discrete", "Modeling", "Classification",
    "Phishing", "Sickness", "Comfort", "On Doctrines", "Cartesian",
    "Information", "Semimodules", "Similarity", "Injection", "Improving",
    "Fibered", "Objects", "Evaluation", "Websites", "Attack", "Persona",
    "Tree", "Combining", "Security", "Privacy", "Technology", "Networks"
}


# === 提取全文文本 ===
def extract_text_from_pdf(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        text = ''
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        print(f"❌ 读取失败: {pdf_path}: {e}")
        return ''


# === 作者提取：前20行，检测逗号或and的行 ===
def extract_authors(text):
    lines = text.strip().split('\n')
    nonempty_lines = [line.strip() for line in lines if line.strip()]

    if len(nonempty_lines) < 2:
        return []

    candidate_lines = nonempty_lines[:20]

    for line in candidate_lines:
        if ('@' in line or 'university' in line.lower() or 'department' in line.lower()):
            continue
        if ',' not in line and ' and ' not in line:
            continue

        name_candidates = re.findall(r'\b[A-Z][a-z]+(?: [A-Z][a-z]+)+\b', line)
        filtered = []
        for name in name_candidates:
            if name in blacklist:
                continue
            if len(name.split()) >= 2:
                filtered.append(name)

        if 1 <= len(filtered) <= 8:
            return filtered

    return []


# === 优化：参考文献区域提取（模糊匹配 + 后1/3文本） ===
def extract_references_section(text):
    start = int(len(text) * 0.66)
    tail_text = text[start:]

    keywords = ['references', '参考文献', 'bibliography', 'works cited', 'literature', '参考', '文献']
    pattern = '|'.join(keywords)

    match = re.search(pattern, tail_text, re.IGNORECASE)
    if match:
        return tail_text[match.start():]

    return ''


# === 从编号到引号前提取被引用作者名 ===
def extract_cited_authors(refs_text):
    # 提取编号后到第一个英文引号 or 句号之间的内容
    pattern = re.findall(r'(?:\[\d+\]|\d+\.)\s*(.*?)(?=["“\.])', refs_text)
    cleaned = []

    for raw in pattern:
        author_part = raw.strip().strip(',;:–—')  # 去掉末尾标点
        if 1 <= len(author_part.split()) <= 12:
            cleaned.append(author_part)

    return list(set(cleaned))

# === 写邻接字典格式CSV ===
def write_adjacency_dict(edges, output_csv):
    adjacency_dict = defaultdict(lambda: defaultdict(int))
    for _, source_author, target_author in edges:
        adjacency_dict[source_author][target_author] += 1

    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Name（当前作者）', 'Value（该作者引用过的作者及引用次数）'])
        for author, neighbors in adjacency_dict.items():
            writer.writerow([author, dict(neighbors)])


# === 主函数 ===
def main():
    edges = []
    failed_files = []

    for filename in os.listdir(pdf_folder):
        if filename.lower().endswith('.pdf'):
            filepath = os.path.join(pdf_folder, filename)
            print(f"📄 正在处理: {filename}")
            full_text = extract_text_from_pdf(filepath)

            source_authors = extract_authors(full_text)
            if not source_authors:
                print(f"⚠️ 未提取到作者: {filename}")
                failed_files.append(f"{filename} - 未识别作者")
                continue

            refs_text = extract_references_section(full_text)
            target_authors = extract_cited_authors(refs_text)
            if not target_authors:
                print(f"⚠️ 未提取到参考文献: {filename}")
                failed_files.append(f"{filename} - 未识别参考文献")
                continue

            for source_author in source_authors:
                for target_author in target_authors:
                    edges.append((filename, source_author, target_author))

    # 写邻接表
    write_adjacency_dict(edges, output_csv)

    # 写失败日志
    if failed_files:
        with open(fail_log, 'w', encoding='utf-8') as f:
            f.write("\n".join(failed_files))
        print(f"⚠️ 有 {len(failed_files)} 个文件识别失败，已记录到 {fail_log}")

    print(f"\n✅ 引用邻接表已输出至: {output_csv}")
    print(f"📦 共构建引用边: {len(edges)} 条")


if __name__ == '__main__':
    main()
