import json

import customtkinter as ctk
import cv2
import numpy as np
from PIL import Image, ImageTk

from config.utils import load_params
from widgets.param_entry_simple_numeric import create_param_entry

class CameraAdjustPosition(ctk.CTkToplevel):
    def __init__(self, parent, image_path):
        super().__init__(parent)
        self.title("Verificação do Ângulo da Câmara")
        self.geometry("1600x900")

        self.image_path = image_path
        self.img_cv = cv2.imread(image_path)
        self.points = []

        self.canvas_width = 1000
        self.canvas_height = 900

        # Layout principal
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, minsize=500)
        self.main_frame.grid_columnconfigure(1, weight=1)

        self.button_frame = ctk.CTkFrame(self.main_frame)
        self.button_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.button_frame.grid_propagate(True)

        self.check_button = ctk.CTkButton(self.button_frame, text="Verificar Perspectiva",
                                          command=self._verificar_alinhamento)
        self.check_button.pack(pady=5)

        # parameters adjustable (default values)
        self.param_path = "config/config_lines_align_camera.json"
        params = load_params(self.param_path)

        line_top = params.get("line_top", 10)
        line_bottom = params.get("line_bottom", 90)
        line_left = params.get("line_left", 10)
        line_right = params.get("line_right", 90)
        gaussian_blur = params.get("gaussian_blur", 7)
        canny_threshold1= params.get("canny_threshold1", 30)
        canny_threshold2 = params.get("canny_threshold2", 120)

        self.line_top = ctk.IntVar(value=line_top)
        self.line_bottom = ctk.IntVar(value=line_bottom)
        self.line_left = ctk.IntVar(value=line_left)
        self.line_right = ctk.IntVar(value=line_right)

        self.gaussian_blur = ctk.IntVar(value=gaussian_blur)
        self.canny_threshold1 = ctk.IntVar(value=canny_threshold1)
        self.canny_threshold2 = ctk.IntVar(value=canny_threshold2)

        self.slider_top = create_param_entry(self.button_frame, "Linha Topo:", self.line_top, self._verificar_alinhamento)
        self.slider_bottom = create_param_entry(self.button_frame, "Linha Fundo:", self.line_bottom,
                                                self._verificar_alinhamento)
        self.slider_left = create_param_entry(self.button_frame, "Linha Esquerda:", self.line_left, self._verificar_alinhamento)
        self.slider_right = create_param_entry(self.button_frame, "Linha Direita:", self.line_right,
                                               self._verificar_alinhamento)

        create_param_entry(self.button_frame, "Gaussian Blur:", self.gaussian_blur, self._verificar_alinhamento)
        create_param_entry(self.button_frame, "Canny Threshold 1:", self.canny_threshold1, self._verificar_alinhamento)
        create_param_entry(self.button_frame, "Canny Threshold 2:", self.canny_threshold2, self._verificar_alinhamento)

        self.textbox = ctk.CTkTextbox(self.button_frame)
        self.textbox.pack(padx=10, pady=10, fill="both", expand=True)

        # Variáveis para linhas ajustadas automaticamente (azuis)
        self.auto_line_top = self.line_top.get()
        self.auto_line_bottom = self.line_bottom.get()
        self.auto_line_left = self.line_left.get()
        self.auto_line_right = self.line_right.get()


        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.pack(pady=5)

        self.image_frame = ctk.CTkFrame(self.main_frame)
        self.image_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.image_frame.grid_propagate(False)

        self.canvas = ctk.CTkCanvas(self.image_frame, width=self.canvas_width, height=self.canvas_height)
        self.canvas.pack(pady=10)

        # Captura da câmera
        #self.cap = cv2.VideoCapture(0)  # Usa a primeira câmera (ID 0)

        self.canvas_img = self.canvas.create_image(0, 0, anchor="nw", image=None)

        # Inicia o loop da câmera
        self._verificar_alinhamento()

    def _update_camera(self, *args):
        print("valor atualizado")
        frame = cv2.resize(self.img_cv, (self.canvas_width, self.canvas_height))

        # linhas verdes - sliders
        line_top = int(self.canvas_height * (self.line_top.get() / 100))
        line_bottom = int(self.canvas_height * (self.line_bottom.get() / 100))
        line_left = int(self.canvas_width * (self.line_left.get() / 100))
        line_right = int(self.canvas_width * (self.line_right.get() / 100))

        cv2.line(frame, (0, line_top), (self.canvas_width, line_top), (255, 0, 0), 2)
        cv2.line(frame, (0, line_bottom), (self.canvas_width, line_bottom), (255, 0, 0), 2)
        cv2.line(frame, (line_left, 0), (line_left, self.canvas_height), (255, 0, 0), 2)
        cv2.line(frame, (line_right, 0), (line_right, self.canvas_height), (255, 0, 0), 2)

        # linhas azuis - ajustadas automaticamente
        auto_top = int(self.canvas_height * (self.auto_line_top / 100))
        auto_bottom = int(self.canvas_height * (self.auto_line_bottom / 100))
        auto_left = int(self.canvas_width * (self.auto_line_left / 100))
        auto_right = int(self.canvas_width * (self.auto_line_right / 100))

        cv2.line(frame, (0, auto_top), (self.canvas_width, auto_top), (255, 0, 0), 2)
        cv2.line(frame, (0, auto_bottom), (self.canvas_width, auto_bottom), (255, 0, 0), 2)
        cv2.line(frame, (auto_left, 0), (auto_left, self.canvas_height), (255, 0, 0), 2)
        cv2.line(frame, (auto_right, 0), (auto_right, self.canvas_height), (255, 0, 0), 2)

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(frame_rgb)
        self.tk_img = ImageTk.PhotoImage(img_pil)
        self.canvas.itemconfig(self.canvas_img, image=self.tk_img)

        self._save_params()

        # self.after(100, self._update_camera)

        # Usar imagem real time
        '''ret, frame = self.cap.read()
        if ret:
            frame = cv2.resize(frame, (self.canvas_width, self.canvas_height))

            # Desenha as linhas diretamente sobre o frame ao vivo
            line_top = int(self.canvas_height * (self.line_top.get() / 100))
            line_bottom = int(self.canvas_height * (self.line_bottom.get() / 100))
            line_left = int(self.canvas_width * (self.line_left.get() / 100))
            line_right = int(self.canvas_width * (self.line_right.get() / 100))

            # Desenhar linhas
            cv2.line(frame, (0, line_top), (self.canvas_width, line_top), (0, 255, 0), 2)
            cv2.line(frame, (0, line_bottom), (self.canvas_width, line_bottom), (0, 255, 0), 2)
            cv2.line(frame, (line_left, 0), (line_left, self.canvas_height), (0, 255, 0), 2)
            cv2.line(frame, (line_right, 0), (line_right, self.canvas_height), (0, 255, 0), 2)

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(frame_rgb)
            self.tk_img = ImageTk.PhotoImage(img_pil)
            self.canvas.itemconfig(self.canvas_img, image=self.tk_img)

            self._save_params()

        self.after(30, self._update_camera)'''

    def _verificar_alinhamento(self):
        self.textbox.delete("0.0", "end")

        k = self.gaussian_blur.get()
        if k % 2 == 0:
            k += 1
        if k < 3:
            k = 3

        frame = cv2.resize(self.img_cv, (self.canvas_width, self.canvas_height)).copy()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (k, k), 0)
        edges = cv2.Canny(blurred, self.canny_threshold1.get(), self.canny_threshold2.get())

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

        cv2.imwrite("debug_edges.jpg", edges)

        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            print("⚠️ Nenhuma borda detectada")
            self.textbox.insert("end", "⚠️ Nenhuma borda detectada\n")

            return

        filtered_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > 50]
        if not filtered_contours:
            print("⚠️ Nenhum contorno válido encontrado")
            self.textbox.insert("end", "⚠️ Nenhum contorno válido encontrado\n")
            return

        largest_contour = max(filtered_contours, key=cv2.contourArea)
        print(f"Área do maior contorno: {cv2.contourArea(largest_contour):.2f}")

        all_points = np.vstack(filtered_contours)
        rect = cv2.minAreaRect(all_points)
        box = cv2.boxPoints(rect).astype(int)

        folha_mask = np.zeros((self.canvas_height, self.canvas_width), dtype=np.uint8)
        cv2.drawContours(folha_mask, [box], -1, 255, -1)

        xs = box[:, 0]
        ys = box[:, 1]
        left_pct = int((xs.min() / self.canvas_width) * 100)
        right_pct = int((xs.max() / self.canvas_width) * 100)
        top_pct = int((ys.min() / self.canvas_height) * 100)
        bottom_pct = int((ys.max() / self.canvas_height) * 100)

        print(
            f"📐 Linhas ajustadas automaticamente: Topo={top_pct}%, Fundo={bottom_pct}%, Esquerda={left_pct}%, Direita={right_pct}%")
        self.textbox.insert("end", f"📐 Linhas ajustadas automaticamente: Topo={top_pct}%, Fundo={bottom_pct}%, Esquerda={left_pct}%, Direita={right_pct}%\n")
        self.auto_line_top = top_pct
        self.auto_line_bottom = bottom_pct
        self.auto_line_left = left_pct
        self.auto_line_right = right_pct


        roi_mask = np.zeros_like(folha_mask)
        top = int(self.canvas_height * (self.line_top.get() / 100))
        bottom = int(self.canvas_height * (self.line_bottom.get() / 100))
        left = int(self.canvas_width * (self.line_left.get() / 100))
        right = int(self.canvas_width * (self.line_right.get() / 100))
        roi_mask[top:bottom, left:right] = 255

        intersection = cv2.bitwise_and(folha_mask, roi_mask)
        inside_area = cv2.countNonZero(intersection)
        folha_area = cv2.countNonZero(folha_mask)

        if folha_area == 0:
            print("⚠️ A folha não foi detectada corretamente.")
            self.textbox.insert("⚠️ A folha não foi detectada corretamente.\n")
            return

        percentage_inside = (inside_area / folha_area) * 100
        print(f"📊 Percentagem da folha dentro da área: {percentage_inside:.2f}%")
        self.textbox.insert("end",f"📊 Percentagem da folha dentro da área: {percentage_inside:.2f}%.\n")

        output_frame = frame.copy()

        # Desenhar linhas azuis baseadas nos valores atuais dos sliders
        line_top = int(self.canvas_height * (self.line_top.get() / 100))
        line_bottom = int(self.canvas_height * (self.line_bottom.get() / 100))
        line_left = int(self.canvas_width * (self.line_left.get() / 100))
        line_right = int(self.canvas_width * (self.line_right.get() / 100))

        cv2.line(output_frame, (0, line_top), (self.canvas_width, line_top), (255, 0, 0), 2)  # Linha Topo - azul
        cv2.line(output_frame, (0, line_bottom), (self.canvas_width, line_bottom), (255, 0, 0), 2)  # Linha Fundo - azul
        cv2.line(output_frame, (line_left, 0), (line_left, self.canvas_height), (255, 0, 0), 2)  # Linha Esquerda - azul
        cv2.line(output_frame, (line_right, 0), (line_right, self.canvas_height), (255, 0, 0),
                 2)  # Linha Direita - azul

        # desenhar o maior contorno a verde
        cv2.drawContours(output_frame, [largest_contour], -1, (0, 255, 0), 2)

        # desenhar a caixa do contorno
        hull = cv2.convexHull(largest_contour)
        points = hull.reshape(-1, 2)

        for i in range(len(points)):
            pt1 = tuple(points[i])
            pt2 = tuple(points[(i + 1) % len(points)])
            cv2.line(output_frame, pt1, pt2, (0, 0, 255), 2)



        # --- Cálculo dos ângulos usando tolerância ---
        tol = 5  # pixels, ajustar se necessário
        min_y = np.min(points[:, 1])
        max_y = np.max(points[:, 1])

        top_points = points[np.abs(points[:, 1] - min_y) < tol]
        bottom_points = points[np.abs(points[:, 1] - max_y) < tol]

        top_left = top_points[np.argmin(top_points[:, 0])]
        top_right = top_points[np.argmax(top_points[:, 0])]
        bottom_left = bottom_points[np.argmin(bottom_points[:, 0])]
        bottom_right = bottom_points[np.argmax(bottom_points[:, 0])]

        angulo_top = self.calcular_angulo(top_left, top_right)
        angulo_bottom = self.calcular_angulo(bottom_left, bottom_right)

        print(f"Ângulo linha de cima: {angulo_top:.2f}°")
        self.textbox.insert("end",f"Ângulo linha de cima: {angulo_top:.2f}°\n")
        print(f"Ângulo linha de baixo: {angulo_bottom:.2f}°")
        self.textbox.insert("end",f"Ângulo linha de baixo: {angulo_bottom:.2f}°\n")

        output_rgb = cv2.cvtColor(output_frame, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(output_rgb)
        self.tk_img = ImageTk.PhotoImage(img_pil)
        self.canvas.itemconfig(self.canvas_img, image=self.tk_img)

        self._save_params()

    def calcular_angulo(self, p1, p2):
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        angle_rad = np.arctan2(dy, dx)
        angle_deg = np.degrees(angle_rad)
        if angle_deg < -90:
            angle_deg += 180
        elif angle_deg > 90:
            angle_deg -= 180
        return angle_deg

    def _save_params(self):
        params = {
            "line_top": self.line_top.get(),
            "line_bottom": self.line_bottom.get(),
            "line_left": self.line_left.get(),
            "line_right": self.line_right.get(),
            "gaussian_blur": self.gaussian_blur.get(),
            "canny_threshold1": self.canny_threshold1.get(),
            "canny_threshold2": self.canny_threshold2.get()
        }
        with open(self.param_path, "w") as f:
            json.dump(params, f, indent=4)