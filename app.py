import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import json
import csv
import os
import sys
import re # Import regex module

def get_db_path():
    """Ensures the SQLite database is created in the exact same folder as the running app."""
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_dir, "rwandan_legal_dictionary.db")

DB_FILE = get_db_path()

def init_db():
    """Initializes the database with an 11-column fully trilingual flat schema."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dictionary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            term_kinyarwanda TEXT,
            term_english TEXT,
            term_french TEXT,
            definition_kinyarwanda TEXT,
            definition_english TEXT,
            definition_french TEXT,
            domain TEXT,
            sub_domain TEXT,
            source_law TEXT,
            article TEXT,
            year INTEGER
        )
    """)
    conn.commit()
    conn.close()

def run_symbolic_ai(data):
    """Mini Symbolic AI rule engine that audits trilingual completion before saving."""
    alerts = []
    # Rule 1: Structural domain alignment check
    if data['sub_domain'].lower() == 'aviation' and data['domain'].lower() != 'business law':
        alerts.append("⚠️ AI Note: 'Aviation' sub-domain usually belongs under the 'Business Law' domain.")
    # Rule 2: Complete legal reference validation
    if not data['article'] or not data['source_law']:
        alerts.append("❌ AI Error: Missing 'Article' number or 'Source Law' citation.")
    # Rule 3: Trilingual Term Completion Check
    if not data['term_rw'] or not data['term_en'] or not data['term_fr']:
        alerts.append("🌐 AI Warning: Ensure all three languages for the LEGAL TERM are filled.")
    # Rule 4: Trilingual Definition Completion Check
    if not data['def_rw'] or not data['def_en'] or not data['def_fr']:
        alerts.append("📝 AI Warning: Ensure all three languages for the LEGAL DEFINITION are filled.")

    # New Rule 5: Year format and range check
    try:
        year_val = int(data['year'])
        if not (1900 <= year_val <= 2099): # Assuming a reasonable range for legal years
            alerts.append(f"❓ AI Suggestion: Year '{data['year']}' seems unusual. Please verify the legislative year (expected range approx. 1900-2099).")
    except ValueError:
        if data['year']: # Only warn if a value was provided but it's not an integer
            alerts.append(f"❌ AI Error: Year '{data['year']}' is not a valid integer. Please enter a numerical year.")
        else: # Also warn if year is empty
            alerts.append("📝 AI Warning: 'Year' field is empty. Please enter the legislative year.")


    # New Rule 6: Source Law pattern suggestion (e.g., Law N° 00/20XX)
    source_law_pattern = re.compile(r'^(Law|Itegeko|Loi)\s+N°\s+\d{2}/\d{4}(\s+of\s+\d{2}/\d{2}/\d{4})?$')
    if data['source_law'] and not source_law_pattern.match(data['source_law']):
        alerts.append("❓ AI Suggestion: 'Source Law Name' format often follows 'Law N° XX/YYYY' or 'Law N° XX/YYYY of DD/MM/YYYY'. Please check for consistency.")

    # New Rule 7: Term capitalization consistency (Warning)
    def check_capitalization(term):
        if not term:
            return False
        # If all uppercase or all lowercase (and not a single letter or number)
        if term.isupper() and len(term) > 1:
            return True # Suggest title case
        if term.islower() and len(term) > 1:
            return True # Suggest title case
        return False

    if check_capitalization(data['term_rw']):
        alerts.append(f"🔡 AI Suggestion: Kinyarwanda term '{data['term_rw']}' might benefit from Title Case capitalization.")
    if check_capitalization(data['term_en']):
        alerts.append(f"🔡 AI Suggestion: English term '{data['term_en']}' might benefit from Title Case capitalization.")
    if check_capitalization(data['term_fr']):
        alerts.append(f"🔡 AI Suggestion: French term '{data['term_fr']}' might benefit from Title Case capitalization.")

    # New Rule 8: Definition sentence capitalization (Warning for first sentence)
    def check_definition_capitalization(definition):
        if not definition:
            return False
        first_sentence_match = re.match(r'^\s*([A-Za-z])', definition)
        if first_sentence_match and first_sentence_match.group(1).islower():
            return True
        return False

    if check_definition_capitalization(data['def_rw']):
        alerts.append("📝 AI Suggestion: Kinyarwanda definition should start with a capital letter.")
    if check_definition_capitalization(data['def_en']):
        alerts.append("📝 AI Suggestion: English definition should start with a capital letter.")
    if check_definition_capitalization(data['def_fr']):
        alerts.append("📝 AI Suggestion: French definition should start with a capital letter.")

    return alerts

class LegalDictApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Rwandan Trilingual Legal Terms Dictionary Editor")
        self.root.geometry("1100x700")
        init_db()
        self.create_layout()
        self.refresh_table()

    def create_layout(self):
        # 1. Entry Form Frame Layout
        form_frame = ttk.LabelFrame(self.root, text=" Data Entry Form (11-Column Trilingual Layout) ")
        form_frame.pack(fill="x", padx=10, pady=5)

        # Meta Fields Configuration Grid
        meta_labels = ["Domain:", "Sub-Domain:", "Source Law Name:", "Article Reference:", "Year:"]
        self.entries = {}

        meta_frame = ttk.Frame(form_frame)
        meta_frame.pack(fill="x", padx=5, pady=5)

        for i, label_text in enumerate(meta_labels):
            ttk.Label(meta_frame, text=label_text).grid(row=0, column=i*2, padx=5, pady=5, sticky="e")
            entry = ttk.Entry(meta_frame, width=15)
            entry.grid(row=0, column=i*2+1, padx=5, pady=5, sticky="w")
            self.entries[label_text] = entry

        # Language Blocks Container (Side-by-Side UI Columns)
        lang_container = ttk.Frame(form_frame)
        lang_container.pack(fill="x", padx=5, pady=5)

        # Kinyarwanda Block
        rw_frame = ttk.LabelFrame(lang_container, text=" Ikinyarwanda ")
        rw_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        ttk.Label(rw_frame, text="Ijambo (Term):").pack(anchor="w", padx=5)
        self.ent_term_rw = ttk.Entry(rw_frame, width=35)
        self.ent_term_rw.pack(fill="x", padx=5, pady=2)
        ttk.Label(rw_frame, text="Igisobanuro (Definition):").pack(anchor="w", padx=5)
        
        # Add scrollbar for Kinyarwanda definition
        rw_def_frame = ttk.Frame(rw_frame)
        rw_def_frame.pack(fill="both", expand=True, padx=5, pady=2)
        self.txt_def_rw = tk.Text(rw_def_frame, height=5, width=35, wrap="word") # Added wrap="word"
        self.txt_def_rw.pack(side="left", fill="both", expand=True)
        rw_scrollbar = ttk.Scrollbar(rw_def_frame, command=self.txt_def_rw.yview)
        rw_scrollbar.pack(side="right", fill="y")
        self.txt_def_rw.config(yscrollcommand=rw_scrollbar.set)


        # English Block
        en_frame = ttk.LabelFrame(lang_container, text=" English ")
        en_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        ttk.Label(en_frame, text="Legal Term:").pack(anchor="w", padx=5)
        self.ent_term_en = ttk.Entry(en_frame, width=35)
        self.ent_term_en.pack(fill="x", padx=5, pady=2)
        ttk.Label(en_frame, text="Legal Definition:").pack(anchor="w", padx=5)

        # Add scrollbar for English definition
        en_def_frame = ttk.Frame(en_frame)
        en_def_frame.pack(fill="both", expand=True, padx=5, pady=2)
        self.txt_def_en = tk.Text(en_def_frame, height=5, width=35, wrap="word") # Added wrap="word"
        self.txt_def_en.pack(side="left", fill="both", expand=True)
        en_scrollbar = ttk.Scrollbar(en_def_frame, command=self.txt_def_en.yview)
        en_scrollbar.pack(side="right", fill="y")
        self.txt_def_en.config(yscrollcommand=en_scrollbar.set)

        # French Block
        fr_frame = ttk.LabelFrame(lang_container, text=" Français ")
        fr_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        ttk.Label(fr_frame, text="Terme Juridique:").pack(anchor="w", padx=5)
        self.ent_term_fr = ttk.Entry(fr_frame, width=35)
        self.ent_term_fr.pack(fill="x", padx=5, pady=2)
        ttk.Label(fr_frame, text="Définition Juridique:").pack(anchor="w", padx=5)

        # Add scrollbar for French definition
        fr_def_frame = ttk.Frame(fr_frame)
        fr_def_frame.pack(fill="both", expand=True, padx=5, pady=2)
        self.txt_def_fr = tk.Text(fr_def_frame, height=5, width=35, wrap="word") # Added wrap="word"
        self.txt_def_fr.pack(side="left", fill="both", expand=True)
        fr_scrollbar = ttk.Scrollbar(fr_def_frame, command=self.txt_def_fr.yview)
        fr_scrollbar.pack(side="right", fill="y")
        self.txt_def_fr.config(yscrollcommand=fr_scrollbar.set)

        # 2. Control Actions Frame
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(btn_frame, text="Add Row (Run AI Check)", command=self.add_entry).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Delete Selected Row", command=self.delete_entry).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Export CSV Table", command=self.export_csv).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Export Unfolded JSON Array", command=self.export_json).pack(side="right", padx=5)

        # 3. High-Performance Visual Data Tree View Layout
        self.tree = ttk.Treeview(self.root, columns=("ID", "Term RW", "Term EN", "Term FR", "Domain", "Sub-Domain", "Source Law", "Article", "Year"), show="headings")

        widths = {"ID": 35, "Term RW": 120, "Term EN": 120, "Term FR": 120, "Domain": 100, "Sub-Domain": 100, "Source Law": 140, "Article": 70, "Year": 50}
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=widths[col], anchor="w")

        self.tree.pack(fill="both", expand=True, padx=10, pady=5)

    def refresh_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id, term_kinyarwanda, term_english, term_french, domain, sub_domain, source_law, article, year FROM dictionary")
        for row in cursor.fetchall():
            self.tree.insert("", "end", values=row)
        conn.close()

    def add_entry(self):
        data = {
            'term_rw': self.ent_term_rw.get().strip(),
            'term_en': self.ent_term_en.get().strip(),
            'term_fr': self.ent_term_fr.get().strip(),
            'def_rw': self.txt_def_rw.get("1.0", "end-1c").strip(),
            'def_en': self.txt_def_en.get("1.0", "end-1c").strip(),
            'def_fr': self.txt_def_fr.get("1.0", "end-1c").strip(),
            'domain': self.entries["Domain:"].get().strip(),
            'sub_domain': self.entries["Sub-Domain:"].get().strip(),
            'source_law': self.entries["Source Law Name:"].get().strip(),
            'article': self.entries["Article Reference:"].get().strip(),
            'year': self.entries["Year:"].get().strip()
        }

        ai_alerts = run_symbolic_ai(data)
        if ai_alerts:
            messagebox.showwarning("Symbolic AI Analysis", "\n".join(ai_alerts))

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO dictionary (
                term_kinyarwanda, term_english, term_french,
                definition_kinyarwanda, definition_english, definition_french,
                domain, sub_domain, source_law, article, year
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (data['term_rw'], data['term_en'], data['term_fr'],
              data['def_rw'], data['def_en'], data['def_fr'],
              data['domain'], data['sub_domain'], data['source_law'], data['article'], data['year']))
        conn.commit()
        conn.close()

        self.refresh_table()

        # Reset text and inputs visually
        self.ent_term_rw.delete(0, "end")
        self.ent_term_en.delete(0, "end")
        self.ent_term_fr.delete(0, "end")
        self.txt_def_rw.delete("1.0", "end")
        self.txt_def_en.delete("1.0", "end")
        self.txt_def_fr.delete("1.0", "end")
        for entry in self.entries.values(): entry.delete(0, "end")
        # Set focus to the first entry field for faster data entry
        self.entries["Domain:"].focus_set()


    def delete_entry(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Selection Error", "Please click a row in the table first to delete it.")
            return
        row_values = self.tree.item(selected_item)['values']
        row_id = row_values[0]
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to remove this trilingual term record?"):
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM dictionary WHERE id = ?", (row_id,))
            conn.commit()
            conn.close()
            self.refresh_table()

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not path: return
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT term_kinyarwanda, term_english, term_french,
                   definition_kinyarwanda, definition_english, definition_french,
                   domain, sub_domain, source_law, article, year
            FROM dictionary
        """)
        headers = [description[0] for description in cursor.description]
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(cursor.fetchall())
        conn.close()
        messagebox.showinfo("Export Complete", "Data exported to CSV successfully!")

    def export_json(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if not path: return
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT term_kinyarwanda, term_english, term_french,
                   definition_kinyarwanda, definition_english, definition_french,
                   domain, sub_domain, source_law, article, year
            FROM dictionary
        """)
        headers = [description[0] for description in cursor.description]
        data = []
        for row in cursor.fetchall():
            data.append(dict(zip(headers, row)))
        conn.close()
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        messagebox.showinfo("Export Complete", "Data exported to JSON successfully!")


if __name__ == "__main__":
    root = tk.Tk()
    app = LegalDictApp(root)
    root.mainloop()
