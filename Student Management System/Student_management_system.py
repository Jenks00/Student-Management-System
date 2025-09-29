import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sqlite3
import csv
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

DB_FILE = "app.db"

# ------------------------ DB Bootstrap ------------------------
def db_connect():
    return sqlite3.connect(DB_FILE)

def init_db():
    conn = db_connect()
    c = conn.cursor()

    # Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin','staff','student'))
        )
    """)

    # Students table (username is UNIQUE so one login links to at most one record)
    c.execute("""
        CREATE TABLE IF NOT EXISTS students (
            roll_no TEXT PRIMARY KEY,
            name TEXT,
            email TEXT,
            gender TEXT,
            contact TEXT,
            dob TEXT,
            address TEXT,
            username TEXT UNIQUE
        )
    """)

    # Seed admin if missing
    c.execute("SELECT 1 FROM users WHERE username='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users (username, password, role) VALUES (?,?,?)",
                  ("admin", "admin123", "admin"))
    conn.commit()
    conn.close()


# ------------------------ Login Window ------------------------
class LoginWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Student Management - Login")
        self.root.geometry("1200x600")
        self.root.config(bg="#ecf0f1")

        self.username = tk.StringVar()
        self.password = tk.StringVar()
        self.show_password = tk.BooleanVar(value=False)

        login_frame = tk.Frame(root, bg="white", bd=5, relief=tk.RIDGE)
        login_frame.place(relx=0.5, rely=0.5, anchor="center", width=420, height=380)

        tk.Label(login_frame, text="Login", font=("Helvetica", 22, "bold"),
                 bg="white", fg="#2c3e50").pack(pady=18)

        tk.Label(login_frame, text="Username", font=("Arial", 12),
                 bg="white", anchor="w").pack(padx=40, anchor="w")
        tk.Entry(login_frame, textvariable=self.username,
                 font=("Arial", 12), width=30).pack(pady=6)

        tk.Label(login_frame, text="Password", font=("Arial", 12),
                 bg="white", anchor="w").pack(padx=40, anchor="w")
        self.password_entry = tk.Entry(login_frame, textvariable=self.password,
                                       font=("Arial", 12), width=30, show="*")
        self.password_entry.pack(pady=6)

        tk.Checkbutton(login_frame, text="Show Password", variable=self.show_password,
                       command=self.toggle_password, bg="white").pack(pady=6)

        row = tk.Frame(login_frame, bg="white")
        row.pack(pady=14)
        tk.Button(row, text="Login", command=self.login, font=("Arial", 12), width=15,
                  bg="#3498db", fg="white").grid(row=0, column=0, padx=6)

        tk.Label(login_frame, text="Default admin: admin / admin123",
                 font=("Arial", 9), bg="white", fg="gray").pack(pady=6)

    def toggle_password(self):
        self.password_entry.config(show="" if self.show_password.get() else "*")

    def login(self):
        user = self.username.get().strip()
        pwd = self.password.get()

        if not user or not pwd:
            messagebox.showerror("Error", "Enter username and password.")
            return

        conn = db_connect()
        c = conn.cursor()
        c.execute("SELECT role FROM users WHERE username=? AND password=?", (user, pwd))
        row = c.fetchone()
        conn.close()

        if row:
            role = row[0]
            self.root.destroy()
            main_root = tk.Tk()
            StudentManagementSystem(main_root, user_role=role, username=user)
            main_root.mainloop()
        else:
            messagebox.showerror("Access Denied", "Invalid username or password!")


# ------------------------ Main App ------------------------
class StudentManagementSystem:
    def __init__(self, root, user_role, username):
        self.root = root
        self.role = user_role.lower()
        self.username = username
        self.dark_mode = False

        self.root.title(f"{self.role.capitalize()} Dashboard - Student Management System")
        self.root.geometry("1600x600")
        self.root.config(bg="white")

        # Title bar
        self.title_bar = tk.Label(self.root, text="Student Management System",
                                  font=("Arial", 20, "bold"), bg="#34495e", fg="white")
        self.title_bar.pack(side=tk.TOP, fill=tk.X)

        # Welcome + theme toggle
        top_row = tk.Frame(self.root, bg="white")
        top_row.pack(fill="x")
        tk.Label(top_row, text=f"Welcome, {self.username} 👋 (Role: {self.role})",
                 font=("Helvetica", 13, "bold"),
                 bg="white", fg="#2c3e50").pack(side="left", padx=10, pady=8)
        self.theme_btn = tk.Button(top_row, text="🌙 Dark Mode", font=("Arial", 10),
                                   command=self.toggle_theme, bg="#34495e", fg="white")
        self.theme_btn.pack(side="right", padx=10)

        # Left: Table (list)
        self.table_frame = tk.Frame(self.root, bd=4, relief=tk.RIDGE, bg="white")
        self.table_frame.place(x=20, y=105, width=550, height=470)

        # Right: Manage student data panel
        self.manage_frame = tk.Frame(self.root, bd=4, relief=tk.RIDGE, bg="white")
        self.manage_frame.place(x=590, y=75, width=670, height=500)

        # ---- Manage panel contents ----
        tk.Label(self.manage_frame, text="Manage Students", bg="white",
                 fg="black", font=("Arial", 15, "bold")).grid(row=0, column=0, columnspan=2, pady=10)

        # Vars
        self.roll_no_var = tk.StringVar()
        self.name_var = tk.StringVar()
        self.email_var = tk.StringVar()
        self.gender_var = tk.StringVar(value="Male")
        self.contact_var = tk.StringVar()
        self.dob_var = tk.StringVar()
        self.username_var = tk.StringVar()  # <-- used to link a student record to a login
        self.search_by = tk.StringVar(value="roll_no")
        self.search_txt = tk.StringVar()

        # Fields
        row_i = 1
        def add_row(label, widget):
            nonlocal row_i
            tk.Label(self.manage_frame, text=label, bg="white", font=("Arial", 11)).grid(row=row_i, column=0, padx=8, pady=6, sticky="w")
            widget.grid(row=row_i, column=1, padx=8, pady=6, sticky="w")
            row_i += 1

        add_row("Roll No", tk.Entry(self.manage_frame, textvariable=self.roll_no_var, width=34))
        add_row("Name", tk.Entry(self.manage_frame, textvariable=self.name_var, width=34))
        add_row("Email", tk.Entry(self.manage_frame, textvariable=self.email_var, width=34))

        gender_combo = ttk.Combobox(self.manage_frame, textvariable=self.gender_var,
                                    values=("Male", "Female", "Other"), state="readonly", width=31)
        gender_combo.current(0)
        add_row("Gender", gender_combo)

        add_row("Contact", tk.Entry(self.manage_frame, textvariable=self.contact_var, width=34))
        add_row("D.O.B", tk.Entry(self.manage_frame, textvariable=self.dob_var, width=34))

        # Username link (admin/staff can set; students fixed to their own)
        uname_entry = tk.Entry(self.manage_frame, textvariable=self.username_var, width=34)
        add_row("Username (link)", uname_entry)

        tk.Label(self.manage_frame, text="Address", bg="white", font=("Arial", 11)).grid(row=row_i, column=0, padx=8, pady=6, sticky="nw")
        self.address_txt = tk.Text(self.manage_frame, width=33, height=4)
        self.address_txt.grid(row=row_i, column=1, padx=8, pady=6, sticky="w")
        row_i += 1

        # If student, lock username field to own login and disable editing
        if self.role == "student":
            self.username_var.set(self.username)
            uname_entry.config(state="disabled")

        # Buttons row inside manage panel
        btn_frame = tk.Frame(self.manage_frame, bg="white")
        btn_frame.grid(row=row_i, column=0, columnspan=2, pady=10)
        if self.role in ("admin", "staff"):
            self.btn_add = tk.Button(btn_frame, text="Add", width=10, command=self.add_student,
                                     bg="#27ae60", fg="white", font=("Arial", 11))
            self.btn_add.grid(row=0, column=0, padx=6)

            self.btn_update = tk.Button(btn_frame, text="Update", width=10, command=self.update_student,
                                        bg="#2980b9", fg="white", font=("Arial", 11))
            self.btn_update.grid(row=0, column=1, padx=6)

            self.btn_delete = tk.Button(btn_frame, text="Delete", width=10, command=self.delete_student,
                                        bg="#c0392b", fg="white", font=("Arial", 11))
            self.btn_delete.grid(row=0, column=2, padx=6)

        self.btn_csv = tk.Button(btn_frame, text="Export CSV", width=10, command=self.export_csv,
                                 bg="#f39c12", fg="white", font=("Arial", 11))
        self.btn_csv.grid(row=0, column=3, padx=6)

        self.btn_pdf = tk.Button(btn_frame, text="Export PDF", width=10, command=self.export_pdf,
                                 bg="#d35400", fg="white", font=("Arial", 11))
        self.btn_pdf.grid(row=0, column=4, padx=6)

        # Admin-only: Add User (popup)
        if self.role == "admin":
            self.btn_add_user = tk.Button(btn_frame, text="Add User", width=10,
                                          command=self.open_add_user_popup, bg="#6c5ce7", fg="white",
                                          font=("Arial", 11))
            self.btn_add_user.grid(row=0, column=5, padx=6)

        # Search area above table (left side)
        search_frame = tk.Frame(self.root, bd=4, relief=tk.RIDGE, bg="white")
        search_frame.place(x=20, y=75, width=550, height=36)

        ttk.Combobox(search_frame, textvariable=self.search_by,
                     values=("roll_no", "name", "contact", "username"),
                     state="readonly", width=14).grid(row=0, column=0, padx=6, pady=3)

        tk.Entry(search_frame, textvariable=self.search_txt, width=30).grid(row=0, column=1, padx=6)
        tk.Button(search_frame, text="Search", command=self.search_student, width=10,
                  bg="#8e44ad", fg="white").grid(row=0, column=2, padx=4)
        tk.Button(search_frame, text="Reset", command=self.fetch_data, width=10,
                  bg="#95a5a6", fg="black").grid(row=0, column=3, padx=4)

        # Table
        self.student_table = ttk.Treeview(self.table_frame,
                                          columns=("roll", "name", "email", "gender", "contact", "dob", "address", "username"),
                                          show="headings")
        for col, w in zip(("roll", "name", "email", "gender", "contact", "dob", "address", "username"),
                          (80, 140, 180, 100, 120, 110, 220, 130)):
            self.student_table.heading(col, text=col.title())
            self.student_table.column(col, width=w, anchor="w")
        self.student_table.pack(fill=tk.BOTH, expand=1)
        self.student_table.bind("<ButtonRelease-1>", self.get_cursor)

        # Role restrictions (student = read-only + own records only)
        if self.role == "student":
            # Only disable if buttons exist (they don't for student)
            for attr in ("btn_add", "btn_update", "btn_delete", "btn_add_user"):
                if hasattr(self, attr):
                    getattr(self, attr).config(state="disabled")

        # Staff can manage students but not add users
        if self.role == "staff" and hasattr(self, "btn_add_user"):
            self.btn_add_user.config(state="disabled")

        self.fetch_data()

    # ------------------------ CRUD ------------------------
    def add_student(self):
        if not self.roll_no_var.get() or not self.name_var.get():
            messagebox.showerror("Error", "Roll No and Name are required.")
            return

        # Map empty username to None so SQLite stores NULL (UNIQUE allows multiple NULLs)
        link_username = self.username_var.get().strip()
        link_username = link_username if link_username else None

        address = self.address_txt.get("1.0", tk.END).strip()
        conn = db_connect()
        c = conn.cursor()
        try:
            c.execute("""
                INSERT INTO students (roll_no, name, email, gender, contact, dob, address, username)
                VALUES (?,?,?,?,?,?,?,?)
            """, (
                self.roll_no_var.get().strip(),
                self.name_var.get().strip(),
                self.email_var.get().strip(),
                self.gender_var.get().strip(),
                self.contact_var.get().strip(),
                self.dob_var.get().strip(),
                address,
                link_username
            ))
            conn.commit()
            messagebox.showinfo("Success", "Student added successfully.")
            self.clear_fields()
            self.fetch_data()
        except sqlite3.IntegrityError as e:
            messagebox.showerror("Error", f"Duplicate Roll No / Username conflict.\n{e}")
        finally:
            conn.close()

    def update_student(self):
        if not self.roll_no_var.get():
            messagebox.showerror("Error", "Select a student from the list.")
            return

        # Allow updating the link (admin/staff); students can't edit (field is disabled)
        link_username = self.username_var.get().strip()
        link_username = link_username if link_username else None

        address = self.address_txt.get("1.0", tk.END).strip()
        conn = db_connect()
        c = conn.cursor()
        try:
            c.execute("""
                UPDATE students SET
                    name=?, email=?, gender=?, contact=?, dob=?, address=?, username=?
                WHERE roll_no=?
            """, (self.name_var.get().strip(), self.email_var.get().strip(), self.gender_var.get().strip(),
                  self.contact_var.get().strip(), self.dob_var.get().strip(), address, link_username,
                  self.roll_no_var.get().strip()))
            conn.commit()
            messagebox.showinfo("Updated", "Student record updated.")
            self.fetch_data()
            self.clear_fields()
        except sqlite3.IntegrityError as e:
            messagebox.showerror("Error", f"Username is already linked to another student.\n{e}")
        finally:
            conn.close()

    def delete_student(self):
        if not self.roll_no_var.get():
            messagebox.showerror("Error", "Select a student from the list.")
            return
        if not messagebox.askyesno("Confirm", "Delete this student?"):
            return

        conn = db_connect()
        c = conn.cursor()
        c.execute("DELETE FROM students WHERE roll_no=?", (self.roll_no_var.get().strip(),))
        conn.commit()
        conn.close()
        messagebox.showinfo("Deleted", "Student record deleted.")
        self.fetch_data()
        self.clear_fields()

    def get_cursor(self, _event):
        sel = self.student_table.focus()
        vals = self.student_table.item(sel, "values")
        if not vals:
            return
        self.roll_no_var.set(vals[0])
        self.name_var.set(vals[1])
        self.email_var.set(vals[2])
        self.gender_var.set(vals[3])
        self.contact_var.set(vals[4])
        self.dob_var.set(vals[5])
        self.address_txt.delete("1.0", tk.END)
        self.address_txt.insert(tk.END, vals[6])
        self.username_var.set(vals[7] if len(vals) > 7 else "")

    def clear_fields(self):
        self.roll_no_var.set("")
        self.name_var.set("")
        self.email_var.set("")
        self.gender_var.set("Male")
        self.contact_var.set("")
        self.dob_var.set("")
        self.username_var.set("" if self.role != "student" else self.username)
        self.address_txt.delete("1.0", tk.END)

    # ------------------------ Search & Load ------------------------
    def fetch_data(self):
        conn = db_connect()
        c = conn.cursor()
        if self.role == "student":
            # Only show the logged-in student's record
            c.execute("SELECT roll_no, name, email, gender, contact, dob, address, username "
                      "FROM students WHERE username=? ORDER BY name", (self.username,))
        else:
            c.execute("SELECT roll_no, name, email, gender, contact, dob, address, username "
                      "FROM students ORDER BY name")
        rows = c.fetchall()
        conn.close()

        self.student_table.delete(*self.student_table.get_children())
        for r in rows:
            self.student_table.insert("", tk.END, values=r)

    def search_student(self):
        field = self.search_by.get()
        val = self.search_txt.get().strip()
        if not val:
            messagebox.showerror("Error", "Enter a value to search.")
            return

        valid = {"roll_no","name","contact","username"}
        if field not in valid:
            field = "name"

        conn = db_connect()
        c = conn.cursor()
        if self.role == "student":
            c.execute(f"SELECT roll_no, name, email, gender, contact, dob, address, username "
                      f"FROM students WHERE username=? AND {field} LIKE ?",
                      (self.username, f"%{val}%"))
        else:
            c.execute(f"SELECT roll_no, name, email, gender, contact, dob, address, username "
                      f"FROM students WHERE {field} LIKE ?", (f"%{val}%",))
        rows = c.fetchall()
        conn.close()

        self.student_table.delete(*self.student_table.get_children())
        for r in rows:
            self.student_table.insert("", tk.END, values=r)

    # ------------------------ Export ------------------------
    def export_csv(self):
        rows = self.student_table.get_children()
        if not rows:
            messagebox.showwarning("No Data", "No data to export.")
            return

        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                            filetypes=[("CSV files", "*.csv")],
                                            title="Save CSV")
        if not path:
            return

        with open(path, "w", newline="", encoding="utf-8") as f:
            wr = csv.writer(f)
            wr.writerow(["Roll No", "Name", "Email", "Gender", "Contact", "D.O.B", "Address", "Username"])
            for r in rows:
                wr.writerow(self.student_table.item(r)["values"])
        messagebox.showinfo("Exported", f"CSV saved to:\n{path}")

    def export_pdf(self):
        rows = self.student_table.get_children()
        if not rows:
            messagebox.showwarning("No Data", "No data to export.")
            return

        path = filedialog.asksaveasfilename(defaultextension=".pdf",
                                            filetypes=[("PDF files", "*.pdf")],
                                            title="Save PDF")
        if not path:
            return

        pdf = canvas.Canvas(path, pagesize=A4)
        w, h = A4
        y = h - 50

        pdf.setTitle("Student Records")
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawCentredString(w / 2, y, "Student Records")
        y -= 24
        pdf.setFont("Helvetica", 9)

        headers = ["Roll No", "Name", "Email", "Gender", "Contact", "D.O.B", "Address", "Username"]
        x = [20, 80, 150, 270, 320, 380, 440, 515]

        for i, hdr in enumerate(headers):
            pdf.drawString(x[i], y, hdr)
        y -= 16

        for r in rows:
            data = list(map(str, self.student_table.item(r)["values"]))
            for i, val in enumerate(data):
                pdf.drawString(x[i], y, val[:35])
            y -= 14
            if y < 40:
                pdf.showPage()
                y = h - 50
                pdf.setFont("Helvetica-Bold", 14)
                pdf.drawCentredString(w / 2, y, "Student Records (cont.)")
                y -= 24
                pdf.setFont("Helvetica", 9)
                for i, hdr in enumerate(headers):
                    pdf.drawString(x[i], y, hdr)
                y -= 16

        pdf.save()
        messagebox.showinfo("Exported", f"PDF saved to:\n{path}")

    # ------------------------ Admin: Add User (Popup) ------------------------
    def open_add_user_popup(self):
        win = tk.Toplevel(self.root)
        win.title("Add New User")
        win.geometry("360x260")
        win.resizable(False, False)
        win.config(bg="white")
        win.transient(self.root)
        win.grab_set()

        tk.Label(win, text="Add New User", font=("Arial", 14, "bold"),
                 bg="white").pack(pady=10)

        frm = tk.Frame(win, bg="white")
        frm.pack(pady=6)

        tk.Label(frm, text="Username:", bg="white").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        uname = tk.Entry(frm, width=24)
        uname.grid(row=0, column=1, padx=8)

        tk.Label(frm, text="Password:", bg="white").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        pwd = tk.Entry(frm, width=24, show="*")
        pwd.grid(row=1, column=1, padx=8)

        tk.Label(frm, text="Role:", bg="white").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        role_var = tk.StringVar(value="student")
        ttk.Combobox(frm, textvariable=role_var, values=["admin", "staff", "student"],
                     state="readonly", width=21).grid(row=2, column=1, padx=8)

        def save_user():
            u = uname.get().strip()
            p = pwd.get()
            r = role_var.get()
            if not u or not p:
                messagebox.showerror("Error", "All fields are required.", parent=win)
                return

            conn = db_connect()
            c = conn.cursor()
            try:
                c.execute("INSERT INTO users (username, password, role) VALUES (?,?,?)", (u, p, r))
                conn.commit()
                messagebox.showinfo("Success", f"User '{u}' added as {r}.", parent=win)
                win.destroy()
            except sqlite3.IntegrityError:
                messagebox.showerror("Error", "Username already exists.", parent=win)
            finally:
                conn.close()

        tk.Button(win, text="Add User", command=save_user, width=12,
                  bg="#2ecc71", fg="white").pack(pady=12)

        if self.dark_mode:
            self._apply_popup_theme(win)

    # ------------------------ Theme ------------------------
    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        if self.dark_mode:
            bg = "#1f2937"   # dark slate
            fg = "white"
            card = "#111827"
            btn = "#374151"
            self.theme_btn.config(text="☀️ Light Mode")
        else:
            bg = "white"
            fg = "black"
            card = "white"
            btn = "#f5f5f5"
            self.theme_btn.config(text="🌙 Dark Mode")

        # Root + title
        self.root.config(bg=bg)
        self.title_bar.config(bg="#0f172a" if self.dark_mode else "#34495e", fg="white")

        # Walk and recolor
        def paint(widget):
            try:
                if isinstance(widget, (tk.Frame, tk.LabelFrame)):
                    widget.config(bg=card)
                elif isinstance(widget, tk.Label):
                    widget.config(bg=card, fg=fg)
                elif isinstance(widget, tk.Button):
                    widget.config(bg=btn, fg=fg, activebackground=btn, activeforeground=fg)
                elif isinstance(widget, (tk.Entry, tk.Text)):
                    widget.config(bg="#111827" if self.dark_mode else "white",
                                  fg=fg, insertbackground=fg)
            except Exception:
                pass
            for ch in widget.winfo_children():
                paint(ch)

        paint(self.root)

        # ttk styles (Treeview/Combobox)
        style = ttk.Style(self.root)
        if self.dark_mode:
            style.theme_use("clam")
            style.configure("Treeview",
                            background="#0b1220", fieldbackground="#0b1220",
                            foreground="white")
            style.configure("TCombobox",
                            fieldbackground="#111827",
                            foreground="white")
        else:
            style.theme_use("default")
            style.configure("Treeview",
                            background="white", fieldbackground="white",
                            foreground="black")
            style.configure("TCombobox",
                            fieldbackground="white",
                            foreground="black")

    def _apply_popup_theme(self, win):
        if not self.dark_mode:
            return
        def paint(widget):
            try:
                if isinstance(widget, (tk.Frame, tk.LabelFrame, tk.Toplevel)):
                    widget.config(bg="#111827")
                elif isinstance(widget, tk.Label):
                    widget.config(bg="#111827", fg="white")
                elif isinstance(widget, tk.Entry):
                    widget.config(bg="#0b1220", fg="white", insertbackground="white")
                elif isinstance(widget, tk.Button):
                    widget.config(bg="#374151", fg="white", activebackground="#374151", activeforeground="white")
            except Exception:
                pass
            for ch in widget.winfo_children():
                paint(ch)
        paint(win)


if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    LoginWindow(root)
    root.mainloop()
