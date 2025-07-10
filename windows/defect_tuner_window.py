import csv
import json
import os
from datetime import datetime

import customtkinter as ctk
import cv2
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from customtkinter import CTkImage
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from config.config import INSPECTION_PREVIEW_WIDTH, INSPECTION_PREVIEW_HEIGHT
from config.utils import center_window
from models.defect_detector import detect_defects
from widgets.param_entry_simple_numeric import create_param_entry


class DefectTunerWindow(ctk.CTkToplevel):
    def __init__(self, master, tpl_img, aligned_img, mask, reopen_callback=None,user_type="User", user_name=""):
        super().__init__(master)
        self.silent_mode = True

        s = (INSPECTION_PREVIEW_WIDTH, INSPECTION_PREVIEW_HEIGHT)
        self.user_type=user_type
        self.user_name=user_name

        self.reopen_callback = reopen_callback
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.state("zoomed")
        self.title("Ajuste de Parâmetros de Defeitos")
        center_window(self, 1050, 800)

        self.tpl = tpl_img
        self.aligned = aligned_img
        self.mask = mask

        # Valores padrão (base)
        self.dark_threshold = 30
        self.bright_threshold = 30
        self.blue_threshold = 25
        self.red_threshold = 25
        self.dark_morph_kernel_size = 3
        self.dark_morph_iterations = 1
        self.bright_morph_kernel_size = 3
        self.bright_morph_iterations = 1
        self.dark_gradient_threshold = 10
        self.min_defect_area = 1

        # StringVars (valores iniciais convertidos para string)
        self.dark_threshold_var = ctk.StringVar(value=str(self.dark_threshold))
        self.bright_threshold_var = ctk.StringVar(value=str(self.bright_threshold))
        self.blue_threshold_var = ctk.StringVar(value=str(self.blue_threshold))
        self.red_threshold_var = ctk.StringVar(value=str(self.red_threshold))
        self.dark_kernel_var = ctk.StringVar(value=str(self.dark_morph_kernel_size))
        self.dark_iterations_var = ctk.StringVar(value=str(self.dark_morph_iterations))
        self.bright_kernel_var = ctk.StringVar(value=str(self.bright_morph_kernel_size))
        self.bright_iterations_var = ctk.StringVar(value=str(self.bright_morph_iterations))
        self.dark_gradient_threshold_var = ctk.StringVar(value=str(self.dark_gradient_threshold))
        self.min_defect_area_var = ctk.StringVar(value=str(self.min_defect_area))

        self.view_mode = ctk.StringVar(value="Final")
        self.display_mode = ctk.StringVar(value="Colorida")

        self.control_frame = ctk.CTkFrame(self, width=500)
        self.control_frame.pack(side="left", fill="y", padx=10, pady=10)
        self.control_frame.propagate(False)

        self.container_sliders = ctk.CTkFrame(self.control_frame, fg_color="transparent")
        self.container_sliders.pack(padx=30, pady=10, fill="x")

        self._create_sliders()

        self.right_frame = ctk.CTkFrame(self)
        self.right_frame.pack(side="top", anchor="nw", padx=10, pady=10)

        self.image_frame = ctk.CTkFrame(
            self.right_frame,
            fg_color="gray80",
        )
        self.image_frame.pack(padx=10, pady=10)

        self.image_label = ctk.CTkLabel(self.image_frame, text="")
        self.image_label.pack(padx=4, pady=4)

        self.graph_frame = ctk.CTkFrame(self.image_frame)
        self.graph_frame.pack()
        self.graph_frame.pack_forget()  # Oculta inicialmente

        self.fig, self.ax = plt.subplots(figsize=(12, 9))
        self.canvas_plot = FigureCanvasTkAgg(self.fig, master=self.graph_frame)
        self.canvas_plot.get_tk_widget().pack()

        self._restore_saved_params()
        self._create_buttons()
        self._update_preview()

        self.silent_mode = False  # <- ativa a execução normal
        self._update_preview()  # primeira atualização após carregar tudo

    def _on_close(self):
        print("🔁 Tuner fechado, a reabrir inspection...")
        self.destroy()
        if self.reopen_callback:
            self.reopen_callback()  # <- chama para reabrir o inspection

    def _create_sliders(self):
        self.dark_threshold_entry = create_param_entry(
            self.container_sliders, "Threshold Escuro", self.dark_threshold_var,
            command=self._on_dark_threshold_change,
            step=1, min_value=0, max_value=255)

        self.bright_threshold_entry = create_param_entry(
            self.container_sliders, "Threshold Amarelo", self.bright_threshold_var,
            command=self._on_bright_threshold_change,
            step=1, min_value=0, max_value=255)

        self.blue_threshold_entry = create_param_entry(
            self.container_sliders, "Threshold Azul", self.blue_threshold_var,
            command=self._on_blue_threshold_change,
            step=1, min_value=0, max_value=255)

        self.red_threshold_entry = create_param_entry(
            self.container_sliders, "Threshold Vermelho", self.red_threshold_var,
            command=self._on_red_threshold_change,
            step=1, min_value=0, max_value=255)

        self.dark_kernel_entry = create_param_entry(
            self.container_sliders, "Kernel Escuro", self.dark_kernel_var,
            command=self._on_dark_kernel_change,
            step=2, min_value=1, max_value=15)  # kernel ímpar, passo 2 para facilitar

        self.dark_iterations_entry = create_param_entry(
            self.container_sliders, "Iterações Escuro", self.dark_iterations_var,
            command=self._on_dark_iterations_change,
            step=1, min_value=1, max_value=10)

        self.bright_kernel_entry = create_param_entry(
            self.container_sliders, "Kernel Colorido", self.bright_kernel_var,
            command=self._on_bright_kernel_change,
            step=2, min_value=1, max_value=15)

        self.bright_iterations_entry = create_param_entry(
            self.container_sliders, "Iterações Colorido", self.bright_iterations_var,
            command=self._on_bright_iterations_change,
            step=1, min_value=1, max_value=10)

        self.dark_gradient_threshold_entry = create_param_entry(
            self.container_sliders, "Gradiente Escuro", self.dark_gradient_threshold_var,
            command=self._on_dark_gradient_threshold_change,
            step=1, min_value=0, max_value=255)

        self.min_defect_area_entry = create_param_entry(
            self.container_sliders, "Tamanho mín. defeito", self.min_defect_area_var,
            command=self._on_min_defect_area_change,
            step=1, min_value=1, max_value=1000)

    def _add_slider(self, label, var, min_val, max_val):
        ctk.CTkLabel(self.container_sliders, text=label).pack(pady=(10, 0), padx=30)
        slider = ctk.CTkSlider(self.container_sliders, from_=min_val, to=max_val,
                               variable=var, command=lambda _: self._update_preview())
        slider.pack(padx=30)

    def _create_buttons(self):

        container1 = ctk.CTkFrame(self.control_frame, fg_color="gray")
        container1.pack(fill="x", padx=30, pady=(30, 10), )

        self.defect_count_label = ctk.CTkLabel(container1, text="", font=("Arial", 16))
        self.defect_count_label.pack(pady=(10, 10), padx=(10, 10), side="left")
        ctk.CTkButton(container1, text="Atualizar Detecção",
                      command=self._update_preview).pack(pady=(10, 10), padx=(10, 10), side="right")

        container2 = ctk.CTkFrame(self.control_frame, fg_color="gray")
        container2.pack(fill="x", padx=30, pady=10, )
        ctk.CTkLabel(container2, text="Tipo de Visualização:", font=("Arial", 16)).pack(pady=(10, 10), padx=(10, 10),
                                                                                        side="left")
        ctk.CTkOptionMenu(
            container2,
            variable=self.view_mode,
            values=["Final", "Escuro", "Amarelo", "Azul", "Vermelho", "Todos (colorido)"],
            command=lambda _: self._update_preview()
        ).pack(pady=(10, 10), padx=(10, 10), side="right")

        container3 = ctk.CTkFrame(self.control_frame, fg_color="gray")
        container3.pack(fill="x", padx=30, pady=10, )

        ctk.CTkLabel(container3, text="Modo de Fundo:", font=("Arial", 16)).pack(pady=(10, 10), padx=(10, 10),
                                                                                 side="left")
        ctk.CTkOptionMenu(
            container3,
            variable=self.display_mode,
            values=["Colorida", "PB"],
            command=lambda _: self._update_preview()
        ).pack(pady=(10, 10), padx=(10, 10), side="right")

        container_view_selector = ctk.CTkFrame(self.control_frame, fg_color="gray")
        container_view_selector.pack(fill="x", padx=30, pady=10)
        ctk.CTkLabel(container_view_selector, text="Modo de Visualização:", font=("Arial", 16)).pack(pady=10, padx=10, side="left")

        self.view_selector = ctk.StringVar(value="Imagem")
        ctk.CTkOptionMenu(
            container_view_selector,
            variable=self.view_selector,
            values=["Imagem", "Gráfico"],
            command=lambda _: self._update_preview()
        ).pack(pady=10, padx=10, side="right")


        container4 = ctk.CTkFrame(self.control_frame, fg_color="gray")
        container4.pack(fill="x", padx=30, pady=30, )

        self.btn_export = ctk.CTkButton(
            container4, text="Exportar Imagem",
            command=self._export_annotated_image
        )
        self.btn_export.pack(side="left", padx=10, pady=10)

        self.btn_save_params = ctk.CTkButton(
            container4, text="Guardar Parâmetros",
            command=self._save_current_params
        )
        self.btn_save_params.pack(side="left", padx=10, pady=10)

        self.btn_plot = ctk.CTkButton(
            container4, text="Gráfico Áreas",
            command=self._plot_defect_areas
        )
        self.btn_plot.pack(side="left", padx=10, pady=10)

    def load_polygons_from_file(self, path="data/mask/instancias_poligonos.txt"):
        """
        Lê os polígonos salvos no ficheiro e retorna um dicionário:
        {
            lata_id: {'center': (x, y), 'radius': r},
            ...
        }
        """
        polygons = {}
        with open(path, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                parts = line.strip().split(':')
                index = int(parts[0])
                values = parts[1].split(',')
                x, y, scale, lata_id = map(float, values)
                polygons[int(lata_id)] = {
                    'center': (int(x), int(y)),
                    'radius': int(scale * 25)  # escala para um raio estimado
                }
        return polygons

    def is_contour_inside_polygon(self, contour, polygon):

        """
        Verifica se o centroide do contorno está dentro do círculo estimado do polígono
        """
        M = cv2.moments(contour)
        if M['m00'] == 0:
            return False
        cx = int(M['m10'] / M['m00'])
        cy = int(M['m01'] / M['m00'])
        center = polygon['center']
        radius = polygon['radius']

        distance = np.sqrt((cx - center[0]) ** 2 + (cy - center[1]) ** 2)
        return distance <= radius

    def calcular_area_por_lata(self, mask, polygons, min_area=10):
        """
        Para uma determinada máscara binária e os polígonos das latas,
        calcula a área total de defeitos dentro de cada polígono.
        Retorna: dicionário {lata_id: soma_areas}
        """
        areas_por_lata = {lata_id: 0 for lata_id in range(1, 49)}
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area:
                continue

            for lata_id, poly in polygons.items():
                if self.is_contour_inside_polygon(cnt, poly):
                    areas_por_lata[lata_id] += area
                    break

        return areas_por_lata

    def _show_graph_view(self):
        # Exemplo de áreas por lata
        latas = list(range(1, 49))  # 1 a 48
        areas = np.random.randint(0, 180, size=len(latas))  # simulação para testar

        # Obter valor do parâmetro relevante
        param_value_map = {
            "Escuro": int(self.dark_threshold_var.get()),
            "Amarelo": int(self.bright_threshold_var.get()),
            "Azul": int(self.blue_threshold_var.get()),
            "Vermelho": int(self.red_threshold_var.get()),
        }
        selected_mode = self.view_mode.get()
        param_value = param_value_map.get(selected_mode, None)

        # Preparar gráfico
        self.ax.clear()
        self.ax.bar(latas, areas, color="gray")
        if param_value is not None:
            self.ax.axhline(y=param_value, color='red', linestyle='--', label=f"{selected_mode} = {param_value}")

        self.ax.set_xlim(0, 50)
        self.ax.set_ylim(0, 200)
        self.ax.set_xlabel("Número da Lata")
        self.ax.set_ylabel("Área de Defeito (px²)")
        self.ax.set_title(f"Áreas por Lata - {selected_mode}")
        self.ax.grid(True)
        self.ax.legend()
        self.canvas_plot.draw()

    def _plot_defect_areas(self):
        selected_mode = self.view_mode.get()
        param_map = {
            "Azul": ("blue", int(self.blue_threshold_var.get())),
            "Vermelho": ("red", int(self.red_threshold_var.get())),
            "Escuro": ("dark", int(self.dark_threshold_var.get())),
            "Amarelo": ("bright", int(self.bright_threshold_var.get()))
        }

        if selected_mode not in param_map:
            print("Modo não suportado para gráfico por lata.")
            return

        label_key, param_value = param_map[selected_mode]

        mask = self.last_masks.get(label_key)
        if mask is None:
            print(f"Máscara não encontrada para {label_key}")
            return

        # Define qual canal usar da imagem alinhada
        if label_key in ["blue", "red"]:
            canal_index = {"blue": 0, "red": 2}[label_key]
            canal_img = self.aligned[:, :, canal_index]
        elif label_key == "dark":
            canal_img = cv2.cvtColor(self.aligned, cv2.COLOR_BGR2GRAY)
        elif label_key == "bright":
            canal_img = cv2.cvtColor(self.aligned, cv2.COLOR_BGR2LAB)[:, :, 0]  # canal L

        # Carregar polígonos das latas
        polygonos = self.load_polygons_from_file("data/mask/instancias_poligonos.txt")

        # Calcular máximo por lata
        max_valores = self.calcular_max_valor_por_lata(
            canal_img, mask, polygonos, min_area=int(self.min_defect_area_var.get())
        )

        # Criar gráfico
        latas = list(range(1, 49))
        valores = [max_valores.get(lata, 0) for lata in latas]

        fig, ax = plt.subplots(figsize=(12, 5))
        bars = ax.bar(latas, valores, color='steelblue')

        # Linha horizontal indicando o threshold atual
        ax.axhline(y=param_value, color='red', linestyle='--', label=f"Threshold = {param_value}")

        # Opcional: mostra valor em cima da barra
        for i, bar in enumerate(bars):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 3,
                    f"{int(bar.get_height())}", ha='center', va='bottom', fontsize=8)

        ax.set_xlim(0, 50)
        ax.set_ylim(0, 260)
        ax.set_xlabel("Número da Lata")
        ax.set_ylabel("Valor máx. do parâmetro")
        ax.set_title(f"Valor Máximo de '{selected_mode}' por Lata")
        ax.grid(True)
        ax.legend()
        plt.tight_layout()
        plt.show()

    def _export_annotated_image(self):
        from datetime import datetime
        path = f"export/defect_preview_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        cv2.imwrite(path, self.last_preview)
        print(f"Imagem exportada para {path}")

    def calcular_max_valor_por_lata(self, image_channel, mask, polygons, min_area=10):
        """
        Para cada contorno válido dentro de uma lata, retorna o maior valor do canal (ex: azul)
        dentro do contorno, agrupado por lata_id.
        """
        max_valores = {lata_id: 0 for lata_id in range(1, 49)}
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area:
                continue

            mask_contorno = np.zeros_like(mask)
            cv2.drawContours(mask_contorno, [cnt], -1, 255, -1)  # máscara do contorno

            # Aplica a máscara ao canal de imagem
            valores = cv2.bitwise_and(image_channel, image_channel, mask=mask_contorno)

            max_valor_contorno = np.max(valores)

            for lata_id, poly in polygons.items():
                if self.is_contour_inside_polygon(cnt, poly):
                    max_valores[lata_id] = max(max_valores[lata_id], max_valor_contorno)
                    break

        return max_valores

    def _update_preview(self):
        # Para pegar valores atuais, converte os StringVars para int
        try:
            dark_th = int(self.dark_threshold_var.get())
            bright_th = int(self.bright_threshold_var.get())
            blue_th = int(self.blue_threshold_var.get())
            red_th = int(self.red_threshold_var.get())
            dark_kernel = int(self.dark_kernel_var.get())
            dark_iter = int(self.dark_iterations_var.get())
            bright_kernel = int(self.bright_kernel_var.get())
            bright_iter = int(self.bright_iterations_var.get())
            dark_grad = int(self.dark_gradient_threshold_var.get())
            min_area = int(self.min_defect_area_var.get())
        except Exception as e:
            print(f"Erro na conversão dos parâmetros: {e}")
            return

        final_mask, all_contours, darker_mask, bright_mask, blue_mask, red_mask = detect_defects(
            self.tpl, self.aligned, self.mask,
            dark_th, bright_th,
            dark_kernel, dark_iter,
            bright_kernel, bright_iter,
            min_area, dark_grad,
            blue_th, red_th
        )

        selected_mode = self.view_mode.get()

        # Escolher imagem base
        if self.display_mode.get() == "PB":
            preview = cv2.cvtColor(self.aligned, cv2.COLOR_BGR2GRAY)
            preview = cv2.cvtColor(preview, cv2.COLOR_GRAY2BGR)
        else:
            preview = self.aligned.copy()

        # Escolher máscara e cor dos contornos
        if selected_mode == "Escuro":
            mask_to_show = darker_mask
            contours_display, _ = cv2.findContours(mask_to_show, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            color = (255, 0, 0)  # Azul
            num_defeitos = 0
            for cnt in contours_display:
                if cv2.contourArea(cnt) >= int(self.min_defect_area_var.get()):
                    cv2.drawContours(preview, [cnt], -1, color, 3)
                    num_defeitos += 1

        elif selected_mode == "Amarelo":
            mask_to_show = bright_mask
            contours_display, _ = cv2.findContours(mask_to_show, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            color = (0, 255, 255)  # Amarelo
            num_defeitos = 0
            for cnt in contours_display:
                if cv2.contourArea(cnt) >= int(self.min_defect_area_var.get()):
                    cv2.drawContours(preview, [cnt], -1, color, 3)
                    num_defeitos += 1

        elif selected_mode == "Azul":
            mask_to_show = blue_mask
            contours_display, _ = cv2.findContours(mask_to_show, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            color = (255, 255, 0)  # Ciano
            num_defeitos = 0
            for cnt in contours_display:
                if cv2.contourArea(cnt) >= int(self.min_defect_area_var.get()):
                    cv2.drawContours(preview, [cnt], -1, color, 3)
                    num_defeitos += 1

        elif selected_mode == "Vermelho":
            mask_to_show = red_mask
            contours_display, _ = cv2.findContours(mask_to_show, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            color = (0, 0, 255)  # Vermelho
            num_defeitos = 0
            for cnt in contours_display:
                if cv2.contourArea(cnt) >= int(self.min_defect_area_var.get()):
                    cv2.drawContours(preview, [cnt], -1, color, 3)
                    num_defeitos += 1

        elif selected_mode == "Todos (colorido)":
            num_defeitos = 0

            # Escuro – Azul
            contours_dark, _ = cv2.findContours(darker_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours_dark:
                if cv2.contourArea(cnt) >= int(self.min_defect_area_var.get()):
                    cv2.drawContours(preview, [cnt], -1, (255, 0, 0), 3)
                    num_defeitos += 1

            # Amarelo – Amarelo
            contours_bright, _ = cv2.findContours(bright_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours_bright:
                if cv2.contourArea(cnt) >= int(self.min_defect_area_var.get()):
                    cv2.drawContours(preview, [cnt], -1, (0, 255, 255), 3)
                    num_defeitos += 1

            # Azul – Ciano
            contours_blue, _ = cv2.findContours(blue_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours_blue:
                if cv2.contourArea(cnt) >= int(self.min_defect_area_var.get()):
                    cv2.drawContours(preview, [cnt], -1, (255, 255, 0), 3)
                    num_defeitos += 1

            # Vermelho – Vermelho
            contours_red, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours_red:
                if cv2.contourArea(cnt) >= int(self.min_defect_area_var.get()):
                    cv2.drawContours(preview, [cnt], -1, (0, 0, 255), 3)
                    num_defeitos += 1

        else:  # Final combinado
            mask_to_show = final_mask
            contours_display, _ = cv2.findContours(mask_to_show, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            color = (0, 255, 0)  # Verde
            num_defeitos = 0
            for cnt in contours_display:
                if cv2.contourArea(cnt) >= int(self.min_defect_area_var.get()):
                    cv2.drawContours(preview, [cnt], -1, color, 3)
                    num_defeitos += 1

        # Obter contornos e desenhar com cor apropriada
        contours_display, _ = cv2.findContours(mask_to_show, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        num_defeitos = 0
        for cnt in contours_display:
            area = cv2.contourArea(cnt)
            if area >= int(self.min_defect_area_var.get()):
                cv2.drawContours(preview, [cnt], -1, color, 3)
                num_defeitos += 1

        # Atualizar label de contagem
        self.defect_count_label.configure(text=f"Total de defeitos: {num_defeitos}")

        # Guardar a imagem anotada
        self.last_preview = preview.copy()

        # Mostrar imagem
        preview_rgb = cv2.cvtColor(preview, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(preview_rgb)
        pil_img = pil_img.resize((INSPECTION_PREVIEW_WIDTH, INSPECTION_PREVIEW_HEIGHT))

        ctk_img = CTkImage(light_image=pil_img, size=(INSPECTION_PREVIEW_WIDTH, INSPECTION_PREVIEW_HEIGHT))

        if self.view_selector.get() == "Imagem":
            self.image_label.pack(padx=4, pady=4)
            self.graph_frame.pack_forget()
            self.image_label.configure(image=ctk_img)
            self.image_label.image = ctk_img
        else:
            self.image_label.pack_forget()
            self.graph_frame.pack(padx=4, pady=4)
            self._show_graph_view()

        self.last_masks = {
            "dark": darker_mask,
            "bright": bright_mask,
            "blue": blue_mask,
            "red": red_mask
        }

    def _restore_saved_params(self):
        import json
        try:
            with open("config/inspection_params.json", "r") as f:
                params = json.load(f)

            # Atualiza as StringVars (que disparam os callbacks para atualizar UI e preview)
            self.dark_threshold_var.set(str(params.get("dark_threshold", 30)))
            self.bright_threshold_var.set(str(params.get("bright_threshold", 30)))
            self.blue_threshold_var.set(str(params.get("blue_threshold", 25)))
            self.red_threshold_var.set(str(params.get("red_threshold", 25)))
            self.dark_kernel_var.set(str(params.get("dark_morph_kernel_size", 3)))
            self.dark_iterations_var.set(str(params.get("dark_morph_iterations", 1)))
            self.bright_kernel_var.set(str(params.get("bright_morph_kernel_size", 3)))
            self.bright_iterations_var.set(str(params.get("bright_morph_iterations", 1)))
            self.dark_gradient_threshold_var.set(str(params.get("dark_gradient_threshold", 10)))
            self.min_defect_area_var.set(str(params.get("detect_area", 1)))

            print("Parâmetros restaurados com sucesso.")

        except FileNotFoundError:
            print("Ficheiro de parâmetros não encontrado.")

    def _save_current_params(self):
        os.makedirs("config", exist_ok=True)
        os.makedirs("logs", exist_ok=True)

        params = {
            "dark_threshold": self.dark_threshold_var.get(),
            "bright_threshold": self.bright_threshold_var.get(),
            "blue_threshold": self.blue_threshold_var.get(),
            "red_threshold": self.red_threshold_var.get(),
            "dark_morph_kernel_size": self.dark_kernel_var.get(),
            "dark_morph_iterations": self.dark_iterations_var.get(),
            "bright_morph_kernel_size": self.bright_kernel_var.get(),
            "bright_morph_iterations": self.bright_iterations_var.get(),
            "dark_gradient_threshold": self.dark_gradient_threshold_var.get(),
            "detect_area": self.min_defect_area_var.get()
        }

        # 1. Guardar JSON principal
        with open("config/inspection_params.json", "w") as f:
            json.dump(params, f, indent=4)

        # 2. Adicionar entrada ao log CSV
        user = self.user_name
        user_type = self.user_type
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_path = "logs/param_history.csv"
        file_exists = os.path.isfile(log_path)

        with open(log_path, mode="a", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile, delimiter=';')
            if not file_exists:
                writer.writerow(["timestamp", "user", "user_type"] + list(params.keys()))
            writer.writerow([timestamp, user, user_type] + list(params.values()))

        print("Parâmetros guardados com sucesso.")

        # Os callbacks para sliders que só atualizam a preview

    def _on_dark_threshold_change(self, new_value=None):
        self.last_changed_param = "dark_threshold"
        self._update_preview()

    def _on_bright_threshold_change(self, new_value=None):
        self.last_changed_param = "bright_threshold"
        self._update_preview()

    def _on_blue_threshold_change(self, new_value=None):
        self.last_changed_param = "blue_threshold"
        self._update_preview()

    def _on_red_threshold_change(self, new_value=None):
        self.last_changed_param = "red_threshold"
        self._update_preview()

    def _on_dark_kernel_change(self, new_value=None):

        self._update_preview()

    def _on_dark_iterations_change(self, new_value=None):

        self._update_preview()

    def _on_bright_kernel_change(self, new_value=None):
        self._update_preview()

    def _on_bright_iterations_change(self, new_value=None):
        self._update_preview()

    def _on_dark_gradient_threshold_change(self, new_value=None):
        self.last_changed_param = "dark_gradient_threshold"
        self._update_preview()

    def _on_min_defect_area_change(self, new_value=None):
        self._update_preview()
