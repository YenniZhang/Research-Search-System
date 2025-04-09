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

# Get authors
def get_authors():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT author_id, full_name FROM author_profile")
    authors = cursor.fetchall()
    cursor.close()
    conn.close()
    return authors

# Delete selected authors
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
                    # and remove the spaces
                    id_str = item[:10].strip()
                    try:
                        author_id = int(id_str)
                        selected_ids.append(author_id)
                    except ValueError:
                        print(f"Invalid ID: {id_str}")
                else:
                    print("Choose a valid row")

            if not selected_ids:
                messagebox.showerror("Error", "Didn't choose any valid author")
                return

            try:
                for author_id in selected_ids:
                    cursor.execute("DELETE FROM author_profile WHERE author_id = %s", (author_id,))
                conn.commit()
                messagebox.showinfo("Success", "Delete Success")
            except Exception as e:
                conn.rollback()
                messagebox.showerror("Error", f"Failed to delete: {str(e)}")
            finally:
                cursor.close()
                conn.close()
                load_authors()
        except subprocess.CalledProcessError as e:
            print(f"Error running script: {e}")
    else:
        print("Database delete operation was cancelled.")

    

# Delete specific author by ID
def delete_by_id():

    # Confirm data deletion
    result = messagebox.askyesno(
        "Confirm Deletion",
        "This action will delete the data of this ID in the database. Are you sure you want to proceed?"
    )
    
    if result:
        try:
            try:
                author_id = int(entry_id.get())
                max_author_id = get_max_author_id()  # Get the largest author_id
                if author_id > max_author_id:
                    messagebox.showerror("Error", f"Input ID exceeds max author ID ({max_author_id})")
                    return
            except ValueError:
                messagebox.showerror("Error", "Please input a valid ID")
                return

            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM author_profile WHERE author_id = %s", (author_id,))
            conn.commit()
            cursor.close()
            conn.close()
            load_authors()
            messagebox.showinfo("Success", "Delete Success")
        except subprocess.CalledProcessError as e:
                print(f"Error running script: {e}")
        else:
            print("Database clearing operation was cancelled.")



# Get the largest author_id
def get_max_author_id():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(author_id) FROM author_profile")
    max_id = cursor.fetchone()[0]  # Get largest author_id
    cursor.close()
    conn.close()
    return max_id if max_id is not None else 0  # Avoid return None


# Delete authors by ID range
def delete_by_range():
     # Confirm data deletion
    result = messagebox.askyesno(
        "Confirm Deletion",
        "This action will delete the data belong to this range in the database. Are you sure you want to proceed?"
    )
    
    if result:
        try:
            try:
                start_id = int(entry_range_start.get())
                end_id = int(entry_range_end.get())
                if start_id >= end_id:
                    messagebox.showerror("Error", "Start ID must be less than End ID")
                    return
            
                max_author_id = get_max_author_id()  # Get the largest author_id
                if end_id > max_author_id:
                    messagebox.showerror("Error", f"End ID exceeds max author ID ({max_author_id})")
                    return
            
            except ValueError:
                messagebox.showerror("Error", "Please input valid range")
                return

            conn = connect_db()
            cursor = conn.cursor()
            try:
                cursor.execute("DELETE FROM author_profile WHERE author_id BETWEEN %s AND %s", (start_id, end_id))
                conn.commit()
                messagebox.showinfo("Success", "Delete Success")
            except Exception as e:
                conn.rollback()
                messagebox.showerror("Error", f"Failed to delete: {str(e)}")
            finally:
                cursor.close()
                conn.close()
                load_authors()
        except subprocess.CalledProcessError as e:
            print(f"Error running script: {e}")
    else:
        print("Database clearing operation was cancelled.")        

# Load authors into the listbox
def load_authors():
    # Clear the contents of the existing list
    listbox.delete(0, tk.END)
    
    authors = get_authors()

    # White and grey alternate rows are displayed
    for index, author in enumerate(authors):
        row_color = 'white' if index % 2 == 0 else 'lightgray'  # Alternate background color
        # Use a format string to align each row
        listbox.insert(tk.END, f"{author[0]:>10} {author[1]:>30}")  # Right align ID and left align Name
        listbox.itemconfig(index, {'bg': row_color})  # Set row bg color

# Create UI 
root = tk.Tk()
root.title("Author Delete System")

# Set the size of window
root.geometry("800x600")

# Create header
header = tk.Label(root, text="Author Delete", font=("Arial", 24), anchor="w", padx=10, pady=10, bg="gray")
header.pack(fill=tk.X)

# Create show author's Frame
listbox_frame = tk.Frame(root)
listbox_frame.pack(pady=10)

# Add column header
column_header = tk.Frame(listbox_frame)
column_header.pack(fill=tk.X)
header_id = tk.Label(column_header, text="Author ID", font=("Arial", 12, "bold"), width=10, anchor="w")
header_id.pack(side=tk.LEFT, padx=10)
header_name = tk.Label(column_header, text="Full Name", font=("Arial", 12, "bold"), width=50, anchor="w")
header_name.pack(side=tk.LEFT, padx=10)

# Create Listbox
listbox = tk.Listbox(listbox_frame, selectmode=tk.MULTIPLE, height=10, width=80)
listbox.pack()

# Load author data
load_authors()

# Delete chosen author Button
delete_button = tk.Button(root, text="Delete the chosen author", command=delete_selected)
delete_button.pack(pady=5)

# Input ID to delete author
frame_id = tk.Frame(root)
frame_id.pack(pady=5)
label_id = tk.Label(frame_id, text="Input ID to delete:")
label_id.pack(side=tk.LEFT)
entry_id = tk.Entry(frame_id)
entry_id.pack(side=tk.LEFT)
delete_id_button = tk.Button(frame_id, text="Delete", command=delete_by_id)
delete_id_button.pack(side=tk.LEFT)

# Input ID range to delete authors
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
