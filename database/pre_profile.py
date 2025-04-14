import mysql.connector
import tkinter as tk
from tkinter import ttk, messagebox
import json
import sys
import subprocess


# Function to run the other Python script

def run_delete_script():
    try:
        
        subprocess.run(["python", "delete_profile.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running script: {e}")


def run_autocheck_script():
    try:
        
        subprocess.run(["python", "autocheck_profile.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running script: {e}")


def run_addcsv_script():
    try:
        
        subprocess.run(["python", "addcsv_profile.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running script: {e}")


# Global variables for pagination control
current_page = 1
total_pages = 1
rows_per_page = 30  # Number of rows to display per page

def run_clear_script():
    # Confirm data deletion
    result = messagebox.askyesno(
        "Confirm Deletion",
        "This action will delete all data in the database. Are you sure you want to proceed?"
    )
    
    if result:
        try:
            subprocess.run(["python", "clear_profile.py"], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error running script: {e}")
    else:
        print("Database clearing operation was cancelled.")

# Database connection
def connect_to_db():
    with open('selected_config.json', 'r') as file:
        config = json.load(file)
    
    required_keys = ["host", "database", "user", "password"]
    for key in required_keys:
        if key not in config or not config[key].strip():
            messagebox.showerror("Error", f"Missing or empty field in config: {key}")
            return None
    
    try:
        return mysql.connector.connect(
            host=config["host"],
            database=config["database"],
            user=config["user"],
            password=config["password"]
        )
    except mysql.connector.Error as err:
        messagebox.showerror("Database Error", f"Connection failed: {err}")
        return None

# Import authors data function
def import_authors():
    conn = connect_to_db()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        
        # Execute data import SQL
        sql = """
        INSERT INTO author_profile (author_id, full_name)
        SELECT id, full_name FROM authors
        ON DUPLICATE KEY UPDATE full_name = VALUES(full_name)
        """
        cursor.execute(sql)
        conn.commit()
        messagebox.showinfo("Success", "Author data import completed!")
        
    except mysql.connector.Error as err:
        conn.rollback()
        messagebox.showerror("Import Error", f"Data import failed: {err}")
    finally:
        if 'cursor' in locals(): cursor.close()
        conn.close()
    
    display_data()  # Refresh display

# Get data from database with pagination
def get_paginated_data(page):
    """Fetch paginated data from database"""
    conn = connect_to_db()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        offset = (page - 1) * rows_per_page
        cursor.execute("SELECT * FROM author_profile LIMIT %s OFFSET %s", 
                      (rows_per_page, offset))
        return cursor.fetchall()
    except mysql.connector.Error as err:
        messagebox.showerror("Query Error", f"Failed to fetch data: {err}")
        return []
    finally:
        if 'cursor' in locals(): cursor.close()
        conn.close()

def get_total_records():
    """Get total number of records in the table"""
    conn = connect_to_db()
    if not conn:
        return 0
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM author_profile")
        return cursor.fetchone()[0]
    except mysql.connector.Error as err:
        messagebox.showerror("Query Error", f"Count failed: {err}")
        return 0
    finally:
        if 'cursor' in locals(): cursor.close()
        conn.close()

def update_pagination_controls():
    """Update the pagination buttons and label states"""
    global total_pages, current_page
    
    # Calculate total pages
    total_records = get_total_records()
    total_pages = (total_records // rows_per_page) + (1 if total_records % rows_per_page != 0 else 0)
    
    # Update page label
    page_label.config(text=f"Page {current_page} of {total_pages}")
    
    # Update button states
    prev_button.config(state=tk.NORMAL if current_page > 1 else tk.DISABLED)
    next_button.config(state=tk.NORMAL if current_page < total_pages else tk.DISABLED)
    
    # Handle empty data case
    if total_records == 0:
        page_label.config(text="No data available")
        prev_button.config(state=tk.DISABLED)
        next_button.config(state=tk.DISABLED)

def display_data():
    """Display data for the current page"""
    global current_page
    
    # Clear current data
    for row in tree.get_children():
        tree.delete(row)
    
    # Insert new data with alternating row colors
    for index, row in enumerate(get_paginated_data(current_page)):
        # Use 'oddrow' and 'evenrow' tags to match your style preferences
        tag = 'oddrow' if index % 2 == 0 else 'evenrow'
        tree.insert("", "end", values=row, tags=(tag,))
    
    # Update pagination controls
    update_pagination_controls()

def prev_page():
    """Navigate to previous page"""
    global current_page
    if current_page > 1:
        current_page -= 1
        display_data()

def next_page():
    """Navigate to next page"""
    global current_page
    if current_page < total_pages:
        current_page += 1
        display_data()

def jump_to_page():
    """Jump to a specific page"""
    global current_page
    try:
        page_number = int(page_entry.get())
        if 1 <= page_number <= total_pages:
            current_page = page_number
            display_data()
        else:
            messagebox.showerror("Invalid Page", f"Please enter a page number between 1 and {total_pages}")
    except ValueError:
        messagebox.showerror("Invalid Input", "Please enter a valid page number")

# GUI interface
root = tk.Tk()
root.title("Author Information Management")
root.geometry("1200x600")  # Set initial window size

# Header frame with return button
header_frame = ttk.Frame(root)
header_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

def return_to_selection():
    root.destroy()
    python = sys.executable
    subprocess.Popen([python, "select_py.py"])

return_button = ttk.Button(
    header_frame,
    text="← Return to Selection",
    command=return_to_selection
)
return_button.pack(side=tk.RIGHT)

# Add new functions for editing records
def edit_selected():
    """Handle edit button click: open edit window for selected row"""
    selected = tree.selection()
    if not selected:
        messagebox.showwarning("No Selection", "Please select a record to edit.")
        return
    
    selected_item = selected[0]
    values = tree.item(selected_item, 'values')
    open_edit_window(values)

def open_edit_window(data):
    """Create edit window with form fields"""
    edit_win = tk.Toplevel(root)
    edit_win.title("Edit Author Profile")
    
    # Create form labels and entries
    tk.Label(edit_win, text="Author ID:").grid(row=0, column=0, sticky='e', padx=5, pady=5)
    tk.Label(edit_win, text=data[0]).grid(row=0, column=1, sticky='w', padx=5, pady=5)
    
    tk.Label(edit_win, text="Full Name:").grid(row=1, column=0, sticky='e', padx=5, pady=5)
    tk.Label(edit_win, text=data[1]).grid(row=1, column=1, sticky='w', padx=5, pady=5)
    
    # Editable fields configuration
    fields = [
        ('bio', 2),
        ('email', 3),
        ('workplace', 4),
        ('job', 5),
        ('research', 6),
        ('reference', 7),
        ('article_number', 8),
        ('influence', 9)
    ]
    
    entries = {}
    for row_idx, (field_name, data_idx) in enumerate(fields, start=2):
        tk.Label(edit_win, text=field_name.replace('_', ' ').title() + ":").grid(
            row=row_idx, column=0, sticky='e', padx=5, pady=5)
        
        entry = tk.Entry(edit_win, width=50)
        entry.grid(row=row_idx, column=1, padx=5, pady=5)
        entry.insert(0, data[data_idx] if data[data_idx] else '')
        entries[field_name] = entry
    
    # Save button
    def save_changes():
        """Collect data and update database"""
        new_values = (
            entries['bio'].get(),
            entries['email'].get(),
            entries['workplace'].get(),
            entries['job'].get(),
            entries['research'].get(),
            entries['reference'].get(),
            entries['article_number'].get(),
            entries['influence'].get(),
            data[0]  # author_id as WHERE clause
        )
        
        conn = connect_to_db()
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            update_sql = """
                UPDATE author_profile 
                SET bio = %s,
                    email = %s,
                    workplace = %s,
                    job = %s,
                    research = %s,
                    reference = %s,
                    article_number = %s,
                    influence = %s
                WHERE author_id = %s
            """
            cursor.execute(update_sql, new_values)
            conn.commit()
            messagebox.showinfo("Success", "Record updated successfully!")
            edit_win.destroy()
            display_data()  # Refresh main view
        except mysql.connector.Error as err:
            conn.rollback()
            messagebox.showerror("Update Error", f"Failed to update record: {err}")
        finally:
            if 'cursor' in locals(): cursor.close()
            conn.close()
    
    btn_frame = ttk.Frame(edit_win)
    btn_frame.grid(row=len(fields)+2, column=0, columnspan=2, pady=10)
    
    ttk.Button(btn_frame, text="Save", command=save_changes).pack(side=tk.LEFT, padx=10)
    ttk.Button(btn_frame, text="Cancel", command=edit_win.destroy).pack(side=tk.LEFT, padx=10)

# Create control panel with buttons
control_frame = ttk.Frame(root)
control_frame.pack(fill=tk.X, padx=10, pady=5)

# Pagination controls
pagination_frame = ttk.Frame(control_frame)
pagination_frame.pack(side=tk.LEFT)

prev_button = ttk.Button(
    pagination_frame,
    text="◀ Previous",
    command=prev_page,
    state=tk.DISABLED
)
prev_button.pack(side=tk.LEFT, padx=2)

page_label = ttk.Label(pagination_frame, text="Page 1 of 1")
page_label.pack(side=tk.LEFT, padx=5)

next_button = ttk.Button(
    pagination_frame,
    text="Next ▶",
    command=next_page,
    state=tk.DISABLED
)
next_button.pack(side=tk.LEFT, padx=2)

# Page number input field and jump button
jump_frame = ttk.Frame(control_frame)
jump_frame.pack(side=tk.LEFT, padx=10)

page_entry = ttk.Entry(jump_frame, width=5)
page_entry.pack(side=tk.LEFT, padx=2)

jump_button = ttk.Button(jump_frame, text="Go", command=jump_to_page)
jump_button.pack(side=tk.LEFT, padx=2)

# Action buttons
button_frame = ttk.Frame(control_frame)
button_frame.pack(side=tk.RIGHT)

# Action buttons should be defined AFTER button_frame creation
button_style = {"padx": 10, "pady": 5, "bd": 0}  # Define button_style here

button_frame = ttk.Frame(control_frame)
button_frame.pack(side=tk.RIGHT)

# Create buttons using the defined style
import_btn = ttk.Button(button_frame, text="Import from authors", 
                      command=import_authors)
import_btn.pack(side=tk.LEFT, padx=5)

run_delete_button = ttk.Button(button_frame, text="Auto Check", 
                              command=run_autocheck_script)
run_delete_button.pack(side=tk.LEFT, padx=5)


refresh_btn = ttk.Button(button_frame, text="Refresh Data",
                       command=display_data)
refresh_btn.pack(side=tk.LEFT, padx=5)

edit_btn = ttk.Button(button_frame, text="Edit", 
                    command=edit_selected)
edit_btn.pack(side=tk.LEFT, padx=5)


run_delete_button = ttk.Button(button_frame, text="Add CSV", 
                              command=run_addcsv_script)
run_delete_button.pack(side=tk.LEFT, padx=5)


run_delete_button = ttk.Button(button_frame, text="Delete", 
                              command=run_delete_script)
run_delete_button.pack(side=tk.LEFT, padx=5)


run_clear_button = ttk.Button(button_frame, text="⚠️Clear", command=run_clear_script)
run_clear_button.pack(side=tk.LEFT, padx=5)


# Create table container
table_frame = ttk.Frame(root)
table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,10))

# Create table and scrollbars
columns = (
    "author_id", "full_name", "bio", "email",
    "workplace", "job", "research", "reference",
    "article_number", "influence"
)
tree = ttk.Treeview(table_frame, columns=columns, show="headings")

# Configure columns
col_config = {
    "author_id": {"width": 80, "anchor": tk.CENTER},
    "full_name": {"width": 150, "minwidth": 120},
    "bio": {"width": 200, "stretch": True},
    "email": {"width": 100, "anchor": tk.CENTER},
    "workplace": {"width": 120},
    "job": {"width": 120},
    "research": {"width": 150},
    "reference": {"width": 100, "anchor": tk.CENTER},
    "article_number": {"width": 120, "anchor": tk.CENTER},
    "influence": {"width": 120, "anchor": tk.CENTER}
}

for col in columns:
    tree.heading(col, text=col.replace('_', ' ').title())
    tree.column(col, **col_config[col])

# Define alternating row colors - CHANGED THESE TAG NAMES TO MATCH WHAT'S USED IN display_data()
tree.tag_configure('oddrow', background='#E8E8E8')  # Light gray for odd rows
tree.tag_configure('evenrow', background='white')    # White for even rows

# Configure scrollbars
y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
x_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=tree.xview)
tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

# Grid layout for table and scrollbars
tree.grid(row=0, column=0, sticky="nsew")
y_scroll.grid(row=0, column=1, sticky="ns")
x_scroll.grid(row=1, column=0, sticky="ew")

table_frame.grid_rowconfigure(0, weight=1)
table_frame.grid_columnconfigure(0, weight=1)

# Configure window resizing
root.grid_rowconfigure(0, weight=0)
root.grid_rowconfigure(1, weight=1)
root.grid_columnconfigure(0, weight=1)
root.minsize(800, 400)

# Initial data load
display_data()

root.mainloop()

input("Press Enter to exit...")
