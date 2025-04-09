import mysql.connector
from tkinter import *
from tkinter import messagebox
from datetime import datetime
import json

# Connect to MySQL Database
def connect_to_db():
    # Read JSON config document
    with open('selected_config.json', 'r') as file:
        config = json.load(file)  # Analyze JSON document
    
    # Make sure the JSON structure is correct
    required_keys = ["host", "database", "user", "password"]
    for key in required_keys:
        if key not in config or not config[key].strip():
            print(f"Error: '{key}' is missing or empty in selected_config.json")
            return None
    
    # Connect to database
    try:
        connection = mysql.connector.connect(
            host=config["host"],
            database=config["database"],
            user=config["user"],
            password=config["password"]
        )
        return connection  # Return the connection object
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None

# Insert new article and authors into the database
def save_to_db():
    try:
        confirm = messagebox.askyesno("Confirm", "Are you sure you want to save this data?")
        if not confirm:
            return

        conn = connect_to_db()
        cursor = conn.cursor()

        # Get article data
        title = title_entry.get()
        content = content_entry.get()
        abstract = abstract_entry.get()
        reference = reference_entry.get()
        url = url_entry.get()
        published_date = date_entry.get()

        # Validate required fields
        if not all([title, content, abstract, reference, url, published_date]):
            messagebox.showerror("Error", "Please fill in all required fields, "
                                "if don't know clearly, please enter 'none' ")
            return

        # Validate date format
        if not validate_date(published_date):
            messagebox.showerror("Error", "Please enter a valid date in YYYY-MM-DD format.")
            return

        # Insert article
        cursor.execute("""
            INSERT INTO articles (title, content, abstract, url, published_date)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (title, content, abstract, reference, url, published_date))
        article_id = cursor.lastrowid

        # Process authors
        authors = []
        for author in authors_rows:
            last = author['last'].get().strip()
            first = author['first'].get().strip()
            middle = author['middle'].get().strip()
            
            if not last or not first:
                messagebox.showerror("Error", "Author must have at least Last and First Name")
                return
            
            full_name = f"{first} {middle} {last}" if middle else f"{first} {last}"
            authors.append((first, middle, last, full_name))

        # Insert authors and relationships
        for first, middle, last, full_name in authors:
            cursor.execute("""
                INSERT INTO authors (first_name, middle_name, last_name, full_name)
                VALUES (%s, %s, %s, %s)
            """, (first, middle, last, full_name))
            author_id = cursor.lastrowid
            cursor.execute("""
                INSERT INTO article_authors (article_id, author_id)
                VALUES (%s, %s)
            """, (article_id, author_id))

        conn.commit()
        cursor.close()
        conn.close()

        messagebox.showinfo("Success", "Data saved successfully!")
        if messagebox.askyesno("Continue?", "Add another article?"):
            clear_form()
        else:
            root.quit()
    except mysql.connector.Error as err:
        messagebox.showerror("Error", f"Database error: {err}")

def validate_date(date_str):
    try:
        datetime.strptime(date_str, "%Y-%m-%d")  # Attempt to parse the date
        return True
    except ValueError:
        return False

def clear_form():
    title_entry.delete(0, END)
    content_entry.delete(0, END)
    abstract_entry.delete(0, END)
    reference_entry.delete(0, END)
    url_entry.delete(0, END)
    date_entry.delete(0, END)
    # Clear all author entries
    for author in authors_rows:
        author['last'].delete(0, END)
        author['middle'].delete(0, END)
        author['first'].delete(0, END)
    # Keep only the first author row
    while len(authors_rows) > 1:
        remove_author_row(authors_rows[-1]['frame'])

# Author management functions
def add_author_row():
    row_frame = Frame(author_frame)
    row_frame.grid(row=len(authors_rows)+1, column=0, columnspan=4, sticky="ew")

    last_entry = Entry(row_frame, width=15, justify="left")
    last_entry.grid(row=0, column=0, padx=(0,2), sticky="w")
    middle_entry = Entry(row_frame, width=15, justify="left")
    middle_entry.grid(row=0, column=1, padx=2, sticky="w")
    first_entry = Entry(row_frame, width=15, justify="left")
    first_entry.grid(row=0, column=2, padx=(2,0), sticky="w")

    remove_btn = Button(row_frame, text="-", command=lambda f=row_frame: remove_author_row(f))
    remove_btn.grid(row=0, column=3, padx=5, sticky="e")
    
    authors_rows.append({
        'frame': row_frame,
        'last': last_entry,
        'middle': middle_entry,
        'first': first_entry
    })

def remove_author_row(target_frame):
    if len(authors_rows) <= 1:
        return
    for author in authors_rows:
        if author['frame'] == target_frame:
            author['frame'].destroy()
            authors_rows.remove(author)
            break

# Create main window
root = Tk()
root.title("Article Management System")

# Article fields
Label(root, text="Title*").grid(row=0, column=0, sticky=W, padx=10, pady=5)
title_entry = Entry(root, width=40)
title_entry.grid(row=0, column=1, columnspan=3, sticky=W, padx=10)

Label(root, text="Content").grid(row=1, column=0, sticky=W, padx=10, pady=5)
content_entry = Entry(root, width=40)
content_entry.grid(row=1, column=1, columnspan=3, sticky=W, padx=10)

Label(root, text="Abstract*").grid(row=2, column=0, sticky=W, padx=10, pady=5)
abstract_entry = Entry(root, width=40)
abstract_entry.grid(row=2, column=1, columnspan=3, sticky=W, padx=10)

Label(root, text="Reference*").grid(row=3, column=0, sticky=W, padx=10, pady=5)
reference_entry = Entry(root, width=40)
reference_entry.grid(row=3, column=1, columnspan=3, sticky=W, padx=10)

Label(root, text="URL*").grid(row=4, column=0, sticky=W, padx=10, pady=5)
url_entry = Entry(root, width=40)
url_entry.grid(row=4, column=1, columnspan=3, sticky=W, padx=10)

Label(root, text="Published Date* (YYYY-MM-DD)").grid(row=5, column=0, sticky=W, padx=10, pady=5)
date_entry = Entry(root, width=40)
date_entry.grid(row=5, column=1, columnspan=3, sticky=W, padx=10)

# Author management
author_frame = Frame(root)
author_frame.grid(row=6, column=0, columnspan=4, sticky=W, padx=10, pady=10)

author_frame.columnconfigure(0, minsize=120, weight=1, uniform="author_cols")
author_frame.columnconfigure(1, minsize=120, weight=1, uniform="author_cols")
author_frame.columnconfigure(2, minsize=120, weight=1, uniform="author_cols")

# Author headers
Label(author_frame, text="Last Name*\n" "", width=15, anchor="w").grid(row=0, column=0, padx=(0,2), sticky="w")
Label(author_frame, text="Middle Name\n" "(Option)", width=15, anchor="w").grid(row=0, column=1, padx=2, sticky="w")
Label(author_frame, text="First Name*\n" "", width=15, anchor="w").grid(row=0, column=2, padx=(2,0), sticky="w")

authors_rows = []
add_author_row()  # Initial author row

# Add author controls
Button(root, text="+ Add Author", command=add_author_row).grid(row=7, column=1, sticky=W, pady=5)

# Save button
Button(root, text="Save Article", command=save_to_db, bg="#4CAF50", fg="blue").grid(row=7, column=2, pady=20, sticky=W)

root.mainloop()
