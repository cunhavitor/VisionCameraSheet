import cv2
import numpy as np
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageTk
import json
import threading
import time
from picamera2 import Picamera2

from config.config import PREVIEW_WIDTH, PREVIEW_HEIGHT


class AlignmentWindow(ctk.CTkToplevel):
    def __init__(self, parent, output_path="data/mask/leaf_mask.png"):
        super().__init__(parent)
        self.state("zoomed")
        self.title("Ajustar Alinhamento")
        self.parent = parent

        self.output_path = output_path
        self.scale = 1.0

        self.canvas = None
        self.tk_image = None

        self.config_path = "config/config_alignment.json"
        self._load_alignment_config()

        # UI
        self._setup_ui()

        # Live camera
        self.use_camera = True
        self.picam2 = None
        self.camera_thread = None
        self.stop_event = threading.Event()
        self._start_camera_preview()

        # Inicializa entradas e máscara
        self._initialize_mask_and_entries()

    def _setup_ui(self):
        self.geometry(f"{PREVIEW_WIDTH + 250}x{PREVIEW_HEIGHT + 40}")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Frame lateral
        self.left_frame = ctk.CTkFrame(self)
        self.left_frame.grid(row=0, column=0, sticky="ns", padx=10, pady=10)

        # Frame principal
        self.right_frame = ctk.CTkFrame(self)
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        self.image_border = ctk.CTkFrame(
            self.right_frame, width=PREVIEW_WIDTH + 4, height=PREVIEW_HEIGHT + 4,
            corner_radius=8, fg_color="gray80"
        )
        self.image_border.pack(pady=(10, 10))

        self.image_frame = ctk.CTkFrame(
            self.image_border, width=PREVIEW_WIDTH, height=PREVIEW_HEIGHT,
            fg_color="black", corner_radius=6
        )
        self.image_frame.pack(padx=2, pady=2)

        self.canvas = ctk.CTkCanvas(
            self.image_frame, width=PREVIEW_WIDTH, height=PREVIEW_HEIGHT, bg="black", cursor="plus",
            highlightthickness=0
        )
        self.canvas.pack()

        # Labels e entradas
        ctk.CTkLabel(self.left_frame, text="Parâmetros de Alinhamento", font=("Arial", 14, "bold")).pack(pady=(10, 5))

        # max_features
        ctk.CTkLabel(self.left_frame, text="max_features").pack()
        self.max_features_entry = ctk.CTkEntry(self.left_frame)
        self.max_features_entry.insert(0, str(self.alignment_config["max_features"]))
        self.max_features_entry.pack(pady=5)

        # good_match_percent
        ctk.CTkLabel(self.left_frame, text="good_match_percent").pack()
        self.match_percent_entry = ctk.CTkEntry(self.left_frame)
        self.match_percent_entry.insert(0, str(self.alignment_config["good_match_percent"]))
        self.match_percent_entry.pack(pady=5)

        # Linhas verdes
        ctk.CTkLabel(self.left_frame, text="Linhas Verdes (Máscara)", font=("Arial", 14, "bold")).pack(pady=(15, 5))

        # Entradas para x_min, x_max, y_min, y_max
        self.x_min_entry = self._add_label_entry("x_min")
        self.x_max_entry = self._add_label_entry("x_max")
        self.y_min_entry = self._add_label_entry("y_min")
        self.y_max_entry = self._add_label_entry("y_max")

        self.sheet_xDim_entry = self._add_label_entry("Dimensão da folha em X", default="1030")
        self.sheet_yDim_entry = self._add_label_entry("Dimensão da folha em Y", default="820")

        # Botões
        update_button = ctk.CTkButton(self.left_frame, text="Atualizar Alinhamento", command=self._update_alignment)
        update_button.pack(pady=(15, 5))
        save_button = ctk.CTkButton(self.left_frame, text="Guardar Configuração", command=self._save_alignment_config)
        save_button.pack(pady=5)

        # Label densidade
        self.density_label = ctk.CTkLabel(self.left_frame, text="Densidade: —")
        self.density_label.pack(pady=(5, 10))

    def _add_label_entry(self, text, default=""):
        ctk.CTkLabel(self.left_frame, text=text).pack()
        entry = ctk.CTkEntry(self.left_frame)
        entry.insert(0, default)
        entry.pack(pady=3)
        return entry

    def _load_alignment_config(self):
        try:
            with open(self.config_path, "r") as f:
                self.alignment_config = json.load(f)
        except Exception:
            self.alignment_config = {
                "max_features": 1000,
                "good_match_percent": 0.2,
                "x_min": 50,
                "x_max": PREVIEW_WIDTH - 50,
                "y_min": 50,
                "y_max": PREVIEW_HEIGHT - 50
            }

    def _initialize_mask_and_entries(self):
        # Atualiza entradas com valores da config
        self.x_min_entry.delete(0, "end")
        self.x_min_entry.insert(0, str(self.alignment_config.get("x_min", 50)))
        self.x_max_entry.delete(0, "end")
        self.x_max_entry.insert(0, str(self.alignment_config.get("x_max", PREVIEW_WIDTH - 50)))
        self.y_min_entry.delete(0, "end")
        self.y_min_entry.insert(0, str(self.alignment_config.get("y_min", 50)))
        self.y_max_entry.delete(0, "end")
        self.y_max_entry.insert(0, str(self.alignment_config.get("y_max", PREVIEW_HEIGHT - 50)))

        # Carrega máscara
        self.mask_path = "data/mask/leaf_mask.png"
        mask_img = cv2.imread(self.mask_path, cv2.IMREAD_GRAYSCALE)
        if mask_img is not None:
            self.mask_resized = cv2.resize(mask_img, (PREVIEW_WIDTH, PREVIEW_HEIGHT), interpolation=cv2.INTER_NEAREST)
        else:
            self.mask_resized = np.ones((PREVIEW_HEIGHT, PREVIEW_WIDTH), dtype=np.uint8) * 255

    def _start_camera_preview(self):
        self.picam2 = Picamera2()
        config = self.picam2.create_preview_configuration(main={"format": "RGB888", "size": (PREVIEW_WIDTH, PREVIEW_HEIGHT)})
        self.picam2.configure(config)
        self.picam2.start()

        self.camera_thread = threading.Thread(target=self._update_camera_loop, daemon=True)
        self.camera_thread.start()

    def _update_camera_loop(self):
        while not self.stop_event.is_set():
            frame = self.picam2.capture_array()
            if frame is None:
                continue

            # Aplica máscara
            frame = cv2.bitwise_and(frame, frame, mask=self.mask_resized)

            # Converte para PIL
            pil_img = Image.fromarray(frame)
            draw = ImageDraw.Draw(pil_img)

            # Linhas verdes
            try:
                x_min = int(self.x_min_entry.get())
                x_max = int(self.x_max_entry.get())
                y_min = int(self.y_min_entry.get())
                y_max = int(self.y_max_entry.get())
            except Exception:
                x_min, x_max, y_min, y_max = 0, PREVIEW_WIDTH, 0, PREVIEW_HEIGHT

            line_color = (0, 255, 0)
            line_width = 2
            draw.line([(x_min, 0), (x_min, PREVIEW_HEIGHT)], fill=line_color, width=line_width)
            draw.line([(x_max, 0), (x_max, PREVIEW_HEIGHT)], fill=line_color, width=line_width)
            draw.line([(0, y_min), (PREVIEW_WIDTH, y_min)], fill=line_color, width=line_width)
            draw.line([(0, y_max), (PREVIEW_WIDTH, y_max)], fill=line_color, width=line_width)

            # Atualiza densidade
            px_w = x_max - x_min
            px_h = y_max - y_min
            try:
                mm_w = float(self.sheet_xDim_entry.get())
                mm_h = float(self.sheet_yDim_entry.get())
                pix_per_mm2 = (px_w * px_h) / (mm_w * mm_h)
                self.density_label.configure(text=f"Densidade: {pix_per_mm2:.2f} px/mm²")
            except Exception:
                self.density_label.configure(text="Densidade: —")

            # Atualiza canvas
            self.tk_image = ImageTk.PhotoImage(pil_img)
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor='nw', image=self.tk_image)

            time.sleep(0.03)

    def _save_alignment_config(self):
        try:
            self.alignment_config["max_features"] = int(self.max_features_entry.get())
            self.alignment_config["good_match_percent"] = float(self.match_percent_entry.get())
            self.alignment_config["x_min"] = int(self.x_min_entry.get())
            self.alignment_config["x_max"] = int(self.x_max_entry.get())
            self.alignment_config["y_min"] = int(self.y_min_entry.get())
            self.alignment_config["y_max"] = int(self.y_max_entry.get())

            with open(self.config_path, "w") as f:
                json.dump(self.alignment_config, f, indent=4)
            print("Configuração guardada com sucesso.")
        except Exception as e:
            print(f"Erro ao guardar configuração: {e}")

    def _update_alignment(self):
        # No live feed, apenas atualizamos entradas, máscara e linhas verdes
        self._initialize_mask_and_entries()

    def destroy(self):
        if self.picam2:
            self.stop_event.set()
            self.camera_thread.join()
            self.picam2.stop()
        super().destroy()
