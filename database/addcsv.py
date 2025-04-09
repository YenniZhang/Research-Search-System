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
    if not date_str.strip():
        return None  # Handle empty values
    try:
        parsed_date = parser.parse(date_str)  # Automatically detect format
        return parsed_date.strftime('%Y-%m-%d')  # Convert to standard DATE format
    except Exception:
        print(f"Warning: Could not parse date '{date_str}', setting to NULL")
        return None  # Return NULL if parsing fails

def load_csv_data(csv_file_path, batch_size=500):
    """ Load data from a CSV file and insert it into the MySQL database in batches. """
    connection = create_connection()
    if not connection:
        return

    cursor = None
    try:
        cursor = connection.cursor()
        article_authors_batch = []  # Store batch inserts for article-author relationships
        processed_rows = 0

        with open(csv_file_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.reader(file)
            headers = next(csv_reader)  # Read the CSV header
            published_date_idx = headers.index("date")  # Find the index of the date column

            for row_idx, row in enumerate(csv_reader):
                # Parse and format the published_date column
                published_date = parse_date(row[published_date_idx])

                # Insert the article data
                article_data = (row[0], row[1], row[2], row[3], row[4], published_date)
                cursor.execute(
                    """INSERT INTO articles 
                    (title, content, abstract, reference, url, published_date)
                    VALUES (%s, %s, %s, %s, %s, %s)""", 
                    article_data
                )
                article_id = cursor.lastrowid

                # Process authors (assuming they are in the last column)
                authors_str = row[-1]
                for author_name in authors_str.split(','):
                    author_name = author_name.strip()
                    if not author_name:
                        continue

                    # Insert author data (only full_name)
                    cursor.execute(
                        """INSERT INTO authors 
                        (full_name)
                        VALUES (%s)
                        ON DUPLICATE KEY UPDATE
                        full_name=VALUES(full_name)""",
                        (author_name,)
                    )
                    author_id = cursor.lastrowid if cursor.lastrowid != 0 else \
                        cursor.execute("SELECT LAST_INSERT_ID()").fetchone()[0]

                    # Store the article-author relationship for batch insertion
                    article_authors_batch.append((article_id, author_id))

                # Batch processing: Insert every 'batch_size' rows
                processed_rows += 1
                if processed_rows % batch_size == 0:
                    cursor.executemany(
                        """INSERT INTO article_authors 
                        (article_id, author_id) VALUES (%s, %s)""",
                        article_authors_batch
                    )
                    connection.commit()
                    article_authors_batch = []
                    print(f"Processed {processed_rows} rows")

            # Insert remaining article-author relationships
            if article_authors_batch:
                cursor.executemany(
                    "INSERT INTO article_authors (article_id, author_id) VALUES (%s, %s)",
                    article_authors_batch
                )
            connection.commit()
            print(f"Total processed: {processed_rows} rows")

    except Exception as e:
        connection.rollback()
        print(f"Error: {str(e)}")
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
