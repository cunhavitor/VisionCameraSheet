import cv2
import numpy as np
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageTk
import json

from config.config import PREVIEW_WIDTH, PREVIEW_HEIGHT
from models.align_image import align_with_template


class AlignmentWindow(ctk.CTkToplevel):
    def __init__(self, parent, image_path, output_path="data/mask/leaf_mask.png", window_width=640):
        super().__init__(parent)
        self.state("zoomed")
        self.title("Ajustar Alinhamento")
        self.window_width = window_width
        self.parent = parent

        self.image_path = image_path
        self.output_path = output_path
        self.image = None
        self.clone = None
        self.scale = 1.0

        self.canvas = None
        self.tk_image = None

        self.config_path = "config/config_alignment.json"
        self._load_alignment_config()

        self._setup_ui()
        self._load_and_prepare_image()

    def _setup_ui(self):
        self.geometry(f"{PREVIEW_WIDTH + 250}x{PREVIEW_HEIGHT + 40}")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Frame lateral com botões e parâmetros
        self.left_frame = ctk.CTkFrame(self)
        self.left_frame.grid(row=0, column=0, sticky="ns", padx=10, pady=10)

        # Frame principal para imagem
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

        # Título parâmetros alinhamento
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

        # Parâmetros para linhas verdes
        ctk.CTkLabel(self.left_frame, text="Linhas Verdes (Máscara)", font=("Arial", 14, "bold")).pack(pady=(15, 5))

        # Criar entradas para x_min, x_max, y_min, y_max
        ctk.CTkLabel(self.left_frame, text="x_min").pack()
        self.x_min_entry = ctk.CTkEntry(self.left_frame)
        self.x_min_entry.pack(pady=3)

        ctk.CTkLabel(self.left_frame, text="x_max").pack()
        self.x_max_entry = ctk.CTkEntry(self.left_frame)
        self.x_max_entry.pack(pady=3)

        ctk.CTkLabel(self.left_frame, text="y_min").pack()
        self.y_min_entry = ctk.CTkEntry(self.left_frame)
        self.y_min_entry.pack(pady=3)

        ctk.CTkLabel(self.left_frame, text="y_max").pack()
        self.y_max_entry = ctk.CTkEntry(self.left_frame)
        self.y_max_entry.pack(pady=3)

        ctk.CTkLabel(self.left_frame, text="Dimensão da folha em X").pack()
        self.sheet_xDim_entry = ctk.CTkEntry(self.left_frame)
        self.sheet_xDim_entry.insert(0, "1030")
        self.sheet_xDim_entry.pack(pady=3)

        ctk.CTkLabel(self.left_frame, text="Dimensão da folha em Y").pack()
        self.sheet_yDim_entry = ctk.CTkEntry(self.left_frame)
        self.sheet_yDim_entry.insert(0, "820")
        self.sheet_yDim_entry.pack(pady=3)

        # Botões
        update_button = ctk.CTkButton(self.left_frame, text="Atualizar Alinhamento", command=self._update_alignment)
        update_button.pack(pady=(15, 5))

        save_button = ctk.CTkButton(self.left_frame, text="Guardar Configuração", command=self._save_alignment_config)
        save_button.pack(pady=5)

    def _resize_image(self, img):
        h, w = img.shape[:2]
        scale_w = PREVIEW_WIDTH / w
        scale_h = PREVIEW_HEIGHT / h
        self.scale = min(1.0, scale_w, scale_h)  # escala para caber na janela (reduzir se necessário)

        new_w = int(w * self.scale)
        new_h = int(h * self.scale)

        resized = cv2.resize(img, (new_w, new_h))
        return resized

    def _load_alignment_config(self):
        try:
            with open(self.config_path, "r") as f:
                self.alignment_config = json.load(f)
        except Exception:
            # Valores default
            self.alignment_config = {
                "max_features": 1000,
                "good_match_percent": 0.2,
                "x_min": 50,
                "x_max": PREVIEW_WIDTH - 50,
                "y_min": 50,
                "y_max": PREVIEW_HEIGHT - 50
            }

    def _load_and_prepare_image(self):
        # 1) Carrega e alinha a imagem
        self.image = cv2.imread(self.image_path)
        if self.image is None:
            print(f"Erro ao carregar a imagem: {self.image_path}")
            return

        template_path = "data/raw/fba_template.jpg"
        template_img = cv2.imread(template_path)
        if template_img is None:
            print(f"Erro ao carregar a imagem template: {template_path}")
            return

        try:
            aligned_img, _ = align_with_template(self.image, template_img, self.config_path)
        except Exception as e:
            print(f"Erro no alinhamento: {e}")
            aligned_img = self.image.copy()

        # 2) Redimensiona para a área de preview
        display_img = self._resize_image(aligned_img)
        new_h, new_w = display_img.shape[:2]

        # 3) Carrega a máscara e aplica
        mask_path = "data/mask/leaf_mask.png"
        mask_img = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
        if mask_img is None:
            print(f"Erro ao carregar a máscara: {mask_path}")
            mask_img = np.ones((new_h, new_w), dtype=np.uint8) * 255

        mask_resized = cv2.resize(mask_img, (new_w, new_h), interpolation=cv2.INTER_NEAREST)
        masked_img = cv2.bitwise_and(display_img, display_img, mask=mask_resized)

        # 4) Converte para PIL e prepara para desenhar
        rgb_img = cv2.cvtColor(masked_img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_img)
        draw = ImageDraw.Draw(pil_img)

        # 5) Calcula bounding box da área branca da máscara
        coords = cv2.findNonZero(mask_resized)
        if coords is not None:
            x, y, w, h = cv2.boundingRect(coords)
            x_min, y_min = x, y
            x_max, y_max = x + w, y + h
        else:
            x_min, y_min = 0, 0
            x_max, y_max = new_w, new_h

        # 8) Calcula e exibe os valores *reais* (des-escala)
        x_min_real = int(x_min / self.scale)
        x_max_real = int(x_max / self.scale)
        y_min_real = int(y_min / self.scale)
        y_max_real = int(y_max / self.scale)

        # 6) Atualiza as entradas (valores escalados)
        self.x_min_entry.delete(0, "end")
        self.x_min_entry.insert(0, str(x_min_real))
        self.x_max_entry.delete(0, "end")
        self.x_max_entry.insert(0, str(x_max_real))
        self.y_min_entry.delete(0, "end")
        self.y_min_entry.insert(0, str(y_min_real))
        self.y_max_entry.delete(0, "end")
        self.y_max_entry.insert(0, str(y_max_real))

        # 7) Desenha as linhas verdes no PIL
        line_color = (0, 255, 0)
        line_width = 2
        draw.line([(x_min, 0), (x_min, new_h)], fill=line_color, width=line_width)
        draw.line([(x_max, 0), (x_max, new_h)], fill=line_color, width=line_width)
        draw.line([(0, y_min), (new_w, y_min)], fill=line_color, width=line_width)
        draw.line([(0, y_max), (new_w, y_max)], fill=line_color, width=line_width)

        # 8) dimensões da folha em pixels reais
        px_w = x_max_real - x_min_real
        px_h = y_max_real - y_min_real

        # 9) Cálculo da densidade px/mm²
        # lê as dimensões em mm diretamente das entradas
        try:
            mm_w = float(self.sheet_xDim_entry.get())
            mm_h = float(self.sheet_yDim_entry.get())
        except ValueError:
            mm_w, mm_h = 0.0, 0.0

        # 10) calcula densidade: total_pixels / área_mm2
        if mm_w > 0 and mm_h > 0:
            pix_per_mm2 = (px_w * px_h) / (mm_w * mm_h)
            texto = f"Densidade: {pix_per_mm2:.2f} px/mm²"
        else:
            texto = "Densidade: —"

        # 11) atualiza ou cria o label de densidade
        if not hasattr(self, "density_label"):
            self.density_label = ctk.CTkLabel(self.left_frame, text=texto)
            self.density_label.pack(pady=(5, 10))
        else:
            self.density_label.configure(text=texto)

        # 12) Exibe no canvas
        self.tk_image = ImageTk.PhotoImage(pil_img)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor='nw', image=self.tk_image)

    def _save_alignment_config(self):
        try:
            self.alignment_config["max_features"] = int(self.max_features_entry.get())
            self.alignment_config["good_match_percent"] = float(self.match_percent_entry.get())


            with open(self.config_path, "w") as f:
                json.dump(self.alignment_config, f, indent=4)

            print("Configuração guardada com sucesso.")
        except Exception as e:
            print(f"Erro ao guardar configuração: {e}")

    def _update_alignment(self):
        try:
            # 1. Atualizar parâmetros da config com os valores dos widgets
            self.alignment_config["max_features"] = int(self.max_features_entry.get())
            self.alignment_config["good_match_percent"] = float(self.match_percent_entry.get())


            # 2. Recarregar imagem e template
            original_image = cv2.imread(self.image_path)
            template_img = cv2.imread("data/raw/fba_template.jpg")
            if original_image is None or template_img is None:
                print("Erro ao recarregar imagens.")
                return

            # 3. Alinhar
            aligned_img, _ = align_with_template(original_image, template_img, self.config_path)
            self.image = aligned_img

            # 4. Recria o preview, as linhas e os rótulos de coordenadas reais
            self._load_and_prepare_image()


        except Exception as e:
            print(f"Erro ao atualizar alinhamento: {e}")
