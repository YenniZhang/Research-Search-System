import json
import mysql.connector
import tkinter as tk
from tkinter import messagebox, ttk
import sys
import subprocess


def connect_to_db():
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
    except mysql.connector.Error as err:
        messagebox.showerror("Database Error", f"Connection failed: {err}")
        return None

def fetch_correlations():
    conn = connect_to_db()
    if not conn:
        return []
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM correlation")
    data = cursor.fetchall()
    conn.close()
    return data

def fetch_authors():
    conn = connect_to_db()
    if not conn:
        return []
    cursor = conn.cursor()
    cursor.execute("SELECT author_id FROM author_profile")
    authors = [row[0] for row in cursor.fetchall()]
    conn.close()
    return authors

def import_authors():
    author_ids = fetch_authors()
    if author_ids:
        entry_author1['values'] = author_ids
        messagebox.showinfo("Success", "Authors imported successfully")
    else:
        messagebox.showerror("Error", "No authors found to import")

def add_correlation():
    author1 = entry_author1.get()
    author2 = entry_author2.get()
    if not author1 or not author2:
        messagebox.showerror("Error", "Both Author IDs are required")
        return
    try:
        conn = connect_to_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO correlation (author1_id, author2_id) VALUES (%s, %s)", (author1, author2))
        conn.commit()
        conn.close()
        refresh_table()
        messagebox.showinfo("Success", "Correlation added successfully")
    except mysql.connector.Error as err:
        messagebox.showerror("Database Error", f"Error adding correlation: {err}")

def delete_correlation():
    # Confirm data deletion
    result = messagebox.askyesno(
        "Confirm Deletion",
        "This action will delete this data in the database. Are you sure you want to proceed?"
    )
    
    if result:
        try:
            selected_item = tree.selection()
            if not selected_item:
                messagebox.showerror("Error", "No item selected")
                return
            item = tree.item(selected_item)
            author1, author2 = item['values']
            try:
                conn = connect_to_db()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM correlation WHERE author1_id=%s AND author2_id=%s", (author1, author2))
                conn.commit()
                conn.close()
                refresh_table()
                messagebox.showinfo("Success", "Correlation deleted successfully")
            except mysql.connector.Error as err:
                messagebox.showerror("Database Error", f"Error deleting correlation: {err}")

        except subprocess.CalledProcessError as e:
            print(f"Error running script: {e}")
    else:
        print("Database clearing operation was cancelled.")



def refresh_table():
    for row in tree.get_children():
        tree.delete(row)
    for row in fetch_correlations():
        tree.insert("", "end", values=row)

def return_to_selection():
    root.destroy()
    python = sys.executable
    subprocess.Popen([python, "select_py.py"])

# UI Setup
root = tk.Tk()
root.title("Correlation Management")

# Header Frame
header_frame = tk.Frame(root)
header_frame.pack(fill=tk.X, pady=5)

return_button = ttk.Button(
    header_frame,
    text="← Return to Selection",
    command=return_to_selection
)
return_button.pack(side=tk.RIGHT)

frame = tk.Frame(root)
frame.pack(pady=10)

tk.Label(frame, text="Author 1 ID:").grid(row=0, column=0)
entry_author1 = ttk.Combobox(frame) # Drop-down box
entry_author1.grid(row=0, column=1)

tk.Button(frame, text="Import Authors", command=import_authors).grid(row=0, column=2)

tk.Label(frame, text="Author 2 ID:").grid(row=1, column=0)
entry_author2 = tk.Entry(frame)
entry_author2.grid(row=1, column=1)

tk.Button(frame, text="Add Correlation", command=add_correlation).grid(row=2, column=0, columnspan=2, pady=5)

tree = ttk.Treeview(root, columns=("Author 1", "Author 2"), show="headings")
tree.heading("Author 1", text="Author 1 ID")
tree.heading("Author 2", text="Author 2 ID")
tree.pack()

tk.Button(root, text="Delete Selected", command=delete_correlation).pack(pady=5)

tk.Button(root, text="Refresh", command=refresh_table).pack()

refresh_table()
root.mainloop()
