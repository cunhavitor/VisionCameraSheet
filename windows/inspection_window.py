import json
import time
from tkinter import StringVar

import customtkinter as ctk
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageTk
from customtkinter import CTkImage

from config.config import INSPECTION_PREVIEW_WIDTH, INSPECTION_PREVIEW_HEIGHT
from config.utils import load_params
from models.align_image import align_with_template
from models.defect_detector import detect_defects # Already there, good!
from widgets.param_entry_hor import create_param_entry


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

        self.zoom_imgtk = None
        self.area_info_textbox = None
        self.state("zoomed")
        self.title("Janela de Inspeção")

        # parameters adjustable (default values)
        self.param_path = "config/inspection_params.json"
        params = load_params(self.param_path)

        self.dark_threshold = params.get("dark_threshold", 30)
        self.bright_threshold = params.get("bright_threshold", 30)

        self.dark_morph_kernel_size = params.get("dark_morph_kernel_size", 3)
        self.dark_morph_iterations = params.get("dark_morph_iterations", 1)
        self.bright_morph_kernel_size = params.get("bright_morph_kernel_size", 3)
        self.bright_morph_iterations = params.get("bright_morph_iterations", 1)

        self.min_defect_area = params.get("detect_area", 1)
        self.dark_gradient_threshold = params.get("dark_gradient_threshold", 10)

        # --- NEW THRESHOLDS FOR COLOR DEFECTS ---
        self.blue_threshold = params.get("blue_threshold", 25) # Default value for blue
        self.red_threshold = params.get("red_threshold", 25)   # Default value for red

        # Initialize all StringVar and BooleanVar objects here
        self.dark_threshold_var = ctk.StringVar(value=str(self.dark_threshold))
        self.bright_threshold_var = ctk.StringVar(value=str(self.bright_threshold))
        self.dark_kernel_var = ctk.StringVar(value=str(self.dark_morph_kernel_size))
        self.dark_iterations_var = ctk.StringVar(value=str(self.dark_morph_iterations))
        self.bright_kernel_var = ctk.StringVar(value=str(self.bright_morph_kernel_size))
        self.bright_iterations_var = ctk.StringVar(value=str(self.bright_morph_iterations))
        self.min_defect_area_var = ctk.StringVar(value=str(self.min_defect_area))
        self.total_defects_var = ctk.StringVar(value="0")
        self.show_contours_var = ctk.BooleanVar(value=True)
        self.dark_gradient_threshold_var = ctk.StringVar(value=str(self.dark_gradient_threshold))
        # --- NEW VARS FOR COLOR THRESHOLDS ---
        self.blue_threshold_var = ctk.StringVar(value=str(self.blue_threshold))
        self.red_threshold_var = ctk.StringVar(value=str(self.red_threshold))


        # 1) Load images and mask
        self.template_full = cv2.imread(template_path)
        self.current_full = cv2.imread(current_path)
        self.mask_full = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)

        # 2) Align current image to template
        self.aligned_full, M = align_with_template(self.current_full, self.template_full)

        # 3) Apply original mask (template space) to aligned image
        self.current_masked = cv2.bitwise_and(self.aligned_full, self.aligned_full, mask=self.mask_full)
        self.template_masked = cv2.bitwise_and(self.template_full, self.template_full, mask=self.mask_full)

        # 4) Use fixed mask to detect defects (already in aligned space)
        # --- UPDATED CALL TO DETECT_DEFECTS ---
        self.defect_mask, self.defect_contours, \
        self.darker_mask_filtered, self.yellow_mask, \
        self.blue_mask, self.red_mask = detect_defects( # <-- NEW RETURN VALUES
            self.template_masked,
            self.current_masked,
            self.mask_full,
            self.dark_threshold,
            self.bright_threshold,
            self.dark_morph_kernel_size,
            self.dark_morph_iterations,
            self.bright_morph_kernel_size,
            self.bright_morph_iterations,
            self.min_defect_area,
            self.dark_gradient_threshold,
            self.blue_threshold, # <-- NEW
            self.red_threshold   # <-- NEW
        )

        # 5) Setup UI
        self._setup_ui()

    # --- _setup_ui method (remains mostly as you had it, no changes needed inside it anymore) ---
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

        # DARK THRESHOLD
        self.dark_threshold_label, self.dark_threshold_entry = create_param_entry(
            self.sliders_frame,
            f"Threshold Escuro: {self.dark_threshold}",
            self.dark_threshold_var,
            self._on_dark_threshold_change
        )

        # BRIGHT/YELLOW THRESHOLD
        self.bright_threshold_label, self.bright_threshold_entry = create_param_entry(
            self.sliders_frame,
            f"Threshold Amarelo: {self.bright_threshold}", # Label changed for clarity
            self.bright_threshold_var,
            self._on_bright_threshold_change
        )

        # --- NEW: BLUE THRESHOLD ENTRY ---
        self.blue_threshold_label, self.blue_threshold_entry = create_param_entry(
            self.sliders_frame,
            f"Threshold Azul: {self.blue_threshold}",
            self.blue_threshold_var,
            self._on_blue_threshold_change
        )

        # --- NEW: RED THRESHOLD ENTRY ---
        self.red_threshold_label, self.red_threshold_entry = create_param_entry(
            self.sliders_frame,
            f"Threshold Vermelho: {self.red_threshold}",
            self.red_threshold_var,
            self._on_red_threshold_change
        )

        # DARK MORPH KERNEL SIZE
        self.dark_kernel_label, self.dark_kernel_entry = create_param_entry(
            self.sliders_frame,
            f"Kernel Escuro: {self.dark_morph_kernel_size}",
            self.dark_kernel_var,
            self._on_dark_kernel_change
        )

        # DARK MORPH ITERATIONS
        self.dark_iterations_label, self.dark_iterations_entry = create_param_entry(
            self.sliders_frame,
            f"Iterações Escuro: {self.dark_morph_iterations}",
            self.dark_iterations_var,
            self._on_dark_iterations_change
        )

        # BRIGHT MORPH KERNEL SIZE (applied to all color defects)
        self.bright_kernel_label, self.bright_kernel_entry = create_param_entry(
            self.sliders_frame,
            f"Kernel Colorido: {self.bright_morph_kernel_size}", # Label changed for clarity
            self.bright_kernel_var,
            self._on_bright_kernel_change
        )

        # BRIGHT MORPH ITERATIONS (applied to all color defects)
        self.bright_iterations_label, self.bright_iterations_entry = create_param_entry(
            self.sliders_frame,
            f"Iterações Colorido: {self.bright_morph_iterations}", # Label changed for clarity
            self.bright_iterations_var,
            self._on_bright_iterations_change
        )

        # Dark Gradient Threshold Entry
        self.dark_gradient_threshold_label, self.dark_gradient_threshold_entry = create_param_entry(
            self.sliders_frame,
            f"Gradiente Escuro: {self.dark_gradient_threshold}",
            self.dark_gradient_threshold_var,
            self._on_dark_gradient_threshold_change
        )

        # MIN DEFECT AREA
        self.min_defect_area_label, self.min_defect_area_entry = create_param_entry(
            self.sliders_frame,
            f"Tamanho mín. defeito: {self.min_defect_area}",
            self.min_defect_area_var,
            self._on_min_defect_area_change
        )

        # Botões e switches continuam iguais
        self.btn_defects = ctk.CTkButton(
            self.left_panel, text="Mostrar Defeitos",
            command=self._show_defects
        )
        self.btn_defects.pack(pady=5)

        # The toggle_contours switch and its variable are already correctly placed in __init__
        self.toggle_contours = ctk.CTkSwitch(
            self.left_panel,
            text="Mostrar Contornos dos Defeitos",
            variable=self.show_contours_var, # This variable is already initialized in __init__
            command=self._toggle_defect_contours,
        )
        self.toggle_contours.pack(pady=10)

        # DefeitosInfo
        # The total_defects_var is also initialized in __init__
        frame_td = ctk.CTkFrame(self.sliders_frame, fg_color="transparent")  # Use transparent frame
        frame_td.pack(fill="x", pady=25)  # Pack this horizontal pair frame vertically
        self.total_defects_count_label = ctk.CTkLabel(frame_td, text="Total de defeitos")
        self.total_defects_count_label.pack(side="left", padx=(0, 10))
        self.total_defects_entry = ctk.CTkEntry(frame_td, textvariable=self.total_defects_var,
                                                state="readonly", width=50, text_color="red")
        self.total_defects_entry.pack(side="right")


        # Área da imagem à direita
        self.frame_img = ctk.CTkFrame(self, width=s[0] + 4, height=s[1] + 4, fg_color="gray80")
        self.frame_img.pack(side="left", padx=10, pady=10)
        self.frame_img.pack_propagate(False)

        self.lbl_img = ctk.CTkLabel(self.frame_img, text="")
        self.lbl_img.bind("<Motion>", self.on_mouse_move)

        self.lbl_img.pack(padx=2, pady=2)

        # painel direita
        self.right_panel = ctk.CTkFrame(self)
        self.right_panel.pack(side="right", fill="y", expand=True, padx=10, pady=10, )

        # Criar o CTkTextbox antes de o configurar
        self.area_info_textbox = ctk.CTkTextbox(self.right_panel, height=200, width=200)
        self.area_info_textbox.pack(pady=10)

        # Criar tooltip para mostrar diferença no mouse
        self.tooltip_img = ctk.CTkLabel(self.right_panel, text="", width= 100, height=100)
        self.tooltip_img.pack(pady=10)

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
        self.show_defect_contours = self.show_contours_var.get()
        self._update_defect_image()

    def _recalculate_defects(self):
        # --- UPDATED CALL TO DETECT_DEFECTS ---
        self.defect_mask, self.defect_contours, \
        self.darker_mask_filtered, self.yellow_mask, \
        self.blue_mask, self.red_mask = detect_defects( # <-- NEW RETURN VALUES
            self.template_masked,
            self.current_masked,
            self.mask_full,
            self.dark_threshold,
            self.bright_threshold,
            self.dark_morph_kernel_size,
            self.dark_morph_iterations,
            self.bright_morph_kernel_size,
            self.bright_morph_iterations,
            self.min_defect_area,
            self.dark_gradient_threshold,
            self.blue_threshold, # <-- NEW
            self.red_threshold   # <-- NEW
        )
        self._update_defect_image()

    def _update_defect_image(self):
        start_time = time.time()
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

        end_time = time.time()

        print(f"_detect_defects demorou {end_time - start_time:.4f} segundos")

    def on_mouse_move(self, event):
        x, y = event.x, event.y

        img_h, img_w = self.current_full.shape[:2]
        lbl_w = self.lbl_img.winfo_width()
        lbl_h = self.lbl_img.winfo_height()

        if lbl_w == 0 or lbl_h == 0:
            return

        img_x = int(x * img_w / lbl_w)
        img_y = int(y * img_h / lbl_h)

        # Limita área 50x50 para zoom
        x1 = max(img_x - 10, 0)
        y1 = max(img_y - 10, 0)
        x2 = min(img_x + 10, img_w)
        y2 = min(img_y + 10, img_h)

        # Converte imagens para grayscale
        tpl_gray = cv2.cvtColor(self.template_full, cv2.COLOR_BGR2GRAY)
        cur_gray = cv2.cvtColor(self.current_full, cv2.COLOR_BGR2GRAY)

        region_tpl = tpl_gray[y1:y2, x1:x2]
        region_cur = cur_gray[y1:y2, x1:x2]

        # Point values
        tpl_gray_val = int(tpl_gray[img_y, img_x])
        cur_gray_val = int(cur_gray[img_y, img_x])
        dark_diff_val = tpl_gray_val - cur_gray_val # Difference for darker defects

        tpl_lab = cv2.cvtColor(self.template_full, cv2.COLOR_BGR2LAB)
        cur_lab = cv2.cvtColor(self.current_full, cv2.COLOR_BGR2LAB)
        tpl_a_val = int(tpl_lab[img_y, img_x, 1]) # A channel value
        cur_a_val = int(cur_lab[img_y, img_x, 1])
        tpl_b_val = int(tpl_lab[img_y, img_x, 2]) # B channel value
        cur_b_val = int(cur_lab[img_y, img_x, 2])

        # Differences for tooltip display
        yellow_diff = cur_b_val - tpl_b_val # Positive if more yellow
        blue_diff = tpl_b_val - cur_b_val   # Positive if more blue (template B > current B)
        red_diff = cur_a_val - tpl_a_val    # Positive if more red (current A > template A)


        # Valor da máscara geral
        mask_val = self.mask_full[img_y, img_x]

        # Intermediate masks for debugging/info
        try:
            darker_mask_val = self.darker_mask_filtered[img_y, img_x]
            yellow_mask_val = self.yellow_mask[img_y, img_x] # Renamed from bright_mask_val for clarity
            blue_mask_val = self.blue_mask[img_y, img_x]     # <-- NEW
            red_mask_val = self.red_mask[img_y, img_x]       # <-- NEW
        except AttributeError: # Handles initial state before masks are fully processed
            darker_mask_val = "-"
            yellow_mask_val = "-"
            blue_mask_val = "-"
            red_mask_val = "-"


        # Prepara imagem em zoom
        zoom_img = cv2.resize(region_cur, (80, 80), interpolation=cv2.INTER_NEAREST)
        zoom_img_rgb = cv2.cvtColor(zoom_img, cv2.COLOR_GRAY2RGB)
        pil_img = Image.fromarray(zoom_img_rgb)
        self.zoom_imgtk = ImageTk.PhotoImage(pil_img)

        self.tooltip_img.configure(image=self.zoom_imgtk)
        self.tooltip_img.image = self.zoom_imgtk

        # Text detail, updated to reflect current state
        text = (
            f"Coords: ({img_x},{img_y})\n"
            f"Máscara Ativa: {mask_val}\n"
            f"Pix (T,C): ({tpl_gray_val},{cur_gray_val}) Δ={dark_diff_val}\n"
            f"LAB A (T,C): ({tpl_a_val},{cur_a_val}) Δ={red_diff} (Vermelho)\n" # <-- NEW LAB A info
            f"LAB B (T,C): ({tpl_b_val},{cur_b_val}) Δ={yellow_diff} (Amarelo)\n" # <-- Updated LAB B for yellow
            f"                  Δ={blue_diff} (Azul)\n" # <-- New LAB B info for blue
            f"Th Escuro: {self.dark_threshold} (Mask={darker_mask_val})\n"
            f"Th Amarelo: {self.bright_threshold} (Mask={yellow_mask_val})\n" # <-- Updated Label
            f"Th Azul: {self.blue_threshold} (Mask={blue_mask_val})\n"         # <-- NEW
            f"Th Vermelho: {self.red_threshold} (Mask={red_mask_val})\n"     # <-- NEW
            f"K/It Escuro: {self.dark_morph_kernel_size}/{self.dark_morph_iterations}\n"
            f"K/It Colorido: {self.bright_morph_kernel_size}/{self.bright_morph_iterations}\n" # <-- Updated Label
            f"Gradiente Escuro: {self.dark_gradient_threshold}\n"
            f"Área mín: {self.min_defect_area}"
        )
        self.area_info_textbox.configure(state="normal")
        self.area_info_textbox.delete("0.0", "end")
        self.area_info_textbox.insert("0.0", text)
        self.area_info_textbox.configure(state="disabled")

    # --- NEW: Separate Change Handlers for Dark Morphology ---
    def _on_dark_kernel_change(self, event):
        val = self.dark_kernel_var.get()
        if val != "":
            k = int(val)
            # The actual kernel size correction is now done inside detect_defects
            k = max(1, min(k, 15)) # Clamp value
            self.dark_morph_kernel_size = k
            self.dark_kernel_label.configure(text=f"Kernel Escuro: {self.dark_morph_kernel_size}")
            self._recalculate_defects()
            self._save_params()
            if str(k) != val:
                self.dark_kernel_var.set(str(k)) # Update entry if value was clamped

    def _on_blue_threshold_change(self, event):
        val = self.blue_threshold_var.get()
        if val != "":
            self.blue_threshold = int(val)
            self.blue_threshold_label.configure(text=f"Threshold Azul: {self.blue_threshold}")
            self._recalculate_defects()
            self._save_params()

    def _on_red_threshold_change(self, event):
        val = self.red_threshold_var.get()
        if val != "":
            self.red_threshold = int(val)
            self.red_threshold_label.configure(text=f"Threshold Vermelho: {self.red_threshold}")
            self._recalculate_defects()
            self._save_params()

    def _on_dark_iterations_change(self, event):
        val = self.dark_iterations_var.get()
        if val != "":
            i = int(val)
            i = max(1, min(i, 10)) # Clamp value
            self.dark_morph_iterations = i
            self.dark_iterations_label.configure(text=f"Iterações Escuro: {self.dark_morph_iterations}")
            self._recalculate_defects()
            self._save_params()
            if str(i) != val:
                self.dark_iterations_var.set(str(i))

    # --- NEW: Separate Change Handlers for Bright Morphology ---
    def _on_bright_kernel_change(self, event):
        val = self.bright_kernel_var.get()
        if val != "":
            k = int(val)
            # The actual kernel size correction is now done inside detect_defects
            k = max(1, min(k, 15)) # Clamp value
            self.bright_morph_kernel_size = k
            self.bright_kernel_label.configure(text=f"Kernel Claro: {self.bright_morph_kernel_size}")
            self._recalculate_defects()
            self._save_params()
            if str(k) != val:
                self.bright_kernel_var.set(str(k))

    def _on_bright_iterations_change(self, event):
        val = self.bright_iterations_var.get()
        if val != "":
            i = int(val)
            i = max(1, min(i, 10)) # Clamp value
            self.bright_morph_iterations = i
            self.bright_iterations_label.configure(text=f"Iterações Claro: {self.bright_morph_iterations}")
            self._recalculate_defects()
            self._save_params()
            if str(i) != val:
                self.bright_iterations_var.set(str(i))

    # Existing change handlers for thresholds and min_defect_area
    def _on_dark_threshold_change(self, event):
        val = self.dark_threshold_var.get()
        if val != "":
            self.dark_threshold = int(val)
            self.dark_threshold_label.configure(text=f"Threshold Escuro: {self.dark_threshold}")
            self._recalculate_defects()
            self._save_params()
    def _on_dark_gradient_threshold_change(self, event):
        val = self.dark_gradient_threshold_var.get()
        if val != "":
            self.dark_gradient_threshold = int(val)
            self.dark_gradient_threshold.configure(text=f"Gradient Threshold Escuro: {self.dark_gradient_threshold}")
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

    def _toggle_image(self):
        if self.toggle.get():
            self.lbl_img.configure(image=self.tk_template)
            self.lbl_img.image = self.tk_template
        else:
            self.lbl_img.configure(image=self.tk_aligned)
            self.lbl_img.image = self.tk_aligned

    def _show_defects(self):
        self.total_defects_var.set(str(len(self.defect_contours)))
        self.lbl_img.configure(image=self.tk_defect)
        self.lbl_img.image = self.tk_defect

    def _save_params(self):
        params = {
            "dark_threshold": self.dark_threshold,
            "bright_threshold": self.bright_threshold,
            "blue_threshold": self.blue_threshold, # <-- NEW
            "red_threshold": self.red_threshold,   # <-- NEW
            "dark_morph_kernel_size": self.dark_morph_kernel_size,
            "dark_morph_iterations": self.dark_morph_iterations,
            "bright_morph_kernel_size": self.bright_morph_kernel_size,
            "bright_morph_iterations": self.bright_morph_iterations,
            "dark_gradient_threshold": self.dark_gradient_threshold,
            "detect_area": self.min_defect_area
        }
        with open(self.param_path, "w") as f:
            json.dump(params, f, indent=4)