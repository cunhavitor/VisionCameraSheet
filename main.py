
import cv2
import customtkinter as ctk
from windows.adjust_positions import AdjustPositionsWindow
from windows.alignment_adjust import AlignmentWindow
from windows.gallery import GalleryWindow
from windows.inspection_window import InspectionWindow
from windows.create_leaf_mask import LeafMaskCreator

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.alignment_adjust_window = None
        self.inspection_window = None
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

        self.adjust_positions_button = ctk.CTkButton(
            self.buttons_frame, text="🛠️ Adjust Positions", command=self.open_adjust_positions)
        self.adjust_positions_button.pack(pady=(0, 10), fill="x")

        self.gallery_button = ctk.CTkButton(
            self.buttons_frame, text="📂 Ver Galeria", command=self.open_gallery)
        self.gallery_button.pack(pady=(0, 10), fill="x")

        self.inspect_button = ctk.CTkButton(
            self.buttons_frame, text="👁️ Inspecção", command=self.open_inspection)
        self.inspect_button.pack(pady=(0, 10), fill="x")

        self.mask_window_button = ctk.CTkButton(
            self.buttons_frame, text="🎭 Máscara", command=self.open_mask_window)
        self.mask_window_button.pack(pady=(0, 10), fill="x")

        self.alignment_adjust_window_button = ctk.CTkButton(
            self.buttons_frame, text="↔️ Alignment Adjust", command=self.open_alignment_adjust_window)
        self.alignment_adjust_window_button.pack(pady=(0, 10), fill="x")


        self.status_label = ctk.CTkLabel(
            self.buttons_frame, text="Pronto para iniciar.", width=140, anchor="w", wraplength=140)
        self.status_label.pack(side="bottom", pady=10)


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
