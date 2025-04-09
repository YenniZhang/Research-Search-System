import tkinter as tk
from tkinter import ttk
import mysql.connector
from mysql.connector import Error
import subprocess
from tkinter import messagebox
import json
import mysql.connector
import sys



# Function to run the other Python script

def run_delete_script():
    try:
        # Replace 'other_script.py' with the path of the script you want to run
        subprocess.run(["python", "delete.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running script: {e}")
        
        
def run_addcsv_script():
    try:
        # Replace 'other_script.py' with the path of the script you want to run
        subprocess.run(["python", "addcsv.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running script: {e}")
        

def run_addone_script():
    try:
        # Replace 'other_script.py' with the path of the script you want to run
        subprocess.run(["python", "addone.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running script: {e}")
        
        
def run_clear_script():
    
    result = messagebox.askyesno(
        "Confirm Deletion",
        "This action will delete all data in the database. Are you sure you want to proceed?"
    )
    
    if result:
    
        try:
            # Replace 'other_script.py' with the path of the script you want to run
            subprocess.run(["python", "clear.py"], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error running script: {e}")
    else:
        print("Database clearing operation was cancelled.")

# Connect to MySQL database
def create_connection():
    try:
        # Read JSON config document
        with open('selected_config.json', 'r') as file:
            config = json.load(file)  # Analysis JSON document
        
        # Make suer JSON structure is correct
        required_keys = ["host", "database", "user", "password"]
        for key in required_keys:
            if key not in config or not config[key].strip():
                print(f"Error: '{key}' is missing or empty in selected_config.json")
                return None

        # Connect to database
        connection = mysql.connector.connect(
            host=config["host"],
            database=config["database"],
            user=config["user"],
            password=config["password"]
        )

        if connection.is_connected():
            print("✅ Connection established successfully!")
        return connection

    except mysql.connector.Error as e:
        print(f"❌ Database Error: {e}")
        return None
    except FileNotFoundError:
        print("❌ Error: selected_config.json file not found.")
        return None
    except json.JSONDecodeError:
        print("❌ Error: Failed to parse selected_config.json.")
        return None
    

# Fetch articles from the database without content, abstract, reference, and URL
def fetch_articles():
    connection = create_connection()
    if connection is None:
        print("Failed to connect to the database.")
        return []

    cursor = connection.cursor()

    # Fetch articles from the database without content, abstract, reference, and URL
    query = """
    SELECT a.id AS article_id, a.title, a.published_date
    FROM articles a
    ORDER BY a.id
    """
    cursor.execute(query)
    articles = cursor.fetchall()

    connection.close()

    return articles


# Fetch authors for a given article
def fetch_authors_for_article(article_id):
    connection = create_connection()
    if connection is None:
        print("Failed to connect to the database.")
        return []

    cursor = connection.cursor()

    # Fetch authors for a specific article
    query = """
    SELECT au.id AS author_id, au.full_name
    FROM authors au
    JOIN article_authors aa ON au.id = aa.author_id
    WHERE aa.article_id = %s
    ORDER BY au.id
    """
    cursor.execute(query, (article_id,))
    authors = cursor.fetchall()

    connection.close()

    return authors


            

# Function to display data in the UI
def display_data():
    # Fetch articles from the database
    articles = fetch_articles()

    # Create a Tkinter window
    root = tk.Tk()
    root.title("Database Preview")

    

    # +++ New：Add return button +++
    header_frame = ttk.Frame(root)
    header_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

    def return_to_selection():
        root.destroy()  # Close the current window
        python = sys.executable
        subprocess.Popen([python, "select_py.py"])  # Start the selection window

    return_button = ttk.Button(
        header_frame,
        text="← Return to Selection",
        command=return_to_selection
    )
    return_button.pack(side=tk.RIGHT)



    # Set the fixed window size with resizing capability
    root.geometry("1200x600")  # Adjusted window size to fit better
    root.minsize(800, 300)  # Set a minimum size to prevent it from shrinking too much

    # Create a main frame to hold all widgets
    main_frame = ttk.Frame(root)
    main_frame.pack(fill=tk.BOTH, expand=True)

    # Create a Canvas widget for scrolling
    canvas = tk.Canvas(main_frame)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    # Create the button frame and adjust the layout
    button_frame = ttk.Frame(root)
    button_frame.pack(side=tk.BOTTOM, pady=5)





    def edit_selected():
        selected_item = treeview.focus()
        if not selected_item:
            messagebox.showwarning("No Selection", "Please select a row to edit")
            return

        # Get article ID
        item_values = treeview.item(selected_item, "values")
        article_id = item_values[0]

        # Create edit window
        edit_window = tk.Toplevel(root)
        edit_window.title("Edit Article")
        edit_window.geometry("700x600")

        # Create scrollable area
        canvas = tk.Canvas(edit_window)
        scrollbar = ttk.Scrollbar(edit_window, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        # Enable mouse wheel scrolling
        def _on_mouse_wheel(event):
            canvas.yview_scroll(-1 * (event.delta // 120), "units")

        scrollable_frame.bind("<Enter>", lambda _: canvas.bind_all("<MouseWheel>", _on_mouse_wheel))
        scrollable_frame.bind("<Leave>", lambda _: canvas.unbind_all("<MouseWheel>"))
        scrollbar.pack(side="right", fill="y")

        # Retrieve article data
        connection = create_connection()
        if not connection:
            return
        cursor = connection.cursor()
        
        cursor.execute("""
            SELECT 
                id,            
                title, 
                content, 
                abstract,
                reference,       
                url, 
                published_date 
            FROM articles 
            WHERE id = %s""", 
            (article_id,))
        article_data = cursor.fetchone()

       
        
        cursor.execute("""
            SELECT au.id, au.full_name 
            FROM authors au
            JOIN article_authors aa ON au.id = aa.author_id
            WHERE aa.article_id = %s
            ORDER BY au.id""", (article_id,))
        authors = cursor.fetchall()
        connection.close()

        # Create input variables
        article_id_var = tk.StringVar(value=article_data[0])
        title_var = tk.StringVar(value=article_data[1])
        content_var = tk.StringVar(value=article_data[2])
        abstract_var = tk.StringVar(value=article_data[3])
        reference_var = tk.StringVar(value=article_data[4])
        url_var = tk.StringVar(value=article_data[5])
        date_var = tk.StringVar(value=article_data[6])
        author_vars = [(tk.StringVar(value=a[0]), tk.StringVar(value=a[1])) for a in authors]

        print(article_id_var.get())


        # Article ID (read-only)
        ttk.Label(scrollable_frame, text="Article ID:").grid(row=0, column=0, sticky="w")
        
        article_id_entry = tk.Entry(scrollable_frame, width=8, textvariable=article_id_var, state='readonly')
    
        article_id_entry.grid(row=0, column=1, columnspan=3, sticky="ew", padx=5, pady=2)



        # Title
        ttk.Label(scrollable_frame, text="Title:").grid(row=1, column=0, sticky="w")
        title_entry = ttk.Entry(scrollable_frame, textvariable=title_var, width=70)
        title_entry.grid(row=1, column=1, columnspan=3, sticky="ew", padx=5, pady=2)

        # Publish Date
        ttk.Label(scrollable_frame, text="Publish Date:").grid(row=2, column=0, sticky="w")
        date_entry = ttk.Entry(scrollable_frame, textvariable=date_var)
        date_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=2)

        # Abstract
        ttk.Label(scrollable_frame, text="Abstract:").grid(row=3, column=0, sticky="w")
        abstract_entry = tk.Text(scrollable_frame, wrap=tk.WORD, width=70, height=4)
        abstract_entry.insert(tk.END, abstract_var.get())
        abstract_entry.grid(row=3, column=1, columnspan=3, sticky="ew", padx=5, pady=2)

        
        # Content
        ttk.Label(scrollable_frame, text="Content:").grid(row=4, column=0, sticky="nw")
        content_text = tk.Text(scrollable_frame, wrap=tk.WORD, width=70, height=4)
        content_text.insert(tk.END, content_var.get())
        content_text.grid(row=4, column=1, columnspan=3, sticky="nsew", padx=5, pady=2)


        # Reference
        ttk.Label(scrollable_frame, text="Reference:").grid(row=5, column=0, sticky="w")
        reference_text = tk.Text(scrollable_frame, wrap=tk.WORD, width=70, height=12)
        reference_text.insert(tk.END, reference_var.get())
        reference_text.grid(row=5, column=1, columnspan=3, sticky="ew", padx=5, pady=2)
        

        # URL
        ttk.Label(scrollable_frame, text="URL:").grid(row=6, column=0, sticky="w")
        url_entry = ttk.Entry(scrollable_frame, textvariable=url_var, width=70)
        url_entry.grid(row=6, column=1, columnspan=3, sticky="ew", padx=5, pady=2)

        # Author section
        author_frame = ttk.LabelFrame(scrollable_frame, text="Authors (ID cannot be modified)")
        author_frame.grid(row=7, column=0, columnspan=4, sticky="ew", padx=5, pady=5)

        def update_author_entries():
            for widget in author_frame.winfo_children():
                widget.destroy()
            
            for i, (id_var, name_var) in enumerate(author_vars):
                ttk.Label(author_frame, text=f"Author {i+1} ID:").grid(row=i, column=0, sticky="w")
                ttk.Entry(author_frame, textvariable=id_var, width=8, state='readonly').grid(row=i, column=1, padx=2)
                ttk.Label(author_frame, text="Name:").grid(row=i, column=2, sticky="w")
                ttk.Entry(author_frame, textvariable=name_var, width=25).grid(row=i, column=3, padx=2, sticky="ew")
                if len(author_vars) > 1:
                    ttk.Button(author_frame, text="-", command=lambda idx=i: remove_author(idx)).grid(row=i, column=4)
            ttk.Button(author_frame, text="+", command=add_author).grid(column=4)
        
        def add_author():
            author_vars.append((tk.StringVar(value=""), tk.StringVar(value="")))
            update_author_entries()

        def remove_author(index):
            if len(author_vars) > 1:
                author_vars.pop(index)
                update_author_entries()
        
        update_author_entries()

       

        # Button frame
        button_frame = ttk.Frame(scrollable_frame)
        button_frame.grid(row=8, column=0, columnspan=4, pady=10)

        

        def save_changes():
            # Show a confirmation dialog before saving changes
            if not messagebox.askyesno("Confirm", "Do you want to save the changes?"):
                edit_window.lift()
                edit_window.focus()
                return  

            # Retrieve updated values from input fields
            new_title = title_var.get()
            new_date = date_var.get()
            new_content = content_text.get("1.0", tk.END).strip()
            new_abstract = abstract_entry.get("1.0", tk.END).strip()
            new_reference = reference_text.get("1.0", tk.END).strip()
            new_url = url_var.get()

            # Ensure the title is not empty
            if not new_title:
                messagebox.showerror("Error", "Title cannot be empty")
                return

            try:
                # Establish a database connection
                connection = create_connection()
                cursor = connection.cursor()

                # Update article details in the database
                cursor.execute("""
                    UPDATE articles 
                    SET title=%s, content=%s, abstract=%s, reference=%s, url=%s, published_date=%s 
                    WHERE id=%s""",
                    (new_title, new_content, new_abstract, new_reference, new_url, new_date, article_id)
                )

                # Retrieve the existing author IDs from the database
                existing_author_ids = {str(a[0]) for a in authors}  # Store original author IDs
                new_author_ids = {id_var.get().strip() for id_var, _ in author_vars}  # Get new author IDs from input fields

                # Identify authors that were removed
                deleted_author_ids = existing_author_ids - new_author_ids

                # Remove deleted authors from `article_authors` table
                for author_id in deleted_author_ids:
                    cursor.execute("DELETE FROM article_authors WHERE article_id = %s AND author_id = %s", (article_id, author_id))

                    # Check if the author is still linked to any other article
                    cursor.execute("SELECT COUNT(*) FROM article_authors WHERE author_id = %s", (author_id,))
                    if cursor.fetchone()[0] == 0:  # If the author is not linked to any article
                        cursor.execute("DELETE FROM authors WHERE id = %s", (author_id,))  # Remove from authors table

                # Process authors (Update existing authors or add new ones)
                for id_var, name_var in author_vars:
                    author_id = id_var.get().strip()
                    author_name = name_var.get().strip()

                    # Skip empty author names to avoid database errors
                    if not author_name:
                        continue  

                    if author_id:  
                        # Update existing author's name in the database
                        cursor.execute("UPDATE authors SET full_name=%s WHERE id=%s", (author_name, author_id))
                    else:  
                        # Insert a new author if no existing ID
                        cursor.execute("INSERT INTO authors (full_name) VALUES (%s)", (author_name,))
                        new_author_id = cursor.lastrowid  # Get the newly inserted author's ID
                        
                        # Insert a new relationship between article and the new author
                        cursor.execute("INSERT INTO article_authors (article_id, author_id) VALUES (%s, %s)", (article_id, new_author_id))

                # Commit transaction to save all changes
                connection.commit()
                messagebox.showinfo("Success", "Changes saved successfully")

                # Close the edit window and refresh data
                edit_window.destroy()
                refresh_data()

            except Error as e:
                # Rollback on error and show error message
                messagebox.showerror("Database Error", str(e))
                connection.rollback()
            finally:
                # Close the database connection
                if connection.is_connected():
                    connection.close()




        # Add the Save and Cancel buttons to the button frame
        ttk.Button(button_frame, text="Save", command=save_changes).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Cancel", command=edit_window.destroy).pack(side=tk.LEFT, padx=10)





 
    
    
    # Create the button to run the external script
    run_addcsv_button = ttk.Button(button_frame, text="Add csv", command=run_addcsv_script)
    run_addcsv_button.pack(side=tk.LEFT, padx=5)

    run_addone_button = ttk.Button(button_frame, text="Add one", command=run_addone_script)
    run_addone_button.pack(side=tk.LEFT, padx=5)

    run_edit_button = ttk.Button(button_frame, text="Edit", command=edit_selected)
    run_edit_button.pack(side=tk.LEFT, padx=5)

    
    run_delete_button = ttk.Button(button_frame, text="Delete", command=run_delete_script)
    run_delete_button.pack(side=tk.LEFT, padx=5)
    
    run_clear_button = ttk.Button(button_frame, text="⚠️Clear", command=run_clear_script)
    run_clear_button.pack(side=tk.LEFT, padx=5)
    
    # Function to refresh data
    def refresh_data():
        nonlocal articles, total_pages
        articles = fetch_articles()  # Retrieve data
        total_pages = (len(articles) // rows_per_page) + (1 if len(articles) % rows_per_page != 0 else 0)
        update_treeview(1)  # Refresh to first page

    refresh_button = ttk.Button(button_frame, text="Refresh", command=refresh_data)
    refresh_button.pack(side=tk.LEFT, padx=5)

    # Create a vertical scrollbar linked to the canvas
    v_scroll = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
    v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    # Create a horizontal scrollbar linked to the canvas
    h_scroll = ttk.Scrollbar(root, orient=tk.HORIZONTAL, command=canvas.xview)
    h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

    # Configure the canvas scrollbars
    canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

    # Create a frame inside the canvas to hold the Treeview
    tree_frame = ttk.Frame(canvas)
    canvas.create_window((0, 0), window=tree_frame, anchor="nw")

    # Bind the canvas to the tree_frame's size to update scroll region
    def update_scrollregion(event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    tree_frame.bind("<Configure>", update_scrollregion)

    # Function to handle mouse wheel scrolling
    def on_mouse_wheel(event):
        if event.delta > 0:
            canvas.yview_scroll(-1, "units")
        else:
            canvas.yview_scroll(1, "units")

    # Bind mouse wheel scrolling to the canvas
    canvas.bind_all("<MouseWheel>", on_mouse_wheel)

    # Display Data
    ttk.Label(tree_frame, text="Articles & Authors", font=('Helvetica', 16, 'bold')).grid(row=0, column=0, sticky='w', padx=10, pady=10)

    # Define base columns
    base_columns = ("article_id", "title", "content", "abstract", "reference", "url", "published_date")


    def get_max_authors_per_article():
        """Get the maximum number of authors per article."""
        connection = create_connection()
        if not connection:
            return 0  # Avoid return None

        try:
            cursor = connection.cursor()
            query = """
                SELECT COALESCE(MAX(author_count), 0) AS max_authors_per_article
                FROM (
                    SELECT article_id, COUNT(author_id) AS author_count
                    FROM article_authors
                    GROUP BY article_id
                ) AS author_counts;
            """
            cursor.execute(query)
            result = cursor.fetchone()
            return int(result[0]) if result and result[0] is not None else 0

        except mysql.connector.Error as e:
            print(f"Error: {e}")
            return 0  # Make suer return a number

        finally:
            if cursor: cursor.close()
            if connection: connection.close()




    # Create columns dynamically for authors
    dynamic_columns = []
    max_authors = get_max_authors_per_article()  # Limit the number of authors you want to display; adjust if needed
    for i in range(1, max_authors + 1):
        dynamic_columns.append(f"id_author{i}")
        dynamic_columns.append(f"author{i}")

    columns = base_columns + tuple(dynamic_columns)

    # Create Treeview with dynamic columns
    treeview = ttk.Treeview(tree_frame, columns=columns, show="headings", height=30)
    treeview.grid(row=1, column=0, padx=10, pady=5, columnspan=5, sticky="nsew")
    


    
    
    
    # Click header to order
    def treeview_sort_column(col, reverse):
        
        if col not in ["article_id", "published_date"]:  # Only order two conlumn
            return
    
        l = [(treeview.set(k, col), k) for k in treeview.get_children('')]
        try:
            l.sort(key=lambda t: int(t[0]), reverse=reverse)
        except ValueError:
            l.sort(reverse=reverse)

        for index, (val, k) in enumerate(l):
            treeview.move(k, '', index)

        treeview.heading(col, command=lambda: treeview_sort_column(col, not reverse))

    for col in columns:
        treeview.heading(col, text=col, 
                        command=lambda _col=col: treeview_sort_column(_col, False))
    
    
    def on_double_click(event):
        # Get the type of click region
        region = treeview.identify_region(event.x, event.y)
        if region != "cell":
            return

        # Get col name and ID
        column_id = treeview.identify_column(event.x)
        col_index = int(column_id[1:])  # transfer #1 to 1
        columns = treeview["columns"]
        if col_index < 0 or col_index >= len(columns):
            return
        col_name = columns[col_index - 1]

        # Only process content、abstract、reference and url
        if col_name not in ["content", "abstract", "reference", "url", "title"]:
            return

        # Get data from choosed row
        selected_item = treeview.focus()
        if not selected_item:
            return
        item_values = treeview.item(selected_item, "values")
        article_id = item_values[0]  # Get article ID

        # According to col name to query all
        if col_name == "content":
            content = fetch_content_or_abstract(article_id, "content")
            display_in_new_window("Content", content)

        elif col_name == "abstract":
            abstract = fetch_content_or_abstract(article_id, "abstract")
            display_in_new_window("Abstract", abstract)

        elif col_name == "reference":
            reference = fetch_content_or_abstract(article_id, "reference")
            display_in_new_window("reference", reference)    

        elif col_name == "url":
            url = fetch_content_or_abstract(article_id, "url")
            display_in_new_window("URL", url)
        
        elif col_name == "title":
            title = fetch_content_or_abstract(article_id, "title")
            display_in_new_window("Title", title)

    # New query function：according article ID query content、abstract、reference or url
    def fetch_content_or_abstract(article_id, column):
        connection = create_connection()
        if connection is None:
            print("Failed to connect to the database.")
            return ""

        cursor = connection.cursor()

        # According to input to query content、abstrac、reference or url
        query = f"""
        SELECT {column}
        FROM articles
        WHERE id = %s
        """
        cursor.execute(query, (article_id,))
        result = cursor.fetchone()

        connection.close()

        return result[0] if result else ""

    # Creat new window to show content
    def display_in_new_window(title, content):
        top = tk.Toplevel(root)
        top.title(f"Full {title}")

        text_frame = ttk.Frame(top)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        text_widget = tk.Text(text_frame, wrap=tk.WORD, width=80, height=20)
        text_widget.insert(tk.END, content)
        text_widget.config(state=tk.DISABLED)  # Set to read only
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(text_frame, command=text_widget.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.config(yscrollcommand=scrollbar.set)



    treeview.bind("<Double-1>", on_double_click)


    # Define the columns headers
    column_headers = ["Article ID", "Title", "Content", "Abstract", "Reference", "URL", "Published Date"]
    for i in range(1, max_authors + 1):
        column_headers.append(f"ID Author {i}")
        column_headers.append(f"Author {i}")
    
    for col, header in zip(columns, column_headers):
        treeview.heading(col, text=header)

    # Configure column widths
    treeview.column("article_id", width=80, anchor="center")  # Article ID
    treeview.column("title", width=150, anchor="w")           # Title
    treeview.column("content", width=200, anchor="w")        # Content
    treeview.column("abstract", width=200, anchor="w")       # Abstract
    treeview.column("reference", width=150, anchor="w")      # Reference
    treeview.column("url", width=150, anchor="w")            # URL
    treeview.column("published_date", width=100, anchor="center")  # Published Date

    # Configure author columns
    for i in range(1, max_authors + 1):
        treeview.column(f"id_author{i}", width=80, anchor="center")  # ID Author
        treeview.column(f"author{i}", width=120, anchor="w")         # Author Name

    # Pagination variables
    current_page = 1
    rows_per_page = 30
    total_pages = (len(articles) // rows_per_page) + (1 if len(articles) % rows_per_page != 0 else 0)

    # Function to update the Treeview with the current page's data
    def update_treeview(page):
        nonlocal current_page, total_pages
        treeview.delete(*treeview.get_children())
        
        # Check if there are any articles
        if len(articles) == 0:
            page_label.config(text="No data available")
            prev_button.config(state=tk.DISABLED)
            next_button.config(state=tk.DISABLED)
            return

        # Calculate total pages based on the available articles
        total_pages = (len(articles) // rows_per_page) + (1 if len(articles) % rows_per_page != 0 else 0)
        current_page = page

        start_index = (current_page - 1) * rows_per_page
        end_index = start_index + rows_per_page
        page_articles = articles[start_index:end_index]

        # Configure tags for alternating row colors - ADD THIS
        treeview.tag_configure("oddrow", background="#E8E8E8")  # Light gray
        treeview.tag_configure("evenrow", background="white")

        for index, article in enumerate(page_articles):
            # Get authors for the current article
            article_id = article[0]
            authors = fetch_authors_for_article(article_id)

            # Prepare author data for dynamic columns
            author_data = []
            for i in range(1, max_authors + 1):
                if i <= len(authors):
                    author_data.append(authors[i - 1][0])  # Author ID
                    author_data.append(authors[i - 1][1])  # Author Name
                else:
                    author_data.append(None)
                    author_data.append(None)

            # Fill content, abstract,reference, and URL with "double click"
            content = "Double click"
            abstract = "Double click"
            reference = "Double click"
            url = "Double click"

            # Set tag based on row index - MODIFY THIS PART
            tag = "oddrow" if index % 2 == 0 else "evenrow"
        
            # Insert article and authors into the treeview with the tag
            treeview.insert("", "end", values=(
                article[0],           # article_id
                article[1],           # title
                content,              # content
                abstract,             # abstract
                reference,           # reference
                url,                  # url
                article[2],           # published_date 
            ) + tuple(author_data), tags=(tag,))

        # REMOVE THIS SECTION - This is creating a separate treeview that's never displayed
        # tree = ttk.Treeview(root, columns=("A",), show = "headings")
        # tree.pack()
        # tree.heading("A", text="column A")
        # tree.tag_configure("bg0", background="#ffffff")
        # tree.tag_configure("bg0", background="#f0f0f0")
        # for i in range(10):
        #     tag = "bg0" if i % 2 == 0 else "bg1"
        #     tree.insert("", "end", values=())

        # Update the page label
        page_label.config(text=f"Page {current_page} of {total_pages}")

        # Update arrow button states
        if current_page == 1:
            prev_button.config(state=tk.DISABLED)
        else:
            prev_button.config(state=tk.NORMAL)

        if current_page == total_pages:
            next_button.config(state=tk.DISABLED)
        else:
            next_button.config(state=tk.NORMAL)

        # If there's only one page, disable both buttons
        if total_pages == 1:
            prev_button.config(state=tk.DISABLED)
            next_button.config(state=tk.DISABLED)


    # Function to go to the previous page
    def prev_page():
        if current_page > 1:
            update_treeview(current_page - 1)

    # Function to go to the next page
    def next_page():
        if current_page < total_pages:
            update_treeview(current_page + 1)

    # Function to jump to a specific page
    def goto_page():
        try:
           page = int(page_entry.get())
           if 1 <= page <= total_pages:
               update_treeview(page)
               page_entry.delete(0, tk.END)  # Clear the page entry field after navigating
        except ValueError:
            pass


    # Create a frame for pagination controls
    pagination_frame = ttk.Frame(root)
    pagination_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))  # Reduced bottom padding

    # Add previous page button
    prev_button = ttk.Button(pagination_frame, text="←", command=prev_page)
    prev_button.grid(row=0, column=0, padx=5)

    # Add next page button
    next_button = ttk.Button(pagination_frame, text="→", command=next_page)
    next_button.grid(row=0, column=1, padx=5)

    # Add page entry and go button
    page_entry = ttk.Entry(pagination_frame, width=5)
    page_entry.grid(row=0, column=2, padx=5)
    goto_button = ttk.Button(pagination_frame, text="Go", command=goto_page)
    goto_button.grid(row=0, column=3, padx=5)

    # Add page label
    page_label = ttk.Label(pagination_frame, text=f"Page {current_page} of {total_pages}")
    page_label.grid(row=0, column=4, padx=5)

    # Initialize the Treeview with the first page
    update_treeview(current_page)

    # Run the Tkinter main loop
    root.mainloop()

# Call the display_data function to launch the UI
display_data()


input("Press Enter to exit...")