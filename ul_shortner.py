import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import string
import random
import webbrowser
import pyperclip
from datetime import datetime
import qrcode
from PIL import Image, ImageTk
import os


class URLShortener:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced URL Shortener")
        self.root.geometry("800x600")
        self.root.configure(bg="#f0f0f0")

        # Initialize database
        self.setup_database()

        # Setup GUI
        self.setup_gui()

        # Statistics variables
        self.total_urls = tk.StringVar()
        self.total_clicks = tk.StringVar()
        self.update_statistics()

    def setup_database(self):
        """Create SQLite database and tables"""
        self.conn = sqlite3.connect('url_shortener.db')
        self.cursor = self.conn.cursor()

        # Create tables
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_url TEXT NOT NULL,
                short_code TEXT UNIQUE NOT NULL,
                created_date DATETIME NOT NULL,
                clicks INTEGER DEFAULT 0,
                custom_code TEXT,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        self.conn.commit()

    def setup_gui(self):
        """Setup the GUI components"""
        # Main Frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # URL Input Section
        input_frame = ttk.LabelFrame(main_frame, text="Shorten URL", padding="10")
        input_frame.pack(fill=tk.X, pady=5)

        # URL Entry
        ttk.Label(input_frame, text="Enter URL:").pack(anchor=tk.W)
        self.url_entry = ttk.Entry(input_frame, width=70)
        self.url_entry.pack(fill=tk.X, pady=5)

        # Custom Code Entry
        ttk.Label(input_frame, text="Custom Code (optional):").pack(anchor=tk.W)
        self.custom_code_entry = ttk.Entry(input_frame, width=30)
        self.custom_code_entry.pack(fill=tk.X, pady=5)

        # Buttons Frame
        buttons_frame = ttk.Frame(input_frame)
        buttons_frame.pack(fill=tk.X, pady=5)

        # Shorten Button
        ttk.Button(
            buttons_frame,
            text="Shorten URL",
            command=self.shorten_url
        ).pack(side=tk.LEFT, padx=5)

        # Clear Button
        ttk.Button(
            buttons_frame,
            text="Clear",
            command=self.clear_entries
        ).pack(side=tk.LEFT)

        # Statistics Frame
        stats_frame = ttk.LabelFrame(main_frame, text="Statistics", padding="10")
        stats_frame.pack(fill=tk.X, pady=5)

        # Statistics Labels
        ttk.Label(stats_frame, text="Total URLs:").pack(side=tk.LEFT, padx=5)
        ttk.Label(stats_frame, textvariable=self.total_urls).pack(side=tk.LEFT, padx=5)
        ttk.Label(stats_frame, text="Total Clicks:").pack(side=tk.LEFT, padx=5)
        ttk.Label(stats_frame, textvariable=self.total_clicks).pack(side=tk.LEFT, padx=5)

        # URLs List
        list_frame = ttk.LabelFrame(main_frame, text="Your URLs", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Treeview
        self.tree = ttk.Treeview(
            list_frame,
            columns=("Original", "Short", "Clicks", "Date"),
            show="headings"
        )

        # Configure columns
        self.tree.heading("Original", text="Original URL")
        self.tree.heading("Short", text="Short URL")
        self.tree.heading("Clicks", text="Clicks")
        self.tree.heading("Date", text="Created Date")

        self.tree.column("Original", width=300)
        self.tree.column("Short", width=100)
        self.tree.column("Clicks", width=70)
        self.tree.column("Date", width=100)

        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Pack tree and scrollbar
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind double-click event
        self.tree.bind("<Double-1>", self.on_url_click)

        # Context menu
        self.create_context_menu()

        # Load existing URLs
        self.load_urls()

    def create_context_menu(self):
        """Create right-click context menu"""
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Copy Original URL", command=self.copy_original_url)
        self.context_menu.add_command(label="Copy Short URL", command=self.copy_short_url)
        self.context_menu.add_command(label="Generate QR Code", command=self.generate_qr_code)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Delete", command=self.delete_url)

        self.tree.bind("<Button-3>", self.show_context_menu)

    def show_context_menu(self, event):
        """Show context menu on right-click"""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def generate_short_code(self, length=6):
        """Generate a random short code"""
        characters = string.ascii_letters + string.digits
        while True:
            code = ''.join(random.choice(characters) for _ in range(length))
            # Check if code exists
            self.cursor.execute("SELECT id FROM urls WHERE short_code = ?", (code,))
            if not self.cursor.fetchone():
                return code

    def shorten_url(self):
        """Shorten the URL and save to database"""
        original_url = self.url_entry.get().strip()
        custom_code = self.custom_code_entry.get().strip()

        if not original_url:
            messagebox.showerror("Error", "Please enter a URL")
            return

        if not original_url.startswith(('http://', 'https://')):
            original_url = 'https://' + original_url

        try:
            short_code = custom_code if custom_code else self.generate_short_code()
            created_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            self.cursor.execute("""
                INSERT INTO urls (original_url, short_code, created_date)
                VALUES (?, ?, ?)
            """, (original_url, short_code, created_date))

            self.conn.commit()
            self.clear_entries()
            self.load_urls()
            self.update_statistics()

            # Show success message with copy option
            if messagebox.askyesno("Success", "URL shortened successfully! Would you like to copy it?"):
                pyperclip.copy(f"http://short.url/{short_code}")

        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "This custom code is already in use")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

    def load_urls(self):
        """Load URLs from database into treeview"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Load URLs
        self.cursor.execute("""
            SELECT original_url, short_code, clicks, created_date 
            FROM urls 
            WHERE is_active = 1 
            ORDER BY created_date DESC
        """)

        for url in self.cursor.fetchall():
            self.tree.insert(
                "",
                "end",
                values=(
                    url[0],
                    f"http://short.url/{url[1]}",
                    url[2],
                    url[3]
                )
            )

    def on_url_click(self, event):
        """Handle double-click on URL"""
        item = self.tree.selection()[0]
        short_url = self.tree.item(item)['values'][1]
        short_code = short_url.split('/')[-1]

        # Update clicks
        self.cursor.execute("""
            UPDATE urls 
            SET clicks = clicks + 1 
            WHERE short_code = ?
        """, (short_code,))
        self.conn.commit()

        # Open URL in browser
        webbrowser.open(self.tree.item(item)['values'][0])

        # Refresh display
        self.load_urls()
        self.update_statistics()

    def update_statistics(self):
        """Update statistics display"""
        self.cursor.execute("SELECT COUNT(*), SUM(clicks) FROM urls WHERE is_active = 1")
        stats = self.cursor.fetchone()
        self.total_urls.set(stats[0] or 0)
        self.total_clicks.set(stats[1] or 0)

    def clear_entries(self):
        """Clear input entries"""
        self.url_entry.delete(0, tk.END)
        self.custom_code_entry.delete(0, tk.END)

    def copy_original_url(self):
        """Copy original URL to clipboard"""
        item = self.tree.selection()[0]
        original_url = self.tree.item(item)['values'][0]
        pyperclip.copy(original_url)
        messagebox.showinfo("Success", "Original URL copied to clipboard!")

    def copy_short_url(self):
        """Copy short URL to clipboard"""
        item = self.tree.selection()[0]
        short_url = self.tree.item(item)['values'][1]
        pyperclip.copy(short_url)
        messagebox.showinfo("Success", "Short URL copied to clipboard!")

    def generate_qr_code(self):
        """Generate QR code for selected URL"""
        item = self.tree.selection()[0]
        short_url = self.tree.item(item)['values'][1]

        # Create QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(short_url)
        qr.make(fit=True)

        # Create and save QR code image
        qr_image = qr.make_image(fill_color="black", back_color="white")

        # Create directory if it doesn't exist
        if not os.path.exists('qrcodes'):
            os.makedirs('qrcodes')

        # Save QR code
        filename = f"qrcodes/qr_{short_url.split('/')[-1]}.png"
        qr_image.save(filename)

        # Show success message
        messagebox.showinfo("Success", f"QR Code saved as {filename}")

    def delete_url(self):
        """Delete selected URL"""
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this URL?"):
            item = self.tree.selection()[0]
            short_url = self.tree.item(item)['values'][1]
            short_code = short_url.split('/')[-1]

            self.cursor.execute("""
                UPDATE urls 
                SET is_active = 0 
                WHERE short_code = ?
            """, (short_code,))
            self.conn.commit()

            self.load_urls()
            self.update_statistics()

    def __del__(self):
        """Cleanup database connection"""
        self.conn.close()


if __name__ == "__main__":
    root = tk.Tk()
    app = URLShortener(root)
    root.mainloop()