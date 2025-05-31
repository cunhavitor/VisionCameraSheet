import os
import datetime
import cv2
import customtkinter as ctk
from PIL import Image
from customtkinter import CTkImage
from config.config import PREVIEW_WIDTH, PREVIEW_HEIGHT, TEMPLATE_IMAGE_PATH
from windows.adjust_positions import AdjustPositionsWindow
from windows.alignment_adjust import AlignmentWindow
from windows.gallery import GalleryWindow
from windows.inspection_window import InspectionWindow
from create_leaf_mask import LeafMaskCreator

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.state("zoomed")
        self.mask_window = None
        self.gallery_window = None
        self.adjust_window = None
        self.title("Detection Lito Errors")
        self.geometry("800x600")
        ctk.set_appearance_mode("dark")

        # Inicialização da webcam
        self.cap = cv2.VideoCapture(0)
        self.preview_running = True
        self.current_frame = None

        # Layout principal
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # --- Botões à esquerda ---
        self.buttons_frame = ctk.CTkFrame(self.main_frame, width=200)
        self.buttons_frame.pack(side="left", fill="y", padx=(0, 20))
        self.buttons_frame.pack_propagate(False)

        self.capture_button = ctk.CTkButton(
            self.buttons_frame, text="📸 Capturar", command=self.capture_image)
        self.capture_button.pack(pady=(10, 10), fill="x")

        self.adjust_positions_button = ctk.CTkButton(
            self.buttons_frame, text="🛠️ Adjust Positions", command=self.open_adjust_positions)
        self.adjust_positions_button.pack(pady=(0, 10), fill="x")

        self.gallery_button = ctk.CTkButton(
            self.buttons_frame, text="📂 Ver Galeria", command=self.open_gallery)
        self.gallery_button.pack(pady=(0, 10), fill="x")

        self.inspect_button = ctk.CTkButton(
            self.buttons_frame, text="📂 Inspecção", command=self.open_inspection)
        self.inspect_button.pack(pady=(0, 10), fill="x")

        self.mask_window_button = ctk.CTkButton(
            self.buttons_frame, text="📂 Máscara", command=self.open_mask_window)
        self.mask_window_button.pack(pady=(0, 10), fill="x")

        self.alignment_adjust_window_button = ctk.CTkButton(
            self.buttons_frame, text="📂 Alignment Adjust", command=self.open_alignment_adjust_window)
        self.alignment_adjust_window_button.pack(pady=(0, 10), fill="x")

        self.status_label = ctk.CTkLabel(
            self.buttons_frame, text="Pronto para iniciar.", width=140, anchor="w", wraplength=140)
        self.status_label.pack(side="bottom", pady=10)

        # --- Área da imagem à direita ---
        self.image_border = ctk.CTkFrame(
            self.main_frame, width=PREVIEW_WIDTH+4, height=PREVIEW_HEIGHT+4, corner_radius=8, fg_color="gray80")
        self.image_border.pack(pady=(10, 10))

        self.image_frame = ctk.CTkFrame(
            self.image_border, width=PREVIEW_WIDTH, height=PREVIEW_HEIGHT, fg_color="black", corner_radius=6)
        self.image_frame.pack(padx=2, pady=2)

        self.image_label = ctk.CTkLabel(
            self.image_frame, text="Imagem aparecerá aqui", width=PREVIEW_WIDTH, height=PREVIEW_HEIGHT, )
        self.image_label.pack()

        # Inicia preview da câmera
        self.update_camera_preview()

        # Fecha a câmera ao sair
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def update_camera_preview(self):
        if self.preview_running and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                self.current_frame = frame.copy()
                img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                pil_img = Image.fromarray(img_rgb).resize((PREVIEW_WIDTH, PREVIEW_HEIGHT), Image.Resampling.LANCZOS)
                ctk_image = CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)
                self.image_label.configure(image=ctk_image, text="")
                self.image_label.image = ctk_image
        self.after(50, self.update_camera_preview)  # type: ignore

    def capture_image(self):
        if self.current_frame is not None:
            os.makedirs("data/raw", exist_ok=True)
            save_path = "data/raw/fba_actual.jpg"
            cv2.imwrite(save_path, self.current_frame)
            self.status_label.configure(text=f"Imagem capturada como fba_actual.jpg")

    def open_adjust_positions(self):
        self.withdraw()  # Esconde a janela principal
        self.adjust_window = AdjustPositionsWindow(self)
        self.adjust_window.protocol("WM_DELETE_WINDOW", self.on_adjust_positions_close)

    def on_adjust_positions_close(self):
        self.adjust_window.destroy()
        self.deiconify()  # Mostra a janela principal de novo

    def open_gallery(self):
        self.withdraw()  # Esconde a janela principal
        self.gallery_window = GalleryWindow(self)
        self.gallery_window.protocol("WM_DELETE_WINDOW", self.on_gallery_close)

    def on_gallery_close(self):
        self.gallery_window.destroy()
        self.deiconify()  # Mostra a janela principal de novo

    def open_inspection(self):
        self.withdraw()
        mask_path = "data/mask/leaf_mask.png"
        template_path = "data/raw/fba_template.jpg"
        current_path = "data/raw/fba_actual.jpg"
        self.inspection_window = InspectionWindow(self, template_path, current_path, mask_path)
        self.inspection_window.protocol("WM_DELETE_WINDOW", self.on_inspection_close)

    def on_inspection_close(self):
        self.inspection_window.destroy()
        self.deiconify()  # Mostra a janela principal de novo

    def open_mask_window(self):
        self.withdraw()
        template_path = "data/raw/fba_template.jpg"
        self.mask_window = LeafMaskCreator(self, template_path)
        self.mask_window.protocol("WM_DELETE_WINDOW", self.on_mask_window_close)

    def on_mask_window_close(self):
        if self.mask_window is not None:
            self.mask_window.destroy()
            self.mask_window = None
        self.deiconify()  # reaparece janela principal

    def open_alignment_adjust_window(self):
        self.withdraw()
        template_path = "data/raw/fba_template.jpg"
        current_path = "data/raw/fba_actual.jpg"
        self.alignment_adjust_window = AlignmentWindow(self, current_path)
        self.alignment_adjust_window.protocol("WM_DELETE_WINDOW", self.on_alignment_adjust_window_close)

    def on_alignment_adjust_window_close(self):
        self.alignment_adjust_window.destroy()
        self.deiconify()  # Mostra a janela principal de novo

    def on_close(self):
        self.preview_running = False
        if self.cap and self.cap.isOpened():
            self.cap.release()
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()
