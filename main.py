import tkinter as tk
from gui import GraphDigitizerApp
from logic import DigitizerLogic

def main():
    """
    Punto de entrada principal para la aplicación de digitalización de gráficas.
    
    Este script inicializa la lógica de negocio y la interfaz gráfica de usuario,
    y luego inicia el bucle principal de la aplicación.
    """
    # 1. Crear la ventana principal de la aplicación
    root = tk.Tk()

    # 2. Instanciar la lógica de negocio
    logic = DigitizerLogic()

    # 3. Instanciar la GUI, inyectando la lógica
    app = GraphDigitizerApp(root, logic)

    # 4. Iniciar el bucle de eventos de la GUI
    root.mainloop()

if __name__ == "__main__":
    main()
