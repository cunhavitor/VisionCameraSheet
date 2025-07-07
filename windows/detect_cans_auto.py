import json

import customtkinter as ctk
import cv2
import numpy as np
from PIL import Image, ImageTk

from config.utils import load_params
from widgets.param_entry_simple_numeric import create_param_entry


class AutoDetectCans(ctk.CTkToplevel):
    def __init__(self, parent, image_path):
        super().__init__(parent)
        self.title("Detecção de Latas")
        self.geometry("1200x900")

        self.image_path = image_path
        self.img_cv = cv2.imread(image_path)
        self.canvas_width = 1000
        self.canvas_height = 900

        # parameters adjustable (default values)
        self.param_path = "config/config_auto_detect_cans_params.json"
        params = load_params(self.param_path)

        gaussian = params.get("gaussian", 10)
        treshold1 = params.get("treshold1", 90)
        treshold2 = params.get("treshold2", 10)
        kernell = params.get("kernell", 90)
        area_min = params.get("area_min", 7)
        area_max = params.get("area_max", 30)
        circularity_min = params.get("circularity_min", 120)

        self.gaussian = ctk.IntVar(value=gaussian)
        self.treshold1 = ctk.IntVar(value=treshold1)
        self.treshold2 = ctk.IntVar(value=treshold2)
        self.kernell = ctk.IntVar(value=kernell)
        self.area_min = ctk.IntVar(value=area_min)
        self.area_max = ctk.IntVar(value=area_max)
        self.circularity_min = ctk.IntVar(value=circularity_min)

        self.area_min = ctk.IntVar(value=10)
        self.area_max = ctk.IntVar(value=100000)
        self.circularity_min = ctk.DoubleVar(value=0.1)

        # Layout
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(1, weight=3)

        self.controls_frame = ctk.CTkFrame(self.main_frame)
        self.controls_frame.grid(row=0, column=0, sticky="ns", padx=10, pady=10)

        # Params
        create_param_entry(self.controls_frame, "Gaussian Blur:", self.gaussian, self.update_canvas)
        create_param_entry(self.controls_frame, "treshold1:", self.treshold1, self.update_canvas)
        create_param_entry(self.controls_frame, "treshold2:", self.treshold2, self.update_canvas)
        create_param_entry(self.controls_frame, "kernell:", self.kernell, self.update_canvas)
        create_param_entry(self.controls_frame, "area_min:", self.area_min, self.update_canvas)
        create_param_entry(self.controls_frame, "area_max:", self.area_max, self.update_canvas)
        create_param_entry(self.controls_frame, "circularity_min:", self.circularity_min, self.update_canvas)


        # Botão para atualizar detecção
        self.btn_update = ctk.CTkButton(self.controls_frame, text="Atualizar Detecção", command=self.update_canvas)

        self.btn_update.pack(pady=10)

        self.btn_show_steps = ctk.CTkButton(self.controls_frame, text="Mostrar Etapas",
                                            command=self.mostrar_etapas_processamento)
        self.btn_show_steps.pack(pady=5)

        # Canvas
        self.image_frame = ctk.CTkFrame(self.main_frame)
        self.image_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.canvas = ctk.CTkCanvas(self.image_frame, width=self.canvas_width, height=self.canvas_height)
        self.canvas.pack()
        self.canvas_img = self.canvas.create_image(0, 0, anchor="nw", image=None)


    def validate_int(self, P):
        # P é o novo valor proposto no Entry
        if P == "":
            return True  # permite apagar tudo temporariamente
        try:
            val = int(P)
            return val >= 0  # só valores positivos
        except ValueError:
            return False

    def validate_float(self, P):
        if P == "":
            return True
        try:
            val = float(P)
            return 0.0 <= val <= 1.0  # circularidade no intervalo esperado
        except ValueError:
            return False

    def update_canvas(self):

        try:
            img, latas = self.detectar_latas()
        except Exception:
            return

        output = img.copy()

        for cnt in latas:
            cv2.drawContours(output, [cnt], -1, (0, 255, 0), 2)

        img_rgb = cv2.cvtColor(output, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img_rgb)
        self.tk_img = ImageTk.PhotoImage(img_pil)
        self.canvas.itemconfig(self.canvas_img, image=self.tk_img)

    def detectar_latas(self):
        img = cv2.resize(self.img_cv, (self.canvas_width, self.canvas_height))
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (self.gaussian.get(), self.gaussian.get()), 0)
        edges = cv2.Canny(blurred, self.treshold1.get(), self.treshold2.get())

        # Usar morfologia para separar latas coladas
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (self.kernell.get(), self.kernell.get()))
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

        # Erosão para separar objetos próximos (ajusta o kernel e iterações)
        kernel_erode = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        separated = cv2.erode(closed, kernel_erode, iterations=2)

        contours, _ = cv2.findContours(separated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        detected = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < self.area_min.get() or area > self.area_max.get():
                continue

            if len(cnt) < 5:
                continue  # necessário pelo menos 5 pontos para ellipse

            ellipse = cv2.fitEllipse(cnt)
            (x, y), (MA, ma), angle = ellipse  # MA = major axis, ma = minor axis

            aspect_ratio = min(MA, ma) / max(MA, ma)

            if aspect_ratio < 0.5:  # oval demais, descarta
                continue

            if aspect_ratio > 1.0:  # improvável, mas só para garantir
                continue

            # pode adicionar filtro de circularidade aqui também

            detected.append(cnt)

        return img, detected

    def mostrar_etapas_processamento(self):
        img = cv2.resize(self.img_cv, (self.canvas_width, self.canvas_height))

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)
        edges = cv2.Canny(blurred, 10, 140)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

        # Converte para BGR para empilhar lado a lado
        gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        blurred_bgr = cv2.cvtColor(blurred, cv2.COLOR_GRAY2BGR)
        edges_bgr = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        closed_bgr = cv2.cvtColor(closed, cv2.COLOR_GRAY2BGR)

        # Redimensiona para evitar janela gigante
        width = 400
        gray_bgr = cv2.resize(gray_bgr, (width, 300))
        blurred_bgr = cv2.resize(blurred_bgr, (width, 300))
        edges_bgr = cv2.resize(edges_bgr, (width, 300))
        closed_bgr = cv2.resize(closed_bgr, (width, 300))

        resultado = np.hstack((gray_bgr, blurred_bgr, edges_bgr, closed_bgr))

        cv2.imshow("Etapas do Processamento (Gray → Blur → Canny → Morph)", resultado)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        self._save_params()

    def _save_params(self):
        params = {
            "gaussian": self.gaussian.get(),
            "treshold1": self.treshold1.get(),
            "treshold2": self.treshold2.get(),
            "kernell": self.kernell.get(),
            "area_min": self.area_min.get(),
            "area_max": self.area_max.get(),
            "circularity_min": self.circularity_min.get()
        }
        with open(self.param_path, "w") as f:
            json.dump(params, f, indent=4)