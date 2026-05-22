import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import json
import csv
import os
import sys
import re

def get_db_path():
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_dir, "rwandan_legal_dictionary.db")

DB_FILE = get_db_path()

# SCHEMA DEFINITION: Easily add or remove columns here
SCHEMA = [
    ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
    ("term_kin", "TEXT"), ("term_en", "TEXT"), ("term_fr", "TEXT"),
    ("def_kin", "TEXT"), ("def_en", "TEXT"), ("def_fr", "TEXT"),
    ("domain", "TEXT"), ("sub_domain", "TEXT"),
    ("law_kin", "TEXT"), ("law_en", "TEXT"), ("law_fr", "TEXT"),
    ("gazette_ref", "TEXT"), ("article", "TEXT"), ("year", "INTEGER")
]

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cols = ", ".join([f"{name} {dtype}" for name, dtype in SCHEMA])
    cursor.execute(f"CREATE TABLE IF NOT EXISTS dictionary ({cols})")
    conn.commit()
    conn.close()

def run_symbolic_ai(data):
    alerts = []
    # Dynamic year check
    if data.get('year'):
        try:
            y = int(data['year'])
            if not (1962 <= y <= 2100): alerts.append("⚠️ Year is outside standard Rwandan post-independence range.")
        except: alerts.append("❌ Year must be a number.")
    
    # Check for empty language pairs
    for lang in ['kin', 'en', 'fr']:
        if not data.get(f'term_{lang}') or not data.get(f'def_{lang}'):
            alerts.append(f"🌐 Missing entries for {lang.upper()} language track.")
    
    # Gazette format validation
    if data.get('gazette_ref') and not re.search(r'n°\s*\d+', data['gazette_ref'].lower()):
        alerts.append("📝 Gazette reference should include the official Number (n°).")

    return alerts

class LegalDictApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Rwandan Legal Editor - Expert Edition")
        self.root.geometry("1200x850")
        init_db()
        
        # Main Scrollable Container for flexibility
        self.main_canvas = tk.Canvas(self.root)
        self.scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.main_canvas.yview)
        self.scrollable_frame = ttk.Frame(self.main_canvas)

        self.scrollable_frame.bind("<Configure>", lambda e: self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all")))
        self.main_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.main_canvas.configure(yscrollcommand=self.scrollbar.set)

        self.main_canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.create_layout()
        self.refresh_table()

    def create_layout(self):
        # Metadata Section
        meta_frame = ttk.LabelFrame(self.scrollable_frame, text=" Document Metadata & Source ")
        meta_frame.pack(fill="x", padx=10, pady=5)
        
        self.meta_vars = {}
        fields = [("Domain", "domain"), ("Sub-Domain", "sub_domain"), ("Gazette Ref", "gazette_ref"), 
                  ("Article", "article"), ("Year", "year")]
        
        for i, (label, key) in enumerate(fields):
            ttk.Label(meta_frame, text=label).grid(row=0, column=i*2, padx=5, pady=5)
            var = tk.StringVar()
            ttk.Entry(meta_frame, textvariable=var, width=15).grid(row=0, column=i*2+1, padx=5, pady=5)
            self.meta_vars[key] = var

        # Trilingual Source Law Name
        law_frame = ttk.LabelFrame(self.scrollable_frame, text=" Source Law Name (Trilingual) ")
        law_frame.pack(fill="x", padx=10, pady=5)
        self.law_vars = {}
        for i, l in enumerate([("Kinyarwanda", "kin"), ("English", "en"), ("French", "fr")]):
            ttk.Label(law_frame, text=l[0]).grid(row=0, column=i*2, padx=5, pady=5)
            v = tk.StringVar()
            ttk.Entry(law_frame, textvariable=v, width=30).grid(row=0, column=i*2+1, padx=5, pady=5)
            self.law_vars[l[1]] = v

        # Trilingual Terms & Definitions
        content_frame = ttk.Frame(self.scrollable_frame)
        content_frame.pack(fill="x", padx=10, pady=5)
        
        self.term_vars = {}
        self.def_widgets = {}

        for i, (name, tag) in enumerate([("Kinyarwanda", "kin"), ("English", "en"), ("French", "fr")]):
            f = ttk.LabelFrame(content_frame, text=name)
            f.grid(row=0, column=i, sticky="nsew", padx=5)
            ttk.Label(f, text="Term").pack(anchor="w")
            v = tk.StringVar()
            ttk.Entry(f, textvariable=v).pack(fill="x")
            self.term_vars[tag] = v
            ttk.Label(f, text="Definition").pack(anchor="w")
            txt = tk.Text(f, height=6, width=30, wrap="word")
            txt.pack(fill="both", expand=True)
            self.def_widgets[tag] = txt

        # Buttons
        btn_frame = ttk.Frame(self.scrollable_frame)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="SAVE & AUDIT", command=self.save_data).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="EXPORT JSON", command=self.export_json).pack(side="left", padx=10)

        # Data View
        self.tree = ttk.Treeview(self.scrollable_frame, columns=[c[0] for c in SCHEMA], show="headings", height=10)
        for c in SCHEMA:
            self.tree.heading(c[0], text=c[0].replace("_", " ").title())
            self.tree.column(c[0], width=100)
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

    def save_data(self):
        data = {**{k: v.get() for k, v in self.meta_vars.items()},
                **{f'law_{k}': v.get() for k, v in self.law_vars.items()},
                **{f'term_{k}': v.get() for k, v in self.term_vars.items()},
                **{f'def_{k}': v.get("1.0", "end-1c") for k, v in self.def_widgets.items()}}
        
        alerts = run_symbolic_ai(data)
        if alerts and not messagebox.askyesno("AI Audit", "\n".join(alerts) + "\n\nSave anyway?"): return

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        keys = [c[0] for c in SCHEMA if c[0] != 'id']
        placeholders = ", ".join(["?"] * len(keys))
        cursor.execute(f"INSERT INTO dictionary ({', '.join(keys)}) VALUES ({placeholders})", 
                       [data.get(k) for k in keys])
        conn.commit()
        conn.close()
        self.refresh_table()

    def refresh_table(self):
        self.tree.delete(*self.tree.get_children())
        conn = sqlite3.connect(DB_FILE)
        rows = conn.execute("SELECT * FROM dictionary").fetchall()
        for r in rows: self.tree.insert("", "end", values=r)
        conn.close()

    def export_json(self):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM dictionary")
        rows = [dict(zip([c[0] for c in SCHEMA], row)) for row in cursor.fetchall()]
        with open("export.json", "w", encoding="utf-8") as f: json.dump(rows, f, indent=2)
        messagebox.showinfo("Success", "Data exported to export.json")

if __name__ == "__main__":
    root = tk.Tk()
    app = LegalDictApp(root)
    root.mainloop()
