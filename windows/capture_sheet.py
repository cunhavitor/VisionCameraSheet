import customtkinter as ctk
from customtkinter import CTkImage
from PIL import Image
import cv2
import os

from config.config import INSPECTION_PREVIEW_WIDTH, INSPECTION_PREVIEW_HEIGHT


class CaptureSheetWindow(ctk.CTkToplevel):
    def __init__(self, master=None, template_path=None):
        super().__init__(master)
        self.title("Captar Template")
        self.geometry("1200x700")

        self.capturing = False
        self.captured_image = None

        # Frame esquerdo - controles
        self.left_frame = ctk.CTkFrame(self, width=350)
        self.left_frame.pack(side="left", fill="y", padx=10, pady=10)
        self.left_frame.pack_propagate(False)

        self.capture_button = ctk.CTkButton(self.left_frame, text="Capturar Foto", command=self.capture_photo)
        self.capture_button.pack(pady=10)

        self.save_button = ctk.CTkButton(self.left_frame, text="Guardar Foto", command=self.save_photo)
        self.save_button.pack(pady=10)

        # Frame direito - imagem
        self.right_frame = ctk.CTkFrame(self)
        self.right_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        self.right_frame.pack_propagate(False)

        self.image_label = ctk.CTkLabel(self.right_frame)
        self.image_label.pack(fill="both", expand=True)

        # Inicializa captura da IMX477
        self.cap = cv2.VideoCapture(0)  # Ajustar se necessário
        self.capturing = True
        self.update_frame()

    def update_frame(self):
        if self.capturing:
            ret, frame = self.cap.read()
            if ret:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_rgb = cv2.resize(frame_rgb, (INSPECTION_PREVIEW_WIDTH, INSPECTION_PREVIEW_HEIGHT))
                img = Image.fromarray(frame_rgb)
                ctk_img = CTkImage(light_image=img, dark_image=img, size=(INSPECTION_PREVIEW_WIDTH, INSPECTION_PREVIEW_HEIGHT))
                self.image_label.configure(image=ctk_img)
                self.image_label.image = ctk_img  # evita garbage collection
        self.after(30, self.update_frame)  # Atualiza ~30fps

    def capture_photo(self):
        ret, frame = self.cap.read()
        if ret:
            self.captured_image = frame.copy()
            # Mostra a imagem capturada
            frame_rgb = cv2.cvtColor(self.captured_image, cv2.COLOR_BGR2RGB)
            frame_rgb = cv2.resize(frame_rgb, (INSPECTION_PREVIEW_WIDTH, INSPECTION_PREVIEW_HEIGHT))
            img = Image.fromarray(frame_rgb)
            ctk_img = CTkImage(light_image=img, dark_image=img, size=(INSPECTION_PREVIEW_WIDTH, INSPECTION_PREVIEW_HEIGHT))
            self.image_label.configure(image=ctk_img)
            self.image_label.image = ctk_img

    def save_photo(self):
        if self.captured_image is not None:
            os.makedirs("data/raw", exist_ok=True)
            save_path = "data/raw/fba_actual.jpg"
            cv2.imwrite(save_path, self.captured_image)
            print(f"Imagem guardada em {save_path}")

    def on_close(self):
        self.capturing = False
        self.cap.release()
        self.destroy()

