
import os

from PIL import Image, ImageDraw, ImageTk
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
        self.coord_por_lata = {}
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
        self.toggle_definir_area.pack(pady=10, fill="x")

        self.status_label = ctk.CTkLabel(self.left_frame, text="Modo normal", wraplength=130, justify="left")
        self.status_label.pack(pady=5, fill="x")

        self.lata_entry = ctk.CTkEntry(self.left_frame, placeholder_text="Número da lata")
        self.lata_entry.pack(pady=5, fill="x")

        self.btn_gravar_lata = CTkButton(self.left_frame, text="Guardar Lata", command=self.salvar_coords)
        self.btn_gravar_lata.pack(pady=5, fill="x")

        self.btn_gerar_mask = CTkButton(self.left_frame, text="Gerar Máscara", command=self.gerar_mascara)
        self.btn_gerar_mask.pack(pady=5, fill="x")

        self.btn_clean_polygon = CTkButton(self.left_frame, text="Limpar Polígono", command=self.clean_polygons)
        self.btn_clean_polygon.pack(pady=5, fill="x")

        # Frame de visualização da imagem
        self.preview_frame = ctk.CTkFrame(self, width=self.scaled_img_width, height=self.scaled_img_height)
        self.preview_frame.pack(side="left", padx=10, pady=10)
        self.preview_frame.pack_propagate(False)

        self.image_label = CTkLabel(self.preview_frame, image=self.tk_image, text="")
        self.image_label.image = self.tk_image
        self.image_label.pack()
        self.image_label.bind("<Button-1>", self.on_click)

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
        for nome, pontos in self.coord_por_lata.items():
            prev = pontos[0]
            draw.ellipse([(prev[0] - radius, prev[1] - radius), (prev[0] + radius, prev[1] + radius)],
                         fill="blue", outline="blue")
            for curr in pontos[1:]:
                draw.line([prev, curr], fill="blue", width=3)
                draw.ellipse([(curr[0] - radius, curr[1] - radius), (curr[0] + radius, curr[1] + radius)],
                             fill="blue", outline="blue")
                prev = curr
            draw.line([pontos[-1], pontos[0]], fill="blue", width=3)

        if self.coords:
            prev = self.coords[0]
            draw.ellipse([(prev[0] - radius, prev[1] - radius), (prev[0] + radius, prev[1] + radius)],
                         fill="red", outline="red")
            for curr in self.coords[1:]:
                draw.line([prev, curr], fill="red", width=3)
                draw.ellipse([(curr[0] - radius, curr[1] - radius), (curr[0] + radius, curr[1] + radius)],
                             fill="red", outline="red")
                prev = curr
            draw.line([self.coords[-1], self.coords[0]], fill="red", width=3)

        self.scaled_image = img_copy.resize((self.scaled_img_width, self.scaled_img_height), Image.Resampling.NEAREST)
        self.tk_image = ImageTk.PhotoImage(self.scaled_image)
        self.image_label.configure(image=self.tk_image)
        self.image_label.image = self.tk_image

    def salvar_coords(self):
        nome_lata = self.lata_entry.get().strip()
        if not nome_lata:
            self.status_label.configure(text="⚠️ Digite o número da lata antes de salvar.")
            return
        if not self.coords:
            self.status_label.configure(text="⚠️ Nenhum ponto definido para salvar.")
            return

        self.coord_por_lata[nome_lata] = list(self.coords)
        self.coords.clear()
        self.lata_entry.delete(0, 'end')
        self.status_label.configure(text=f"✅ Lata '{nome_lata}' salva.")
        self.atualizar_imagem_com_pontos()

        with open("data/mask/coords_individuais.txt", "w") as f:
            for nome, pontos in self.coord_por_lata.items():
                f.write(f"{nome}:" + ";".join(f"{int(x)},{int(y)}" for x, y in pontos) + "\n")

    def gerar_mascara(self):
        mask = Image.new("L", (self.original_img_width, self.original_img_height), 0)
        draw = ImageDraw.Draw(mask)

        for pontos in self.coord_por_lata.values():
            draw.polygon(pontos, fill=255)

        os.makedirs("data/mask", exist_ok=True)
        mask.save("data/mask/leaf_mask.png")
        self.status_label.configure(text="✅ Máscara gerada com sucesso.")

        with open("data/mask/coords_matriz.txt", "w") as f:
            for nome, pontos in self.coord_por_lata.items():
                f.write(f"{nome}:" + ";".join(f"{int(x)},{int(y)}" for x, y in pontos) + "\n")

    def clean_polygons(self):
        self.coords.clear()
        self.atualizar_imagem_com_pontos()

    def destroy(self):
        super().destroy()

