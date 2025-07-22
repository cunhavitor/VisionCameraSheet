import os
import json
import cv2
import tkinter as tk

import numpy as np
from PIL import Image, ImageTk
import customtkinter as ctk
from customtkinter import CTkButton
from ultralytics import YOLO
from config.config import TEMPLATE_IMAGE_PATH, INSPECTION_PREVIEW_WIDTH, INSPECTION_PREVIEW_HEIGHT
from config.utils import center_window



class AdjustPositionsWindow(ctk.CTkToplevel):
    def __init__(self, master=None, template_path=None):
        super().__init__(master)
        self.base_img_np = None
        self.annotated_imf_lines = None
        self.polygons_instances = []
        self.title("Ajustar Máscara")
        center_window(self, 1200, 700)

        # Tamanhos fixos da imagem de pré-visualização
        self.preview_size = (INSPECTION_PREVIEW_WIDTH, INSPECTION_PREVIEW_HEIGHT)

        # Carregamento da imagem
        self.original_image = cv2.imread(template_path)
        self.img_size = (self.original_image.shape[1], self.original_image.shape[0])

        # Frame lateral (parâmetros)
        self.left_frame = ctk.CTkFrame(self, width=350)
        self.left_frame.pack(side="left", fill="y", padx=10, pady=10)
        self.left_frame.pack_propagate(False)

        self.line_entries = []  # lista para guardar as entradas de linhas

        self.model = YOLO("models/weights/best.pt")

        self.polygons = []  # Lista de polígonos aplicados

        self.polygon_data = []  # Lista de tuplas: (cx, cy, scale)

        # Valores padrão
        default_latas_x = 0
        default_latas_y = 0

        # StringVars
        self.num_latas_x_var = ctk.StringVar(value=str(default_latas_x))
        self.num_latas_y_var = ctk.StringVar(value=str(default_latas_y))

        # Cria um frame horizontal dentro do left_frame
        button_frame = ctk.CTkFrame(self.left_frame)
        button_frame.pack(pady=10)

        self.detect_button = ctk.CTkButton(button_frame, text="Detectar Latas", command=self.run_detection)
        self.detect_button.pack(side="left", padx=(0, 10))  # espaço à direita para separar os botões

        # Novo botão à direita do detect_button
        self.create_form = ctk.CTkButton(button_frame, text="Criar Forma", command=self.abrir_janela_criar_forma)
        self.create_form.pack(side="left")

        # Entradas de parâmetros
        # Frame que mostra o número de latas em X (valor calculado)
        self.num_latas_x_frame = ctk.CTkFrame(self.left_frame)
        self.num_latas_x_frame.pack(pady=5, anchor="w")

        # Label de descrição
        self.num_latas_x_label = ctk.CTkLabel(self.num_latas_x_frame, text="Número de latas em X:")
        self.num_latas_x_label.pack(side="left", padx=(5, 10))

        # Label do valor (atualizado depois)
        self.num_latas_x_value = ctk.CTkLabel(self.num_latas_x_frame, text="0")
        self.num_latas_x_value.pack(side="left")

        # Frame que mostra o número de latas em Y (valor calculado)
        self.num_latas_y_frame = ctk.CTkFrame(self.left_frame)
        self.num_latas_y_frame.pack(pady=5, anchor="w")

        # Label de descrição
        self.num_latas_y_label = ctk.CTkLabel(self.num_latas_y_frame, text="Número de latas em Y:")
        self.num_latas_y_label.pack(side="left", padx=(5, 10))

        # Label do valor (atualizado depois)
        self.num_latas_y_value = ctk.CTkLabel(self.num_latas_y_frame, text="0")
        self.num_latas_y_value.pack(side="left")

        # Frame de pré-visualização
        self.preview_frame = ctk.CTkFrame(self, width=self.preview_size[0] + 4, height=self.preview_size[1] + 8, fg_color="gray80")
        self.preview_frame.pack(side="left", padx=10, pady=10)
        self.preview_frame.pack_propagate(False)

        # Converte BGR para RGB para ser compatível com PIL
        image_rgb = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)

        self.current_pil_image = pil_image

        # Cria um CTkImage
        ctk_image = ctk.CTkImage(light_image=pil_image, size=self.preview_size)

        self.ctk_image = ctk_image
        self.image_label = ctk.CTkLabel(self.preview_frame, image=ctk_image, text="")
        self.image_label.image = ctk_image
        self.image_label.pack(pady=10)

    def update_line_entries(self, num_fila_y):
        # Apaga entradas antigas
        for entry in self.line_entries:
            entry[0].master.destroy()  # Destrói o frame pai do entry (o frame criado para cada linha)
        self.line_entries.clear()

        # Cópia da imagem base para desenhar as linhas (usar uma cópia para não perder original)
        base_img = self.original_image.copy()

        # Para guardar as linhas y atuais (em pixels) para desenhar as linhas
        self.line_positions_y = []

        try:
            num_linhas = int(num_fila_y)
        except ValueError:
            num_linhas = 0

        for i in range(num_linhas):
            frame = ctk.CTkFrame(self.left_frame)
            frame.pack(fill="x", padx=5, pady=2)

            # Label da linha
            label = ctk.CTkLabel(frame, text=f"Linha {i + 1}", width=80, anchor="w")
            label.pack(side="left", padx=(0, 10))

            # Entrada com controle via roda do rato
            var = ctk.IntVar(value=int(
                self.img_size[1] * (num_linhas - i) / (
                            num_linhas + 1)))  # Invertido: primeira linha em baixo, última em cima

            entry = ctk.CTkEntry(frame, textvariable=var, width=60)
            entry.pack(side="left")

            def make_wheel_func(var, index=i):
                def on_mousewheel(event):
                    if event.delta > 0:
                        var.set(min(var.get() + 1, self.preview_size[1]))
                    else:
                        var.set(max(var.get() - 1, 0))
                    self.update_line_position(index, var.get())

                return on_mousewheel

            entry.bind("<MouseWheel>", make_wheel_func(var))

            # Atualiza a linha se o valor for alterado manualmente na entry (ex: digitado)
            def on_var_change(var=var, index=i):
                try:
                    val = int(var.get())
                except Exception:
                    val = 0
                val = max(0, min(val, self.preview_size[1]))
                var.set(val)
                self.update_line_position(index, val)

            var.trace_add("write", lambda *args, v=var, idx=i: on_var_change(v, idx))

            # OptionMenu com direções
            direction_var = ctk.StringVar(value="left->right")
            option_menu = ctk.CTkOptionMenu(
                frame,
                values=["left->right", "right->left"],
                variable=direction_var,
                width=120
            )
            option_menu.pack(side="left", padx=(10, 0))

            self.line_entries.append((frame, var, direction_var))

            # Guarda posição inicial da linha
            self.line_positions_y.append(var.get())

        self.enumerate_polygons = CTkButton(self.left_frame, text="Numerar Latas", command=self.number_polygons_on_lines)
        self.enumerate_polygons.pack(pady=10)

        self.save_mask = CTkButton(self.left_frame, text="Guardar Máscara",
                                            command=self.on_salvar_mascara)
        self.save_mask.pack(pady=10)
        self.save_mask.configure(state="disabled")
        # Após criar todas as linhas, desenha elas na imagem e atualiza a label
        self.redraw_lines()

    def update_line_position(self, index, new_y):
        # Atualiza a posição da linha no índice index
        if 0 <= index < len(self.line_positions_y):
            self.line_positions_y[index] = new_y
            self.redraw_lines()

    def redraw_lines(self):
        if not hasattr(self, 'annotated_img_np'):
            # fallback para original
            img = self.base_img_np.copy()
        else:
            img = self.annotated_img_np.copy()

        # Cor da linha e espessura
        line_color = (0, 0, 255)  # verde
        thickness = 4
        for y in self.line_positions_y:
            y_int = int(y)
            cv2.line(img, (0, y_int), (self.img_size[0], y_int), line_color, thickness)

        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)

        self.annotated_imf_lines = pil_img

        self.ctk_image = ctk.CTkImage(light_image=pil_img, size=self.preview_size)
        self.image_label.configure(image=self.ctk_image)
        self.image_label.image = self.ctk_image  # manter referência
        self.image_label.update()
        self.config(cursor="")

    def load_forma_base(self, path="data/mask/forma_base.json"):
        with open(path, "r") as f:
            data = json.load(f)
        return data  # Lista de pontos normalizados (entre 0 e 1)


    def draw_polygon_on_box(self, image, box, base_shape):
        """
        Desenha a forma base ajustada proporcionalmente dentro da bbox.
        """
        # ✅ Certifica que é um array numpy float32
        base_shape = np.array(base_shape, dtype=np.float32)

        print(f"Desenhando polígono na caixa: {box}")
        x, y, w, h = box

        # Normaliza forma_base para a origem (0,0)
        min_x, min_y = base_shape.min(axis=0)
        shape_norm = base_shape - [min_x, min_y]

        orig_width = np.ptp(shape_norm[:, 0])
        orig_height = np.ptp(shape_norm[:, 1])

        scale = min(w / orig_width, h / orig_height)
        shape_scaled = shape_norm * scale

        new_width = np.ptp(shape_scaled[:, 0])
        new_height = np.ptp(shape_scaled[:, 1])

        offset_x = x + (w - new_width) / 2
        offset_y = y + (h - new_height) / 2

        shape_translated = shape_scaled + [offset_x, offset_y]
        polygon = shape_translated.astype(np.int32)

        print(f"Polígono pontos: {polygon}")
        self.polygons.append(polygon.tolist())  # Guarda como lista de pontos (para serializar se quiseres)

        # Calcula centro da box
        cx = int(x + w / 2)
        cy = int(y + h / 2)

        # Guarda como tupla (lista pontos, escala)
        self.polygons_instances.append({
            "points": [cx, cy],
            "scale": scale
        })

        cv2.polylines(image, [polygon], isClosed=True, color=(0, 255, 0), thickness=4)

    # encontrar contorno, em fase de teste, com muitas falhas
    '''def draw_polygon_on_box(self, image, box, base_shape):
        """
        Detecta e desenha o maior contorno dentro da caixa (box) usando inversão, OTSU e morfologia.
        """
        x, y, w, h = box
        roi = image[y:y + h, x:x + w]

        # Converte para escala de cinza
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

        # Inverte a imagem
        img_inv = 255 - gray

        # Aplica threshold com OTSU
        _, thresh = cv2.threshold(img_inv, 15, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Aplica fechamento morfológico
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        thresh_closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        # Detecta contornos
        contours, _ = cv2.findContours(thresh_closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            print("Nenhum contorno encontrado na região.")
            return

        # Seleciona o maior contorno
        target_contour = max(contours, key=cv2.contourArea)

        area = cv2.contourArea(target_contour)
        print(f"Contorno selecionado (maior) com área {area:.2f} e {len(target_contour)} pontos.")

        # Ajusta o contorno para coordenadas globais
        target_contour_shifted = target_contour + np.array([[[x, y]]], dtype=np.int32)

        # Desenha na imagem
        cv2.polylines(image, [target_contour_shifted], isClosed=True, color=(0, 255, 0), thickness=4)

        # Guarda como lista de pontos
        self.polygons.append(target_contour_shifted.reshape(-1, 2).tolist())

        # Centro da caixa
        cx = int(x + w / 2)
        cy = int(y + h / 2)

        self.polygons_instances.append({
            "points": [cx, cy],
            "scale": 1.0  # Escala padrão
        })'''

    def run_detection(self):
        self.config(cursor="watch")
        print("[INFO] Botão de deteção clicado.")

        # Converte imagem para RGB (modelo espera RGB)
        image_rgb = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2RGB)

        # Executa o modelo YOLO
        results = self.model.predict(image_rgb, verbose=False)

        if not results:
            print("[ERRO] Nenhum resultado retornado pelo modelo.")
            return

        result = results[0]
        boxes = result.boxes

        # Verifica se há caixas
        if boxes is None or boxes.xywh is None or len(boxes.xywh) == 0:
            print("[INFO] Nenhuma lata detetada.")
            return

        print(f"[INFO] {len(boxes.xywh)} latas detetadas.")

        # Carrega forma base (pontos normalizados)
        base_shape = self.load_forma_base()

        # Faz uma cópia da imagem para desenhar os polígonos
        annotated = self.original_image.copy()


        # Para cada caixa desenha o polígono ajustado
        for bbox in boxes.xywh.cpu().numpy():  # formato: cx, cy, w, h
            cx, cy, w, h = bbox
            x = int(cx - w / 2)
            y = int(cy - h / 2)
            self.draw_polygon_on_box(annotated, (x, y, int(w), int(h)), base_shape)
            print(f"Box: x={x}, y={y}, w={int(w)}, h={int(h)}")


        # Atualiza a imagem na interface
        annotated_rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
        #cv2.imshow("Teste", annotated_rgb)
        updated_pil_image = Image.fromarray(annotated_rgb)
        self.annotated_img_np = annotated.copy()

        self.ctk_image = ctk.CTkImage(light_image=updated_pil_image, size=self.preview_size)
        self.image_label.configure(image=self.ctk_image)
        self.image_label.image = self.ctk_image  # manter referência
        self.image_label.update()

        print("[INFO] Máscaras desenhadas e imagem atualizada.")

        # Detecta filas a partir dos polígonos
        filas = self.detectar_filas_poligonos(self.polygons)

        # Debug info
        num_filas = len(filas)
        poligonos_por_fila = [len(f) for f in filas]
        self.num_latas_x_value.configure(text=str(poligonos_por_fila[0]))
        self.num_latas_y_value.configure(text=str(num_filas))
        self.update_line_entries(num_filas)

    def detectar_filas_poligonos(self, polygons, tolerancia_y=20):

        """
        Detecta o número de filas em Y e quantos polígonos há em cada fila,
        agrupando os centros dos polígonos pela coordenada Y.

        Args:
            polygons (list): Lista de polígonos. Cada polígono é uma lista de (x, y).
            tolerancia_y (int): Tolerância para considerar que dois polígonos estão na mesma linha.

        Returns:
            list: Lista de listas. Cada sublista representa uma fila e contém os centros dos polígonos dessa fila.
        """
        # Calcula os centros dos polígonos
        centros = []
        for poly in polygons:
            poly_np = np.array(poly)
            cx = int(np.mean(poly_np[:, 0]))
            cy = int(np.mean(poly_np[:, 1]))
            centros.append((cx, cy))

        # Agrupa os centros por Y (filas horizontais)
        filas = []
        for cx, cy in sorted(centros, key=lambda c: c[1]):
            encontrado = False
            for fila in filas:
                _, y_medio = np.mean(fila, axis=0)
                if abs(cy - y_medio) < tolerancia_y:
                    fila.append((cx, cy))
                    encontrado = True
                    break
            if not encontrado:
                filas.append([(cx, cy)])

        # Ordena os centros dentro de cada fila da esquerda para a direita
        for fila in filas:
            fila.sort(key=lambda c: c[0])

        print(f"Detectado {len(filas)} filas")
        for i, fila in enumerate(filas):
            print(f"  Fila {i + 1}: {len(fila)} polígonos")

        return filas

    def number_polygons_on_lines(self):
        """
        Numerar polígonos em filas horizontais, de acordo com direção da linha,
        desenhando os números na imagem atual (annotated_img_np).
        """
        num_latas_y = int(self.num_latas_y_value.cget("text"))
        num_latas_x = int(self.num_latas_x_value.cget("text"))

        if not hasattr(self, 'polygons') or not self.polygons:
            print("[WARN] Não há polígonos para numerar.")
            return

        # Detecta as filas automaticamente
        filas = self.detectar_filas_poligonos(self.polygons)

        # Lista com o valor máximo (número final) de cada linha
        lista_valores_filas = [(i + 1) * num_latas_x for i in range(num_latas_y)]

        print(f"Lista de valores filas: {lista_valores_filas}")
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 4
        thickness = 4
        color = (0, 0, 255)  # vermelho

        img = self.annotated_img_np.copy()
        nl=0
        for i, fila in enumerate(reversed(filas)):

            if i >= len(self.line_entries):
                print(f"[WARN] Linha {i + 1} sem definição de var/direction. Pulando numeração.")
                continue

            _, var, direction_var = self.line_entries[i]
            num_latas = var.get()
            direction = direction_var.get()

            if i >= len(lista_valores_filas):
                print(f"[WARN] lista_valores_filas não tem valor para linha {i + 1}")
                continue

            fim = lista_valores_filas[i]
            inicio = fim - num_latas_x + 1

            if direction == "left->right":
                numeros = list(range(inicio, fim + 1))
            else:  # right->left
                numeros = list(range(fim, inicio - 1, -1))

            num_poligonos = min(len(fila), num_latas)
            threshold = 100  # ou outro valor adequado ao tamanho da sua imagem

            for j in range(num_poligonos):
                cx, cy = fila[j]
                numero = numeros[j]

                text = str(numero)
                (w, h), _ = cv2.getTextSize(text, font, font_scale, thickness)
                org = (int(cx - w / 2), int(cy + h / 2))

                cv2.putText(img, text, org, font, font_scale, color, thickness, lineType=cv2.LINE_AA)

                for idx, poly_data in enumerate(self.polygons_instances):

                    for idx, poly_data in enumerate(self.polygons_instances):
                        pcx, pcy = poly_data['points']  # centro do polígono armazenado

                        dist = (pcx - cx) ** 2 + (pcy - cy) ** 2  # distância ao centro da fila atual

                        # Define um threshold pequeno para aceitar o polígono como correspondente
                        if dist < threshold ** 2:
                            self.polygons_instances[idx]['numero'] = numero
                            break

        # Atualiza a imagem anotada com a numeração
        self.annotated_img_np = img

        # Atualiza a imagem exibida na interface
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)
        self.ctk_image = ctk.CTkImage(light_image=pil_img, size=self.preview_size)
        self.image_label.configure(image=self.ctk_image)
        self.image_label.image = self.ctk_image
        self.image_label.update()

        self.save_mask.configure(state="normal")

        print("[INFO] Numeração aplicada e imagem atualizada.")

    def on_salvar_mascara(self):
        # Cria uma imagem preta (tudo zeros) do tamanho da pré-visualização (altura, largura)
        mask = np.zeros((self.img_size[1], self.img_size[0]), dtype=np.uint8)

        # Preenche os polígonos com branco (255)
        for polygon in self.polygons:
            pts = np.array(polygon, dtype=np.int32)  # pontos do polígono
            cv2.fillPoly(mask, [pts], 255)

        # Garante que a pasta existe
        os.makedirs("data/mask", exist_ok=True)

        # Salva a máscara em PNG (grayscale 8 bits)
        cv2.imwrite("data/mask/leaf_mask.png", mask)

        print("[INFO] Máscara salva em 'data/mask/leaf_mask.png'.")

        # Continua salvando os polígonos no txt
        self.salvar_poligonos_txt()

    def salvar_poligonos_txt(self, caminho="data/mask/instancias_poligonos.txt"):
        """
        Salva os polígonos definidos no formato:
        numero:cx,cy,escala
        """
        if not hasattr(self, 'polygons_instances') or not self.polygons_instances:
            print("[WARN] Nenhum polígono para salvar.")
            return

        try:
            with open(caminho, "w") as f:
                for i, instancia in enumerate(self.polygons_instances):
                    numero = instancia.get("numero", i)  # usa i se não tiver numero
                    cx, cy = instancia["points"]  # aqui é só 2 valores
                    escala = instancia.get("scale", 1.0)

                    linha = f"{numero}:{cx},{cy},{escala:.3f}\n"
                    f.write(linha)

            print(f"[INFO] Polígonos salvos com sucesso em '{caminho}'.")

        except Exception as e:
            print(f"[ERRO] Falha ao salvar polígonos: {e}")

    def abrir_janela_criar_forma(self):
        CriarFormaWindow(self)

class CriarFormaWindow(ctk.CTkToplevel):
    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.title("Definir Forma Manual do Polígono")
        self.parent_window = parent_window
        self.geometry("900x700")

        self.original_image = Image.open(TEMPLATE_IMAGE_PATH)
        self.img_width, self.img_height = self.original_image.size
        self.scale = 0.6
        self.scaled_w = int(self.img_width * self.scale)
        self.scaled_h = int(self.img_height * self.scale)
        self.img_resized = self.original_image.resize((self.scaled_w, self.scaled_h), Image.Resampling.NEAREST)

        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.main_frame.rowconfigure(0, weight=1)
        self.main_frame.rowconfigure(1, weight=0)
        self.main_frame.columnconfigure(0, weight=1)

        self.frame_canvas = ctk.CTkFrame(self.main_frame)
        self.frame_canvas.grid(row=0, column=0, sticky="nsew", pady=(0, 10))

        self.canvas = tk.Canvas(self.frame_canvas, width=self.scaled_w, height=self.scaled_h)
        self.canvas.pack(fill="both", expand=True)

        self.tk_image = ImageTk.PhotoImage(self.img_resized)
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)

        # Variáveis para armazenar os pontos do retângulo
        self.start_x = None
        self.start_y = None
        self.rect_id = None  # id do retângulo no canvas
        self.contour_id = None  # id do contorno desenhado no canvas

        # Bindings para mouse
        self.canvas.bind("<Button-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)

        self.frame_botoes = ctk.CTkFrame(self.main_frame)
        self.frame_botoes.grid(row=1, column=0, sticky="ew")

        self.btn_undo = ctk.CTkButton(self.frame_botoes, text="⏪ Remover Último", command=self.remover_ultimo)
        self.btn_undo.grid(row=0, column=0, padx=5, pady=5)

        self.btn_guardar = ctk.CTkButton(self.frame_botoes, text="✅ Guardar Forma", command=self.guardar_forma)
        self.btn_guardar.grid(row=0, column=1, padx=5, pady=5)

        self.btn_cancelar = ctk.CTkButton(self.frame_botoes, text="❌ Cancelar", command=self.destroy)
        self.btn_cancelar.grid(row=0, column=2, padx=5, pady=5)

        self.btn_next_contour = ctk.CTkButton(self.frame_botoes, text="Próximo Contorno",
                                              command=self.mostrar_proximo_contorno)
        self.btn_next_contour.grid(row=0, column=3, padx=5, pady=5)


        self.pontos = []  # Para guardar os pontos do polígono final (se desejar)

    def on_button_press(self, event):
        # Começo do retângulo
        self.start_x = event.x
        self.start_y = event.y

        # Remove retângulo e contorno antigo
        if self.rect_id:
            self.canvas.delete(self.rect_id)
            self.rect_id = None
        if self.contour_id:
            self.canvas.delete(self.contour_id)
            self.contour_id = None

        # Cria novo retângulo invisível
        self.rect_id = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline="red", width=2)

    def on_move_press(self, event):
        curX, curY = event.x, event.y

        # Atualiza retângulo com posição atual do mouse
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, curX, curY)

    def on_button_release(self, event):
        end_x, end_y = event.x, event.y

        x1, x2 = sorted([self.start_x, end_x])
        y1, y2 = sorted([self.start_y, end_y])

        x1_orig = int(x1 / self.scale)
        y1_orig = int(y1 / self.scale)
        x2_orig = int(x2 / self.scale)
        y2_orig = int(y2 / self.scale)

        self.last_x_offset = x1_orig
        self.last_y_offset = y1_orig

        img_crop = self.original_image.crop((x1_orig, y1_orig, x2_orig, y2_orig)).convert("L")
        img_np = np.array(img_crop)

        # Inverte a imagem (lata clara vira escura e vice-versa)
        img_inv = 255 - img_np

        # Aplica threshold com OTSU
        _, thresh = cv2.threshold(img_inv, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Aplica fechamento morfológico para eliminar buracos internos
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        thresh_closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        # Salva imagem para debug (opcional)
        cv2.imwrite("debug_thresh_closed.png", thresh_closed)

        # Detecta contornos (use RETR_CCOMP para pegar contornos externos e internos)
        contours, hierarchy = cv2.findContours(thresh_closed, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            print("Nenhum contorno encontrado após processamento.")
            return

        # Filtra e ordena contornos por área decrescente
        max_area = 1750000  # ajuste conforme necessário
        contornos_filtrados = [cnt for cnt in contours if cv2.contourArea(cnt) < max_area]

        if not contornos_filtrados:
            print(f"Nenhum contorno válido encontrado após filtragem.")
            return

        self.contours_sorted = sorted(contornos_filtrados, key=cv2.contourArea, reverse=True)
        self.current_contour_index = 0  # inicia no maior contorno

        self._desenhar_contorno_atual(x1_orig, y1_orig)

    def _desenhar_contorno_atual(self, x_offset, y_offset):
        cnt = self.contours_sorted[self.current_contour_index]
        area = cv2.contourArea(cnt)
        print(f"Mostrando contorno {self.current_contour_index + 1} com área {area:.2f}")

        contorno_scaled = (cnt + np.array([x_offset, y_offset])) * self.scale
        contorno_scaled = contorno_scaled.astype(int)

        if hasattr(self, 'contour_id') and self.contour_id:
            self.canvas.delete(self.contour_id)

        pontos_contorno = contorno_scaled.reshape(-1, 2).tolist()
        self.contour_id = self.canvas.create_polygon(pontos_contorno, outline="blue", fill="", width=2)

        self.pontos = [(int(x / self.scale), int(y / self.scale)) for x, y in pontos_contorno]
        print(f"Contorno desenhado com {len(self.pontos)} pontos.")

    def mostrar_proximo_contorno(self):
        if not hasattr(self, 'contours_sorted') or not self.contours_sorted:
            print("Nenhum contorno carregado para navegar.")
            return

        self.current_contour_index += 1
        if self.current_contour_index >= len(self.contours_sorted):
            self.current_contour_index = 0  # volta ao primeiro

        # Supondo que você guardou os offsets da última seleção para reaproveitar aqui
        self._desenhar_contorno_atual(self.last_x_offset, self.last_y_offset)

    def remover_ultimo(self):
        # Aqui você pode implementar para apagar o último polígono salvo, se desejar.
        pass

    def guardar_forma(self):
        if len(self.pontos) < 3:
            self.parent_window.status_label.configure(text="⚠️ Defina pelo menos 3 pontos.")
            return

        cx = sum(x for x, y in self.pontos) / len(self.pontos)
        cy = sum(y for x, y in self.pontos) / len(self.pontos)
        forma_normalizada = [(x - cx, y - cy) for x, y in self.pontos]
        self.parent_window.forma_base = forma_normalizada

        os.makedirs("data/mask", exist_ok=True)
        caminho = "data/mask/forma_base.json"
        with open(caminho, "w") as f:
            json.dump(forma_normalizada, f)

        self.destroy()
