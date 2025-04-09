import tkinter as tk
from tkinter import messagebox
import mysql.connector 
import subprocess
import sys
import json
import os

# Cnfiguration files
CONFIG_FILE = 'db_configs.json'  # Store all configurations
SELECTED_CONFIG_FILE = 'selected_config.json'  # Only store the selected configuration
def load_configs():
    """Load all configurations from file"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_configs(configs):
    """Save all configurations to file"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(configs, f, indent=4)

def save_selected_config(config):
    """Save select config to selected_config.json，Evervtime it will overwrite the old file"""
    if os.path.exists(SELECTED_CONFIG_FILE):
        os.remove(SELECTED_CONFIG_FILE)  # Delete the old file
    with open(SELECTED_CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)
    
    # **Debug make sure database is stored correctly**
    print("Already saved to selected_config.json:", config)  


root = tk.Tk()
root.title("MySQL Connection")

# Create a new label
tk.Label(root, text="Database server IP").grid(row=0, column=0)
tk.Label(root, text="User").grid(row=1, column=0)
tk.Label(root, text="Password").grid(row=2, column=0)
tk.Label(root, text="Database name").grid(row=3, column=0)

entry_host = tk.Entry(root)
entry_host.grid(row=0, column=1)
entry_user = tk.Entry(root)
entry_user.grid(row=1, column=1)
entry_password = tk.Entry(root, show="*")
entry_password.grid(row=2, column=1)
entry_database = tk.Entry(root)
entry_database.grid(row=3, column=1)

def connect_to_db():
    """Database connection"""
    host = entry_host.get().strip()
    user = entry_user.get().strip()
    password = entry_password.get().strip()
    database = entry_database.get().strip()  # **Make sure database name is not empty**

    if not all([host, user, password, database]):
        messagebox.showwarning("Warning", "All fields cannot be empty！")
        return

    try:
        connection = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        if connection.is_connected():
            messagebox.showinfo("Success", "Connection successful！")
            connection.close()
            root.destroy()

            # **Save selected database config**
            save_selected_config({
                "host": host,
                "user": user,
                "password": password,
                "database": database  # **Make sure database been stored**
            })

            # **Start pre.py**
            python_executable = sys.executable
            subprocess.Popen([python_executable, 'select_py.py'])
    except mysql.connector.Error as err:
        messagebox.showerror("Fail", f"connection fail：{err}")


def open_config_manager():
    """Open the configuration manager"""
    config_window = tk.Toplevel(root)
    config_window.title("Configuration Manager")
    
    # Configurations list
    listbox = tk.Listbox(config_window, width=50)
    listbox.pack(padx=10, pady=5)
    
    # Load configurations
    configs = load_configs()
    for name in configs:
        listbox.insert(tk.END, name)
    
    # Input configuration name
    tk.Label(config_window, text="configuration name").pack()
    entry_name = tk.Entry(config_window)
    entry_name.pack()
    
    def save_config():
        """Save the current configuration"""
        name = entry_name.get()
        if not name:
            messagebox.showwarning("Warning", "Please enter a configuration name")
            return
            
        new_config = {
            'host': entry_host.get(),
            'user': entry_user.get(),
            'password': entry_password.get(),
            'database': entry_database.get()
        }
        
        configs = load_configs()
        if name in configs:
            if not messagebox.askyesno("Confirm", "The configuration name already exists, do you want to overwrite it?"):
                return
        configs[name] = new_config
        save_configs(configs)
        
        # Update the listbox
        listbox.delete(0, tk.END)
        for config in configs:
            listbox.insert(tk.END, config)
        messagebox.showinfo("Success", "Saved configuration successfully")
    
    def load_config():
        """Load the selected configuration"""
        selection = listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a configuration first")
            return

        name = listbox.get(selection[0])
        configs = load_configs()
        config = configs.get(name)

        if config:
            # **Make sure database is been filled**
            entry_host.delete(0, tk.END)
            entry_host.insert(0, config.get("host", ""))
            entry_user.delete(0, tk.END)
            entry_user.insert(0, config.get("user", ""))
            entry_password.delete(0, tk.END)
            entry_password.insert(0, config.get("password", ""))
            entry_database.delete(0, tk.END)
            entry_database.insert(0, config.get("database", ""))  # **Ensure that database fields are not lost**

            # **Save the currently selected database configuration**
            save_selected_config(config)
            
            config_window.destroy()

    
    def delete_config():
        """Delete the selected configuration"""
        selection = listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a configuration first")
            return
            
        name = listbox.get(selection[0])
        configs = load_configs()
        if name in configs:
            del configs[name]
            save_configs(configs)
            listbox.delete(selection[0])
            messagebox.showinfo("Success", "Deleted configuration successfully")
    
    # Button frame
    btn_frame = tk.Frame(config_window)
    btn_frame.pack(pady=5)
    
    tk.Button(btn_frame, text="Save the current configuration", command=save_config).pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame, text="Load the selected configuration", command=load_config).pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame, text="Delete the selected configuration", command=delete_config).pack(side=tk.LEFT, padx=5)

# Interface layout
btn_frame = tk.Frame(root)
btn_frame.grid(row=4, column=0, columnspan=2, pady=5)

tk.Button(btn_frame, text="Connect to database", command=connect_to_db).pack(side=tk.LEFT, padx=5)
tk.Button(btn_frame, text="Configuration management", command=open_config_manager).pack(side=tk.LEFT, padx=5)

root.mainloop()
