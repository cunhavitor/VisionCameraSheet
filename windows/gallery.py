import os
import customtkinter as ctk
from PIL import Image
from customtkinter import CTkImage
from config.config import PREVIEW_WIDTH, PREVIEW_HEIGHT, TEMPLATE_IMAGE_PATH

class GalleryWindow(ctk.CTkToplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("Galeria de Imagens")
        self.geometry("800x600")

        self.image_folder = "data/raw"
        self.selected_image_path = None

        # Usar CTkScrollableFrame para lista de imagens com scroll
        self.list_frame = ctk.CTkScrollableFrame(self, width=200)
        self.list_frame.pack(side="left", fill="y", padx=10, pady=10)

        # Lista de botões para cada imagem
        self.image_buttons = []

        # Frame para mostrar a imagem selecionada
        self.preview_frame = ctk.CTkFrame(self)
        self.preview_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        self.image_label = ctk.CTkLabel(self.preview_frame, text="Selecione uma imagem")
        self.image_label.pack(expand=True)

        self.load_images()

    def load_images(self):
        self.image_buttons.clear()

        files = sorted(os.listdir(self.image_folder))
        image_files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

        for widget in self.list_frame.winfo_children():
            widget.destroy()

        for img_file in image_files:
            lbl = ctk.CTkLabel(self.list_frame, text=img_file, width=180, cursor="hand2", anchor="w")
            lbl.pack(pady=5, fill="x")
            lbl.bind("<Button-1>", lambda e, f=img_file: self.show_image(f))
            self.image_buttons.append(lbl)

    def show_image(self, filename):
        path = os.path.join(self.image_folder, filename)
        self.selected_image_path = path

        pil_image = Image.open(path)
        pil_image = pil_image.resize((self.preview_frame.winfo_width() - 20,
                                      self.preview_frame.winfo_height() - 20), Image.Resampling.LANCZOS)
        ctk_img = CTkImage(light_image=pil_image, dark_image=pil_image, size=pil_image.size)
        self.image_label.configure(image=ctk_img, text="")
        self.image_label.image = ctk_img
