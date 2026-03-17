import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime

DB_FILE = "uova.db"

# --- Data Access Layer (SQLite) ---
class UovaRepository:
    def __init__(self, db_path=DB_FILE):
        self.db_path = db_path
        self._ensure_db()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _ensure_db(self):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS raccolte (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data TEXT NOT NULL,
                    uova INTEGER NOT NULL CHECK(uova >= 0)
                )
                """
            )
            conn.commit()

    def inserisci(self, data_str, uova):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO raccolte (data, uova) VALUES (?, ?)", (data_str, uova))
            conn.commit()

    def aggiorna(self, row_id, data_str, uova):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE raccolte SET data = ?, uova = ? WHERE id = ?",
                (data_str, uova, row_id),
            )
            conn.commit()

    def elimina(self, row_id):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM raccolte WHERE id = ?", (row_id,))
            conn.commit()

    def lista(self):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, data, uova FROM raccolte ORDER BY date(data) DESC, id DESC")
            return cur.fetchall()

# --- Validazioni ---
def valida_data(data_str):
    """Ritorna True se la data è nel formato YYYY-MM-DD ed è valida."""
    try:
        datetime.strptime(data_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def valida_uova(val):
    """Ritorna (True, int) se uova è un intero >= 0, altrimenti (False, None)."""
    try:
        n = int(val)
        return (n >= 0, n if n >= 0 else None)
    except Exception:
        return (False, None)

# --- GUI App ---
class RegistroUovaApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Registro Uova (SQLite + Tkinter)")
        self.geometry("560x420")
        self.resizable(False, False)

        self.repo = UovaRepository()
        self.selezionato_id = None

        self._build_widgets()
        self._carica_dati()

    def _build_widgets(self):
        padding = {"padx": 8, "pady": 6}

        # Frame superiore per input
        frame_input = ttk.LabelFrame(self, text="Inserimento / Modifica")
        frame_input.pack(fill="x", **padding)

        # Data
        ttk.Label(frame_input, text="Data (YYYY-MM-DD):").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        self.var_data = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        self.entry_data = ttk.Entry(frame_input, textvariable=self.var_data, width=16)
        self.entry_data.grid(row=0, column=1, sticky="w", padx=6, pady=6)

        # Numero uova
        ttk.Label(frame_input, text="Numero uova:").grid(row=0, column=2, sticky="w", padx=6, pady=6)
        self.var_uova = tk.StringVar(value="0")
        self.entry_uova = ttk.Entry(frame_input, textvariable=self.var_uova, width=10)
        self.entry_uova.grid(row=0, column=3, sticky="w", padx=6, pady=6)

        # Pulsanti azione
        frame_buttons = ttk.Frame(frame_input)
        frame_buttons.grid(row=1, column=0, columnspan=4, sticky="w", padx=6, pady=(0,6))

        self.btn_salva = ttk.Button(frame_buttons, text="Salva", command=self._azione_salva)
        self.btn_salva.grid(row=0, column=0, padx=4)

        self.btn_aggiorna = ttk.Button(frame_buttons, text="Aggiorna selezionato", command=self._azione_aggiorna)
        self.btn_aggiorna.grid(row=0, column=1, padx=4)

        self.btn_elimina = ttk.Button(frame_buttons, text="Elimina selezionato", command=self._azione_elimina)
        self.btn_elimina.grid(row=0, column=2, padx=4)

        self.btn_pulisci = ttk.Button(frame_buttons, text="Pulisci campi", command=self._pulisci_campi)
        self.btn_pulisci.grid(row=0, column=3, padx=4)

        # Frame elenco
        frame_elenco = ttk.LabelFrame(self, text="Registrazioni")
        frame_elenco.pack(fill="both", expand=True, **padding)

        columns = ("id", "data", "uova")
        self.tree = ttk.Treeview(frame_elenco, columns=columns, show="headings", height=12)
        self.tree.heading("id", text="ID")
        self.tree.heading("data", text="Data")
        self.tree.heading("uova", text="Uova")

        self.tree.column("id", width=60, anchor="center")
        self.tree.column("data", width=120, anchor="center")
        self.tree.column("uova", width=100, anchor="e")

        # Scrollbar
        vsb = ttk.Scrollbar(frame_elenco, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side="left", fill="both", expand=True, padx=(6,0), pady=6)
        vsb.pack(side="left", fill="y", padx=(0,6), pady=6)

        # Bind selezione
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # Barra stato
        self.status = tk.StringVar(value="Pronto.")
        ttk.Label(self, textvariable=self.status, anchor="w").pack(fill="x", padx=8, pady=(0,8))

    def _carica_dati(self):
        # Svuota
        for i in self.tree.get_children():
            self.tree.delete(i)
        # Carica
        try:
            righe = self.repo.lista()
            for row_id, data_str, uova in righe:
                self.tree.insert("", "end", values=(row_id, data_str, uova))
            self.status.set(f"Caricate {len(righe)} righe.")
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile caricare i dati:\n{e}")

    def _on_select(self, event):
        item = self._get_selected_item()
        if not item:
            return
        values = self.tree.item(item, "values")
        self.selezionato_id = int(values[0])
        self.var_data.set(values[1])
        self.var_uova.set(str(values[2]))
        self.status.set(f"Selezionato ID {self.selezionato_id}")

    def _get_selected_item(self):
        sel = self.tree.selection()
        return sel[0] if sel else None

    def _pulisci_campi(self):
        self.selezionato_id = None
        self.var_data.set(date.today().strftime("%Y-%m-%d"))
        self.var_uova.set("0")
        self.tree.selection_remove(self.tree.selection())
        self.status.set("Campi puliti.")

    # --- Azioni ---
    def _azione_salva(self):
        data_str = self.var_data.get().strip()
        ok_data = valida_data(data_str)
        ok_uova, n_uova = valida_uova(self.var_uova.get().strip())

        if not ok_data:
            messagebox.showwarning("Dato non valido", "Inserisci una data valida nel formato YYYY-MM-DD.")
            return
        if not ok_uova:
            messagebox.showwarning("Dato non valido", "Il numero di uova deve essere un intero maggiore o uguale a 0.")
            return

        try:
            self.repo.inserisci(data_str, n_uova)
            self._carica_dati()
            self._pulisci_campi()
            self.status.set("Salvato con successo.")
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile salvare:\n{e}")

    def _azione_aggiorna(self):
        if self.selezionato_id is None:
            messagebox.showinfo("Nessuna selezione", "Seleziona prima una riga da aggiornare.")
            return

        data_str = self.var_data.get().strip()
        ok_data = valida_data(data_str)
        ok_uova, n_uova = valida_uova(self.var_uova.get().strip())

        if not ok_data:
            messagebox.showwarning("Dato non valido", "Inserisci una data valida nel formato YYYY-MM-DD.")
            return
        if not ok_uova:
            messagebox.showwarning("Dato non valido", "Il numero di uova deve essere un intero maggiore o uguale a 0.")
            return

        try:
            self.repo.aggiorna(self.selezionato_id, data_str, n_uova)
            self._carica_dati()
            self.status.set(f"Aggiornato ID {self.selezionato_id}.")
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile aggiornare:\n{e}")

    def _azione_elimina(self):
        if self.selezionato_id is None:
            messagebox.showinfo("Nessuna selezione", "Seleziona prima una riga da eliminare.")
            return

        if not messagebox.askyesno("Conferma", f"Vuoi davvero eliminare la riga ID {self.selezionato_id}?"):
            return

        try:
            self.repo.elimina(self.selezionato_id)
            self._carica_dati()
            self._pulisci_campi()
            self.status.set("Eliminazione completata.")
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile eliminare:\n{e}")

if __name__ == "__main__":
    app = RegistroUovaApp()
   
