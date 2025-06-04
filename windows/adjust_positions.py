import json
import os
import re

from PIL import Image, ImageDraw, ImageFont, ImageTk
import customtkinter as ctk
from customtkinter import CTkLabel, CTkButton
from config.config import TEMPLATE_IMAGE_PATH

CONFIG_PATH = "config/config_positions.json"


class AdjustPositionsWindow(ctk.CTkToplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("Ajustar Máscara")

        self.definir_area_ativa = False
        self.coords = []
        self.scale_factor = 0.2

        # Carrega a imagem original
        self.original_image = Image.open(TEMPLATE_IMAGE_PATH)
        self.original_img_width, self.original_img_height = self.original_image.size

        # Cria imagem ampliada
        self.zoom_image(self.scale_factor)

        self.geometry(f"{self.scaled_img_width + 200}x{self.scaled_img_height + 100}")

        # Frame lateral
        self.left_frame = ctk.CTkFrame(self, width=150)
        self.left_frame.pack(side="left", fill="y", padx=10, pady=10)
        self.left_frame.pack_propagate(False)

        self.toggle_definir_area = ctk.CTkCheckBox(
            self.left_frame,
            text="Modo definir Posições",
            command=self.toggle_definir_area_modo
        )
        self.toggle_definir_area.pack(pady=20, fill="x")

        self.status_label = ctk.CTkLabel(self.left_frame, text="Modo normal", wraplength=130, justify="left")
        self.status_label.pack(pady=10, fill="x")

        # Carrega configuração existente
        config_data = self.load_config()

        # Variáveis configuráveis
        self.latas_x_var = ctk.IntVar(value=config_data.get("latas_x", 10))
        self.latas_y_var = ctk.IntVar(value=config_data.get("latas_y", 6))
        self.passo_x_var = ctk.DoubleVar(value=config_data.get("passo_x", 50.0))
        self.half_passo_x_var = ctk.DoubleVar(value=config_data.get("half_passo_x", 25.0))
        self.passo_y_var = ctk.DoubleVar(value=config_data.get("passo_y", 40.0))

        for var in [self.latas_x_var, self.latas_y_var, self.passo_x_var, self.half_passo_x_var, self.passo_y_var]:
            var.trace_add("write", lambda *args: self.salvar_config_alignment())

        # Validação de entradas
        def only_int(char):
            return char.isdigit() or char == ""

        def only_float(char, current):
            new_text = current + char
            if char == "":
                return True
            return re.match(r"^\d*\.?\d*$", new_text) is not None

        vcmd_int = (self.register(only_int), "%S")
        vcmd_float = (self.register(only_float), "%S", "%P")

        # Criação de campos de entrada para parâmetros
        self.criar_entry(self.left_frame, "Latas X:", self.latas_x_var, vcmd_int)
        self.criar_entry(self.left_frame, "Latas Y:", self.latas_y_var, vcmd_int)
        self.criar_entry(self.left_frame, "Passo X:", self.passo_x_var, vcmd_float)
        self.criar_entry(self.left_frame, "1/2 Passo X:", self.half_passo_x_var, vcmd_float)
        self.criar_entry(self.left_frame, "Passo Y:", self.passo_y_var, vcmd_float)

        # Botões de ação
        self.btn_clean_polygon = CTkButton(self.left_frame, text="Limpar Polígonos", command=self.clean_polygons)
        self.btn_clean_polygon.pack(pady=20, fill="x")

        self.btn_gerar_matriz = CTkButton(self.left_frame, text="Gerar Matriz", command=self.gerar_matriz_pontos)
        self.btn_gerar_matriz.pack(pady=20, fill="x")

        self.btn_definir_area = CTkButton(self.left_frame, text="Gravar", command=self.salvar_coords)
        self.btn_definir_area.pack(pady=20, fill="x")

        # Frame de visualização da imagem
        self.preview_frame = ctk.CTkFrame(self, width=self.scaled_img_width, height=self.scaled_img_height)
        self.preview_frame.pack(side="left", padx=10, pady=10)
        self.preview_frame.pack_propagate(False)

        self.image_label = CTkLabel(self.preview_frame, image=self.tk_image, text="")
        self.image_label.image = self.tk_image
        self.image_label.pack()
        self.image_label.bind("<Button-1>", self.on_click)

    def criar_entry(self, parent, label, var, validatecommand):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=(10, 0))
        ctk.CTkLabel(frame, text=label, width=80).pack(side="left", padx=(0, 5))
        entry = ctk.CTkEntry(frame, textvariable=var, fg_color="white", text_color="black",
                             validate="key", validatecommand=validatecommand)
        entry.pack(side="left", fill="x", expand=True)

    def load_config(self):
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r") as f:
                return json.load(f)
        return {}

    def save_config(self, data):
        with open(CONFIG_PATH, "w") as f:
            json.dump(data, f, indent=4)

    def salvar_config_alignment(self):
        data = {
            "latas_x": self.latas_x_var.get(),
            "latas_y": self.latas_y_var.get(),
            "passo_x": self.passo_x_var.get(),
            "half_passo_x": self.half_passo_x_var.get(),
            "passo_y": self.passo_y_var.get()
        }
        self.save_config(data)

    def zoom_image(self, factor):
        self.scale_factor = factor
        self.scaled_img_width = int(self.original_img_width * factor)
        self.scaled_img_height = int(self.original_img_height * factor)
        self.scaled_image = self.original_image.resize(
            (self.scaled_img_width, self.scaled_img_height), Image.Resampling.NEAREST)
        self.tk_image = ImageTk.PhotoImage(self.scaled_image)

    def toggle_definir_area_modo(self):
        self.definir_area_ativa = self.toggle_definir_area.get() == 1
        if self.definir_area_ativa:
            self.coords.clear()
            self.status_label.configure(text="Modo definir área: clique para definir pontos")
            self.image_label.configure(cursor="crosshair")
        else:
            self.status_label.configure(text="Modo normal")
            self.image_label.configure(cursor="arrow")
        self.atualizar_imagem_com_pontos()

    def on_click(self, event):
        if self.definir_area_ativa:
            original_x = int(event.x / self.scale_factor)
            original_y = int(event.y / self.scale_factor)
            self.coords.append((original_x, original_y))
            self.status_label.configure(text=f"Pontos guardados: {len(self.coords)}")
            self.atualizar_imagem_com_pontos()

    def atualizar_imagem_com_pontos(self):
        img_copy = self.original_image.copy()
        draw = ImageDraw.Draw(img_copy)
        radius = 7
        if self.coords:
            prev = self.coords[0]
            draw.ellipse([(prev[0] - radius, prev[1] - radius), (prev[0] + radius, prev[1] + radius)],
                         fill="red", outline="red")
            for curr in self.coords[1:]:
                draw.line([prev, curr], fill="red", width=4)
                draw.ellipse([(curr[0] - radius, curr[1] - radius), (curr[0] + radius, curr[1] + radius)],
                             fill="red", outline="red")
                prev = curr
            if len(self.coords) > 2:
                draw.line([self.coords[-1], self.coords[0]], fill="red", width=4)

        self.scaled_image = img_copy.resize((self.scaled_img_width, self.scaled_img_height), Image.Resampling.NEAREST)
        self.tk_image = ImageTk.PhotoImage(self.scaled_image)
        self.image_label.configure(image=self.tk_image)
        self.image_label.image = self.tk_image

    def gerar_matriz_pontos(self):
        if not self.coords:
            return []

        matriz = []
        img_copy = self.original_image.copy()
        draw = ImageDraw.Draw(img_copy)
        radius = 7

        for iy in range(int(self.latas_y_var.get())):
            offset_x = float(self.half_passo_x_var.get()) if iy % 2 == 1 else 0

            # Cria uma lista temporária para armazenar polígonos da linha atual
            linha_poligonos = []

            for ix in range(int(self.latas_x_var.get())):
                dx = ix * float(self.passo_x_var.get()) + offset_x
                dy = iy * float(self.passo_y_var.get())
                deslocado = [(x + dx, y + dy) for x, y in self.coords]
                linha_poligonos.append(deslocado)

            # Agora desenhe os polígonos da linha, numerando normalmente
            for deslocado in linha_poligonos:
                matriz.append(deslocado)

                # Desenhar círculo e linhas do polígono
                prev = deslocado[0]
                draw.ellipse([(prev[0] - radius, prev[1] - radius), (prev[0] + radius, prev[1] + radius)],
                             fill="red", outline="red")
                for curr in deslocado[1:]:
                    draw.line([prev, curr], fill="red", width=4)
                    draw.ellipse([(curr[0] - radius, curr[1] - radius), (curr[0] + radius, curr[1] + radius)],
                                 fill="red", outline="red")
                    prev = curr
                if len(deslocado) > 2:
                    draw.line([deslocado[-1], deslocado[0]], fill="red", width=4)

                # Calcular centroide para posicionar o número
                xs = [p[0] for p in deslocado]
                ys = [p[1] for p in deslocado]
                centroide_x = sum(xs) / len(xs)
                centroide_y = sum(ys) / len(ys)


        self.scaled_image = img_copy.resize((self.scaled_img_width, self.scaled_img_height), Image.Resampling.NEAREST)
        self.tk_image = ImageTk.PhotoImage(self.scaled_image)
        self.image_label.configure(image=self.tk_image)
        self.image_label.image = self.tk_image

        return matriz

    def clean_polygons(self):
        self.coords.clear()
        self.definir_area_ativa = False
        self.status_label.configure(text="Modo normal")
        self.image_label.configure(cursor="arrow")
        self.zoom_image(self.scale_factor)
        self.image_label.configure(image=self.tk_image)
        self.image_label.image = self.tk_image

    def salvar_coords(self):
        matriz = self.gerar_matriz_pontos()
        if matriz:
            with open("coords_matriz.txt", "w") as f:
                for poly in matriz:
                    f.write(";".join(f"{int(x)},{int(y)}" for x, y in poly) + "\n")
            print("Polígonos salvos em coords_matriz.txt")

    def destroy(self):
        super().destroy()