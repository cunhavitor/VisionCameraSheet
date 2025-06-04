import json
import cv2
import numpy as np
import customtkinter as ctk
from PIL import Image, ImageDraw
from customtkinter import CTkImage
from models.align_image import align_with_template
from config.config import INSPECTION_PREVIEW_WIDTH, INSPECTION_PREVIEW_HEIGHT
from config.utils import load_inspection_params
from skimage.metrics import structural_similarity as ssim  # Adiciona no topo do ficheiro


def _prepare_image(img_cv, size, draw_contours=None):
    # redimensiona e converte para CTkImage; opcionalmente desenha contornos
    resized = cv2.resize(img_cv, size)
    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(rgb)

    if draw_contours:
        draw = ImageDraw.Draw(pil)
        sx, sy = size[0] / img_cv.shape[1], size[1] / img_cv.shape[0]
        for cnt in draw_contours:
            pts = [(int(pt[0][0] * sx), int(pt[0][1] * sy)) for pt in cnt]
            draw.line(pts + [pts[0]], fill="red", width=2)

    return CTkImage(light_image=pil, dark_image=pil, size=size)


def _prepare_image_grayscale(img_cv, size, draw_contours=None):
    # redimensiona e converte para grayscale CTkImage; opcionalmente desenha contornos
    resized = cv2.resize(img_cv, size)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)  # converte para grayscale

    # Para desenhar contornos em grayscale, converte para RGB para desenhar em vermelho
    pil = Image.fromarray(gray).convert("RGB")

    if draw_contours:
        draw = ImageDraw.Draw(pil)
        sx, sy = size[0] / img_cv.shape[1], size[1] / img_cv.shape[0]

        for i, cnt in enumerate(draw_contours):
            # Calcular área e perímetro antes de desenhar
            area = cv2.contourArea(cnt)
            perimeter = cv2.arcLength(cnt, True)

            # Desenhar contorno redimensionado
            pts = [(int(pt[0][0] * sx), int(pt[0][1] * sy)) for pt in cnt]
            draw.line(pts + [pts[0]], fill="red", width=2)

    return CTkImage(light_image=pil, dark_image=pil, size=size)


def _validate_numeric(value_if_allowed):
    if value_if_allowed == "":
        return True
    try:
        int(value_if_allowed)
        return True
    except ValueError:
        return False


class InspectionWindow(ctk.CTkToplevel):
    def __init__(self, parent, template_path, current_path, mask_path):
        super().__init__(parent)
        #self.state("zoomed")
        self.title("Janela de Inspeção")

        # parâmetros ajustáveis (valores default)
        # Carrega parâmetros do JSON
        self.param_path = "config/inspection_params.json"
        params = load_inspection_params(self.param_path)

        self.dark_threshold = params.get("dark_threshold", 30)
        self.bright_threshold = params.get("bright_threshold", 30)
        self.morph_kernel_size = params.get("morph_kernel_size", 2)
        self.morph_iterations = params.get("morph_iterations", 1)
        self.min_defect_area = params.get("detect_area", 1)
        self.ssim_threshold = 30  # Valor inicial, pode ser ajustado pelo utilizador

        self.show_defect_contours = True
        # Criar a variável
        self.show_contours_var = ctk.BooleanVar(value=True)

        # 1) Carrega a s imagens e a máscara (máscara do template, geralmente)
        self.template_full = cv2.imread(template_path)
        self.current_full = cv2.imread(current_path)
        self.mask_full = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)

        # 2) Alinha a imagem atual para o template
        self.aligned_full, M = align_with_template(self.current_full, self.template_full)

        # 3) Aplica a máscara original (que está no espaço do template) na imagem alinhada
        self.current_masked = cv2.bitwise_and(self.aligned_full, self.aligned_full, mask=self.mask_full)
        self.template_masked = cv2.bitwise_and(self.template_full, self.template_full, mask=self.mask_full)

        # 4) Usa essa máscara fixa para detectar defeitos (já no espaço alinhado)
        self.defect_mask, self.defect_contours = self._detect_defects(
            self.template_masked, self.current_masked, self.mask_full)

        # 5) Prepara UI
        self._setup_ui()

    def _setup_ui(self):
        s = (INSPECTION_PREVIEW_WIDTH, INSPECTION_PREVIEW_HEIGHT)

        self.left_panel = ctk.CTkFrame(self)
        self.left_panel.pack(side="left", fill="y", expand=True, padx=10, pady=10)

        self.toggle = ctk.CTkSwitch(
            self.left_panel, text="Mostrar Template",
            command=self._toggle_image
        )
        self.toggle.pack(pady=10)

        self.sliders_frame = ctk.CTkFrame(self.left_panel)
        self.sliders_frame.pack(fill="x", pady=10)

        # --- DARK THRESHOLD ENTRY ---
        self.dark_threshold_var = ctk.StringVar(value=str(self.dark_threshold))
        self.dark_threshold_entry = ctk.CTkEntry(self.sliders_frame,
                                                 textvariable=self.dark_threshold_var,
                                                 fg_color="white",
                                                 text_color= "black")
        self.dark_threshold_entry.pack(fill="x", pady=10)
        self.dark_threshold_label = ctk.CTkLabel(self.sliders_frame, text=f"Threshold Escuro: {self.dark_threshold}")
        self.dark_threshold_label.pack()
        self.dark_threshold_entry.configure(validate="key",
                                            validatecommand=(self.register(_validate_numeric), '%P'))
        self.dark_threshold_entry.bind("<FocusOut>", self._on_dark_threshold_change)

        # --- BRIGHT THRESHOLD ENTRY ---
        self.bright_threshold_var = ctk.StringVar(value=str(self.bright_threshold))
        self.bright_threshold_entry = ctk.CTkEntry(self.sliders_frame,
                                                   textvariable=self.bright_threshold_var,
                                                   fg_color="white",
                                                   text_color= "black")
        self.bright_threshold_entry.pack(fill="x", pady=10)
        self.bright_threshold_label = ctk.CTkLabel(self.sliders_frame, text=f"Threshold Claro: {self.bright_threshold}")
        self.bright_threshold_label.pack()
        self.bright_threshold_entry.configure(validate="key",
                                              validatecommand=(self.register(_validate_numeric), '%P'))
        self.bright_threshold_entry.bind("<FocusOut>", self._on_bright_threshold_change)

        # Kernel Size Entry (substitui slider)
        self.kernel_var = ctk.StringVar(value=str(self.morph_kernel_size))
        self.kernel_entry = ctk.CTkEntry(self.sliders_frame,
                                         textvariable=self.kernel_var,
                                         fg_color="white",
                                         text_color= "black")
        self.kernel_entry.pack(fill="x", pady=10)
        self.kernel_label = ctk.CTkLabel(self.sliders_frame, text=f"Kernel Size: {self.morph_kernel_size}")
        self.kernel_label.pack()
        self.kernel_entry.configure(validate="key", validatecommand=(self.register(_validate_numeric), '%P'))
        self.kernel_entry.bind("<FocusOut>", self._on_kernel_change)

        # Iterations Entry (substitui slider)
        self.iterations_var = ctk.StringVar(value=str(self.morph_iterations))
        self.iterations_entry = ctk.CTkEntry(
            self.sliders_frame,
            textvariable=self.iterations_var,
            fg_color="white",
            text_color="black"
        )
        self.iterations_entry.pack(fill="x", pady=10)
        self.iterations_label = ctk.CTkLabel(self.sliders_frame, text=f"Iterations: {self.morph_iterations}")
        self.iterations_label.pack()
        self.iterations_entry.configure(validate="key", validatecommand=(self.register(_validate_numeric), '%P'))
        self.iterations_entry.bind("<FocusOut>", self._on_iterations_change)

        # --- MIN DEFECT AREA ENTRY ---
        self.min_defect_area_var = ctk.StringVar(value=str(self.min_defect_area))
        self.min_defect_area_entry = ctk.CTkEntry(self.sliders_frame,
                                                  textvariable=self.min_defect_area_var,
                                                  fg_color="white",
                                                  text_color= "black")
        self.min_defect_area_entry.pack(fill="x", pady=10)
        self.min_defect_area_label = ctk.CTkLabel(self.sliders_frame,
                                                  text=f"Tamanho mín. defeito: {self.min_defect_area}")
        self.min_defect_area_label.pack()
        self.min_defect_area_entry.configure(validate="key",
                                             validatecommand=(self.register(_validate_numeric), '%P'))
        self.min_defect_area_entry.bind("<FocusOut>", self._on_min_defect_area_change)

        # Botões e switches continuam iguais

        self.btn_defects = ctk.CTkButton(
            self.left_panel, text="Mostrar Defeitos",
            command=self._show_defects
        )
        self.btn_defects.pack(pady=5)

        self.show_contours_var = ctk.BooleanVar(value=True)
        self.toggle_contours = ctk.CTkSwitch(
            self.left_panel,
            text="Mostrar Contornos dos Defeitos",
            variable=self.show_contours_var,
            command=self._toggle_defect_contours,
        )

        self.toggle_contours.pack(pady=10)


        # DefeitosInfo
        self.total_defects_var = ctk.StringVar(value="0")
        self.total_defects_entry = ctk.CTkEntry(self.sliders_frame, textvariable=self.total_defects_var,
                                                state="readonly")
        self.total_defects_entry.pack(pady=25)
        self.total_defects_count_label = ctk.CTkLabel(self.sliders_frame,                                      text="Total de defeitos")
        self.total_defects_count_label.pack(pady=5)


        # Área da imagem à direita
        self.frame_img = ctk.CTkFrame(self, width=s[0] + 4, height=s[1] + 4, fg_color="gray80")
        self.frame_img.pack(side="left", padx=10, pady=10)
        self.frame_img.pack_propagate(False)

        self.lbl_img = ctk.CTkLabel(self.frame_img, text="")
        self.lbl_img.pack(padx=2, pady=2)

        # Preparação das imagens
        self.tk_template = _prepare_image_grayscale(self.template_masked, s)
        self.tk_aligned = _prepare_image_grayscale(self.current_masked, s)

        aligned_masked = cv2.bitwise_and(self.aligned_full, self.aligned_full,
                                         mask=self.mask_full)
        self.tk_defect = _prepare_image_grayscale(aligned_masked, s, draw_contours=self.defect_contours)

        self.lbl_img.configure(image=self.tk_aligned)
        self.lbl_img.image = self.tk_aligned

        # Janela fixa
        self.geometry(f"{s[0] + 200}x{s[1] + 40}")
        self.resizable(False, False)

    def _toggle_defect_contours(self):
        # Ler o estado via variável associada, não pelo switch direto
        self.show_defect_contours = self.show_contours_var.get()
        self._update_defect_image()

    def _detect_defects(self, tpl, aligned, mask):
        # Converter para grayscale e equalizar
        t_gray = cv2.cvtColor(tpl, cv2.COLOR_BGR2GRAY)
        a_gray = cv2.cvtColor(aligned, cv2.COLOR_BGR2GRAY)

        t_gray_eq = cv2.equalizeHist(t_gray)
        a_gray_eq = cv2.equalizeHist(a_gray)

        diff = cv2.subtract(t_gray_eq, a_gray_eq)  # defeitos escuros
        # diff_inv = cv2.subtract(a_gray_eq, t_gray_eq)  # defeitos claros (não amarelos)

        # Converter para LAB para detectar amarelos (canal b)
        tpl_lab = cv2.cvtColor(tpl, cv2.COLOR_BGR2LAB)
        aligned_lab = cv2.cvtColor(aligned, cv2.COLOR_BGR2LAB)

        tpl_b = tpl_lab[:, :, 2]
        aligned_b = aligned_lab[:, :, 2]

        diff_b = cv2.subtract(aligned_b, tpl_b)

        # Threshold para amarelos (mais brilhantes no canal b)
        _, yellow_mask = cv2.threshold(diff_b, self.bright_threshold, 255, cv2.THRESH_BINARY)

        # Threshold para defeitos escuros
        _, darker_mask = cv2.threshold(diff, self.dark_threshold, 255, cv2.THRESH_BINARY)

        # Combine máscaras - só com escuros e amarelos
        combined = cv2.bitwise_or(darker_mask, yellow_mask)

        # Morfologia para limpar ruídos
        k = np.ones((self.morph_kernel_size, self.morph_kernel_size), np.uint8)
        clean = cv2.morphologyEx(combined, cv2.MORPH_OPEN, k, iterations=self.morph_iterations)
        clean = cv2.morphologyEx(clean, cv2.MORPH_CLOSE, k, iterations=self.morph_iterations)

        # Aplica a máscara da folha
        clean_masked = cv2.bitwise_and(clean, clean, mask=mask)

        # Encontra contornos
        contours, _ = cv2.findContours(clean_masked, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Filtrar por área mínima
        # min_defect_area = getattr(self, "min_defect_area", 30)  # valor padrão: 30 px
        filtered_contours = [cnt for cnt in contours if cv2.contourArea(cnt) >= self.min_defect_area]

        return clean_masked, filtered_contours

    def _on_kernel_change(self, event):
        val = self.kernel_var.get()
        if val != "":
            k = int(val)
            if k % 2 == 0:
                k += 1
            k = max(1, min(k, 15))
            self.morph_kernel_size = k
            self.kernel_label.configure(text=f"Kernel Size: {self.morph_kernel_size}")
            self._recalculate_defects()
            self._save_params()
            # Atualiza texto da entry se o valor mudou
            if str(k) != val:
                self.kernel_var.set(str(k))

    def _on_iterations_change(self, event):
        val = self.iterations_var.get()
        if val != "":
            i = int(val)
            i = max(1, min(i, 10))
            self.morph_iterations = i
            self.iterations_label.configure(text=f"Iterations: {self.morph_iterations}")
            self._recalculate_defects()
            self._save_params()
            if str(i) != val:
                self.iterations_var.set(str(i))

    # funções que atualizam os parâmetros e recalculam defeitos
    def _on_dark_threshold_change(self, event):
        val = self.dark_threshold_var.get()
        if val != "":
            self.dark_threshold = int(val)
            self.dark_threshold_label.configure(text=f"Threshold Escuro: {self.dark_threshold}")
            self._recalculate_defects()
            self._save_params()

    def _on_bright_threshold_change(self, event):
        val = self.bright_threshold_var.get()
        if val != "":
            self.bright_threshold = int(val)
            self.bright_threshold_label.configure(text=f"Threshold Claro: {self.bright_threshold}")
            self._recalculate_defects()
            self._save_params()

    def _on_min_defect_area_change(self, event):
        val = self.min_defect_area_var.get()
        if val != "":
            self.min_defect_area = int(val)
            self.min_defect_area_label.configure(text=f"Tamanho mín. defeito: {self.min_defect_area}")
            self._recalculate_defects()
            self._save_params()

    def _recalculate_defects(self):
        self.defect_mask, self.defect_contours = self._detect_defects(
            self.template_masked,
            self.current_masked,
            self.mask_full
        )
        self._update_defect_image()

    def _toggle_image(self):
        if self.toggle.get():
            # Mostrar template com máscara
            self.lbl_img.configure(image=self.tk_template)
            self.lbl_img.image = self.tk_template
        else:
            # Mostrar imagem atual ALINHADA com máscara
            self.lbl_img.configure(image=self.tk_aligned)
            self.lbl_img.image = self.tk_aligned


    def _show_defects(self):
        #self.defects_info()
        self.total_defects_var.set(str(len(self.defect_contours)))


        self.lbl_img.configure(image=self.tk_defect)
        self.lbl_img.image = self.tk_defect

    def _save_params(self):
        params = {
            "dark_threshold": self.dark_threshold,
            "bright_threshold": self.bright_threshold,
            "morph_kernel_size": self.morph_kernel_size,
            "morph_iterations": self.morph_iterations,
            "detect_area": int(self.min_defect_area_var.get())
        }
        with open(self.param_path, "w") as f:
            json.dump(params, f, indent=4)

    def _update_defect_image(self):
        s = (INSPECTION_PREVIEW_WIDTH, INSPECTION_PREVIEW_HEIGHT)
        self.total_defects_var.set(str(len(self.defect_contours)))

        if self.show_defect_contours:
            aligned_masked = cv2.bitwise_and(self.aligned_full, self.aligned_full, mask=self.mask_full)
            self.tk_defect = _prepare_image_grayscale(aligned_masked, s, draw_contours=self.defect_contours)
        else:
            aligned_masked = cv2.bitwise_and(self.aligned_full, self.aligned_full, mask=self.mask_full)
            self.tk_defect = _prepare_image_grayscale(aligned_masked, s)

        self.lbl_img.configure(image=self.tk_defect)
        self.lbl_img.image = self.tk_defect
