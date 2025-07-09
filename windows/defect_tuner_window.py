import customtkinter as ctk
from PIL import Image, ImageTk
import cv2

from config.utils import center_window
from models.defect_detector import detect_defects
import numpy as np
import matplotlib.pyplot as plt
from widgets.param_entry_simple_numeric import create_param_entry


class DefectTunerWindow(ctk.CTkToplevel):
    def __init__(self, master, tpl_img, aligned_img, mask,reopen_callback=None):
        super().__init__(master)

        self.reopen_callback = reopen_callback
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.title("Ajuste de Parâmetros de Defeitos")
        center_window(self, 1000, 800)

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

        self.control_frame = ctk.CTkFrame(self, width=400)
        self.control_frame.pack(side="left", fill="y", padx=10, pady=10)

        self._create_sliders()
        self.defect_count_label = ctk.CTkLabel(self.control_frame, text="")
        self.defect_count_label.pack(pady=10)

        self.image_label = ctk.CTkLabel(self, text="")
        self.image_label.pack(side="right", padx=10, pady=10)

        self._restore_saved_params()
        self._create_buttons()
        self._update_preview()

    def _on_close(self):
        print("🔁 Tuner fechado, a reabrir inspection...")
        self.destroy()
        if self.reopen_callback:
            self.reopen_callback()  # <- chama para reabrir o inspection

    def _create_sliders(self):
        self.dark_threshold_entry = create_param_entry(
            self.control_frame, "Threshold Escuro", self.dark_threshold_var,
            command=self._on_dark_threshold_change,
            step=1, min_value=0, max_value=255)

        self.bright_threshold_entry = create_param_entry(
            self.control_frame, "Threshold Amarelo", self.bright_threshold_var,
            command=self._on_bright_threshold_change,
            step=1, min_value=0, max_value=255)

        self.blue_threshold_entry = create_param_entry(
            self.control_frame, "Threshold Azul", self.blue_threshold_var,
            command=self._on_blue_threshold_change,
            step=1, min_value=0, max_value=255)

        self.red_threshold_entry = create_param_entry(
            self.control_frame, "Threshold Vermelho", self.red_threshold_var,
            command=self._on_red_threshold_change,
            step=1, min_value=0, max_value=255)

        self.dark_kernel_entry = create_param_entry(
            self.control_frame, "Kernel Escuro", self.dark_kernel_var,
            command=self._on_dark_kernel_change,
            step=2, min_value=1, max_value=15)  # kernel ímpar, passo 2 para facilitar

        self.dark_iterations_entry = create_param_entry(
            self.control_frame, "Iterações Escuro", self.dark_iterations_var,
            command=self._on_dark_iterations_change,
            step=1, min_value=1, max_value=10)

        self.bright_kernel_entry = create_param_entry(
            self.control_frame, "Kernel Colorido", self.bright_kernel_var,
            command=self._on_bright_kernel_change,
            step=2, min_value=1, max_value=15)

        self.bright_iterations_entry = create_param_entry(
            self.control_frame, "Iterações Colorido", self.bright_iterations_var,
            command=self._on_bright_iterations_change,
            step=1, min_value=1, max_value=10)

        self.dark_gradient_threshold_entry = create_param_entry(
            self.control_frame, "Gradiente Escuro", self.dark_gradient_threshold_var,
            command=self._on_dark_gradient_threshold_change,
            step=1, min_value=0, max_value=255)

        self.min_defect_area_entry = create_param_entry(
            self.control_frame, "Tamanho mín. defeito", self.min_defect_area_var,
            command=self._on_min_defect_area_change,
            step=1, min_value=1, max_value=1000)

    def _add_slider(self, label, var, min_val, max_val):
        ctk.CTkLabel(self.control_frame, text=label).pack(pady=(10, 0))
        slider = ctk.CTkSlider(self.control_frame, from_=min_val, to=max_val,
                               variable=var, command=lambda _: self._update_preview())
        slider.pack(fill="x", padx=10)

    def _create_buttons(self):
        ctk.CTkButton(self.control_frame, text="Atualizar Detecção",
                      command=self._update_preview).pack(pady=20)
        ctk.CTkLabel(self.control_frame, text="Tipo de Visualização:").pack(pady=(20, 0))
        ctk.CTkOptionMenu(
            self.control_frame,
            variable=self.view_mode,
            values=["Final", "Escuro", "Amarelo", "Azul", "Vermelho", "Todos (colorido)"],
            command=lambda _: self._update_preview()
        ).pack()
        ctk.CTkLabel(self.control_frame, text="Modo de Fundo:").pack(pady=(20, 0))
        ctk.CTkOptionMenu(
            self.control_frame,
            variable=self.display_mode,
            values=["Colorida", "PB"],
            command=lambda _: self._update_preview()
        ).pack()
        self.btn_export = ctk.CTkButton(
            self.control_frame, text="Exportar Imagem",
            command=self._export_annotated_image
        )
        self.btn_export.pack(pady=5)

        self.btn_save_params = ctk.CTkButton(
            self.control_frame, text="Guardar Parâmetros",
            command=self._save_current_params
        )
        self.btn_save_params.pack(pady=5)

        self.btn_plot = ctk.CTkButton(
            self.control_frame, text="Gráfico Áreas",
            command=self._plot_defect_areas
        )
        self.btn_plot.pack(pady=5)

    def _plot_defect_areas(self):
        def get_avg_area(mask):
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            areas = [cv2.contourArea(c) for c in contours if cv2.contourArea(c) >= int(self.min_defect_area_var.get())]
            return np.mean(areas) if areas else 0

        areas = {
            "Escuro": get_avg_area(self.last_masks["dark"]),
            "Amarelo": get_avg_area(self.last_masks["bright"]),
            "Azul": get_avg_area(self.last_masks["blue"]),
            "Vermelho": get_avg_area(self.last_masks["red"]),
        }

        plt.bar(areas.keys(), areas.values(), color=["blue", "yellow", "cyan", "red"])
        plt.title("Área média dos defeitos por tipo")
        plt.ylabel("Área (pixels)")
        plt.grid(True)
        plt.show()

    def _export_annotated_image(self):
        from datetime import datetime
        path = f"export/defect_preview_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        cv2.imwrite(path, self.last_preview)
        print(f"Imagem exportada para {path}")

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
        pil_img = pil_img.resize((900, 700))
        img_tk = ImageTk.PhotoImage(pil_img)
        self.image_label.configure(image=img_tk)
        self.image_label.image = img_tk

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
        import json, os

        os.makedirs("config", exist_ok=True)
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

        with open("config/inspection_params.json", "w") as f:
            json.dump(params, f, indent=4)

        print("Parâmetros guardados com sucesso.")

    def _on_dark_threshold_change(self, new_value=None):
        self._update_preview()

    def _on_bright_threshold_change(self, new_value=None):
        self._update_preview()

    def _on_blue_threshold_change(self, new_value=None):
        self._update_preview()

    def _on_red_threshold_change(self, new_value=None):
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
        self._update_preview()

    def _on_min_defect_area_change(self, new_value=None):
        self._update_preview()
