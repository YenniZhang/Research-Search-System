import pandas as pd
import mysql.connector
import os
import json
import tkinter as tk
from tkinter import filedialog
from mysql.connector import Error

def read_csv_with_fallback(file_path):
    """Attempt to read CSV with multiple encodings to handle encoding issues."""
    encodings = ['utf-8', 'gbk', 'ISO-8859-1']
    for enc in encodings:
        try:
            return pd.read_csv(file_path, encoding=enc)
        except UnicodeDecodeError:
            continue
    raise ValueError("Failed to read CSV with tried encodings.")

def safe_value(val, val_type=None):
    """Sanitize values and convert to appropriate types, handling missing data."""
    if pd.isna(val) or val == "fail":
        return None
    if val_type == "int":
        try:
            return int(val)
        except:
            return None
    if val_type == "float":
        try:
            return float(val)
        except:
            return None
    return str(val).strip() if isinstance(val, str) else val

def connect_db():
    """Establish MySQL connection using config from selected_config.json."""
    try:
        with open('selected_config.json', 'r') as file:
            config = json.load(file)
        
        # Validate required configuration parameters
        required_keys = ["host", "database", "user", "password"]
        for key in required_keys:
            if key not in config or not config[key].strip():
                raise ValueError(f"Missing required config key: {key}")
        
        return mysql.connector.connect(
            host=config["host"],
            database=config["database"],
            user=config["user"],
            password=config["password"]
        )
    except Exception as e:
        print(f"Database connection error: {str(e)}")
        return None

def get_author_id_by_name(cursor, name):
    """Retrieve author_id by full name, handling potential duplicates."""
    query = "SELECT author_id FROM author_profile WHERE full_name = %s"
    cursor.execute(query, (name,))
    results = cursor.fetchall()
    
    if not results:
        return None
    elif len(results) == 1:
        return results[0][0]
    else:
        print(f"[Warning] Multiple entries found for {name}, using first ID: {results[0][0]}")
        return results[0][0]

def select_csv_file():
    """Open file dialog to select CSV file and return path."""
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    file_path = filedialog.askopenfilename(
        title="Select CSV File",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )
    root.destroy()
    return file_path

def main():
    # Select CSV file through GUI dialog
    file_path = select_csv_file()
    if not file_path:
        print("No file selected. Exiting.")
        return

    # Read and preprocess CSV data
    try:
        df = read_csv_with_fallback(file_path)
        df.replace("fail", None, inplace=True)
    except Exception as e:
        print(f"Error processing CSV file: {str(e)}")
        return

    # Establish database connection
    conn = connect_db()
    if not conn:
        return
    
    cursor = conn.cursor()
    update_sql = """
    UPDATE author_profile SET
        bio = %s, email = %s, workplace = %s, job = %s,
        research = %s, reference = %s, article_number = %s, influence = %s
    WHERE author_id = %s
    """

    # Process each row and update database
    update_count = 0
    for _, row in df.iterrows():
        name = safe_value(row.get('full_name'))
        if not name:
            print("Skipping row with missing name")
            continue

        author_id = get_author_id_by_name(cursor, name)
        if not author_id:
            print(f"[Skip] Author not found in database: {name}")
            continue

        # Prepare parameter values with type safety
        params = (
            safe_value(row.get('bio')),
            safe_value(row.get('email')),
            safe_value(row.get('workplace')),
            safe_value(row.get('job')),
            safe_value(row.get('research')),
            None,  # reference field intentionally left blank
            safe_value(row.get('article_number'), 'int'),
            safe_value(row.get('influence'), 'float'),
            author_id
        )

        try:
            cursor.execute(update_sql, params)
            update_count += 1
            print(f"Updated {name} (ID: {author_id})")
        except Error as e:
            print(f"Update failed for {name}: {str(e)}")
            conn.rollback()  # Rollback on individual failure

    # Finalize database operations
    conn.commit()
    cursor.close()
    conn.close()
    print(f"✅ Update complete. {update_count}/{len(df)} records processed.")

if __name__ == "__main__":
    main()
