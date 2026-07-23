"""
Sicherer, lokaler Passwort-Manager mit grafischer Oberfläche.

Start:
    python main.py

Alle Daten werden ausschließlich lokal unter
~/.python_password_manager/ gespeichert, verschlüsselt mit einem aus
deinem Master-Passwort abgeleiteten Schlüssel. Das Master-Passwort
selbst wird nirgends gespeichert.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk

try:
    import pyperclip
    CLIPBOARD_AVAILABLE = True
except ImportError:
    CLIPBOARD_AVAILABLE = False

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    AUTOTYPE_AVAILABLE = True
except Exception:
    # Kann u.a. fehlschlagen, wenn kein Display / kein X11 vorhanden ist
    # (z. B. Wayland ohne XWayland) oder wenn pyautogui nicht installiert ist.
    AUTOTYPE_AVAILABLE = False

import crypto_utils
import storage

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

CLIPBOARD_CLEAR_SECONDS = 20
AUTO_LOCK_MS = 5 * 60 * 1000  # 5 Minuten Inaktivität -> automatisch sperren


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Passwort-Manager")
        self.geometry("980x600")
        self.minsize(820, 520)

        self.key = None
        self.entries = []
        self._autolock_job = None
        self._clipboard_job = None

        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True)

        self.bind_all("<Key>", self._reset_autolock_timer)
        self.bind_all("<Button>", self._reset_autolock_timer)

        self.show_start_screen()

    # ---------- Bildschirm-Wechsel ----------

    def _clear_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def show_start_screen(self):
        self._clear_container()
        if storage.vault_exists():
            self.show_login_screen()
        else:
            self.show_setup_screen()

    def show_setup_screen(self):
        self._clear_container()
        frame = ctk.CTkFrame(self.container)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            frame, text="🔐 Passwort-Manager einrichten",
            font=ctk.CTkFont(size=22, weight="bold")
        ).grid(row=0, column=0, columnspan=2, padx=30, pady=(30, 5))

        ctk.CTkLabel(
            frame,
            text="Lege ein Master-Passwort fest. Es verschlüsselt deinen\n"
                 "gesamten Tresor und wird nirgends gespeichert –\n"
                 "wenn du es vergisst, sind die Daten NICHT wiederherstellbar.",
            justify="center", text_color="gray70"
        ).grid(row=1, column=0, columnspan=2, padx=30, pady=(0, 20))

        pw1 = ctk.CTkEntry(frame, placeholder_text="Master-Passwort", show="•", width=280)
        pw1.grid(row=2, column=0, columnspan=2, padx=30, pady=6)

        pw2 = ctk.CTkEntry(frame, placeholder_text="Master-Passwort bestätigen", show="•", width=280)
        pw2.grid(row=3, column=0, columnspan=2, padx=30, pady=6)

        strength_label = ctk.CTkLabel(frame, text="", text_color="gray70")
        strength_label.grid(row=4, column=0, columnspan=2, pady=(0, 4))

        def on_key(_event=None):
            pw = pw1.get()
            if pw:
                strength_label.configure(text=f"Stärke: {crypto_utils.password_strength_label(pw)}")
            else:
                strength_label.configure(text="")

        pw1.bind("<KeyRelease>", on_key)

        error_label = ctk.CTkLabel(frame, text="", text_color="#ff6666")
        error_label.grid(row=5, column=0, columnspan=2)

        def do_setup():
            p1, p2 = pw1.get(), pw2.get()
            if len(p1) < 8:
                error_label.configure(text="Master-Passwort sollte mindestens 8 Zeichen haben.")
                return
            if p1 != p2:
                error_label.configure(text="Die Passwörter stimmen nicht überein.")
                return
            self.key = storage.create_vault(p1)
            self.entries = []
            self.show_vault_screen()

        ctk.CTkButton(frame, text="Tresor erstellen", command=do_setup, width=280).grid(
            row=6, column=0, columnspan=2, padx=30, pady=(10, 30)
        )
        pw1.focus()
        pw2.bind("<Return>", lambda e: do_setup())

    def show_login_screen(self):
        self._clear_container()
        frame = ctk.CTkFrame(self.container)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            frame, text="🔐 Passwort-Manager",
            font=ctk.CTkFont(size=22, weight="bold")
        ).grid(row=0, column=0, padx=40, pady=(30, 5))

        ctk.CTkLabel(frame, text="Master-Passwort eingeben, um den Tresor zu entsperren.",
                     text_color="gray70").grid(row=1, column=0, padx=40, pady=(0, 20))

        pw_entry = ctk.CTkEntry(frame, placeholder_text="Master-Passwort", show="•", width=280)
        pw_entry.grid(row=2, column=0, padx=40, pady=6)

        error_label = ctk.CTkLabel(frame, text="", text_color="#ff6666")
        error_label.grid(row=3, column=0)

        def do_login(_event=None):
            pw = pw_entry.get()
            if not pw:
                return
            try:
                entries, key = storage.load_entries(pw)
            except storage.WrongPasswordError:
                error_label.configure(text="Falsches Master-Passwort.")
                pw_entry.delete(0, "end")
                return
            self.key = key
            self.entries = entries
            self.show_vault_screen()

        ctk.CTkButton(frame, text="Entsperren", command=do_login, width=280).grid(
            row=4, column=0, padx=40, pady=(10, 30)
        )
        pw_entry.bind("<Return>", do_login)
        pw_entry.focus()

    def show_vault_screen(self):
        self._clear_container()
        self._reset_autolock_timer()

        top_bar = ctk.CTkFrame(self.container, fg_color="transparent")
        top_bar.pack(fill="x", padx=16, pady=(14, 6))

        ctk.CTkLabel(top_bar, text="🔐 Meine Passwörter",
                     font=ctk.CTkFont(size=18, weight="bold")).pack(side="left")

        ctk.CTkButton(top_bar, text="🔒 Sperren", width=90, fg_color="gray30",
                      command=self.lock_vault).pack(side="right", padx=(6, 0))
        ctk.CTkButton(top_bar, text="Master-PW ändern", width=140, fg_color="gray30",
                      command=self.open_change_password_dialog).pack(side="right", padx=(6, 0))
        ctk.CTkButton(top_bar, text="+ Neuer Eintrag", width=130,
                      command=lambda: self.open_entry_dialog(None)).pack(side="right", padx=(6, 0))

        search_bar = ctk.CTkFrame(self.container, fg_color="transparent")
        search_bar.pack(fill="x", padx=16, pady=(0, 8))
        self.search_var = tk.StringVar()
        search_entry = ctk.CTkEntry(search_bar, textvariable=self.search_var,
                                     placeholder_text="🔍 Suche nach Dienst oder Benutzername …")
        search_entry.pack(fill="x")
        self.search_var.trace_add("write", lambda *_: self.refresh_table())

        # --- Tabelle (ttk.Treeview, in dunklem Theme eingefärbt) ---
        table_frame = ctk.CTkFrame(self.container)
        table_frame.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Vault.Treeview",
                         background="#2b2b2b", fieldbackground="#2b2b2b",
                         foreground="white", rowheight=42, borderwidth=0,
                         font=("", 14))
        style.configure("Vault.Treeview.Heading",
                         background="#1f1f1f", foreground="white",
                         relief="flat", font=("", 13, "bold"))
        style.map("Vault.Treeview", background=[("selected", "#1f6aa5")])
        # Kein Rahmen zwischen Kopf und Zellen
        style.layout("Vault.Treeview", [
            ("Vault.Treeview.treearea", {"sticky": "nswe"})
        ])

        columns = ("service", "username", "url", "updated")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings",
                                  style="Vault.Treeview", selectmode="browse")
        self.tree.heading("service", text="Dienst", anchor="center")
        self.tree.heading("username", text="Benutzername", anchor="center")
        self.tree.heading("url", text="URL", anchor="center")
        self.tree.heading("updated", text="Zuletzt geändert", anchor="center")
        self.tree.column("service", width=200, anchor="center")
        self.tree.column("username", width=240, anchor="center")
        self.tree.column("url", width=240, anchor="center")
        self.tree.column("updated", width=170, anchor="center")
        self.tree.pack(fill="both", expand=True, side="left")

        # Abwechselnde Zeilenfarben für bessere Lesbarkeit
        self.tree.tag_configure("even_row", background="#2b2b2b")
        self.tree.tag_configure("odd_row", background="#323232")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(fill="y", side="right")
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.bind("<Double-1>", lambda e: self.open_entry_dialog(self._selected_entry()))

        # --- Aktionsleiste unten ---
        action_bar = ctk.CTkFrame(self.container, fg_color="transparent")
        action_bar.pack(fill="x", padx=16, pady=(0, 14))

        ctk.CTkButton(action_bar, text="⌨️ Auto-Ausfüllen", width=160,
                      fg_color="#2f8f5b", hover_color="#256e46",
                      command=self.start_autotype).pack(side="left", padx=(0, 6))
        ctk.CTkButton(action_bar, text="👁 Passwort anzeigen", width=170,
                      command=self.show_selected_password).pack(side="left", padx=(0, 6))
        ctk.CTkButton(action_bar, text="📋 Benutzername kopieren", width=190,
                      command=lambda: self.copy_field("username")).pack(side="left", padx=6)
        ctk.CTkButton(action_bar, text="📋 Passwort kopieren", width=170,
                      command=lambda: self.copy_field("password")).pack(side="left", padx=6)
        ctk.CTkButton(action_bar, text="✏️ Bearbeiten", width=120,
                      command=lambda: self.open_entry_dialog(self._selected_entry())).pack(side="left", padx=6)
        ctk.CTkButton(action_bar, text="🗑️ Löschen", width=110, fg_color="#a13b3b",
                      hover_color="#7a2c2c",
                      command=self.delete_selected_entry).pack(side="left", padx=6)

        self.status_label = ctk.CTkLabel(action_bar, text="", text_color="gray70")
        self.status_label.pack(side="right")

        self.refresh_table()

    # ---------- Tabellen-Logik ----------

    def refresh_table(self):
        query = self.search_var.get().strip().lower() if hasattr(self, "search_var") else ""
        for row in self.tree.get_children():
            self.tree.delete(row)
        visible_entries = [
            e for e in sorted(self.entries, key=lambda e: e.service.lower())
            if not query or query in e.service.lower() or query in e.username.lower()
        ]
        for i, entry in enumerate(visible_entries):
            updated = entry.updated_at.replace("T", " ")
            tag = "even_row" if i % 2 == 0 else "odd_row"
            self.tree.insert("", "end", iid=entry.id,
                              values=(entry.service, entry.username, entry.url, updated),
                              tags=(tag,))
        count = len(self.entries)
        self.status_label.configure(text=f"{count} Eintrag/Einträge gesamt")

    def _selected_entry(self):
        sel = self.tree.selection()
        if not sel:
            return None
        entry_id = sel[0]
        return next((e for e in self.entries if e.id == entry_id), None)

    def _persist(self):
        storage.save_entries(self.entries, self.key)

    # ---------- Eintrag anlegen / bearbeiten ----------

    def open_entry_dialog(self, entry):
        is_new = entry is None
        dialog = ctk.CTkToplevel(self)
        dialog.title("Neuer Eintrag" if is_new else "Eintrag bearbeiten")
        dialog.geometry("460x600")
        dialog.minsize(420, 420)
        dialog.transient(self)
        dialog.grab_set()

        # Fest sichtbare Fußzeile mit Speichern/Abbrechen wird ZUERST gepackt
        # (side="bottom"), damit sie nie durch lange Formulare verdeckt wird.
        btn_bar = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_bar.pack(side="bottom", fill="x", pady=14)

        # Scrollbarer Bereich für alle Formularfelder darüber
        scroll = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        scroll.pack(side="top", fill="both", expand=True, padx=4, pady=(4, 0))

        labels_and_keys = [
            ("Dienst / Website *", "service"),
            ("Benutzername / E-Mail *", "username"),
            ("URL", "url"),
        ]
        vars_map = {}

        row = 0
        for label_text, key in labels_and_keys:
            ctk.CTkLabel(scroll, text=label_text).grid(row=row, column=0, columnspan=2,
                                                         sticky="w", padx=16, pady=(14 if row == 0 else 6, 0))
            row += 1
            var = tk.StringVar(value=getattr(entry, key) if entry else "")
            ctk.CTkEntry(scroll, textvariable=var, width=380).grid(
                row=row, column=0, columnspan=2, padx=16, pady=(2, 0))
            vars_map[key] = var
            row += 1

        ctk.CTkLabel(scroll, text="Passwort *").grid(row=row, column=0, columnspan=2,
                                                       sticky="w", padx=16, pady=(6, 0))
        row += 1
        pw_var = tk.StringVar(value=entry.password if entry else "")
        pw_entry = ctk.CTkEntry(scroll, textvariable=pw_var, width=280, show="•")
        pw_entry.grid(row=row, column=0, padx=(16, 6), pady=(2, 0), sticky="w")

        def toggle_show():
            pw_entry.configure(show="" if pw_entry.cget("show") == "•" else "•")

        ctk.CTkButton(scroll, text="👁", width=40, command=toggle_show).grid(
            row=row, column=1, padx=(0, 16), pady=(2, 0), sticky="w")
        row += 1

        strength_label = ctk.CTkLabel(scroll, text="", text_color="gray70")
        strength_label.grid(row=row, column=0, columnspan=2, sticky="w", padx=16)
        row += 1

        def update_strength(*_):
            pw = pw_var.get()
            strength_label.configure(
                text=f"Stärke: {crypto_utils.password_strength_label(pw)}" if pw else "")
        pw_var.trace_add("write", update_strength)
        update_strength()

        def generate_and_fill():
            pw_var.set(crypto_utils.generate_password(20, True, True, True))

        ctk.CTkButton(scroll, text="🎲 Sicheres Passwort generieren",
                      command=generate_and_fill).grid(row=row, column=0, columnspan=2,
                                                        padx=16, pady=(4, 6))
        row += 1

        ctk.CTkLabel(scroll, text="Notizen").grid(row=row, column=0, columnspan=2,
                                                    sticky="w", padx=16, pady=(6, 0))
        row += 1
        notes_box = ctk.CTkTextbox(scroll, width=380, height=70)
        notes_box.grid(row=row, column=0, columnspan=2, padx=16, pady=(2, 0))
        if entry and entry.notes:
            notes_box.insert("1.0", entry.notes)
        row += 1

        error_label = ctk.CTkLabel(scroll, text="", text_color="#ff6666")
        error_label.grid(row=row, column=0, columnspan=2, pady=(6, 0))
        row += 1

        def save():
            service = vars_map["service"].get().strip()
            username = vars_map["username"].get().strip()
            password = pw_var.get()
            if not service or not username or not password:
                error_label.configure(text="Dienst, Benutzername und Passwort sind Pflichtfelder.")
                return

            if is_new:
                new_entry = storage.Entry(
                    service=service, username=username, password=password,
                    url=vars_map["url"].get().strip(),
                    notes=notes_box.get("1.0", "end").strip(),
                )
                self.entries.append(new_entry)
            else:
                from datetime import datetime
                entry.service = service
                entry.username = username
                entry.password = password
                entry.url = vars_map["url"].get().strip()
                entry.notes = notes_box.get("1.0", "end").strip()
                entry.updated_at = datetime.now().isoformat(timespec="seconds")

            self._persist()
            self.refresh_table()
            dialog.destroy()

        ctk.CTkButton(btn_bar, text="Speichern", command=save, width=150).pack(
            side="left", padx=6, expand=True)
        ctk.CTkButton(btn_bar, text="Abbrechen", fg_color="gray30",
                      command=dialog.destroy, width=150).pack(side="left", padx=6, expand=True)

    def delete_selected_entry(self):
        entry = self._selected_entry()
        if not entry:
            messagebox.showinfo("Kein Eintrag ausgewählt", "Bitte wähle zuerst einen Eintrag aus.")
            return
        if messagebox.askyesno("Löschen bestätigen",
                                f"'{entry.service}' ({entry.username}) wirklich löschen?"):
            self.entries = [e for e in self.entries if e.id != entry.id]
            self._persist()
            self.refresh_table()

    def show_selected_password(self):
        entry = self._selected_entry()
        if not entry:
            messagebox.showinfo("Kein Eintrag ausgewählt", "Bitte wähle zuerst einen Eintrag aus.")
            return
        messagebox.showinfo(f"Passwort für {entry.service}", entry.password)

    # ---------- Auto-Ausfüllen (wie "Auto-Type" bei KeePass) ----------
    #
    # Simuliert echte Tastatureingaben in das Fenster/Feld, das gerade den
    # Fokus hat (Browser-Login, Desktop-App, egal was). Es findet keine
    # Erkennung von Formularfeldern statt – du musst also selbst vorher in
    # das richtige Feld klicken. Dafür funktioniert es überall, ganz ohne
    # Browser-Erweiterung, und bleibt komplett lokal.

    def start_autotype(self):
        entry = self._selected_entry()
        if not entry:
            messagebox.showinfo("Kein Eintrag ausgewählt", "Bitte wähle zuerst einen Eintrag aus.")
            return
        if not AUTOTYPE_AVAILABLE:
            messagebox.showwarning(
                "Auto-Ausfüllen nicht verfügbar",
                "Installiere 'pyautogui' (pip install pyautogui) und stelle sicher,\n"
                "dass eine grafische Sitzung läuft (unter Linux: X11, nicht reines Wayland).")
            return

        self._autotype_cancelled = False
        self.iconify()  # Fenster aus dem Weg räumen, damit du das Zielfeld siehst
        self._show_autotype_overlay(entry, 3)

    def _show_autotype_overlay(self, entry, seconds_left):
        if not hasattr(self, "_autotype_overlay") or not self._autotype_overlay.winfo_exists():
            overlay = tk.Toplevel(self)
            overlay.overrideredirect(True)
            overlay.attributes("-topmost", True)
            overlay.configure(bg="#1f6aa5")
            label = tk.Label(
                overlay, text="", font=("", 13, "bold"),
                bg="#1f6aa5", fg="white", padx=18, pady=12, justify="center")
            label.pack()
            overlay.update_idletasks()
            sw, sh = overlay.winfo_screenwidth(), overlay.winfo_screenheight()
            overlay.geometry(f"+{sw - 420}+{sh - 150}")
            overlay.bind("<Escape>", lambda e: self._cancel_autotype())
            overlay.focus_force()
            self._autotype_overlay = overlay
            self._autotype_label = label

        if self._autotype_cancelled:
            return

        if seconds_left <= 0:
            self._autotype_label.configure(text="⌨️  Tippe jetzt …")
            self._autotype_overlay.update()
            self.after(150, lambda: self._finish_autotype(entry))
            return

        self._autotype_label.configure(
            text=f"Jetzt in das Login-Feld klicken!\nAusfüllen in {seconds_left} … (ESC = Abbrechen)")
        self.after(1000, lambda: self._show_autotype_overlay(entry, seconds_left - 1))

    def _cancel_autotype(self):
        self._autotype_cancelled = True
        if hasattr(self, "_autotype_overlay") and self._autotype_overlay.winfo_exists():
            self._autotype_overlay.destroy()
        self.deiconify()
        self.lift()

    def _finish_autotype(self, entry):
        if getattr(self, "_autotype_cancelled", False):
            return
        try:
            pyautogui.write(entry.username, interval=0.03)
            pyautogui.press("tab")
            pyautogui.write(entry.password, interval=0.03)
        except Exception as e:
            messagebox.showerror("Fehler beim automatischen Ausfüllen", str(e))
        finally:
            if hasattr(self, "_autotype_overlay") and self._autotype_overlay.winfo_exists():
                self._autotype_overlay.destroy()
            self.deiconify()
            self.lift()

    def copy_field(self, field_name):
        entry = self._selected_entry()
        if not entry:
            messagebox.showinfo("Kein Eintrag ausgewählt", "Bitte wähle zuerst einen Eintrag aus.")
            return
        if not CLIPBOARD_AVAILABLE:
            messagebox.showwarning(
                "Zwischenablage nicht verfügbar",
                "Installiere 'pyperclip' (pip install pyperclip), um Kopieren zu nutzen.")
            return
        value = getattr(entry, field_name)
        pyperclip.copy(value)
        self.status_label.configure(
            text=f"{'Passwort' if field_name == 'password' else 'Benutzername'} kopiert "
                 f"(wird in {CLIPBOARD_CLEAR_SECONDS}s automatisch gelöscht)")

        if self._clipboard_job:
            self.after_cancel(self._clipboard_job)

        def clear_clipboard():
            try:
                if pyperclip.paste() == value:
                    pyperclip.copy("")
            except Exception:
                pass

        self._clipboard_job = self.after(CLIPBOARD_CLEAR_SECONDS * 1000, clear_clipboard)

    # ---------- Master-Passwort ändern ----------

    def open_change_password_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Master-Passwort ändern")
        dialog.geometry("380x300")
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="Master-Passwort ändern",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(20, 10))

        current_pw = ctk.CTkEntry(dialog, placeholder_text="Aktuelles Master-Passwort",
                                   show="•", width=300)
        current_pw.pack(pady=6)
        new_pw = ctk.CTkEntry(dialog, placeholder_text="Neues Master-Passwort", show="•", width=300)
        new_pw.pack(pady=6)
        new_pw2 = ctk.CTkEntry(dialog, placeholder_text="Neues Passwort bestätigen",
                                show="•", width=300)
        new_pw2.pack(pady=6)

        error_label = ctk.CTkLabel(dialog, text="", text_color="#ff6666")
        error_label.pack(pady=(4, 0))

        def do_change():
            try:
                storage.load_entries(current_pw.get())  # nur zur Verifikation
            except storage.WrongPasswordError:
                error_label.configure(text="Aktuelles Passwort ist falsch.")
                return
            if len(new_pw.get()) < 8:
                error_label.configure(text="Neues Passwort sollte mindestens 8 Zeichen haben.")
                return
            if new_pw.get() != new_pw2.get():
                error_label.configure(text="Die neuen Passwörter stimmen nicht überein.")
                return
            self.key = storage.change_master_password(self.entries, new_pw.get())
            messagebox.showinfo("Erfolg", "Master-Passwort wurde geändert.")
            dialog.destroy()

        ctk.CTkButton(dialog, text="Ändern", command=do_change, width=300).pack(pady=(14, 6))
        ctk.CTkButton(dialog, text="Abbrechen", fg_color="gray30",
                      command=dialog.destroy, width=300).pack()

    # ---------- Sperren / Auto-Lock ----------

    def lock_vault(self):
        self.key = None
        self.entries = []
        if self._autolock_job:
            self.after_cancel(self._autolock_job)
            self._autolock_job = None
        self.show_login_screen()

    def _reset_autolock_timer(self, _event=None):
        if self.key is None:
            return  # nicht eingeloggt, kein Auto-Lock nötig
        if self._autolock_job:
            self.after_cancel(self._autolock_job)
        self._autolock_job = self.after(AUTO_LOCK_MS, self._autolock_trigger)

    def _autolock_trigger(self):
        if self.key is not None:
            self.lock_vault()
            messagebox.showinfo("Automatisch gesperrt",
                                 "Der Tresor wurde nach Inaktivität automatisch gesperrt.")


if __name__ == "__main__":
    app = App()
    app.mainloop()
