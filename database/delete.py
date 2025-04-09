import subprocess
import tkinter as tk
from tkinter import messagebox
import mysql.connector
import json


# Connect to database
def connect_db():
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

# Get articles and correspond author
def get_articles():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT a.id, a.title, GROUP_CONCAT(b.full_name) "
                "FROM articles a "
                "LEFT JOIN article_authors aa ON a.id = aa.article_id "
                "LEFT JOIN authors b ON aa.author_id = b.id "
                "GROUP BY a.id")
    articles = cursor.fetchall()
    cursor.close()
    conn.close()
    return articles

def delete_selected():

    # Confirm data deletion
    result = messagebox.askyesno(
        "Confirm Deletion",
        "This action will delete selected data in the database. Are you sure you want to proceed?"
    )
    
    if result:
        try:
            conn = connect_db()
            cursor = conn.cursor()

            selected_ids = []
            selected_items = listbox.curselection()

            for i in selected_items:
                item = listbox.get(i)
                if item:
                    # Extract the first 10 characters as the ID part 
                    # and remove the Spaces
                    id_str = item[:10].strip()
                    try:
                        article_id = int(id_str)
                        selected_ids.append(article_id)
                    except ValueError:
                        print(f"Invalid ID：{id_str}")
                else:
                    print("Choose the empty row")

            if not selected_ids:
                messagebox.showerror("Error", "Didn't choose any valid article")
                return

            try:
                for article_id in selected_ids:
                    cursor.execute("DELETE FROM articles WHERE id = %s", (article_id,))
                conn.commit()
                messagebox.showinfo("Success", "Delete Success")
            except Exception as e:
                conn.rollback()
                messagebox.showerror("Error", f"Fail to delete: {str(e)}")
            finally:
                cursor.close()
                conn.close()
                load_articles()

        except subprocess.CalledProcessError as e:
            print(f"Error running script: {e}")
    else:
        print("Database clearing operation was cancelled.")



# Delete specific ID's article
def delete_by_id():

    # Confirm data deletion
    result = messagebox.askyesno(
        "Confirm Deletion",
        "This action will delete the article of this range in the database. Are you sure you want to proceed?"
    )
    
    if result:
        try:
            try:
                article_id = int(entry_id.get())
                max_article_id = get_max_article_id()  # Get the largest article_id
                if article_id > max_article_id:
                    messagebox.showerror("Error", f"End ID exceeds max article ID ({max_article_id})")
                    return
            except ValueError:
                messagebox.showerror("Error", "Plese input valid ID")
                return

            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM articles WHERE id = %s", (article_id,))
            conn.commit()
            cursor.close()
            conn.close()
            load_articles()
            messagebox.showinfo("Success", "Delete Success")
        
        except subprocess.CalledProcessError as e:
            print(f"Error running script: {e}")
    else:
        print("Database clearing operation was cancelled.")



# Get the largest article_id
def get_max_article_id():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(id) FROM articles")
    max_id = cursor.fetchone()[0]  # Get largest article_id
    cursor.close()
    conn.close()
    return max_id if max_id is not None else 0  # Avoid return None


# Delete specific ID range's article
def delete_by_range():

    # Confirm data deletion
    result = messagebox.askyesno(
        "Confirm Deletion",
        "This action will delete the article of this ID in the database. Are you sure you want to proceed?"
    )
    
    if result:
        try:
            try:
                start_id = int(entry_range_start.get())
                end_id = int(entry_range_end.get())
                if start_id >= end_id:
                    messagebox.showerror("Error", "Start ID must be less than End ID")
                    return
            
                max_article_id = get_max_article_id()  # Get the largest article_id
                if end_id > max_article_id:
                    messagebox.showerror("Error", f"End ID exceeds max article ID ({max_article_id})")
                    return
                
            except ValueError:
                messagebox.showerror("Error", "Please input the valid range")
                return

            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM articles WHERE id BETWEEN {start_id} AND {end_id}")
            conn.commit()
            cursor.close()
            conn.close()
            load_articles()
            messagebox.showinfo("Success", "Delete Success")

        except subprocess.CalledProcessError as e:
            print(f"Error running script: {e}")
    else:
        print("Database clearing operation was cancelled.")


# Load articles' list
def load_articles():
    # Clear the contents of an existing list
    listbox.delete(0, tk.END)
    
    articles = get_articles()

    # White and grey alternate rows are displayed
    for index, article in enumerate(articles):
        row_color = 'white' if index % 2 == 0 else 'lightgray'  # Alternate background color
        # Use a format string to align each row
        listbox.insert(tk.END, f"{article[0]:>10} {article[1]:>30}")  # Right align ID and left align Title
        listbox.itemconfig(index, {'bg': row_color})  # Set row bg color

# Create UI 
root = tk.Tk()
root.title("Article Delete System")

# Set the size of window
root.geometry("800x600")

# Create header
header = tk.Label(root, text="Article Delete", font=("Arial", 24), anchor="w", padx=10, pady=10, bg="gray")
header.pack(fill=tk.X)

# Create show article's Frame
listbox_frame = tk.Frame(root)
listbox_frame.pack(pady=10)

# Add column header
column_header = tk.Frame(listbox_frame)
column_header.pack(fill=tk.X)
header_id = tk.Label(column_header, text="Article ID", font=("Arial", 12, "bold"), width=10, anchor="w")
header_id.pack(side=tk.LEFT, padx=10)
header_title = tk.Label(column_header, text="Article Title", font=("Arial", 12, "bold"), width=50, anchor="w")
header_title.pack(side=tk.LEFT, padx=10)

# Create Listbox
listbox = tk.Listbox(listbox_frame, selectmode=tk.MULTIPLE, height=10, width=80)
listbox.pack()

# Load article data
load_articles()

# Delete choosed article Button
delete_button = tk.Button(root, text="Delete the choosed article", command=delete_selected)
delete_button.pack(pady=5)

# Input ID delete article
frame_id = tk.Frame(root)
frame_id.pack(pady=5)
label_id = tk.Label(frame_id, text="Input ID to delete:")
label_id.pack(side=tk.LEFT)
entry_id = tk.Entry(frame_id)
entry_id.pack(side=tk.LEFT)
delete_id_button = tk.Button(frame_id, text="Delete", command=delete_by_id)
delete_id_button.pack(side=tk.LEFT)

# Input ID range delete article
frame_range = tk.Frame(root)
frame_range.pack(pady=5)
label_range = tk.Label(frame_range, text="Input ID range to delete (start - end):")
label_range.pack(side=tk.LEFT)
entry_range_start = tk.Entry(frame_range, width=5)
entry_range_start.pack(side=tk.LEFT)
label_to = tk.Label(frame_range, text="to")
label_to.pack(side=tk.LEFT)
entry_range_end = tk.Entry(frame_range, width=5)
entry_range_end.pack(side=tk.LEFT)
delete_range_button = tk.Button(frame_range, text="Delete", command=delete_by_range)
delete_range_button.pack(side=tk.LEFT)

# Start interface
root.mainloop()
