import json
import os
from tkinter import simpledialog

from PIL import Image, ImageDraw, ImageTk
import customtkinter as ctk
from customtkinter import CTkLabel, CTkButton
from config.config import TEMPLATE_IMAGE_PATH
import tkinter as tk  # import necessário

class InstanciaPoligono:
    def __init__(self, center, scale=1.0, numero_lata=None):
        self.center = center
        self.scale = scale
        self.numero_lata = numero_lata  # novo campo

class AdjustPositionsWindow(ctk.CTkToplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("Ajustar Máscara")

        self.definir_area_ativa = False
        self.ovals = []
        self.selected_oval = None
        self.scale_factor = 0.2

        self.original_image = Image.open(TEMPLATE_IMAGE_PATH)
        self.original_img_width, self.original_img_height = self.original_image.size

        self.zoom_image(self.scale_factor)
        self.geometry(f"{self.scaled_img_width + 200}x{self.scaled_img_height + 100}")

        # Polígonos
        self.forma_base = []  # forma definida manualmente (lista de pontos relativos ao centro)
        self.instancias_poligono = []  # instâncias da forma_base colocadas na imagem



        # Frame lateral
        self.left_frame = ctk.CTkFrame(self, width=150)
        self.left_frame.pack(side="left", fill="y", padx=10, pady=10)
        self.left_frame.pack_propagate(False)

        self.toggle_definir_area = ctk.CTkCheckBox(
            self.left_frame,
            text="Modo definir posições",
            command=self.toggle_definir_area_modo
        )
        self.toggle_definir_area.pack(pady=10, fill="x")

        self.status_label = ctk.CTkLabel(self.left_frame, text="Modo normal", wraplength=130, justify="left")
        self.status_label.pack(pady=5, fill="x")

        self.btn_criar_forma = CTkButton(self.left_frame, text="Criar Forma Manual", command=self.abrir_janela_criar_forma)
        self.btn_criar_forma.pack(pady=5, fill="x")

        self.btn_gravar_instancias = CTkButton(self.left_frame, text="Guardar Instâncias", command=self.salvar_instancias)
        self.btn_gravar_instancias.pack(pady=5, fill="x")

        self.btn_gerar_mask = CTkButton(self.left_frame, text="Gerar Máscara", command=self.gerar_mascara)
        self.btn_gerar_mask.pack(pady=5, fill="x")

        self.btn_clean_polygon = CTkButton(self.left_frame, text="Limpar Tudo", command=self.clean_polygons)
        self.btn_clean_polygon.pack(pady=5, fill="x")

        # Frame de imagem
        self.preview_frame = ctk.CTkFrame(self, width=self.scaled_img_width, height=self.scaled_img_height)
        self.preview_frame.pack(side="left", padx=10, pady=10)
        self.preview_frame.pack_propagate(False)

        self.image_label = CTkLabel(self.preview_frame, image=self.tk_image, text="")
        self.image_label.image = self.tk_image
        self.image_label.pack()

        self.image_label.bind("<Button-1>", self.on_click)
        self.image_label.bind("<B1-Motion>", self.on_drag)
        self.image_label.bind("<ButtonRelease-1>", self.on_release)
        self.image_label.bind("<MouseWheel>", self.on_mousewheel)
        self.image_label.bind("<Motion>", self.on_mouse_move)

        # Depois de criar os outros widgets, adicione:
        self.label_numero_lata = ctk.CTkLabel(self.left_frame, text="Número da lata:")
        self.entry_numero_lata = ctk.CTkEntry(self.left_frame)
        self.entry_numero_lata.bind("<Return>", self.atualizar_numero_lata)

        # Esconde no início
        self.label_numero_lata.pack_forget()
        self.entry_numero_lata.pack_forget()

        self.carregar_forma()
        self.carregar_instancias()

    def carregar_instancias(self):
        caminho = "data/mask/instancias_poligonos.txt"
        if not os.path.exists(caminho):
            return

        with open(caminho, "r") as f:
            for linha in f:
                try:
                    _, dados = linha.strip().split(":")
                    cx, cy, s, numero = dados.split(",")
                    instancia = InstanciaPoligono(center=(int(cx), int(cy)), scale=float(s), numero_lata=int(numero))
                    self.instancias_poligono.append(instancia)
                except:
                    continue

    def zoom_image(self, factor):
        self.scale_factor = factor
        self.scaled_img_width = int(self.original_img_width * factor)
        self.scaled_img_height = int(self.original_img_height * factor)
        self.scaled_image = self.original_image.resize(
            (self.scaled_img_width, self.scaled_img_height), Image.Resampling.NEAREST)
        self.tk_image = ImageTk.PhotoImage(self.scaled_image)

    def toggle_definir_area_modo(self):
        self.definir_area_ativa = self.toggle_definir_area.get() == 1
        self.status_label.configure(
            text="Modo definir: clique para adicionar polígonos" if self.definir_area_ativa else "Modo normal"
        )
        self.image_label.configure(cursor="crosshair" if self.definir_area_ativa else "arrow")
        self.atualizar_imagem_com_pontos()

    def pedir_numero_lata(self):
        numero = simpledialog.askinteger("Número da Lata", "Insira o número desta lata:", parent=self)
        return numero

    def abrir_janela_criar_forma(self):
        CriarFormaWindow(self)

    def on_click(self, event):
        if not self.definir_area_ativa:
            return

        x = int(event.x / self.scale_factor)
        y = int(event.y / self.scale_factor)

        # Verifica se clicou perto de uma instância para selecionar e mostrar número da lata
        for instancia in self.instancias_poligono:
            cx, cy = instancia.center
            if abs(cx - x) < 10 and abs(cy - y) < 10:
                self.selected_oval = instancia
                # Mostrar entrada para número da lata
                self.label_numero_lata.pack(pady=(20, 0))
                self.entry_numero_lata.pack(pady=(0, 10))
                if instancia.numero_lata is not None:
                    self.entry_numero_lata.delete(0, "end")
                    self.entry_numero_lata.insert(0, str(instancia.numero_lata))
                else:
                    self.entry_numero_lata.delete(0, "end")
                return  # selecionou instância

        if self.forma_base:
            numero = self.pedir_numero_lata()
            if numero is not None:
                self.instancias_poligono.append(InstanciaPoligono(center=(x, y), numero_lata=numero))
                self.status_label.configure(text=f"🟢 Instâncias adicionadas: {len(self.instancias_poligono)}")
                self.atualizar_imagem_com_pontos()
            else:
                self.status_label.configure(text="⚠️ Número não definido. Polígono não adicionado.")
            return

    def atualizar_numero_lata(self, event=None):
        if self.selected_oval:
            texto = self.entry_numero_lata.get().strip()
            if texto.isdigit():
                self.selected_oval.numero_lata = int(texto)
                self.status_label.configure(text=f"✅ Número da lata atualizado para {texto}")
            else:
                self.status_label.configure(text="⚠️ Insira um número válido")


    def on_drag(self, event):
        if not self.definir_area_ativa:
            return

        x = int(event.x / self.scale_factor)
        y = int(event.y / self.scale_factor)

        if self.selected_oval:
            self.selected_oval.center = (x, y)
            self.atualizar_imagem_com_pontos()
            return

        # Seleciona instância de polígono para mover
        for instancia in self.instancias_poligono:
            cx, cy = instancia.center
            if abs(cx - x) < 10 and abs(cy - y) < 10:
                self.selected_oval = instancia
                instancia.center = (x, y)
                self.atualizar_imagem_com_pontos()
                return

    def on_release(self, event):
        self.selected_oval = None

    def on_mousewheel(self, event):
        x = int(self.image_label.winfo_pointerx() - self.image_label.winfo_rootx())
        y = int(self.image_label.winfo_pointery() - self.image_label.winfo_rooty())
        x = int(x / self.scale_factor)
        y = int(y / self.scale_factor)

        # Redimensiona instância de polígono
        for instancia in self.instancias_poligono:
            cx, cy = instancia.center
            if abs(cx - x) < 10 and abs(cy - y) < 10:
                instancia.scale += 0.05 if event.delta > 0 else -0.05
                instancia.scale = max(0.2, instancia.scale)
                self.atualizar_imagem_com_pontos()
                break

    def on_mouse_move(self, event):
        if not self.definir_area_ativa:
            self.image_label.configure(cursor="arrow")
            return

        x = int(event.x / self.scale_factor)
        y = int(event.y / self.scale_factor)

        for instancia in self.instancias_poligono:
            cx, cy = instancia.center
            if abs(cx - x) < 10 and abs(cy - y) < 10:
                self.image_label.configure(cursor="fleur")  # cursor mover
                return

        self.image_label.configure(cursor="crosshair")

    def atualizar_imagem_com_pontos(self):
        img_copy = self.original_image.copy()
        draw = ImageDraw.Draw(img_copy)

        for instancia in self.instancias_poligono:
            cx, cy = instancia.center
            s = instancia.scale
            pontos_absolutos = [(int(cx + x * s), int(cy + y * s)) for x, y in self.forma_base]
            draw.polygon(pontos_absolutos, outline="red", fill=None, width=8)
            draw.ellipse([(cx - 15, cy - 15), (cx + 15, cy + 15)], fill="red")
            draw.text((cx, cy-100), str(instancia.numero_lata), fill="black", anchor="mm", font_size=120)

        self.scaled_image = img_copy.resize((self.scaled_img_width, self.scaled_img_height), Image.Resampling.NEAREST)
        self.tk_image = ImageTk.PhotoImage(self.scaled_image)
        self.image_label.configure(image=self.tk_image)
        self.image_label.image = self.tk_image

    def salvar_instancias(self):
        os.makedirs("data/mask", exist_ok=True)
        with open("data/mask/instancias_poligonos.txt", "w") as f:
            for i, instancia in enumerate(self.instancias_poligono):
                cx, cy = instancia.center
                s = instancia.scale
                num = instancia.numero_lata if instancia.numero_lata is not None else -1
                f.write(f"{i}:{cx},{cy},{s:.3f},{instancia.numero_lata}\n")

        self.status_label.configure(text="✅ Instâncias guardadas com sucesso.")

    def gerar_mascara(self):
        mask = Image.new("L", (self.original_img_width, self.original_img_height), 0)
        draw = ImageDraw.Draw(mask)

        for instancia in self.instancias_poligono:
            cx, cy = instancia.center
            s = instancia.scale
            pontos_absolutos = [(int(cx + x * s), int(cy + y * s)) for x, y in self.forma_base]
            draw.polygon(pontos_absolutos, fill=255)

        os.makedirs("data/mask", exist_ok=True)
        mask.save("data/mask/leaf_mask.png")
        self.status_label.configure(text="✅ Máscara gerada com sucesso.")

    def clean_polygons(self):
        self.ovals.clear()
        self.instancias_poligono.clear()
        self.status_label.configure(text="🔄 Tudo limpo.")
        self.atualizar_imagem_com_pontos()

    def carregar_forma(self):
        caminho = "data/mask/forma_base.json"
        if os.path.exists(caminho):
            try:
                with open(caminho, "r") as f:
                    self.forma_base = json.load(f)  # lista de [x,y]
                self.status_label.configure(text="🔄 Forma carregada do ficheiro.")
            except json.JSONDecodeError:
                self.forma_base = None
                self.status_label.configure(text="⚠️ Ficheiro JSON inválido. Forma não carregada.")
        else:
            self.forma_base = None
            self.status_label.configure(text="⚠️ Nenhuma forma guardada encontrada.")

class CriarFormaWindow(ctk.CTkToplevel):
    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.title("Definir Forma Manual do Polígono")
        self.parent_window = parent_window
        self.geometry("900x700")
        self.pontos = []

        self.original_image = Image.open(TEMPLATE_IMAGE_PATH)
        self.img_width, self.img_height = self.original_image.size
        self.scale = 0.6
        self.scaled_w = int(self.img_width * self.scale)
        self.scaled_h = int(self.img_height * self.scale)
        self.img_resized = self.original_image.resize((self.scaled_w, self.scaled_h), Image.Resampling.NEAREST)

        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Configura as linhas e colunas do grid
        self.main_frame.rowconfigure(0, weight=1)  # Canvas cresce verticalmente
        self.main_frame.rowconfigure(1, weight=0)  # Botões altura fixa
        self.main_frame.columnconfigure(0, weight=1)  # ocupa toda largura

        # Frame do canvas
        self.frame_canvas = ctk.CTkFrame(self.main_frame)
        self.frame_canvas.grid(row=0, column=0, sticky="nsew", pady=(0, 10))

        self.canvas = tk.Canvas(self.frame_canvas, width=self.scaled_w, height=self.scaled_h)
        self.canvas.pack(fill="both", expand=True)

        self.tk_image = ImageTk.PhotoImage(self.img_resized)
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)

        self.canvas.bind("<Button-1>", self.on_click)

        # Frame dos botões
        self.frame_botoes = ctk.CTkFrame(self.main_frame)
        self.frame_botoes.grid(row=1, column=0, sticky="ew")

        self.btn_undo = ctk.CTkButton(self.frame_botoes, text="⏪ Remover Último", command=self.remover_ultimo)
        self.btn_undo.grid(row=0, column=0, padx=5, pady=5)

        self.btn_guardar = ctk.CTkButton(self.frame_botoes, text="✅ Guardar Forma", command=self.guardar_forma)
        self.btn_guardar.grid(row=0, column=1, padx=5, pady=5)

        self.btn_cancelar = ctk.CTkButton(self.frame_botoes, text="❌ Cancelar", command=self.destroy)
        self.btn_cancelar.grid(row=0, column=2, padx=5, pady=5)

    def remover_ultimo_event(self, event):
        self.remover_ultimo()


    def on_click(self, event):
        # Como a imagem está redimensionada para self.scaled_w x self.scaled_h,
        # event.x e event.y já são em relação a essa escala.
        # Para armazenar os pontos em coordenadas da imagem original, convertemos assim:
        x = int(event.x / self.scale)
        y = int(event.y / self.scale)
        self.pontos.append((x, y))
        self.atualizar_imagem()

    def atualizar_imagem(self):
        self.canvas.delete("ponto")  # limpa pontos desenhados

        for p in self.pontos:
            x = int(p[0] * self.scale)
            y = int(p[1] * self.scale)
            r = 5
            self.canvas.create_oval(x - r, y - r, x + r, y + r, fill="red", tags="ponto")

        # Desenhar linhas entre pontos
        if len(self.pontos) > 1:
            scaled_points = [(int(x * self.scale), int(y * self.scale)) for x, y in self.pontos]
            self.canvas.create_line(*[coord for point in scaled_points for coord in point], fill="red", width=2,
                                    tags="ponto")

    def remover_ultimo(self):
        if self.pontos:
            self.pontos.pop()
            self.atualizar_imagem()

    def guardar_forma(self):
        if len(self.pontos) < 3:
            self.parent_window.status_label.configure(text="⚠️ Defina pelo menos 3 pontos.")
            return
        cx = sum(x for x, y in self.pontos) / len(self.pontos)
        cy = sum(y for x, y in self.pontos) / len(self.pontos)
        forma_normalizada = [(x - cx, y - cy) for x, y in self.pontos]
        self.parent_window.forma_base = forma_normalizada

        # Salvar em ficheiro JSON
        os.makedirs("data/mask", exist_ok=True)
        caminho = "data/mask/forma_base.json"
        with open(caminho, "w") as f:
            json.dump(forma_normalizada, f)

        self.parent_window.status_label.configure(text="✅ Forma definida e guardada com sucesso.")
        self.destroy()
