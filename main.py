import customtkinter as ctk

from windows.adjust_positions import AdjustPositionsWindow
from windows.alignment_adjust import AlignmentWindow
from windows.camera_adjust_positions import CameraAdjustPosition
from windows.create_leaf_mask import LeafMaskCreator
from windows.gallery import GalleryWindow
from windows.inspection_window import InspectionWindow


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.cap = None
        self.preview_running = None
        self.alignment_adjust_window = None
        self.inspection_window = None
        self.state("zoomed")
        self.mask_window = None
        self.gallery_window = None
        self.adjust_window = None
        self.title("Detection Lito Errors")
        self.geometry("800x600")
        ctk.set_appearance_mode("dark")

        # Layout principal
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        self.main_frame.grid_columnconfigure((0, 1, 2), weight=1)  # 3 colunas com distribuição igual

        # --- Botões à esquerda (coluna 0) ---

        self.user_frame = ctk.CTkFrame(self.main_frame)
        self.user_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.user_frame.grid_propagate(False)

        self.status_label = ctk.CTkLabel(self.user_frame, text="Usuário:", width=140, wraplength=140,
            text_color="white", font=("Arial", 20))
        self.status_label.pack(side="top", pady=10)

        self.login_button = ctk.CTkButton(self.user_frame, text="Login", width=200)
        self.login_button.pack(pady=(10, 10), anchor="center")

        self.new_user_button = ctk.CTkButton(self.user_frame, text="Novo User", width=200)
        self.new_user_button.pack(pady=(0, 10), anchor="center")

        # --- Coluna do meio (coluna 1) ---
        self.middle_frame = ctk.CTkFrame(self.main_frame)
        self.middle_frame.grid(row=0, column=1, sticky="nsew", pady=20, padx=20)

        self.status_label = ctk.CTkLabel(self.middle_frame, text="Settings:", width=140, wraplength=140,
            text_color="white", font=("Arial", 20))
        self.status_label.pack(side="top", pady=10)

        self.adjust_positions_button = ctk.CTkButton(self.middle_frame, text="🛠️ Adjust Positions",
            command=self.open_adjust_positions, width=200)
        self.adjust_positions_button.pack(pady=(0, 10), anchor="center")

        self.mask_window_button = ctk.CTkButton(self.middle_frame, text="🎭 Máscara", command=self.open_mask_window,
            width=200)
        self.mask_window_button.pack(pady=(0, 10), anchor="center")

        self.alignment_adjust_window_button = ctk.CTkButton(self.middle_frame, text="↔️ Alignment Adjust",
            command=self.open_alignment_adjust_window, width=200)
        self.alignment_adjust_window_button.pack(pady=(0, 10), anchor="center")

        self.angle_checker_window_button = ctk.CTkButton(self.middle_frame, text="📐 Check Camera Positions",
                                                         command=self.open_check_camera_position_window, width=200)
        self.angle_checker_window_button.pack(pady=(0, 10), anchor="center")

        # --- Coluna da direita (coluna 2) ---
        self.right_frame = ctk.CTkFrame(self.main_frame)
        self.right_frame.grid(row=0, column=2, sticky="nsew", pady=20, padx=20)

        self.status_label = ctk.CTkLabel(self.right_frame, text="Inspeção:", width=140, wraplength=140,
            text_color="white", font=("Arial", 20))
        self.status_label.pack(side="top", pady=10)

        self.gallery_button = ctk.CTkButton(self.right_frame, text="📂 Ver Galeria", command=self.open_gallery,
            width=200)
        self.gallery_button.pack(pady=(0, 10), anchor="center")

        self.inspect_button = ctk.CTkButton(self.right_frame, text="👁️ Inspecção", command=self.open_inspection,
            width=200)
        self.inspect_button.pack(pady=(0, 10), anchor="center")

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

    def open_check_camera_position_window(self):
        self.withdraw()  # Esconde a janela principal
        self.angle_ckecker_window = CameraAdjustPosition(parent=self, image_path="data/raw/fba_template_persp.jpg")
        self.angle_ckecker_window.protocol("WM_DELETE_WINDOW", self.on_check_camera_position_window_close)

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

    def on_check_camera_position_window_close(self):
        self.angle_ckecker_window.destroy()
        self.deiconify()  # Mostra a janela principal de novo

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
