import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import mysql.connector
import json
import hashlib
import os
import uuid
from datetime import datetime
import sys
import subprocess

class UserAdminTool:
    def __init__(self, root):
        self.root = root
        self.root.title("User Management Admin Tool")
        self.root.geometry("1000x600")
        
        # Add return button in the header frame
        self.header_frame = ttk.Frame(root)
        self.header_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        
        self.return_button = ttk.Button(
            self.header_frame,
            text="← Return to Selection",
            command=self.return_to_selection
        )
        self.return_button.pack(side=tk.RIGHT)
        
        # Connect to database
        self.db = self.connect_to_db()
        if not self.db:
            messagebox.showerror("Error", "Failed to connect to database")
            root.destroy()
            return
            
        # Create main frame
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create tabs
        self.tab_control = ttk.Notebook(self.main_frame)
        
        # Users tab
        self.users_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.users_tab, text="Users")
        
        # Profiles tab
        self.profiles_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.profiles_tab, text="Profiles")
        
        # Search History tab
        self.search_history_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.search_history_tab, text="Search History")
        
        # Saved Searches tab
        self.saved_searches_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.saved_searches_tab, text="Saved Searches")
        
        # Favorites tab
        self.favorites_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.favorites_tab, text="Favorites")
        
        self.tab_control.pack(expand=True, fill=tk.BOTH)
        
        # Setup each tab
        self.setup_users_tab()
        self.setup_profiles_tab()
        self.setup_search_history_tab()
        self.setup_saved_searches_tab()
        self.setup_favorites_tab()  # Setup the new favorites tab
        
        # Load initial data
        self.load_users()
    
    def return_to_selection(self):
        self.root.destroy()  # Close the current window
        python = sys.executable
        subprocess.Popen([python, "select_py.py"])  # Start the selection window
        
    def connect_to_db(self):
        try:
            # Read JSON config document
            with open('selected_config.json', 'r') as file:
                config = json.load(file)
            
            # Make sure the JSON structure is correct
            required_keys = ["host", "database", "user", "password"]
            for key in required_keys:
                if key not in config or not config[key].strip():
                    print(f"Error: '{key}' is missing or empty in selected_config.json")
                    return None
            
            # Connect to the database
            db = mysql.connector.connect(
                host=config["host"],
                database=config["database"],
                user=config["user"],
                password=config["password"]
            )
            return db
        except Exception as e:
            print(f"Database connection error: {e}")
            return None
    
    def refresh_db_connection(self):
        """Refresh the database connection to get the latest data"""
        try:
            # Close the existing connection if it exists
            if self.db and self.db.is_connected():
                self.db.close()
                
            # Create a new connection
            self.db = self.connect_to_db()
            return True
        except Exception as e:
            print(f"Error refreshing database connection: {e}")
            messagebox.showerror("Error", f"Failed to refresh database connection: {e}")
            return False
    
    def setup_users_tab(self):
        # Create frame for buttons
        button_frame = ttk.Frame(self.users_tab)
        button_frame.pack(fill=tk.X, pady=5)
        
        # Add buttons
        ttk.Button(button_frame, text="Refresh", command=self.load_users).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Add User", command=self.add_user).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Edit User", command=self.edit_user).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Delete User", command=self.delete_user).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Change Password", command=self.change_password).pack(side=tk.LEFT, padx=5)
        
        # Create search frame
        search_frame = ttk.Frame(self.users_tab)
        search_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        self.user_search_var = tk.StringVar()
        ttk.Entry(search_frame, textvariable=self.user_search_var).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(search_frame, text="Search", command=self.search_users).pack(side=tk.LEFT, padx=5)
        
        # Create treeview for users
        columns = ("id", "email", "password", "salt", "created_at")
        self.users_tree = ttk.Treeview(self.users_tab, columns=columns, show="headings")
        
        # Define headings
        self.users_tree.heading("id", text="ID")
        self.users_tree.heading("email", text="Email")
        self.users_tree.heading("password", text="Password (Hashed)")
        self.users_tree.heading("salt", text="Salt")
        self.users_tree.heading("created_at", text="Created At")
        
        # Define columns
        self.users_tree.column("id", width=200)
        self.users_tree.column("email", width=150)
        self.users_tree.column("password", width=250)
        self.users_tree.column("salt", width=150)
        self.users_tree.column("created_at", width=150)
        
        # Configure tags for alternating row colors
        self.users_tree.tag_configure('oddrow', background='#E8E8E8')  # Light gray
        self.users_tree.tag_configure('evenrow', background='white')
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.users_tab, orient=tk.VERTICAL, command=self.users_tree.yview)
        self.users_tree.configure(yscroll=scrollbar.set)
        
        # Pack treeview and scrollbar
        self.users_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        scrollbar.pack(fill=tk.Y, side=tk.RIGHT)
        
        # Bind double click event
        self.users_tree.bind("<Double-1>", lambda event: self.edit_user())
    
    def setup_profiles_tab(self):
        # Create frame for buttons
        button_frame = ttk.Frame(self.profiles_tab)
        button_frame.pack(fill=tk.X, pady=5)
        
        # Add buttons
        ttk.Button(button_frame, text="Refresh", command=self.load_profiles).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Edit Profile", command=self.edit_profile).pack(side=tk.LEFT, padx=5)
        
        # Create treeview for profiles
        columns = ("user_id", "username", "full_name", "avatar_url", "updated_at")
        self.profiles_tree = ttk.Treeview(self.profiles_tab, columns=columns, show="headings")
        
        # Define headings
        self.profiles_tree.heading("user_id", text="User ID")
        self.profiles_tree.heading("username", text="Username")
        self.profiles_tree.heading("full_name", text="Full Name")
        self.profiles_tree.heading("avatar_url", text="Avatar URL")
        self.profiles_tree.heading("updated_at", text="Updated At")
        
        # Define columns
        self.profiles_tree.column("user_id", width=200)
        self.profiles_tree.column("username", width=150)
        self.profiles_tree.column("full_name", width=150)
        self.profiles_tree.column("avatar_url", width=250)
        self.profiles_tree.column("updated_at", width=150)
        
        # Configure tags for alternating row colors
        self.profiles_tree.tag_configure('oddrow', background='#E8E8E8')  # Light gray
        self.profiles_tree.tag_configure('evenrow', background='white')
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.profiles_tab, orient=tk.VERTICAL, command=self.profiles_tree.yview)
        self.profiles_tree.configure(yscroll=scrollbar.set)
        
        # Pack treeview and scrollbar
        self.profiles_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        scrollbar.pack(fill=tk.Y, side=tk.RIGHT)
        
        # Bind double click event
        self.profiles_tree.bind("<Double-1>", lambda event: self.edit_profile())
    
    def setup_search_history_tab(self):
        # Create frame for buttons
        button_frame = ttk.Frame(self.search_history_tab)
        button_frame.pack(fill=tk.X, pady=5)
        
        # Add buttons
        ttk.Button(button_frame, text="Refresh", command=self.load_search_history).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Delete Entry", command=self.delete_search_history).pack(side=tk.LEFT, padx=5)
        
        # Create treeview for search history
        columns = ("id", "user_id", "query", "created_at")
        self.search_history_tree = ttk.Treeview(self.search_history_tab, columns=columns, show="headings")
        
        # Define headings
        self.search_history_tree.heading("id", text="ID")
        self.search_history_tree.heading("user_id", text="User ID")
        self.search_history_tree.heading("query", text="Query")
        self.search_history_tree.heading("created_at", text="Created At")
        
        # Define columns
        self.search_history_tree.column("id", width=200)
        self.search_history_tree.column("user_id", width=200)
        self.search_history_tree.column("query", width=400)
        self.search_history_tree.column("created_at", width=150)
        
        # Configure tags for alternating row colors
        self.search_history_tree.tag_configure('oddrow', background='#E8E8E8')  # Light gray
        self.search_history_tree.tag_configure('evenrow', background='white')
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.search_history_tab, orient=tk.VERTICAL, command=self.search_history_tree.yview)
        self.search_history_tree.configure(yscroll=scrollbar.set)
        
        # Pack treeview and scrollbar
        self.search_history_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        scrollbar.pack(fill=tk.Y, side=tk.RIGHT)
    
    def setup_saved_searches_tab(self):
        # Create frame for buttons
        button_frame = ttk.Frame(self.saved_searches_tab)
        button_frame.pack(fill=tk.X, pady=5)
        
        # Add buttons
        ttk.Button(button_frame, text="Refresh", command=self.load_saved_searches).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Delete Entry", command=self.delete_saved_search).pack(side=tk.LEFT, padx=5)
        
        # Create treeview for saved searches
        columns = ("id", "user_id", "query", "created_at")
        self.saved_searches_tree = ttk.Treeview(self.saved_searches_tab, columns=columns, show="headings")
        
        # Define headings
        self.saved_searches_tree.heading("id", text="ID")
        self.saved_searches_tree.heading("user_id", text="User ID")
        self.saved_searches_tree.heading("query", text="Query")
        self.saved_searches_tree.heading("created_at", text="Created At")
        
        # Define columns
        self.saved_searches_tree.column("id", width=200)
        self.saved_searches_tree.column("user_id", width=200)
        self.saved_searches_tree.column("query", width=400)
        self.saved_searches_tree.column("created_at", width=150)
        
        # Configure tags for alternating row colors
        self.saved_searches_tree.tag_configure('oddrow', background='#E8E8E8')  # Light gray
        self.saved_searches_tree.tag_configure('evenrow', background='white')
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.saved_searches_tab, orient=tk.VERTICAL, command=self.saved_searches_tree.yview)
        self.saved_searches_tree.configure(yscroll=scrollbar.set)
        
        # Pack treeview and scrollbar
        self.saved_searches_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        scrollbar.pack(fill=tk.Y, side=tk.RIGHT)
    
    # Setup the new favorites tab
    def setup_favorites_tab(self):
        # Create frame for buttons
        button_frame = ttk.Frame(self.favorites_tab)
        button_frame.pack(fill=tk.X, pady=5)
        
        # Add buttons
        ttk.Button(button_frame, text="Refresh", command=self.load_favorites).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Delete Favorite", command=self.delete_favorite).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Add Favorite", command=self.add_favorite).pack(side=tk.LEFT, padx=5)
        
        # Create treeview for favorites
        columns = ("id", "user_id", "article_id", "created_at")
        self.favorites_tree = ttk.Treeview(self.favorites_tab, columns=columns, show="headings")
        
        # Define headings
        self.favorites_tree.heading("id", text="ID")
        self.favorites_tree.heading("user_id", text="User ID")
        self.favorites_tree.heading("article_id", text="Article ID")
        self.favorites_tree.heading("created_at", text="Created At")
        
        # Define columns
        self.favorites_tree.column("id", width=200)
        self.favorites_tree.column("user_id", width=200)
        self.favorites_tree.column("article_id", width=200)
        self.favorites_tree.column("created_at", width=150)
        
        # Configure tags for alternating row colors
        self.favorites_tree.tag_configure('oddrow', background='#E8E8E8')  # Light gray
        self.favorites_tree.tag_configure('evenrow', background='white')
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.favorites_tab, orient=tk.VERTICAL, command=self.favorites_tree.yview)
        self.favorites_tree.configure(yscroll=scrollbar.set)
        
        # Pack treeview and scrollbar
        self.favorites_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        scrollbar.pack(fill=tk.Y, side=tk.RIGHT)
    
    def load_users(self):
        # Refresh the database connection to get the latest data
        if not self.refresh_db_connection():
            return
            
        # Clear existing data
        for item in self.users_tree.get_children():
            self.users_tree.delete(item)
        
        try:
            cursor = self.db.cursor()
            cursor.execute("SELECT id, email, password, salt, created_at FROM users")
            users = cursor.fetchall()
            
            # Insert with alternating row colors
            for i, user in enumerate(users):
                tag = 'oddrow' if i % 2 == 0 else 'evenrow'
                self.users_tree.insert("", tk.END, values=user, tags=(tag,))
            
            cursor.close()
            
            # Also load related data
            self.load_profiles()
            self.load_search_history()
            self.load_saved_searches()
            self.load_favorites()  # Load favorites data
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load users: {e}")
    
    def load_profiles(self):
        # Clear existing data
        for item in self.profiles_tree.get_children():
            self.profiles_tree.delete(item)
        
        try:
            cursor = self.db.cursor()
            cursor.execute("SELECT user_id, username, full_name, avatar_url, updated_at FROM profiles")
            profiles = cursor.fetchall()
            
            # Insert with alternating row colors
            for i, profile in enumerate(profiles):
                tag = 'oddrow' if i % 2 == 0 else 'evenrow'
                self.profiles_tree.insert("", tk.END, values=profile, tags=(tag,))
            
            cursor.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load profiles: {e}")
    
    def load_search_history(self):
        # Clear existing data
        for item in self.search_history_tree.get_children():
            self.search_history_tree.delete(item)
        
        try:
            cursor = self.db.cursor()
            cursor.execute("SELECT id, user_id, query, created_at FROM search_history")
            history = cursor.fetchall()
            
            # Insert with alternating row colors
            for i, entry in enumerate(history):
                tag = 'oddrow' if i % 2 == 0 else 'evenrow'
                self.search_history_tree.insert("", tk.END, values=entry, tags=(tag,))
            
            cursor.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load search history: {e}")
    
    def load_saved_searches(self):
        # Clear existing data
        for item in self.saved_searches_tree.get_children():
            self.saved_searches_tree.delete(item)
        
        try:
            cursor = self.db.cursor()
            cursor.execute("SELECT id, user_id, query, created_at FROM saved_searches")
            searches = cursor.fetchall()
            
            # Insert with alternating row colors
            for i, search in enumerate(searches):
                tag = 'oddrow' if i % 2 == 0 else 'evenrow'
                self.saved_searches_tree.insert("", tk.END, values=search, tags=(tag,))
            
            cursor.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load saved searches: {e}")
    
    # Load favorites data
    def load_favorites(self):
        # Clear existing data
        for item in self.favorites_tree.get_children():
            self.favorites_tree.delete(item)
        
        try:
            cursor = self.db.cursor()
            cursor.execute("SELECT id, user_id, article_id, created_at FROM favorites")
            favorites = cursor.fetchall()
            
            # Insert with alternating row colors
            for i, favorite in enumerate(favorites):
                tag = 'oddrow' if i % 2 == 0 else 'evenrow'
                self.favorites_tree.insert("", tk.END, values=favorite, tags=(tag,))
            
            cursor.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load favorites: {e}")
    
    def search_users(self):
        search_term = self.user_search_var.get().strip()
        if not search_term:
            self.load_users()
            return
        
        # Clear existing data
        for item in self.users_tree.get_children():
            self.users_tree.delete(item)
        
        try:
            cursor = self.db.cursor()
            cursor.execute("SELECT id, email, password, salt, created_at FROM users WHERE email LIKE %s", (f"%{search_term}%",))
            users = cursor.fetchall()
            
            # Insert with alternating row colors
            for i, user in enumerate(users):
                tag = 'oddrow' if i % 2 == 0 else 'evenrow'
                self.users_tree.insert("", tk.END, values=user, tags=(tag,))
            
            cursor.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to search users: {e}")
    
    def add_user(self):
        # Create a new window for adding a user
        add_window = tk.Toplevel(self.root)
        add_window.title("Add New User")
        add_window.geometry("400x200")
        add_window.grab_set()  # Make window modal
        
        # Create form fields
        ttk.Label(add_window, text="Email:").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        email_var = tk.StringVar()
        ttk.Entry(add_window, textvariable=email_var, width=30).grid(row=0, column=1, padx=10, pady=10)
        
        ttk.Label(add_window, text="Password:").grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        password_var = tk.StringVar()
        ttk.Entry(add_window, textvariable=password_var, show="*", width=30).grid(row=1, column=1, padx=10, pady=10)
        
        # Create buttons
        button_frame = ttk.Frame(add_window)
        button_frame.grid(row=2, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="Save", command=lambda: self.save_new_user(email_var.get(), password_var.get(), add_window)).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Cancel", command=add_window.destroy).pack(side=tk.LEFT, padx=10)
    
    def save_new_user(self, email, password, window):
        if not email or not password:
            messagebox.showerror("Error", "Email and password are required", parent=window)
            return
        
        try:
            # Generate user ID and hash password
            user_id = str(uuid.uuid4())
            hashed_password, salt = self.hash_password(password)
            
            # Insert into database
            cursor = self.db.cursor()
            cursor.execute(
                'INSERT INTO users (id, email, password, salt) VALUES (%s, %s, %s, %s)',
                (user_id, email, hashed_password, salt)
            )
            cursor.execute('INSERT INTO profiles (user_id) VALUES (%s)', (user_id,))
            
            self.db.commit()
            cursor.close()
            
            messagebox.showinfo("Success", "User added successfully", parent=window)
            window.destroy()
            self.load_users()
        except Exception as e:
            self.db.rollback()
            messagebox.showerror("Error", f"Failed to add user: {e}", parent=window)
    
    def edit_user(self):
        selected_item = self.users_tree.selection()
        if not selected_item:
            messagebox.showinfo("Info", "Please select a user to edit")
            return
        
        # Get user data
        user_data = self.users_tree.item(selected_item[0], "values")
        user_id = user_data[0]
        email = user_data[1]
        
        # Create a new window for editing
        edit_window = tk.Toplevel(self.root)
        edit_window.title("Edit User")
        edit_window.geometry("400x150")
        edit_window.grab_set()  # Make window modal
        
        # Create form fields
        ttk.Label(edit_window, text="Email:").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        email_var = tk.StringVar(value=email)
        ttk.Entry(edit_window, textvariable=email_var, width=30).grid(row=0, column=1, padx=10, pady=10)
        
        # Create buttons
        button_frame = ttk.Frame(edit_window)
        button_frame.grid(row=1, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="Save", command=lambda: self.save_edited_user(user_id, email_var.get(), edit_window)).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Cancel", command=edit_window.destroy).pack(side=tk.LEFT, padx=10)
    
    def save_edited_user(self, user_id, email, window):
        if not email:
            messagebox.showerror("Error", "Email is required", parent=window)
            return
        
        try:
            cursor = self.db.cursor()
            cursor.execute('UPDATE users SET email = %s WHERE id = %s', (email, user_id))
            
            self.db.commit()
            cursor.close()
            
            messagebox.showinfo("Success", "User updated successfully", parent=window)
            window.destroy()
            self.load_users()
        except Exception as e:
            self.db.rollback()
            messagebox.showerror("Error", f"Failed to update user: {e}", parent=window)
    
    def delete_user(self):
        selected_item = self.users_tree.selection()
        if not selected_item:
            messagebox.showinfo("Info", "Please select a user to delete")
            return
        
        # Get user data
        user_data = self.users_tree.item(selected_item[0], "values")
        user_id = user_data[0]
        email = user_data[1]
        
        # Confirm deletion
        if not messagebox.askyesno("Confirm", f"Are you sure you want to delete user {email}?"):
            return
        
        try:
            cursor = self.db.cursor()
            # The ON DELETE CASCADE will handle related records
            cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
            
            self.db.commit()
            cursor.close()
            
            messagebox.showinfo("Success", "User deleted successfully")
            self.load_users()
        except Exception as e:
            self.db.rollback()
            messagebox.showerror("Error", f"Failed to delete user: {e}")
    
    def change_password(self):
        selected_item = self.users_tree.selection()
        if not selected_item:
            messagebox.showinfo("Info", "Please select a user to change password")
            return
        
        # Get user data
        user_data = self.users_tree.item(selected_item[0], "values")
        user_id = user_data[0]
        email = user_data[1]
        
        # Create a new window for changing password
        password_window = tk.Toplevel(self.root)
        password_window.title(f"Change Password for {email}")
        password_window.geometry("400x150")
        password_window.grab_set()  # Make window modal
        
        # Create form fields
        ttk.Label(password_window, text="New Password:").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        password_var = tk.StringVar()
        ttk.Entry(password_window, textvariable=password_var, show="*", width=30).grid(row=0, column=1, padx=10, pady=10)
        
        # Create buttons
        button_frame = ttk.Frame(password_window)
        button_frame.grid(row=1, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="Save", command=lambda: self.save_new_password(user_id, password_var.get(), password_window)).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Cancel", command=password_window.destroy).pack(side=tk.LEFT, padx=10)
    
    def save_new_password(self, user_id, password, window):
        if not password:
            messagebox.showerror("Error", "Password is required", parent=window)
            return
        
        try:
            # Hash the new password
            hashed_password, salt = self.hash_password(password)
            
            cursor = self.db.cursor()
            cursor.execute('UPDATE users SET password = %s, salt = %s WHERE id = %s', 
                          (hashed_password, salt, user_id))
            
            self.db.commit()
            cursor.close()
            
            messagebox.showinfo("Success", "Password updated successfully", parent=window)
            window.destroy()
            self.load_users()
        except Exception as e:
            self.db.rollback()
            messagebox.showerror("Error", f"Failed to update password: {e}", parent=window)
    
    def edit_profile(self):
        selected_item = self.profiles_tree.selection()
        if not selected_item:
            messagebox.showinfo("Info", "Please select a profile to edit")
            return
        
        # Get profile data
        profile_data = self.profiles_tree.item(selected_item[0], "values")
        user_id = profile_data[0]
        username = profile_data[1] if profile_data[1] else ""
        full_name = profile_data[2] if profile_data[2] else ""
        avatar_url = profile_data[3] if profile_data[3] else ""
        
        # Create a new window for editing
        edit_window = tk.Toplevel(self.root)
        edit_window.title("Edit Profile")
        edit_window.geometry("500x250")
        edit_window.grab_set()  # Make window modal
        
        # Create form fields
        ttk.Label(edit_window, text="Username:").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        username_var = tk.StringVar(value=username)
        ttk.Entry(edit_window, textvariable=username_var, width=30).grid(row=0, column=1, padx=10, pady=10)
        
        ttk.Label(edit_window, text="Full Name:").grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        full_name_var = tk.StringVar(value=full_name)
        ttk.Entry(edit_window, textvariable=full_name_var, width=30).grid(row=1, column=1, padx=10, pady=10)
        
        ttk.Label(edit_window, text="Avatar URL:").grid(row=2, column=0, padx=10, pady=10, sticky=tk.W)
        avatar_url_var = tk.StringVar(value=avatar_url)
        ttk.Entry(edit_window, textvariable=avatar_url_var, width=30).grid(row=2, column=1, padx=10, pady=10)
        
        # Create buttons
        button_frame = ttk.Frame(edit_window)
        button_frame.grid(row=3, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="Save", command=lambda: self.save_edited_profile(
            user_id, username_var.get(), full_name_var.get(), avatar_url_var.get(), edit_window
        )).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Cancel", command=edit_window.destroy).pack(side=tk.LEFT, padx=10)
    
    def save_edited_profile(self, user_id, username, full_name, avatar_url, window):
        try:
            cursor = self.db.cursor()
            cursor.execute(
                'UPDATE profiles SET username = %s, full_name = %s, avatar_url = %s, updated_at = %s WHERE user_id = %s',
                (username, full_name, avatar_url, datetime.now(), user_id)
            )
            
            self.db.commit()
            cursor.close()
            
            messagebox.showinfo("Success", "Profile updated successfully", parent=window)
            window.destroy()
            self.load_profiles()
        except Exception as e:
            self.db.rollback()
            messagebox.showerror("Error", f"Failed to update profile: {e}", parent=window)
    
    def delete_search_history(self):
        selected_item = self.search_history_tree.selection()
        if not selected_item:
            messagebox.showinfo("Info", "Please select a search history entry to delete")
            return
        
        # Get entry data
        entry_data = self.search_history_tree.item(selected_item[0], "values")
        entry_id = entry_data[0]
        
        # Confirm deletion
        if not messagebox.askyesno("Confirm", "Are you sure you want to delete this search history entry?"):
            return
        
        try:
            cursor = self.db.cursor()
            cursor.execute('DELETE FROM search_history WHERE id = %s', (entry_id,))
            
            self.db.commit()
            cursor.close()
            
            messagebox.showinfo("Success", "Search history entry deleted successfully")
            self.load_search_history()
        except Exception as e:
            self.db.rollback()
            messagebox.showerror("Error", f"Failed to delete search history entry: {e}")
    
    def delete_saved_search(self):
        selected_item = self.saved_searches_tree.selection()
        if not selected_item:
            messagebox.showinfo("Info", "Please select a saved search to delete")
            return
        
        # Get entry data
        entry_data = self.saved_searches_tree.item(selected_item[0], "values")
        entry_id = entry_data[0]
        
        # Confirm deletion
        if not messagebox.askyesno("Confirm", "Are you sure you want to delete this saved search?"):
            return
        
        try:
            cursor = self.db.cursor()
            cursor.execute('DELETE FROM saved_searches WHERE id = %s', (entry_id,))
            
            self.db.commit()
            cursor.close()
            
            messagebox.showinfo("Success", "Saved search deleted successfully")
            self.load_saved_searches()
        except Exception as e:
            self.db.rollback()
            messagebox.showerror("Error", f"Failed to delete saved search: {e}")
    
    # Add a new favorite
    def add_favorite(self):
        # Create a new window for adding a favorite
        add_window = tk.Toplevel(self.root)
        add_window.title("Add New Favorite")
        add_window.geometry("400x200")
        add_window.grab_set()  # Make window modal
        
        # Create form fields
        ttk.Label(add_window, text="User ID:").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        user_id_var = tk.StringVar()
        ttk.Entry(add_window, textvariable=user_id_var, width=30).grid(row=0, column=1, padx=10, pady=10)
        
        ttk.Label(add_window, text="Article ID:").grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        article_id_var = tk.StringVar()
        ttk.Entry(add_window, textvariable=article_id_var, width=30).grid(row=1, column=1, padx=10, pady=10)
        
        # Create buttons
        button_frame = ttk.Frame(add_window)
        button_frame.grid(row=2, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="Save", command=lambda: self.save_new_favorite(
            user_id_var.get(), article_id_var.get(), add_window
        )).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Cancel", command=add_window.destroy).pack(side=tk.LEFT, padx=10)
    
    # Save a new favorite
    def save_new_favorite(self, user_id, article_id, window):
        if not user_id or not article_id:
            messagebox.showerror("Error", "User ID and Article ID are required", parent=window)
            return
        
        try:
            # Generate favorite ID
            favorite_id = str(uuid.uuid4())
            
            # Insert into database
            cursor = self.db.cursor()
            cursor.execute(
                'INSERT INTO favorites (id, user_id, article_id) VALUES (%s, %s, %s)',
                (favorite_id, user_id, article_id)
            )
            
            self.db.commit()
            cursor.close()
            
            messagebox.showinfo("Success", "Favorite added successfully", parent=window)
            window.destroy()
            self.load_favorites()
        except Exception as e:
            self.db.rollback()
            messagebox.showerror("Error", f"Failed to add favorite: {e}", parent=window)
    
    # Delete a favorite
    def delete_favorite(self):
        selected_item = self.favorites_tree.selection()
        if not selected_item:
            messagebox.showinfo("Info", "Please select a favorite to delete")
            return
        
        # Get favorite data
        favorite_data = self.favorites_tree.item(selected_item[0], "values")
        favorite_id = favorite_data[0]
        
        # Confirm deletion
        if not messagebox.askyesno("Confirm", "Are you sure you want to delete this favorite?"):
            return
        
        try:
            cursor = self.db.cursor()
            cursor.execute('DELETE FROM favorites WHERE id = %s', (favorite_id,))
            
            self.db.commit()
            cursor.close()
            
            messagebox.showinfo("Success", "Favorite deleted successfully")
            self.load_favorites()
        except Exception as e:
            self.db.rollback()
            messagebox.showerror("Error", f"Failed to delete favorite: {e}")
    
    def hash_password(self, password, salt=None):
        if salt is None:
            salt = os.urandom(16).hex()
        hashed = hashlib.sha256((password + salt).encode()).hexdigest()
        return hashed, salt
    
    def verify_password(self, password, hashed_password, salt):
        return self.hash_password(password, salt)[0] == hashed_password


def main():
    root = tk.Tk()
    app = UserAdminTool(root)
    root.mainloop()

if __name__ == "__main__":
    main()