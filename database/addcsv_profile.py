import csv
import json
import mysql.connector
from mysql.connector import Error
from tkinter import Tk, filedialog, messagebox

def connect_to_db():
    """ Connect to MySQL database using selected_config.json """
    try:
        with open('selected_config.json', 'r') as file:
            config = json.load(file)
        
        required_keys = ["host", "database", "user", "password"]
        for key in required_keys:
            if key not in config or not config[key].strip():
                messagebox.showerror("Error", f"Missing or empty field in config: {key}")
                return None
        
        return mysql.connector.connect(
            host=config["host"],
            database=config["database"],
            user=config["user"],
            password=config["password"]
        )
    except (FileNotFoundError, json.JSONDecodeError) as e:
        messagebox.showerror("Error", f"Config file error: {e}")
        return None
    except mysql.connector.Error as err:
        messagebox.showerror("Database Error", f"Connection failed: {err}")
        return None

def process_csv(conn, csv_filepath):
    """ Process CSV file by column position """
    cursor = conn.cursor()
    
    with open(csv_filepath, 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)  # Use regular reader to read by column index
        
        # Skip the header row (if present)
        next(reader, None)
        
        for row_num, row in enumerate(reader, 1):
            try:
                # Extract data by column index (based on table definition)
                # Column index mapping: A=0, B=1, C=2, D=3, E=4, F=5, G=6, H=7
                csv_name = row[0].strip().lower()  # Column A: full_name
                bio = row[1].strip()               # Column B: bio
                email = row[2].strip()             # Column C: email
                workplace = row[3].strip()         # Column D: workplace
                job = row[4].strip()               # Column E: job
                research = row[5].strip()          # Column F: research
                reference = row[6].strip()         # Column G: reference
                article_num = row[7].strip()       # Column H: article_num influence (assuming a single value)
                # Ignore columns I/J
                
                # Query existing database records
                cursor.execute("""
                    SELECT author_id, full_name, bio, email, workplace, job, research, reference, article_number, influence 
                    FROM author_profile WHERE LOWER(TRIM(full_name)) = %s
                """, (csv_name,))
                result = cursor.fetchone()
                
                if result:
                    author_id = result[0]
                    current_data = list(result[1:])  # Convert to list for easy modification
                    
                    # Update columns (retain original value if new value is empty)
                    update_data = [
                        row[0].strip() or current_data[0],  # full_name
                        bio or current_data[1],              # bio
                        email or current_data[2],            # email
                        workplace or current_data[3],        # workplace
                        job or current_data[4],              # job
                        research or current_data[5],         # research
                        int(reference) if reference else current_data[6],  # reference
                        int(article_num) if article_num else current_data[7],  # article_number
                        current_data[8],  # influence (not in CSV, retain original value)
                        author_id
                    ]
                    
                    # Execute update query
                    cursor.execute("""
                        UPDATE author_profile SET
                            full_name = %s, bio = %s, email = %s, workplace = %s,
                            job = %s, research = %s, reference = %s, article_number = %s, influence = %s
                        WHERE author_id = %s
                    """, update_data)
                    print(f"Row {row_num}: Updated author ID {author_id}")
                else:
                    print(f"Row {row_num}: No matching author: {csv_name}")
                    
            except IndexError:
                print(f"Row {row_num}: Insufficient columns, skipping")
            except ValueError as e:
                print(f"Row {row_num}: Data format error - {e}")
            except Exception as e:
                print(f"Row {row_num}: Unknown error - {e}")
    
    conn.commit()

def browse_file():
    """ Open file dialog to select a CSV file """
    root = Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(title="Select CSV File", filetypes=[("CSV files", "*.csv")])
    return file_path

if __name__ == '__main__':
    csv_path = browse_file()
    if not csv_path:
        print("No file selected. Exiting.")
        exit()
    
    conn = connect_to_db()
    if conn:
        try:
            process_csv(conn, csv_path)
            print("CSV import completed!")
        finally:
            conn.close()
    else:
        print("Failed to establish database connection")
