import csv
import json
import os
from datetime import datetime

import customtkinter as ctk
import cv2
from PIL import Image
from customtkinter import CTkImage

from config.config import INSPECTION_PREVIEW_WIDTH, INSPECTION_PREVIEW_HEIGHT
from config.utils import center_window
from models.defect_detector import detect_defects
from widgets.param_entry_simple_numeric import create_param_entry


class DefectTunerWindow(ctk.CTkToplevel):
    def __init__(self, master, tpl_img, aligned_img, mask, reopen_callback=None,user_type="User", user_name=""):
        super().__init__(master)

        s = (INSPECTION_PREVIEW_WIDTH, INSPECTION_PREVIEW_HEIGHT)
        self.user_type=user_type
        self.user_name=user_name

        #self.reopen_callback = reopen_callback
        #self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.state("zoomed")
        self.title("Ajuste de Parâmetros de Defeitos")
        center_window(self, 1050, 800)

        self.bind("<space>", self._on_space_key)

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
        self.display_mode = ctk.StringVar(value="PB")

        # Para debounce da atualização (evitar muitas chamadas rapidíssimas)
        self._update_scheduled = False




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


        self._restore_saved_params()
        self._create_buttons()
        self._update_preview()

        self._create_reset_button()

    def _create_reset_button(self):
        container_reset = ctk.CTkFrame(self.control_frame, fg_color="gray")
        container_reset.pack(fill="x", padx=30, pady=(0, 20))

        btn_reset = ctk.CTkButton(container_reset, text="Reset Valores Padrão", command=self._reset_to_defaults)
        btn_reset.pack(padx=20, pady=10)

    def _reset_to_defaults(self):
        # Define os valores padrão originais
        self.dark_threshold_var.set(str(30))
        self.bright_threshold_var.set(str(30))
        self.blue_threshold_var.set(str(25))
        self.red_threshold_var.set(str(25))
        self.dark_kernel_var.set(str(3))
        self.dark_iterations_var.set(str(1))
        self.bright_kernel_var.set(str(3))
        self.bright_iterations_var.set(str(1))
        self.dark_gradient_threshold_var.set(str(10))
        self.min_defect_area_var.set(str(1))
        self._update_preview()

    def _schedule_update_preview(self):
        if not self._update_scheduled:
            self._update_scheduled = True
            # Atualiza a preview daqui a 150ms (debounce)
            self.after(100, self._debounced_update)

    def _debounced_update(self):
        self._update_scheduled = False
        self._update_preview()


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
        ctk.CTkButton(container1, text="Atualizar Detecção (SPACE)",
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
            values=["PB", "Colorida"],
            command=lambda _: self._update_preview()
        ).pack(pady=(10, 10), padx=(10, 10), side="right")

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


    def _export_annotated_image(self):
        from datetime import datetime
        path = f"export/defect_preview_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        cv2.imwrite(path, self.last_preview)
        print(f"Imagem exportada para {path}")


    def _update_preview(self):
        if not hasattr(self, "defect_count_label"):
            return

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
                    cv2.drawContours(preview, [cnt], -1, color, 5)
                    num_defeitos += 1

        elif selected_mode == "Amarelo":
            mask_to_show = bright_mask
            contours_display, _ = cv2.findContours(mask_to_show, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            color = (0, 255, 255)  # Amarelo
            num_defeitos = 0
            for cnt in contours_display:
                if cv2.contourArea(cnt) >= int(self.min_defect_area_var.get()):
                    cv2.drawContours(preview, [cnt], -1, color, 5)
                    num_defeitos += 1

        elif selected_mode == "Azul":
            mask_to_show = blue_mask
            contours_display, _ = cv2.findContours(mask_to_show, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            color = (255, 255, 0)  # Ciano
            num_defeitos = 0
            for cnt in contours_display:
                if cv2.contourArea(cnt) >= int(self.min_defect_area_var.get()):
                    cv2.drawContours(preview, [cnt], -1, color, 5)
                    num_defeitos += 1

        elif selected_mode == "Vermelho":
            mask_to_show = red_mask
            contours_display, _ = cv2.findContours(mask_to_show, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            color = (0, 0, 255)  # Vermelho
            num_defeitos = 0
            for cnt in contours_display:
                if cv2.contourArea(cnt) >= int(self.min_defect_area_var.get()):
                    cv2.drawContours(preview, [cnt], -1, color, 5)
                    num_defeitos += 1

        elif selected_mode == "Todos (colorido)":
            num_defeitos = 0

            # Escuro – Azul
            contours_dark, _ = cv2.findContours(darker_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours_dark:
                if cv2.contourArea(cnt) >= int(self.min_defect_area_var.get()):
                    cv2.drawContours(preview, [cnt], -1, (255, 0, 0), 5)
                    num_defeitos += 1

            # Amarelo – Amarelo
            contours_bright, _ = cv2.findContours(bright_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours_bright:
                if cv2.contourArea(cnt) >= int(self.min_defect_area_var.get()):
                    cv2.drawContours(preview, [cnt], -1, (0, 255, 255), 5)
                    num_defeitos += 1

            # Azul – Ciano
            contours_blue, _ = cv2.findContours(blue_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours_blue:
                if cv2.contourArea(cnt) >= int(self.min_defect_area_var.get()):
                    cv2.drawContours(preview, [cnt], -1, (255, 255, 0), 5)
                    num_defeitos += 1

            # Vermelho – Vermelho
            contours_red, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours_red:
                if cv2.contourArea(cnt) >= int(self.min_defect_area_var.get()):
                    cv2.drawContours(preview, [cnt], -1, (0, 0, 255), 5)
                    num_defeitos += 1

        else:  # Final combinado
            mask_to_show = final_mask
            contours_display, _ = cv2.findContours(mask_to_show, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            color = (0, 255, 0)  # Verde
            num_defeitos = 0
            for cnt in contours_display:
                if cv2.contourArea(cnt) >= int(self.min_defect_area_var.get()):
                    cv2.drawContours(preview, [cnt], -1, color, 5)
                    num_defeitos += 1

        # Obter contornos e desenhar com cor apropriada
        contours_display, _ = cv2.findContours(mask_to_show, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        num_defeitos = 0
        for cnt in contours_display:
            area = cv2.contourArea(cnt)
            if area >= int(self.min_defect_area_var.get()):
                cv2.drawContours(preview, [cnt], -1, color, 5)

                (x, y), radius = cv2.minEnclosingCircle(cnt)
                center = (int(x), int(y))
                radius = int(radius) + 3

                cv2.circle(preview, center, radius, (0, 0, 255), 3)

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

        self.image_label.pack(padx=4, pady=4)
        self.graph_frame.pack_forget()
        self.image_label.configure(image=ctk_img)
        self.image_label.image = ctk_img

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
        #self._update_preview()
        self._schedule_update_preview()

    def _on_bright_threshold_change(self, new_value=None):
        self.last_changed_param = "bright_threshold"
        #self._update_preview()
        self._schedule_update_preview()

    def _on_blue_threshold_change(self, new_value=None):
        self.last_changed_param = "blue_threshold"
        #self._update_preview()
        self._schedule_update_preview()

    def _on_red_threshold_change(self, new_value=None):
        self.last_changed_param = "red_threshold"
        #self._update_preview()
        self._schedule_update_preview()

    def _on_dark_kernel_change(self, new_value=None):
        '''teste'''
        #self._update_preview()

    def _on_dark_iterations_change(self, new_value=None):
        '''teste'''
        #self._update_preview()

    def _on_bright_kernel_change(self, new_value=None):
        '''teste'''
        #self._update_preview()

    def _on_bright_iterations_change(self, new_value=None):
        '''teste'''
        #self._update_preview()

    def _on_dark_gradient_threshold_change(self, new_value=None):
        self.last_changed_param = "dark_gradient_threshold"
        #self._update_preview()
        self._schedule_update_preview()

    def _on_min_defect_area_change(self, new_value=None):
        '''teste'''
        #self._update_preview()

    def _on_space_key(self, event):
        self._update_preview()
