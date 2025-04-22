# @Version : 1.00
# @Author : Senyan
# @File : get_arXiv_article.py
# @Time : 2025/4/22 17:40

import mysql.connector
import requests
import feedparser

def get_arxiv_papers(query="computer science", max_results=10):
    base_url = "http://export.arxiv.org/api/query?"
    params = {
        "search_query": query.replace(" ", "+"),
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending"
    }

    response = requests.get(base_url, params=params)
    if response.status_code != 200:
        print("API request failed")
        return []

    feed = feedparser.parse(response.text)
    papers = []

    for entry in feed.entries:
        title = entry.title
        authors = ", ".join(author.name for author in entry.authors)
        publish_date = entry.published
        source = entry.id  # article arXiv URL
        abstract = entry.summary.replace("\n", " ")
        citations = "N/A"  # arXiv API does not provide direct reference information

        papers.append((title, authors, publish_date, source, abstract, citations))

    return papers

#  connect MySQL database
def create_connection():
    try:
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='030715',
            database='papers_db'
        )
        return conn
    except mysql.connector.Error as err:
        print(f"failed: {err}")
        exit(1)

def create_table(cursor):
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS papers (
        id INT AUTO_INCREMENT PRIMARY KEY,
        title VARCHAR(255) NOT NULL UNIQUE,  
        authors TEXT,
        publish_date VARCHAR(50),
        source VARCHAR(255),
        abstract TEXT,
        citations TEXT
    ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    """)

def insert_titles(cursor, titles):
    insert_query = """
        INSERT INTO papers (title, authors, publish_date, source, abstract, citations) VALUES (%s, %s, %s, %s, %s, %s) 
        ON DUPLICATE KEY UPDATE abstract=VALUES(abstract), citations=VALUES(citations)
    """
    cursor.executemany(insert_query, titles)

all_papers = get_arxiv_papers(query="artificial intelligence", max_results=20)

connection = create_connection()
cursor = connection.cursor()

create_table(cursor)

if all_papers:
    insert_titles(cursor, all_papers)

connection.commit()
cursor.close()
connection.close()

print(f"get {len(all_papers)}  arXiv data successfully!")
