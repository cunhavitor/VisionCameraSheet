import json
import time

import customtkinter as ctk
import cv2
from PIL import Image, ImageDraw
from customtkinter import CTkImage
from shapely.geometry import Polygon, Point

from config.config import INSPECTION_PREVIEW_WIDTH, INSPECTION_PREVIEW_HEIGHT
from config.utils import load_params
from models.align_image import align_with_template
from models.defect_detector import detect_defects
from widgets.param_entry_hor import create_param_entry
from windows.defect_tuner_window import DefectTunerWindow


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
            #area = cv2.contourArea(cnt)
            #perimeter = cv2.arcLength(cnt, True)

            # Desenhar contorno redimensionado
            pts = [(int(pt[0][0] * sx), int(pt[0][1] * sy)) for pt in cnt]
            draw.line(pts + [pts[0]], fill="red", width=2)

    return CTkImage(light_image=pil, dark_image=pil, size=size)


class InspectionWindow(ctk.CTkToplevel):
    def __init__(self, parent, template_path, current_path, mask_path, user_type="User", user=""):
        super().__init__(parent)

        self.template_masked = None
        self.current_masked = None
        self.aligned_full = None
        self.mask_full = None
        self.current_full = None
        self.template_full = None
        self.param_path = None
        self.tuner_window = None
        self.bright_threshold_label = None
        self.dark_threshold_label = None
        self.bright_iterations_label = None
        self.bright_kernel_label = None
        self.dark_iterations_label = None
        self.red_threshold_label = None
        self.blue_threshold_label = None
        self.dark_kernel_label = None
        self.dark_gradient_threshold_entry = None
        self.bright_iterations_entry = None
        self.bright_kernel_entry = None
        self.dark_iterations_entry = None
        self.dark_kernel_entry = None
        self.red_threshold_entry = None
        self.blue_threshold_entry = None
        self.bright_threshold_entry = None
        self.dark_threshold_entry = None
        self.template_path = template_path
        self.current_path = current_path
        self.mask_path = mask_path

        self.zoom_imgtk = None
        self.area_info_textbox = None
        self.state("zoomed")
        self.title("Janela de Inspeção")

        self.user_type = user_type
        self.user = user

        s = (INSPECTION_PREVIEW_WIDTH, INSPECTION_PREVIEW_HEIGHT)
        self.template_full = cv2.imread(self.template_path)
        self.mask_full = cv2.imread(self.mask_path, cv2.IMREAD_GRAYSCALE)

        self.mask1 = cv2.imread("data/mask/leaf_mask1.png", cv2.IMREAD_GRAYSCALE)
        self.mask2 = cv2.imread("data/mask/leaf_mask2.png", cv2.IMREAD_GRAYSCALE)

        self.template_masked = cv2.bitwise_and(self.template_full, self.template_full, mask=self.mask_full)
        self.tk_template = _prepare_image_grayscale(self.template_masked, s)


        # load params
        self._load_params()

        self.show_defect_contours = self.show_contours_var.get()

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
            variable=self.show_contours_var,  # This variable is already initialized in __init__
            command=self._toggle_defect_contours,
        )
        self.toggle_contours.pack(pady=10)

        # DefeitosInfo

        self.label_info = ctk.CTkLabel(
            self.sliders_frame,
            text="Total de defeitos\n(verificados)",  # texto inicial
            justify="left",
            width=200,  # largura fixa
            wraplength=200,  # quebra linha automática com base na largura
            anchor="nw"  # alinha no topo à esquerda (opcional)
        )
        self.label_info.pack(side="left", padx=(0, 40), pady=(40, 40))

        # Tuner Window
        self.button_tuner_window = ctk.CTkButton(
            self.left_panel, text="Tuner Window",
            command=self.open_tuner_window
        )
        self.button_tuner_window.pack(pady=5)

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
        self.area_info_textbox = ctk.CTkTextbox(self.right_panel, height=200, width=250)
        self.area_info_textbox.pack(pady=10)

        # Criar tooltip para mostrar diferença no rato
        self.tooltip_img = ctk.CTkLabel(self.right_panel, text="", width=150, height=150)
        self.tooltip_img.pack(pady=10)

        # Janela fixa
        self.geometry(f"{s[0] + 200}x{s[1] + 40}")
        self.resizable(False, False)

        if self.user_type == "User":
            self.dark_threshold_entry.configure(state="disabled", fg_color="gray70")
            self.bright_threshold_entry.configure(state="disabled", fg_color="gray70")
            self.blue_threshold_entry.configure(state="disabled", fg_color="gray70")
            self.red_threshold_entry.configure(state="disabled", fg_color="gray70")
            self.dark_kernel_entry.configure(state="disabled", fg_color="gray70")
            self.dark_iterations_entry.configure(state="disabled", fg_color="gray70")
            self.bright_kernel_entry.configure(state="disabled", fg_color="gray70")
            self.bright_iterations_entry.configure(state="disabled", fg_color="gray70")
            self.dark_gradient_threshold_entry.configure(state="disabled", fg_color="gray70")
            self.min_defect_area_entry.configure(state="disabled", fg_color="gray70")

    def _load_params(self):
        # parameters adjustable (default values)
        self.param_path = "config/inspection_params.json"
        params = load_params(self.param_path)

        self.dark_threshold = int(params.get("dark_threshold", 30))
        self.bright_threshold = int(params.get("bright_threshold", 30))
        self.dark_morph_kernel_size = int(params.get("dark_morph_kernel_size", 3))
        self.dark_morph_iterations = int(params.get("dark_morph_iterations", 1))
        self.bright_morph_kernel_size = int(params.get("bright_morph_kernel_size", 3))
        self.bright_morph_iterations = int(params.get("bright_morph_iterations", 1))
        self.min_defect_area = int(params.get("detect_area", 1))
        self.dark_gradient_threshold = int(params.get("dark_gradient_threshold", 10))
        self.blue_threshold = int(params.get("blue_threshold", 25))
        self.red_threshold = int(params.get("red_threshold", 25))

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

    def open_tuner_window(self):
        # 1) Load images and mask
        self.template_full = cv2.imread(self.template_path)
        self.current_full = cv2.imread(self.current_path)

        self.mask_full = cv2.imread(self.mask_path, cv2.IMREAD_GRAYSCALE)

        # 2) Align current image to template
        self.aligned_full, M = align_with_template(self.current_full, self.template_full)

        # 3) Apply original mask (template space) to aligned image
        self.current_masked = cv2.bitwise_and(self.aligned_full, self.aligned_full, mask=self.mask_full)
        self.template_masked = cv2.bitwise_and(self.template_full, self.template_full, mask=self.mask_full)

        self.withdraw()  # Esconde a janela de inspeção
        self.tuner_window = DefectTunerWindow(
            master=self,
            tpl_img=self.template_masked,
            aligned_img=self.current_masked,
            mask=self.mask_full,
            reopen_callback=self._on_tuner_close,
            user_type=self.user_type,
            user_name=self.user
        )
        self.tuner_window.protocol("WM_DELETE_WINDOW", self._on_tuner_close)

    def _on_tuner_close(self):
        self.deiconify()  # Reabre a janela de inspeção
        self.state("zoomed")
        self._load_params()
        self._analisar_latas_com_defeito()



    def _show_defects(self):
        total_start = time.perf_counter()
        s = (INSPECTION_PREVIEW_WIDTH, INSPECTION_PREVIEW_HEIGHT)

        # 1) Leitura da imagem
        t0 = time.perf_counter()
        self.current_full = cv2.imread(self.current_path)
        print(f"[Tempo] Leitura da imagem: {time.perf_counter() - t0:.4f} segundos")

        # 2) Alinhamento com template
        t0 = time.perf_counter()
        self.aligned_full, M = align_with_template(self.current_full, self.template_full)
        print(f"[Tempo] Alinhamento com template: {time.perf_counter() - t0:.4f} segundos")

        # 3) Aplicação da máscara
        t0 = time.perf_counter()
        self.current_masked = cv2.bitwise_and(self.aligned_full, self.aligned_full, mask=self.mask_full)
        print(f"[Tempo] Aplicação de máscara: {time.perf_counter() - t0:.4f} segundos")

        # 4) Detecção de defeitos
        t0 = time.perf_counter()
        self.defect_mask, self.defect_contours, \
            self.darker_mask_filtered, self.yellow_mask, \
            self.blue_mask, self.red_mask = detect_defects(
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
            self.blue_threshold,
            self.red_threshold
        )
        print(f"[Tempo] Detecção de defeitos: {time.perf_counter() - t0:.4f} segundos")

        # 5) Preparação para visualização
        t0 = time.perf_counter()
        self.tk_aligned = _prepare_image_grayscale(self.current_masked, s)
        self.tk_defect = _prepare_image_grayscale(self.current_masked, s, draw_contours=self.defect_contours)
        print(f"[Tempo] Preparação para visualização: {time.perf_counter() - t0:.4f} segundos")

        # 6) Atualização da interface
        t0 = time.perf_counter()
        self.total_defects_var.set(str(len(self.defect_contours)))
        self._analisar_latas_com_defeito()

        if self.toggle_contours.get():
            self.lbl_img.configure(image=self.tk_defect)
            self.lbl_img.image = self.tk_defect
        else:
            self.lbl_img.configure(image=self.tk_aligned)
            self.lbl_img.image = self.tk_aligned
        print(f"[Tempo] Atualização da interface: {time.perf_counter() - t0:.4f} segundos")

        print(f"[Tempo Total] _show_defects: {time.perf_counter() - total_start:.4f} segundos")

    def _toggle_defect_contours(self):
        self.show_defect_contours = self.show_contours_var.get()

        if self.toggle_contours.get():
            self.lbl_img.configure(image=self.tk_defect)
            self.lbl_img.image = self.tk_template
        else:
            self.lbl_img.configure(image=self.tk_aligned)
            self.lbl_img.image = self.tk_aligned

    def _analisar_latas_com_defeito(self):
        # Carrega forma base
        try:
            with open("data/mask/forma_base.json", "r") as f:
                forma_base = json.load(f)  # lista de [x, y]
        except Exception as e:
            print("❌ Erro ao carregar forma base:", e)
            return

        # Carrega instâncias
        instancias = []
        try:
            with open("data/mask/instancias_poligonos.txt", "r") as f:
                for line in f:
                    parts = line.strip().split(":")
                    if len(parts) != 2:
                        continue
                    idx_str, rest = parts
                    cx_str, cy_str, s_str = rest.split(",")
                    idx = int(idx_str)
                    cx = int(cx_str)
                    cy = int(cy_str)
                    s = float(s_str)

                    instancias.append({
                        "center": (cx, cy),
                        "scale": s,
                        "numero_lata": idx  # Usa o índice como número da lata
                    })
        except Exception as e:
            print("❌ Erro ao carregar instâncias:", e)
            return

        # Calcula os polígonos reais
        poligonos = []
        for inst in instancias:
            cx, cy = inst["center"]
            s = inst["scale"]
            pontos = [(cx + x * s, cy + y * s) for x, y in forma_base]
            poligonos.append({
                "numero_lata": inst["numero_lata"],
                "polygon": Polygon(pontos)
            })

        # Analisa defeitos
        latas_com_defeito = set()
        for cnt in self.defect_contours:
            m = cv2.moments(cnt)
            if m["m00"] == 0:
                continue
            cx = int(m["m10"] / m["m00"])
            cy = int(m["m01"] / m["m00"])
            ponto_defeito = Point(cx, cy)

            for pol in poligonos:
                if pol["polygon"].contains(ponto_defeito):
                    latas_com_defeito.add(pol["numero_lata"])
                    break

        if latas_com_defeito:
            texto = f"⚠️ Latas com defeitos: {self.total_defects_var.get()}\n\r" + ", ".join(
                str(n) for n in sorted(latas_com_defeito))
        else:
            texto = "✅ Nenhum defeito dentro das latas detectado."

        self.label_info.configure(text=texto)

        print(texto)

    def on_mouse_move(self, event):
        x, y = event.x, event.y

        img_h, img_w = self.current_full.shape[:2]
        lbl_w = self.lbl_img.winfo_width()
        lbl_h = self.lbl_img.winfo_height()

        if lbl_w == 0 or lbl_h == 0:
            return

        img_x = int(x * img_w / lbl_w)
        img_y = int(y * img_h / lbl_h)

        # Limita área para "zoom"
        x1 = max(img_x - 10, 0)
        y1 = max(img_y - 10, 0)
        x2 = min(img_x + 10, img_w)
        y2 = min(img_y + 10, img_h)

        # Converte imagens para grayscale
        tpl_gray = cv2.cvtColor(self.template_full, cv2.COLOR_BGR2GRAY)
        cur_gray = cv2.cvtColor(self.current_full, cv2.COLOR_BGR2GRAY)

        #region_tpl = tpl_gray[y1:y2, x1:x2]
        region_cur = cur_gray[y1:y2, x1:x2]

        # Point values
        tpl_gray_val = int(tpl_gray[img_y, img_x])
        cur_gray_val = int(cur_gray[img_y, img_x])
        dark_diff_val = tpl_gray_val - cur_gray_val  # Difference for darker defects

        tpl_lab = cv2.cvtColor(self.template_full, cv2.COLOR_BGR2LAB)
        cur_lab = cv2.cvtColor(self.current_full, cv2.COLOR_BGR2LAB)
        tpl_a_val = int(tpl_lab[img_y, img_x, 1])  # A channel value
        cur_a_val = int(cur_lab[img_y, img_x, 1])
        tpl_b_val = int(tpl_lab[img_y, img_x, 2])  # B channel value
        cur_b_val = int(cur_lab[img_y, img_x, 2])

        # Differences for tooltip display
        yellow_diff = cur_b_val - tpl_b_val  # Positive if more yellow
        blue_diff = tpl_b_val - cur_b_val  # Positive if more blue (template B > current B)
        red_diff = cur_a_val - tpl_a_val  # Positive if more red (current A > template A)

        # Valor da máscara geral
        mask_val = self.mask_full[img_y, img_x]

        # Intermediate masks for debugging/info
        try:
            darker_mask_val = self.darker_mask_filtered[img_y, img_x]
            yellow_mask_val = self.yellow_mask[img_y, img_x]  # Renamed from bright_mask_val for clarity
            blue_mask_val = self.blue_mask[img_y, img_x]  # <-- NEW
            red_mask_val = self.red_mask[img_y, img_x]  # <-- NEW
        except AttributeError:  # Handles initial state before masks are fully processed
            darker_mask_val = "-"
            yellow_mask_val = "-"
            blue_mask_val = "-"
            red_mask_val = "-"

        # Prepara imagem em zoom
        zoom_img = cv2.resize(region_cur, (150, 150), interpolation=cv2.INTER_NEAREST)
        zoom_img_rgb = cv2.cvtColor(zoom_img, cv2.COLOR_GRAY2RGB)
        pil_img = Image.fromarray(zoom_img_rgb)
        self.zoom_imgtk = CTkImage(light_image=pil_img, size=(150, 150))

        self.tooltip_img.configure(image=self.zoom_imgtk)
        self.tooltip_img.image = self.zoom_imgtk

        # Text detail, updated to reflect current state
        text = (
            f"Coords: ({img_x},{img_y})\n"
            f"Máscara Ativa: {mask_val}\n"
            f"Pix (T,C): ({tpl_gray_val},{cur_gray_val}) Δ={dark_diff_val}\n"
            f"LAB A (T,C): ({tpl_a_val},{cur_a_val}) Δ={red_diff} (Vermelho)\n"  # <-- NEW LAB A info
            f"LAB B (T,C): ({tpl_b_val},{cur_b_val}) Δ={yellow_diff} (Amarelo)\n"  # <-- Updated LAB B for yellow
            f"                  Δ={blue_diff} (Azul)\n"  # <-- New LAB B info for blue
            f"Th Escuro: {self.dark_threshold} (Mask={darker_mask_val})\n"
            f"Th Amarelo: {self.bright_threshold} (Mask={yellow_mask_val})\n"  # <-- Updated Label
            f"Th Azul: {self.blue_threshold} (Mask={blue_mask_val})\n"  # <-- NEW
            f"Th Vermelho: {self.red_threshold} (Mask={red_mask_val})\n"  # <-- NEW
            f"K/It Escuro: {self.dark_morph_kernel_size}/{self.dark_morph_iterations}\n"
            f"K/It Colorido: {self.bright_morph_kernel_size}/{self.bright_morph_iterations}\n"  # <-- Updated Label
            f"Gradiente Escuro: {self.dark_gradient_threshold}\n"
            f"Área mín: {self.min_defect_area}"
        )
        self.area_info_textbox.configure(state="normal")
        self.area_info_textbox.delete("0.0", "end")
        self.area_info_textbox.insert("0.0", text)
        self.area_info_textbox.configure(state="disabled")

    def _on_min_defect_area_change(self, event):
        val = self.min_defect_area_var.get()
        if val != "":
            self.min_defect_area = int(val)
            self.min_defect_area_label.configure(text=f"Tamanho mín. defeito: {self.min_defect_area}")
            self._show_defects()
            self._save_params()

    #toggle template or image
    def _toggle_image(self):
        if self.toggle.get():
            self.lbl_img.configure(image=self.tk_template)
            self.lbl_img.image = self.tk_template
            self.toggle_contours.configure(state="disabled")
        else:
            self.toggle_contours.configure(state="normal")
            if self.toggle_contours.get():
                self.lbl_img.configure(image=self.tk_defect)
                self.lbl_img.image = self.tk_template
            else:
                self.lbl_img.configure(image=self.tk_aligned)
                self.lbl_img.image = self.tk_aligned

    def _save_params(self):
        params = {
            "dark_threshold": self.dark_threshold,
            "bright_threshold": self.bright_threshold,
            "blue_threshold": self.blue_threshold,  # <-- NEW
            "red_threshold": self.red_threshold,  # <-- NEW
            "dark_morph_kernel_size": self.dark_morph_kernel_size,
            "dark_morph_iterations": self.dark_morph_iterations,
            "bright_morph_kernel_size": self.bright_morph_kernel_size,
            "bright_morph_iterations": self.bright_morph_iterations,
            "dark_gradient_threshold": self.dark_gradient_threshold,
            "detect_area": self.min_defect_area
        }
        with open(self.param_path, "w") as f:
            json.dump(params, f, indent=4)

