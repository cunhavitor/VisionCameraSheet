from tkinter import messagebox

import cv2
import numpy as np
import customtkinter as ctk
from PIL import Image, ImageTk
import os

from config.config import PREVIEW_WIDTH, PREVIEW_HEIGHT


def _cancel():
    print("✖️ Criação da máscara cancelada.")
    messagebox.showinfo("✖️ Operação Cancelada.", f"✅ ✖️ Criação da máscara cancelada.")


class LeafMaskCreator(ctk.CTkToplevel):
    def __init__(self, parent, image_path, output_path="data/mask/leaf_mask.png", window_width=640):
        super().__init__(parent)
        self.state("zoomed")
        self.title("Selecionar Máscara da Folha")
        self.window_width = window_width
        self.parent = parent

        self.image_path = image_path
        self.output_path = output_path
        self.points = []
        self.image = None
        self.clone = None
        self.done = False
        self.scale = 1.0
        self.max_display_size = window_width

        self.canvas = None
        self.tk_image = None

        self._setup_ui()
        self._load_and_prepare_image()

    def _setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Frame lateral com botões
        self.left_frame = ctk.CTkFrame(self)
        self.left_frame.grid(row=0, column=0, sticky="ns", padx=10, pady=10)

        self.btn_confirm = ctk.CTkButton(self.left_frame, text="Confirmar (Enter)", command=self._confirm)
        self.btn_confirm.pack(pady=(10, 5), fill="x")

        self.btn_undo = ctk.CTkButton(self.left_frame, text="Desfazer (Z)", command=self._undo)
        self.btn_undo.pack(pady=5, fill="x")

        self.btn_cancel = ctk.CTkButton(self.left_frame, text="Cancelar (Esc)", command=_cancel)
        self.btn_cancel.pack(pady=5, fill="x")

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
        self.canvas.bind("<Button-1>", self._on_canvas_click)

    def _load_and_prepare_image(self):
        self.image = cv2.imread(self.image_path)
        if self.image is None:
            ctk.CTkLabel(self, text="Erro ao carregar a imagem.").grid(row=0, column=0)
            return

        display_img = self._resize_image(self.image)
        self.clone = display_img.copy()

        new_h, new_w = display_img.shape[:2]

        # Atualizar tamanho da janela com base na nova largura/altura da imagem
        total_width = new_w + 250
        total_height = max(new_h + 40, 300)
        self.geometry(f"{total_width}x{total_height}")

        # Atualizar tamanhos dos frames e canvas
        self.image_border.configure(width=new_w + 4, height=new_h + 4)
        self.image_frame.configure(width=new_w, height=new_h)
        self.canvas.configure(width=new_w, height=new_h)

        print("Mask dimensions - new_w: {}, new_h: {}".format(new_w, new_h))
        self._draw_polygon()

    def _resize_image(self, img):
        h, w = img.shape[:2]
        scale_w = PREVIEW_WIDTH / w
        scale_h = PREVIEW_HEIGHT / h
        self.scale = min(1.0, scale_w, scale_h)

        new_w = int(w * self.scale)
        new_h = int(h * self.scale)
        resized = cv2.resize(img, (new_w, new_h))
        return resized

    def _draw_polygon(self):
        img = self.clone.copy()
        for i in range(len(self.points)):
            x = int(self.points[i][0] * self.scale)
            y = int(self.points[i][1] * self.scale)
            cv2.circle(img, (x, y), 3, (0, 0, 255), -1)
            if i > 0:
                x_prev = int(self.points[i - 1][0] * self.scale)
                y_prev = int(self.points[i - 1][1] * self.scale)
                cv2.line(img, (x_prev, y_prev), (x, y), (0, 0, 255), 1)
        if self.done and len(self.points) > 2:
            x_first = int(self.points[0][0] * self.scale)
            y_first = int(self.points[0][1] * self.scale)
            x_last = int(self.points[-1][0] * self.scale)
            y_last = int(self.points[-1][1] * self.scale)
            cv2.line(img, (x_last, y_last), (x_first, y_first), (0, 255, 0), 2)

        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_img)
        self.tk_image = ImageTk.PhotoImage(pil_img)
        self.canvas.create_image(0, 0, anchor='nw', image=self.tk_image)

    def _on_canvas_click(self, event):
        if not self.done:
            orig_x = int(event.x / self.scale)
            orig_y = int(event.y / self.scale)
            self.points.append((orig_x, orig_y))
            self._draw_polygon()

    def _confirm(self):
        if len(self.points) < 3:
            print("⚠️ Pelo menos 3 pontos são necessários.")
            messagebox.showinfo("⚠️ Erro!", "⚠️ Pelo menos 3 pontos são necessários.")
            return
        self.done = True
        self._draw_polygon()
        self._create_and_save_mask()

    def _undo(self):
        if self.points:
            self.points.pop()
            self._draw_polygon()

    def _create_and_save_mask(self):
        mask = np.zeros(self.image.shape[:2], dtype=np.uint8)
        pts = np.array([self.points], dtype=np.int32)
        cv2.fillPoly(mask, pts, 255)

        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        cv2.imwrite(self.output_path, mask)
        print(f"✅ Máscara salva em: {self.output_path}")
        messagebox.showinfo("Máscara Salva", f"✅ Máscara salva em:\n{self.output_path}")
