import csv
import mysql.connector
from mysql.connector import Error
from tkinter import Tk
from tkinter.filedialog import askopenfilename
import json
from dateutil import parser  # Used for parsing dates

def select_csv_file():
    """ Open a file dialog to select a CSV file. """
    Tk().withdraw()
    return askopenfilename(
        title="Select CSV File",
        filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
    )

def create_connection():
    """ Establish a connection to the MySQL database using config from a JSON file. """
    with open('selected_config.json', 'r') as file:
        config = json.load(file)
    
    required_keys = ["host", "database", "user", "password"]
    for key in required_keys:
        if key not in config or not config[key].strip():
            print(f"Error: '{key}' missing in config")
            return None
    
    try:
        return mysql.connector.connect(
            host=config["host"],
            database=config["database"],
            user=config["user"],
            password=config["password"]
        )
    except Error as e:
        print(f"Database error: {e}")
        return None

def parse_date(date_str):
    """
    Parse various date formats and convert them to 'YYYY-MM-DD' (MySQL DATE format).
    If the date is invalid or empty, return None.
    """
    if not date_str or not date_str.strip():
        return None
    try:
        parsed_date = parser.parse(date_str)
        return parsed_date.strftime('%Y-%m-%d')
    except Exception:
        print(f"Warning: Could not parse date '{date_str}', setting to NULL")
        return None

def load_csv_data(csv_file_path, batch_size=500):
    """ Load data from CSV into MySQL with title duplicate check. """
    connection = create_connection()
    if not connection:
        return

    cursor = None
    try:
        cursor = connection.cursor()
        article_authors_batch = []
        processed_rows = 0

        try:
            file = open(csv_file_path, 'r', encoding='utf-8')
        except UnicodeDecodeError:
            file = open(csv_file_path, 'r', encoding='gbk')

        with file:
            csv_reader = csv.reader(file)
            headers = next(csv_reader)
            try:
                published_date_idx = headers.index("date")
                authors_idx = headers.index("authors")
            except ValueError:
                print("CSV header missing required 'date' or 'authors' columns.")
                return

            for row_idx, row in enumerate(csv_reader):
                if len(row) < 7:
                    print(f"Skipping row {row_idx + 2}: insufficient columns.")
                    continue

                title = row[0].strip()
                if not title:
                    continue

                # Check for duplicate article title
                cursor.execute("SELECT id FROM articles WHERE title = %s", (title,))
                if cursor.fetchone():
                    print(f"Skipping duplicate title: {title}")
                    continue

                content = row[1].strip() if len(row) > 1 else ''
                abstract = row[2].strip() if len(row) > 2 else ''
                reference = row[3].strip() if len(row) > 3 else ''
                url = row[4].strip() if len(row) > 4 else ''
                published_date = parse_date(row[published_date_idx])

                article_data = (title, content, abstract, reference, url, published_date)
                cursor.execute(
                    """INSERT INTO articles 
                    (title, content, abstract, reference, url, published_date)
                    VALUES (%s, %s, %s, %s, %s, %s)""", 
                    article_data
                )
                article_id = cursor.lastrowid

                authors_str = row[authors_idx]
                for author_name in authors_str.split(','):
                    author_name = author_name.strip()
                    if not author_name:
                        continue

                    # Try to find author first
                    cursor.execute("SELECT id FROM authors WHERE full_name = %s", (author_name,))
                    result = cursor.fetchone()
                    if result:
                        author_id = result[0]
                    else:
                        # Insert new author
                        cursor.execute("INSERT INTO authors (full_name) VALUES (%s)", (author_name,))
                        author_id = cursor.lastrowid

                    article_authors_batch.append((article_id, author_id))

                processed_rows += 1
                if processed_rows % batch_size == 0:
                    cursor.executemany(
                        "INSERT INTO article_authors (article_id, author_id) VALUES (%s, %s)",
                        article_authors_batch
                    )
                    connection.commit()
                    article_authors_batch = []
                    print(f"Processed {processed_rows} rows")

            if article_authors_batch:
                cursor.executemany(
                    "INSERT INTO article_authors (article_id, author_id) VALUES (%s, %s)",
                    article_authors_batch
                )
            connection.commit()
            print(f"✅ Import complete. Total processed: {processed_rows} rows")

    except Exception as e:
        if connection:
            connection.rollback()
        print(f"❌ Error: {str(e)}")
    finally:
        if cursor: cursor.close()
        if connection: connection.close()

if __name__ == "__main__":
    csv_path = select_csv_file()
    if csv_path:
        print(f"Importing {csv_path}...")
        load_csv_data(csv_path)
    else:
        print("No file selected")
