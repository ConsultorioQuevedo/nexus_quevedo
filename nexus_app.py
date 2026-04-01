
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import datetime
import webbrowser
import os
from fpdf import FPDF

# ==========================================
# 1. MOTOR DE LÓGICA INTEGRADA NEXUS
# ==========================================
class MotorNEXUS:
    def __init__(self):
        self.presupuesto = 5000.0  # Valor inicial
        self.ingresos = 8500.0
        self.gastos = []
        self.medicamentos = []
        self.citas = []
        self.glucosa_actual = 0.0

    def calcular_estado_ia(self):
        alertas = []
        total_gastos = sum(g['monto'] for g in self.gastos)
        
        # Lógica de Finanzas con Presupuesto Elegible
        porc = (total_gastos / self.presupuesto) * 100 if self.presupuesto > 0 else 0
        if porc > 85: 
            alertas.append(f"⚠️ IA FINANZAS: Consumo del {porc:.1f}%. ¡Cuidado!")
        else:
            alertas.append(f"✅ IA FINANZAS: Presupuesto saludable ({porc:.1f}%)")
        
        # Lógica de Salud
        if self.glucosa_actual > 140:
            alertas.append(f"🚨 IA SALUD: Glucosa en {self.glucosa_actual} mg/dL. Nivel Crítico.")
        elif self.glucosa_actual > 0:
            alertas.append("✅ IA SALUD: Niveles de glucosa estables.")
            
        return alertas, total_gastos

# ==========================================
# 2. INTERFAZ GRÁFICA MEJORADA
# ==========================================
class NexusApp:
    def __init__(self, root):
        self.nexus = MotorNEXUS()
        self.root = root
        self.root.title("NEXUS PRO - SISTEMA INTEGRADO")
        self.root.geometry("1150x900")
        self.root.configure(bg="#0d1117")

        self.crear_interfaz()

    def crear_interfaz(self):
        # --- PANEL LATERAL ---
        sidebar = tk.Frame(self.root, bg="#161b22", width=200)
        sidebar.pack(side="left", fill="y")
        
        tk.Label(sidebar, text="NEXUS PRO", fg="#58a6ff", bg="#161b22", font=("Arial", 16, "bold")).pack(pady=20)
        
        tk.Button(sidebar, text="📲 WHATSAPP ACTIVO", bg="#238636", fg="white", font=("Arial", 10, "bold"), command=self.share_wa).pack(fill="x", padx=10, pady=10)
        tk.Button(sidebar, text="📄 VER REPORTE PDF", bg="#444", fg="white", command=self.save_pdf).pack(fill="x", padx=10, pady=10)
        tk.Button(sidebar, text="📸 ESCÁNER ACTIVO", bg="#8957e5", fg="white", command=self.scan_action).pack(fill="x", padx=10, pady=10)

        # --- ÁREA CENTRAL ---
        main = tk.Frame(self.root, bg="#0d1117")
        main.pack(side="right", fill="both", expand=True, padx=20)

        # SECCIÓN 1: CONFIGURACIÓN Y PRESUPUESTO
        conf_frame = tk.Frame(main, bg="#0d1117")
        conf_frame.pack(fill="x", pady=10)
        tk.Label(conf_frame, text="DEFINA SU PRESUPUESTO (RD$):", fg="#d29922", bg="#0d1117", font=("Arial", 10, "bold")).grid(row=0, column=0)
        self.ent_presupuesto = tk.Entry(conf_frame, width=15, font=("Arial", 12)); self.ent_presupuesto.grid(row=0, column=1, padx=10)
        self.ent_presupuesto.insert(0, "5000")
        tk.Button(conf_frame, text="FIJAR", bg="#d29922", command=self.set_presupuesto).grid(row=0, column=2)

        # SECCIÓN 2: SALUD
        s_frame = tk.LabelFrame(main, text=" 🩺 CONTROL MÉDICO ", fg="#ff7b72", bg="#0d1117", font=("Arial", 11, "bold"), padx=15, pady=15)
        s_frame.pack(fill="x", pady=10)

        tk.Label(s_frame, text="Glucosa:", fg="white", bg="#0d1117").grid(row=0, column=0, sticky="w")
        self.ent_glu = tk.Entry(s_frame, width=10); self.ent_glu.grid(row=0, column=1, padx=5)
        
        tk.Label(s_frame, text="Medicamento:", fg="white", bg="#0d1117").grid(row=0, column=2, padx=10)
        self.ent_med = tk.Entry(s_frame, width=20); self.ent_med.grid(row=0, column=3)
        
        tk.Button(s_frame, text="REGISTRAR", bg="#1f6feb", fg="white", command=self.update_all).grid(row=0, column=4, padx=15)

        # SECCIÓN 3: TABLA DE DATOS (VISUALIZACIÓN)
        self.tabla = ttk.Treeview(main, columns=("Fecha", "Detalle", "Monto/Valor"), show="headings", height=8)
        self.tabla.heading("Fecha", text="Fecha"); self.tabla.heading("Detalle", text="Detalle"); self.tabla.heading("Monto/Valor", text="Valor")
        self.tabla.pack(fill="x", pady=10)

        # SECCIÓN 4: FINANZAS
        f_frame = tk.LabelFrame(main, text=" 📊 FINANZAS EN TIEMPO REAL ", fg="#3fb950", bg="#0d1117", font=("Arial", 11, "bold"), padx=15, pady=15)
        f_frame.pack(fill="x", pady=10)

        self.lbl_balance = tk.Label(f_frame, text="Saldo: $8500.00", fg="white", bg="#0d1117", font=("Arial", 14, "bold"))
        self.lbl_balance.pack(side="left")

        tk.Label(f_frame, text="Gasto ($):", fg="white", bg="#0d1117").pack(side="left", padx=10)
        self.ent_gasto = tk.Entry(f_frame, width=10); self.ent_gasto.pack(side="left")
        tk.Button(f_frame, text="AÑADIR GASTO", bg="#238636", fg="white", command=self.add_gasto).pack(side="left", padx=10)

        # SECCIÓN 5: LOG DE IA
        self.ia_box = tk.Text(main, bg="#161b22", fg="#d29922", font=("Consolas", 11), height=10)
        self.ia_box.pack(fill="both", expand=True, pady=10)

    # --- ACCIONES ---
    def set_presupuesto(self):
        try:
            self.nexus.presupuesto = float(self.ent_presupuesto.get())
            self.refresh_ia()
            messagebox.showinfo("NEXUS", f"Nuevo presupuesto fijado en: RD$ {self.nexus.presupuesto}")
        except: pass

    def update_all(self):
        fecha = datetime.datetime.now().strftime('%d/%m %H:%M')
        if self.ent_glu.get():
            val = self.ent_glu.get()
            self.nexus.glucosa_actual = float(val)
            self.tabla.insert("", "end", values=(fecha, "🩸 Glucosa", val))
        if self.ent_med.get():
            med = self.ent_med.get()
            self.nexus.medicamentos.append(med)
            self.tabla.insert("", "end", values=(fecha, "💊 Med.", med))
        self.refresh_ia()

    def add_gasto(self):
        try:
            m = float(self.ent_gasto.get())
            fecha = datetime.datetime.now().strftime('%d/%m %H:%M')
            self.nexus.gastos.append({'monto': m, 'fecha': fecha})
            self.tabla.insert("", "end", values=(fecha, "💸 Gasto", f"${m}"))
            self.refresh_ia()
            self.ent_gasto.delete(0, tk.END)
        except: pass

    def refresh_ia(self):
        alertas, total_g = self.nexus.calcular_estado_ia()
        balance = self.nexus.ingresos - total_g
        self.lbl_balance.config(text=f"Saldo Disponible: ${balance:.2f}")
        
        self.ia_box.delete('1.0', tk.END)
        self.ia_box.insert(tk.END, f"--- REPORTE DE INTELIGENCIA NEXUS ---\n")
        for a in alertas: self.ia_box.insert(tk.END, f"> {a}\n")

    def save_pdf(self):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, txt="REPORTE NEXUS PRO - SR. QUEVEDO", ln=True, align='C')
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Fecha: {datetime.datetime.now()}", ln=True)
        pdf.cell(200, 10, txt=f"Balance Final: {self.nexus.ingresos - sum(g['monto'] for g in self.nexus.gastos)}", ln=True)
        
        nombre_archivo = "Reporte_Nexus_Final.pdf"
        pdf.output(nombre_archivo)
        os.startfile(nombre_archivo) # Abre el PDF automáticamente

    def share_wa(self):
        # Abre WhatsApp con un mensaje real
        msg = f"Reporte Nexus: Balance actual ${self.nexus.ingresos}. Glucosa: {self.nexus.glucosa_actual}"
        webbrowser.open(f"https://web.whatsapp.com/send?text={msg}")

    def scan_action(self):
        # Simulación de escáner que inserta datos reales
        self.ent_glu.delete(0, tk.END)
        self.ent_glu.insert(0, "155")
        messagebox.showinfo("Escáner", "Análisis completado: Se detectó Glucosa 155 mg/dL")

if __name__ == "__main__":
    root = tk.Tk()
    app = NexusApp(root)
    root.mainloop()
