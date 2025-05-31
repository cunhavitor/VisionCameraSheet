from PIL import Image, ImageDraw, ImageTk
import customtkinter as ctk
from customtkinter import CTkLabel, CTkButton
from config.config import TEMPLATE_IMAGE_PATH


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

        self.btn_definir_area = CTkButton(self.left_frame, text="Definir área folha",
                                          command=self.ativar_definir_area)
        self.btn_definir_area.pack(pady=20, fill="x")

        self.btn_definir_area = CTkButton(self.left_frame, text="Gravar",
                                          command=self.salvar_coords)
        self.btn_definir_area.pack(pady=20, fill="x")

        self.status_label = ctk.CTkLabel(self.left_frame, text="Modo normal", wraplength=130, justify="left")
        self.status_label.pack(pady=10, fill="x")


        # Frame de imagem
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
        self.scaled_image = self.original_image.resize((self.scaled_img_width, self.scaled_img_height), Image.Resampling.NEAREST)
        self.tk_image = ImageTk.PhotoImage(self.scaled_image)

    def ativar_definir_area(self):
        self.definir_area_ativa = True
        self.coords.clear()
        self.status_label.configure(text="Modo definir área: clique para definir pontos")
        self.image_label.configure(cursor="crosshair")
        self.atualizar_imagem_com_pontos()

    def on_click(self, event):
        if self.definir_area_ativa:
            original_x = int(event.x / self.scale_factor)
            original_y = int(event.y / self.scale_factor)

            self.coords.append((original_x, original_y))
            print(f"event.x={event.x}, event.y={event.y}")
            print(f"scale_factor={self.scale_factor}")
            print(f"Ponto guardado (original coords): ({original_x}, {original_y})")

            self.status_label.configure(text=f"Pontos guardados: {len(self.coords)}")
            self.atualizar_imagem_com_pontos()

    def atualizar_imagem_com_pontos(self):
        img_copy = self.original_image.copy()
        draw = ImageDraw.Draw(img_copy)
        radius = 7

        if len(self.coords) > 0:
            prev_x, prev_y = self.coords[0]
            # Desenha o primeiro ponto
            draw.ellipse([(prev_x - radius, prev_y - radius), (prev_x + radius, prev_y + radius)],
                         fill="red", outline="red")
            print(f"Desenhar ponto na original: ({prev_x}, {prev_y})")

            # Itera a partir do segundo ponto
            for x, y in self.coords[1:]:
                # Desenha linha do anterior para o atual
                draw.line([(prev_x, prev_y), (x, y)], fill="red", width=4)

                # Desenha o ponto atual
                draw.ellipse([(x - radius, y - radius), (x + radius, y + radius)],
                             fill="red", outline="red")
                print(f"Desenhar ponto na original: ({x}, {y})")

                # Atualiza o ponto anterior
                prev_x, prev_y = x, y

        # Atualizar imagem ampliada
        self.scaled_image = img_copy.resize((self.scaled_img_width, self.scaled_img_height), Image.Resampling.NEAREST)
        self.tk_image = ImageTk.PhotoImage(self.scaled_image)
        self.image_label.configure(image=self.tk_image)
        self.image_label.image = self.tk_image

    def salvar_coords(self, path="mask_coords.txt"):
        with open(path, "w") as f:
            for x, y in self.coords:
                f.write(f"{x},{y}\n")
        print(f"Coordenadas guardadas em {path}")

    def destroy(self):

        super().destroy()
