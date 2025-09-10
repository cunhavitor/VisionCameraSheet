import customtkinter as ctk
from customtkinter import CTkImage
from PIL import Image
import cv2
import os
from picamera2 import Picamera2
from config.config import INSPECTION_PREVIEW_WIDTH, INSPECTION_PREVIEW_HEIGHT

class CaptureSheetWindow(ctk.CTkToplevel):
    def __init__(self, master=None, template_path=None):
        super().__init__(master)
        self.title("Captar Template")
        self.geometry("1200x700")

        self.capturing_live = True  # Se estiver a mostrar live
        self.captured_image = None

        # Frame esquerdo - controles
        self.left_frame = ctk.CTkFrame(self, width=350)
        self.left_frame.pack(side="left", fill="y", padx=10, pady=10)
        self.left_frame.pack_propagate(False)

        self.capture_button = ctk.CTkButton(self.left_frame, text="Capturar Foto", command=self.capture_photo)
        self.capture_button.pack(pady=10)

        self.save_button = ctk.CTkButton(self.left_frame, text="Guardar Foto", command=self.save_photo)
        self.save_button.pack(pady=10)

        self.delete_button = ctk.CTkButton(self.left_frame, text="Eliminar Foto", command=self.delete_photo)
        self.delete_button.pack(pady=10)

        # Frame direito - imagem
        self.right_frame = ctk.CTkFrame(self)
        self.right_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        self.right_frame.pack_propagate(False)

        self.image_label = ctk.CTkLabel(self.right_frame)
        self.image_label.pack(fill="both", expand=True)

        # Inicializa Picamera2
        self.picam2 = Picamera2()
        camera_config = self.picam2.create_still_configuration(main={"size": (3473, 2697)})
        self.picam2.configure(camera_config)
        self.picam2.start()

        self.update_frame()

        # Quando fechar a janela
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def update_frame(self):
        if self.capturing_live:
            frame = self.picam2.capture_array()
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_rgb = cv2.resize(frame_rgb, (INSPECTION_PREVIEW_WIDTH, INSPECTION_PREVIEW_HEIGHT))
            img = Image.fromarray(frame_rgb)
            ctk_img = CTkImage(light_image=img, dark_image=img, size=(INSPECTION_PREVIEW_WIDTH, INSPECTION_PREVIEW_HEIGHT))
            self.image_label.configure(image=ctk_img)
            self.image_label.image = ctk_img  # evita garbage collection
        self.after(30, self.update_frame)  # Atualiza ~30fps

    def capture_photo(self):
        frame = self.picam2.capture_array()
        self.captured_image = frame.copy()
        self.capturing_live = False
        self.show_captured_image()

    def show_captured_image(self):
        if self.captured_image is not None:
            frame_rgb = cv2.cvtColor(self.captured_image, cv2.COLOR_BGR2RGB)
            frame_rgb = cv2.resize(frame_rgb, (INSPECTION_PREVIEW_WIDTH, INSPECTION_PREVIEW_HEIGHT))
            img = Image.fromarray(frame_rgb)
            ctk_img = CTkImage(light_image=img, dark_image=img, size=(INSPECTION_PREVIEW_WIDTH, INSPECTION_PREVIEW_HEIGHT))
            self.image_label.configure(image=ctk_img)
            self.image_label.image = ctk_img

    def delete_photo(self):
        self.captured_image = None
        self.capturing_live = True  # volta ao live

    def save_photo(self):
        if self.captured_image is not None:
            os.makedirs("data/raw", exist_ok=True)
            save_path = "data/raw/fba_template.jpg"
            cv2.imwrite(save_path, self.captured_image)
            print(f"Imagem guardada em {save_path}")

    def on_close(self):
        self.picam2.stop()
        self.destroy()
