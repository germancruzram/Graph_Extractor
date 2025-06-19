import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from tkinter import font as tkFont
import webbrowser
import cv2
import numpy as np
from PIL import Image, ImageTk
from logic import DigitizerLogic
import base64
import io
from image_data import IMAGE_DATA

class GraphDigitizerApp:
    def __init__(self, master, logic):
        self.master = master
        self.logic = logic
        self.master.title("Digitalizador de Gráficos")
        self.master.geometry("1000x850")

        self.tk_image = None
        self.image_display_scale = 1.0
        self.image_on_canvas = None
        self.mode = 'idle'

        self.notebook = ttk.Notebook(master)
        self.notebook.pack(pady=10, padx=10, fill="both", expand=True)

        descriptor_frame = tk.Frame(self.notebook)
        digitizer_frame = tk.Frame(self.notebook)
        self.notebook.add(descriptor_frame, text='Descriptor')
        self.notebook.add(digitizer_frame, text='Digitalizador')

        self.setup_descriptor_tab(descriptor_frame)
        self.setup_digitizer_tab(digitizer_frame)

    def setup_descriptor_tab(self, parent_frame):
        desc_main_frame = tk.Frame(parent_frame)
        desc_main_frame.pack(pady=20, padx=30, fill="both", expand=True)

        # --- Grid Layout Configuration ---
        desc_main_frame.grid_columnconfigure(0, weight=1)
        desc_main_frame.grid_rowconfigure(0, weight=0)  # Title
        desc_main_frame.grid_rowconfigure(1, weight=1, minsize=150)  # Image (weight 1)
        desc_main_frame.grid_rowconfigure(2, weight=2)  # Text (weight 2)
        desc_main_frame.grid_rowconfigure(3, weight=0)  # Dedication

        # --- Widgets ---
        font_title = tkFont.Font(family="Helvetica", size=18, weight="bold")
        title_label = tk.Label(desc_main_frame, text="GRAPH EXTRACTOR 1.10", font=font_title, justify=tk.CENTER)
        title_label.grid(row=0, column=0, pady=(0, 10), sticky='n')

        self.image_desc_frame = tk.Frame(desc_main_frame)
        self.image_desc_frame.grid(row=1, column=0, pady=10, sticky='nsew')

        self.desc_image_label = tk.Label(self.image_desc_frame)
        self.desc_image_label.pack(fill=tk.BOTH, expand=True)
        self.original_desc_image = None
        try:
            image_bytes = base64.b64decode(IMAGE_DATA)
            image_stream = io.BytesIO(image_bytes)
            self.original_desc_image = Image.open(image_stream)
        except Exception as e:
            self.desc_image_label.config(text=f"Error al cargar imagen:\n{e}", bg='lightgrey')
        self.image_desc_frame.bind("<Configure>", self.resize_desc_image)

        text_container = tk.Frame(desc_main_frame)
        text_container.grid(row=2, column=0, pady=10, sticky='nsew')
        
        text_widget = tk.Text(text_container, wrap=tk.WORD, bd=0, bg=parent_frame.cget('bg'), font=("Helvetica", 10), padx=10)
        text_widget.pack(side="left", fill="both", expand=True)

        text_widget.tag_configure("intro", font=("Helvetica", 11), spacing1=5)
        text_widget.tag_configure("heading", font=("Helvetica", 10, "bold"), spacing3=5)
        text_widget.tag_configure("body", lmargin1=15, lmargin2=15, spacing1=2)

        text_widget.insert(tk.END, "Graph Extractor, es una una herramienta para estudiantes y profesionales de la ingeniería, permite la extracción de datos cuantitativos a partir de gráficas en formato de imagen. El proceso metodológico es el siguiente:\n\n", "intro")
        
        steps = [
            ("1. Carga de Imagen:", "Seleccione un archivo de imagen (PNG, JPG, BMP) que contenga la gráfica a digitalizar."),
            ("2. Calibración de Ejes:", "Defina el dominio y rango de la gráfica. Posteriormente, realice una calibración espacial mediante la selección de cuatro puntos de referencia para corregir distorsiones:\n  • Origen (Xmín, Ymín)\n  • Extremo del eje X (Xmáx, Ymín)\n  • Extremo del eje Y (Xmín, Ymáx)\n  • Punto opuesto (Xmáx, Ymáx)"),
            ("3. Trazado de Curvas:", "Capture la morfología de la curva mediante la selección de puntos a lo largo de su trazado. Es preferible más de 8 puntos para que el algoritmo de interpolación cúbica (spline) genere una representación suave y de alta densidad."),
            ("4. Exportación de Datos:", "Guarde cada curva digitalizada en un archivo CSV. Los datos resultantes están listos para su uso en análisis posteriores")
        ]

        for heading, body in steps:
            text_widget.insert(tk.END, f"{heading}\n", "heading")
            text_widget.insert(tk.END, f"{body}\n\n", "body")

        text_widget.config(state=tk.DISABLED)

        # Dedicatoria
        font_dedication = tkFont.Font(family="Helvetica", size=8, slant="italic")
        dedication_label = tk.Label(desc_main_frame, text="Dedicado a la memoria de Denis Ramírez Avilés (2025)", font=font_dedication, justify=tk.RIGHT)
        dedication_label.grid(row=3, column=0, sticky='se', padx=5, pady=5)

    def setup_digitizer_tab(self, parent_frame):
        control_frame = tk.Frame(parent_frame, width=300, relief=tk.RIDGE, bd=2)
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        control_frame.pack_propagate(False)

        top_control_frame = tk.Frame(control_frame)
        top_control_frame.pack(side=tk.TOP, anchor='n')

        self.canvas_frame = tk.Frame(parent_frame, relief=tk.SUNKEN, bd=2)
        self.canvas_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.canvas = tk.Canvas(self.canvas_frame, bg='gray')
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<Configure>", self.on_resize)

        load_frame = tk.LabelFrame(top_control_frame, text="1. Cargar Imagen", padx=10, pady=10)
        load_frame.pack(fill=tk.X, padx=5, pady=5)
        self.btn_load = tk.Button(load_frame, text="Cargar Imagen de Gráfica", command=self.load_image_gui)
        self.btn_load.pack(fill=tk.X)

        axis_frame = tk.LabelFrame(top_control_frame, text="2. Definir Ejes", padx=10, pady=10)
        axis_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(axis_frame, text="Valor X Mínimo:").grid(row=0, column=0, sticky='w')
        self.x_min_var = tk.StringVar(value="0")
        self.entry_x_min = tk.Entry(axis_frame, textvariable=self.x_min_var)
        self.entry_x_min.grid(row=0, column=1)

        tk.Label(axis_frame, text="Valor X Máximo:").grid(row=1, column=0, sticky='w')
        self.x_max_var = tk.StringVar(value="100")
        self.entry_x_max = tk.Entry(axis_frame, textvariable=self.x_max_var)
        self.entry_x_max.grid(row=1, column=1)

        tk.Label(axis_frame, text="Valor Y Mínimo:").grid(row=2, column=0, sticky='w')
        self.y_min_var = tk.StringVar(value="0")
        self.entry_y_min = tk.Entry(axis_frame, textvariable=self.y_min_var)
        self.entry_y_min.grid(row=2, column=1)

        tk.Label(axis_frame, text="Valor X,Y Máximo (coord):").grid(row=3, column=0, sticky='w')
        self.xy_max_var = tk.StringVar(value="100, 100")
        self.entry_xy_max = tk.Entry(axis_frame, textvariable=self.xy_max_var)
        self.entry_xy_max.grid(row=3, column=1)

        self.is_log_x_var = tk.BooleanVar(value=False)
        self.check_log_x = tk.Checkbutton(axis_frame, text="Eje X es Logarítmico", variable=self.is_log_x_var)
        self.check_log_x.grid(row=4, columnspan=2, sticky='w')

        self.is_log_y_var = tk.BooleanVar(value=False)
        self.check_log_y = tk.Checkbutton(axis_frame, text="Eje Y es Logarítmico", variable=self.is_log_y_var)
        self.check_log_y.grid(row=5, columnspan=2, sticky='w')

        process_frame = tk.LabelFrame(top_control_frame, text="3. Proceso", padx=10, pady=10)
        process_frame.pack(fill=tk.X, padx=5, pady=5)

        self.btn_calibrate = tk.Button(process_frame, text="Iniciar Calibración de Ejes", command=self.start_calibration, state=tk.DISABLED)
        self.btn_calibrate.pack(fill=tk.X, pady=2)

        self.btn_trace = tk.Button(process_frame, text="Iniciar Trazado de Curva", command=self.start_tracing, state=tk.DISABLED)
        self.btn_trace.pack(fill=tk.X, pady=2)
        
        self.btn_add_curve = tk.Button(process_frame, text="Añadir Curva a la Sesión", command=self.add_curve_gui, state=tk.DISABLED)
        self.btn_add_curve.pack(fill=tk.X, pady=2)

        self.btn_save_all = tk.Button(process_frame, text="Guardar Fichero Consolidado", command=self.save_all_gui, state=tk.DISABLED)
        self.btn_save_all.pack(fill=tk.X, pady=2)

        status_frame = tk.LabelFrame(top_control_frame, text="Estado", padx=10, pady=10)
        status_frame.pack(fill=tk.X, padx=5, pady=5)
        self.status_label = tk.Label(status_frame, text="Cargue una imagen para comenzar.", wraplength=280, justify=tk.LEFT)
        self.status_label.pack(fill=tk.X)

        author_frame = tk.LabelFrame(top_control_frame, text="Autor", padx=10, pady=10)
        author_frame.pack(fill=tk.X, padx=5, pady=(15, 5))

        author_label = tk.Label(author_frame, text="German Ahmed Cruz Ramírez", font=("Helvetica", 10, "bold"))
        author_label.pack()

        linkedin_url = "https://www.linkedin.com/in/german-cruz-ram-in24/"
        github_url = "https://github.com/germancruzram"

        hyperlink_font = tkFont.Font(family="Helvetica", size=9, underline=True)

        link_linkedin = tk.Label(author_frame, text="Perfil de LinkedIn", fg="blue", cursor="hand2", font=hyperlink_font)
        link_linkedin.pack(pady=2)
        link_linkedin.bind("<Button-1>", lambda e: self.open_link(linkedin_url))

        link_github = tk.Label(author_frame, text="Perfil de GitHub", fg="blue", cursor="hand2", font=hyperlink_font)
        link_github.pack(pady=2)
        link_github.bind("<Button-1>", lambda e: self.open_link(github_url))

    def update_status(self, text):
        self.status_label.config(text=text)

    def open_link(self, url):
        webbrowser.open_new(url)

    def resize_desc_image(self, event):
        if not self.original_desc_image:
            return
        
        frame_width = event.width
        frame_height = event.height
        
        img_width, img_height = self.original_desc_image.size
        ratio = min(frame_width / img_width, frame_height / img_height)
        
        new_width = int(img_width * ratio)
        new_height = int(img_height * ratio)
        
        resized_img = self.original_desc_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        self.desc_tk_image = ImageTk.PhotoImage(resized_img)
        self.desc_image_label.config(image=self.desc_tk_image)

    def load_image_gui(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp")])
        if not path:
            return
        
        success, message = self.logic.load_image(path)
        if not success:
            messagebox.showerror("Error", message)
            return
        
        self.redraw_points()
        self.btn_calibrate.config(state=tk.NORMAL)
        self.btn_trace.config(state=tk.DISABLED)
        self.btn_add_curve.config(state=tk.DISABLED)
        self.btn_save_all.config(state=tk.DISABLED)
        self.update_status(message)

    def on_resize(self, event):
        self.redraw_points()

    def on_canvas_click(self, event):
        if self.mode == 'idle' or self.logic.cv_image is None:
            return

        is_ctrl_pressed = (event.state & 4) != 0

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        img_h, img_w, _ = self.logic.cv_image.shape
        
        displayed_w = int(img_w * self.image_display_scale)
        displayed_h = int(img_h * self.image_display_scale)
        
        offset_x = (canvas_width - displayed_w) / 2
        offset_y = (canvas_height - displayed_h) / 2
        
        x = int((event.x - offset_x) / self.image_display_scale)
        y = int((event.y - offset_y) / self.image_display_scale)

        if not (0 <= x < img_w and 0 <= y < img_h):
            return

        if self.mode == 'calibration':
            count = self.logic.add_calibration_point((x, y))
            self.redraw_points()
            self.update_status(f"Punto de calibración {count}/{self.logic.num_calibration_points} añadido.")
            if self.logic.is_calibration_ready():
                self.finish_calibration()
        
        elif self.mode == 'tracing':
            if is_ctrl_pressed:
                count = self.logic.remove_last_tracing_point()
                self.update_status(f"Último punto eliminado. {count} puntos restantes.")
            else:
                count = self.logic.add_tracing_point((x, y))
                self.update_status(f"{count} puntos trazados. (Ctrl+Click para eliminar).")
            
            self.redraw_points()
            if self.logic.can_save_curve():
                self.btn_add_curve.config(state=tk.NORMAL)
            else:
                self.btn_add_curve.config(state=tk.DISABLED)

    def redraw_points(self):
        if self.logic.cv_image is None:
            self.canvas.delete("all")
            return
        
        self.canvas.delete("all")
        
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            self.master.after(50, self.redraw_points)
            return

        h, w, _ = self.logic.cv_image.shape
        
        scale_w = canvas_width / w
        scale_h = canvas_height / h
        self.image_display_scale = min(scale_w, scale_h)
        
        new_w = int(w * self.image_display_scale)
        new_h = int(h * self.image_display_scale)
        
        resized_image = cv2.resize(self.logic.cv_image, (new_w, new_h)) # pylint: disable=no-member
        img_rgb = cv2.cvtColor(resized_image, cv2.COLOR_BGR2RGB) # pylint: disable=no-member
        self.tk_image = ImageTk.PhotoImage(Image.fromarray(img_rgb))
        
        self.image_on_canvas = self.canvas.create_image(canvas_width/2, canvas_height/2, anchor=tk.CENTER, image=self.tk_image)
        
        for (x, y) in self.logic.calibration_points_pixels:
            self.draw_point_on_canvas(x, y, 'red')
        
        for i, (x, y) in enumerate(self.logic.points_clicked_pixels):
            self.draw_point_on_canvas(x, y, 'purple')
            if i > 0:
                self.draw_line_on_canvas(self.logic.points_clicked_pixels[i-1], (x,y), 'red')

    def draw_point_on_canvas(self, x_orig, y_orig, color):
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        img_h, img_w, _ = self.logic.cv_image.shape
        displayed_w = int(img_w * self.image_display_scale)
        displayed_h = int(img_h * self.image_display_scale)
        offset_x = (canvas_width - displayed_w) / 2
        offset_y = (canvas_height - displayed_h) / 2

        x_canvas = x_orig * self.image_display_scale + offset_x
        y_canvas = y_orig * self.image_display_scale + offset_y
        self.canvas.create_oval(x_canvas-4, y_canvas-4, x_canvas+4, y_canvas+4, fill=color, outline='white', width=1)

    def draw_line_on_canvas(self, p1_orig, p2_orig, color):
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        img_h, img_w, _ = self.logic.cv_image.shape
        displayed_w = int(img_w * self.image_display_scale)
        displayed_h = int(img_h * self.image_display_scale)
        offset_x = (canvas_width - displayed_w) / 2
        offset_y = (canvas_height - displayed_h) / 2

        x1_c = p1_orig[0] * self.image_display_scale + offset_x
        y1_c = p1_orig[1] * self.image_display_scale + offset_y
        x2_c = p2_orig[0] * self.image_display_scale + offset_x
        y2_c = p2_orig[1] * self.image_display_scale + offset_y
        self.canvas.create_line(x1_c, y1_c, x2_c, y2_c, fill=color, width=2)

    def start_calibration(self):
        self.mode = 'calibration'
        self.logic.calibration_points_pixels = []
        self.redraw_points()
        self.btn_trace.config(state=tk.DISABLED)
        self.btn_add_curve.config(state=tk.DISABLED)
        self.update_status("MODO CALIBRACIÓN:\nClic en 4 puntos en orden:\n1. Origen (Xmín, Ymín)\n2. Eje X (Xmáx, Ymín)\n3. Eje Y (Xmín, Ymáx)\n4. Opuesto (Xmáx, Ymáx)")

    def finish_calibration(self):
        success, message = self.logic.finish_calibration()
        if success:
            self.mode = 'idle'
            self.btn_trace.config(state=tk.NORMAL)
            self.update_status(message)
            messagebox.showinfo("Calibración Completa", message)
        else:
            messagebox.showerror("Error de Calibración", message)

    def start_tracing(self):
        self.mode = 'tracing'
        curve_num = self.logic.start_new_curve()
        self.redraw_points()
        self.btn_add_curve.config(state=tk.DISABLED)
        self.update_status(f"MODO TRAZADO: Trazando curva {curve_num}.\nHaz clic en al menos {self.logic.min_trace_points} puntos.\n(Ctrl+Click para eliminar el último punto).")

    def _get_axis_values(self):
        try:
            x_max_val = float(self.x_max_var.get())
            
            parts = [p.strip() for p in self.xy_max_var.get().split(',')]
            if len(parts) != 2:
                raise ValueError("Se requieren dos valores para las coordenadas (X,Y).")
            
            x_from_coord, y_max_val = float(parts[0]), float(parts[1])

            if not np.isclose(x_max_val, x_from_coord):
                messagebox.showwarning("Advertencia de Coordenadas", 
                                     f"El 'Valor X Máximo' ({x_max_val}) no coincide con la coordenada X máxima ({x_from_coord}).\n"
                                     "Por favor, asegúrese de que ambos valores sean consistentes.")
                # Se podría detener aquí si se quisiera una validación estricta,
                # pero por ahora solo advertimos y continuamos usando los valores separados.
            
            return {
                'x_min': self.x_min_var.get(), 'x_max': self.x_max_var.get(),
                'y_min': self.y_min_var.get(), 'y_max': y_max_val,
                'is_log_x': self.is_log_x_var.get(),
                'is_log_y': self.is_log_y_var.get()
            }
        except (ValueError, IndexError) as e:
            messagebox.showerror("Error de Formato", f"Formato de valores de ejes no válido.\n\nError: {e}")
            return None

    def add_curve_gui(self):
        if not self.logic.can_save_curve():
            messagebox.showwarning("Puntos insuficientes", f"Se necesitan al menos {self.logic.min_trace_points} puntos.")
            return

        curve_name = simpledialog.askstring("Nombre de la Curva", f"Introduce un nombre para la curva {self.logic.curve_count} (e.g., H, M, L):")
        if not curve_name:
            curve_name = f"curva_{self.logic.curve_count}"
        
        axis_values = self._get_axis_values()
        if axis_values is None:
            return

        success, message = self.logic.add_curve_to_session(axis_values, curve_name)
        
        if success:
            messagebox.showinfo("Éxito", message)
            self.mode = 'idle'
            self.logic.points_clicked_pixels = []
            self.redraw_points()
            self.btn_add_curve.config(state=tk.DISABLED)
            self.btn_trace.config(state=tk.NORMAL)
            self.btn_save_all.config(state=tk.NORMAL)
            self.update_status(f"{message}\nPuedes trazar otra curva o guardar el fichero consolidado.")
        else:
            messagebox.showerror("Error al Añadir Curva", message)

    def save_all_gui(self):
        if not self.logic.session_curves:
            messagebox.showwarning("No hay curvas", "No hay curvas en la sesión para guardar.")
            return

        output_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[
                ("CSV files", "*.csv"),
                ("Excel files", "*.xlsx"),
                ("Excel 97-2003", "*.xls"),
                ("All files", "*.*")
            ],
            title="Guardar fichero consolidado"
        )
        if not output_path:
            return

        axis_values = self._get_axis_values()
        if axis_values is None:
            return

        success, message = self.logic.save_session_to_file(output_path, axis_values)

        if success:
            messagebox.showinfo("Éxito", message)
            self.btn_save_all.config(state=tk.DISABLED)
            self.update_status("Fichero consolidado guardado. Puede cargar una nueva imagen.")
        else:
            messagebox.showerror("Error al Guardar", message)
