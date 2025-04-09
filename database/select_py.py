import tkinter as tk
from tkinter import messagebox
# import mysql.connector
import subprocess
import sys
# import json
import os
from PIL import Image, ImageTk

SELECTED_CONFIG_FILE = 'selected_config.json'

# Selection Window
class SelectionWindow:
    def __init__(self, master):
        self.master = master
        self.window = tk.Toplevel(master)
        self.window.title("Select Program")
        self.window.geometry("700x500")
        
        # Program List (Each program has an image path)
        self.programs = [
            ("pre.py", "Article Information", "article.jpg"),
            ("pre_profile.py", "Author Information", "author.jpg"),
            ("correlation.py", "Correlation", "correlation.png"),
            ("client.py", "User Management", "client.png"),
            ("function5.py", "Function 5", "function5.png"),
            ("function6.py", "Function 6", "function6.png")
        ]
        
        # Store images to avoid garbage collection
        self.images = []
        
        # Main container
        main_frame = tk.Frame(self.window)
        main_frame.pack(pady=20, padx=20, fill=tk.BOTH, expand=True)
        
        # Create grid layout (2 rows, 3 columns)
        row_count = 2
        col_count = 3
        
        for index, (script, text, img_path) in enumerate(self.programs):
            row = index // col_count  # Calculate row index
            col = index % col_count   # Calculate column index
            
            # Create frame for each item
            item_frame = tk.Frame(main_frame, relief="ridge", borderwidth=2, padx=10, pady=10)
            item_frame.grid(row=row, column=col, padx=10, pady=10)
            
            # Load image
            try:
                if os.path.exists(img_path):
                    img = Image.open(img_path)
                    img = img.resize((100, 100), Image.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    self.images.append(photo)
                    img_label = tk.Label(item_frame, image=photo)
                else:
                    raise FileNotFoundError
            except FileNotFoundError:
                img_label = tk.Label(item_frame, text="No Image", width=12, height=6, relief="groove")
            
            img_label.pack()
            
            # Create button
            btn = tk.Button(
                item_frame,
                text=text,
                width=20,
                command=lambda s=script: self.run_script(s),
                relief="groove",
                bg="white",
                activebackground="#e0e0e0"
            )
            btn.pack(pady=5)
        
        # Exit button (placed below the grid)
        exit_frame = tk.Frame(self.window)
        exit_frame.pack(pady=20)
        tk.Button(
            exit_frame,
            text="Exit System",
            command=self.on_close,
            width=20,
            bg="#ff9999",
            relief="groove"
        ).pack()
        
        # Handle window close event
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def run_script(self, script_name):
        """Run the selected script."""
        self.window.destroy()
        self.master.destroy()
        python = sys.executable
        subprocess.Popen([python, script_name])
    
    def on_close(self):
        # Confirm exit
        result = messagebox.askyesno(
            "Confirm Exit",
            "This action will exit the database management tool. Are you sure you want to proceed?"
        )
        if result:
            self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    SelectionWindow(root)
    root.mainloop()
