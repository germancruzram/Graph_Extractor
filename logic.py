import cv2
import numpy as np
import pandas as pd
import os
from scipy.interpolate import interp1d

class DigitizerLogic:
    def __init__(self):
        self.output_folder = 'curvas_extraidas'
        self.num_calibration_points = 4
        self.min_trace_points = 4
        self.cv_image = None
        self.image_path = None
        self.points_clicked_pixels = []
        self.calibration_points_pixels = []
        self.transform_matrix = None
        self.max_width = 0
        self.max_height = 0
        self.curve_count = 0
        self.session_curves = []  # Almacenará las curvas de la sesión actual

        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)

    def reset_state(self):
        self.points_clicked_pixels = []
        self.calibration_points_pixels = []
        self.transform_matrix = None
        self.curve_count = 0
        self.cv_image = None
        self.image_path = None
        self.session_curves = []

    def load_image(self, path):
        self.reset_state()
        self.image_path = path
        self.cv_image = cv2.imread(self.image_path)
        if self.cv_image is None:
            self.image_path = None
            return False, f"No se pudo cargar la imagen: {path}"
        return True, "Imagen cargada. Defina los ejes y calibre."

    def add_calibration_point(self, point):
        if len(self.calibration_points_pixels) < self.num_calibration_points:
            self.calibration_points_pixels.append(point)
        return len(self.calibration_points_pixels)

    def is_calibration_ready(self):
        return len(self.calibration_points_pixels) == self.num_calibration_points

    def finish_calibration(self):
        if not self.is_calibration_ready():
            return False, "Puntos de calibración insuficientes."

        p_origen, p_xmax, p_ymax, p_xymax = self.calibration_points_pixels
        rect = np.array([p_ymax, p_xymax, p_xmax, p_origen], dtype="float32")
        
        width_a = np.sqrt(((p_xymax[0] - p_ymax[0]) ** 2) + ((p_xymax[1] - p_ymax[1]) ** 2))
        width_b = np.sqrt(((p_xmax[0] - p_origen[0]) ** 2) + ((p_xmax[1] - p_origen[1]) ** 2))
        self.max_width = max(int(width_a), int(width_b))

        height_a = np.sqrt(((p_ymax[0] - p_origen[0]) ** 2) + ((p_ymax[1] - p_origen[1]) ** 2))
        height_b = np.sqrt(((p_xymax[0] - p_xmax[0]) ** 2) + ((p_xymax[1] - p_xmax[1]) ** 2))
        self.max_height = max(int(height_a), int(height_b))

        dst = np.array([[0, 0], [self.max_width - 1, 0], [self.max_width - 1, self.max_height - 1], [0, self.max_height - 1]], dtype="float32")
        self.transform_matrix = cv2.getPerspectiveTransform(rect, dst)
        return True, "Calibración completada. Listo para trazar curvas."

    def start_new_curve(self):
        self.points_clicked_pixels = []
        self.curve_count += 1
        return self.curve_count

    def add_tracing_point(self, point):
        self.points_clicked_pixels.append(point)
        return len(self.points_clicked_pixels)

    def remove_last_tracing_point(self):
        if self.points_clicked_pixels:
            self.points_clicked_pixels.pop()
        return len(self.points_clicked_pixels)

    def can_save_curve(self):
        return len(self.points_clicked_pixels) >= self.min_trace_points

    def add_curve_to_session(self, axis_values, curve_name):
        if not self.can_save_curve():
            return False, f"Se necesitan al menos {self.min_trace_points} puntos."

        if not curve_name:
            curve_name = f"curva_{self.curve_count}"

        try:
            x_min_val = float(axis_values['x_min'])
            x_max_val = float(axis_values['x_max'])
            y_min_val = float(axis_values['y_min'])
            y_max_val = float(axis_values['y_max'])
            is_log_x = bool(axis_values['is_log_x'])
            is_log_y = bool(axis_values['is_log_y'])
        except (ValueError, KeyError) as e:
            return False, f"Error en los valores de los ejes: {e}"

        if is_log_x and (x_min_val <= 0 or x_max_val <= 0):
            return False, "Para el eje X logarítmico, los valores Mínimo y Máximo deben ser positivos."
        if is_log_y and (y_min_val <= 0 or y_max_val <= 0):
            return False, "Para el eje Y logarítmico, los valores Mínimo y Máximo deben ser positivos."

        transformed_points = cv2.perspectiveTransform(np.float32([self.points_clicked_pixels]), self.transform_matrix)[0]
        
        real_coords = []
        for x_pix, y_pix in transformed_points:
            y_pix_inv = self.max_height - y_pix
            
            if is_log_y:
                log_y_min, log_y_max = np.log10(y_min_val), np.log10(y_max_val)
                log_y_val = log_y_min + (y_pix_inv / self.max_height) * (log_y_max - log_y_min)
                y_val = 10**log_y_val
            else:
                y_val = y_min_val + (y_pix_inv / self.max_height) * (y_max_val - y_min_val)

            if is_log_x:
                if x_min_val <= 0: return False, "El valor X Mínimo debe ser > 0 para escala logarítmica."
                log_x_min, log_x_max = np.log10(x_min_val), np.log10(x_max_val)
                log_x_val = log_x_min + (x_pix / self.max_width) * (log_x_max - log_x_min)
                x_val = 10**log_x_val
            else:
                x_val = x_min_val + (x_pix / self.max_width) * (x_max_val - x_min_val)
            
            real_coords.append((x_val, y_val))

        if real_coords:
            last_point = real_coords[-1]
            x_last, y_last = last_point
            x_range, y_range = x_max_val - x_min_val, y_max_val - y_min_val
            x_threshold, y_threshold = 0.05 * x_range, 0.05 * y_range

            if x_max_val - x_last < x_threshold: real_coords.append((x_max_val, y_last))
            elif x_last - x_min_val < x_threshold: real_coords.append((x_min_val, y_last))
            if y_max_val - y_last < y_threshold: real_coords.append((x_last, y_max_val))
            elif y_last - y_min_val < y_threshold: real_coords.append((x_last, y_min_val))

        df_manual = pd.DataFrame(real_coords, columns=['X', 'Y']).sort_values(by='X').drop_duplicates(subset=['X'])
        
        if len(df_manual) < 2: # Se necesitan al menos 2 puntos para interpolar
            return False, f"No hay suficientes puntos únicos ({len(df_manual)}) para interpolar."

        self.session_curves.append({'name': curve_name, 'data': df_manual})
        return True, f"Curva '{curve_name}' añadida a la sesión."

    def save_session_to_file(self, output_path, axis_values):
        if not self.session_curves:
            return False, "No hay curvas en la sesión para guardar."

        try:
            x_min_val = float(axis_values['x_min'])
            x_max_val = float(axis_values['x_max'])
            y_min_val = float(axis_values['y_min'])
            y_max_val = float(axis_values['y_max'])
            is_log_x = bool(axis_values['is_log_x'])
            is_log_y = bool(axis_values['is_log_y'])
        except (ValueError, KeyError) as e:
            return False, f"Error en los valores de los ejes: {e}"

        if is_log_x and (x_min_val <= 0 or x_max_val <= 0):
            return False, "Para el eje X logarítmico, los valores Mínimo y Máximo deben ser positivos."
        if is_log_y and (y_min_val <= 0 or y_max_val <= 0):
            return False, "Para el eje Y logarítmico, los valores Mínimo y Máximo deben ser positivos."

        if is_log_x:
            x_common = np.logspace(np.log10(x_min_val), np.log10(x_max_val), num=500)
        else:
            x_common = np.linspace(x_min_val, x_max_val, num=500)
        
        df_master = pd.DataFrame({'X': x_common})

        for curve in self.session_curves:
            curve_data = curve['data']
            curve_name = curve['name']
            
            # Asegurar suficientes puntos para interpolación cúbica
            kind = 'cubic' if len(curve_data) >= self.min_trace_points else 'linear'
            interp_func = interp1d(curve_data['X'], curve_data['Y'], kind=kind, fill_value="extrapolate")
            
            y_interp = interp_func(x_common)
            
            # Aplicar control de fronteras a los valores 'Y' interpolados
            y_interp_clipped = np.clip(y_interp, y_min_val, y_max_val)
            
            df_master[f'Y_{curve_name}'] = y_interp_clipped

        # El eje X ya está inherentemente dentro de los límites por su generación
        file_extension = os.path.splitext(output_path)[1].lower()

        try:
            if file_extension == '.csv':
                df_master.to_csv(output_path, index=False, float_format='%.4f')
            elif file_extension == '.xlsx':
                df_master.to_excel(output_path, index=False, float_format='%.4f', sheet_name='DatosDigitalizados', engine='openpyxl')
            elif file_extension == '.xls':
                df_master.to_excel(output_path, index=False, float_format='%.4f', sheet_name='DatosDigitalizados', engine='xlwt')
            else:
                return False, f"Formato de fichero no soportado: '{file_extension}'.\nPor favor, seleccione .csv, .xlsx o .xls."

            self.session_curves = []  # Limpiar la sesión después de guardar
            return True, f"Fichero de curvas guardado en:\n{output_path}"
        
        except ImportError as e:
            if 'openpyxl' in str(e).lower():
                return False, "Para guardar como .xlsx, necesita instalar la librería 'openpyxl'.\nUse el comando: pip install openpyxl"
            if 'xlwt' in str(e).lower():
                return False, "Para guardar como .xls, necesita instalar la librería 'xlwt'.\nUse el comando: pip install xlwt"
            return False, f"Error de importación no reconocido: {e}"
        except Exception as e:
            return False, f"Ocurrió un error inesperado al guardar el fichero: {e}"
