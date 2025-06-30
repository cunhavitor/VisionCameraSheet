import customtkinter as ctk
import cv2
import numpy as np
from PIL import Image, ImageTk
from customtkinter import CTkImage
import math
import os


class CameraAngleCheckerWindow(ctk.CTkToplevel):
    def __init__(self, parent, image_path):
        super().__init__(parent)
        self.title("Verificação do Ângulo da Câmara")
        self.geometry("1100x900")

        self.image_path = image_path
        self.img_cv = cv2.imread(image_path)
        self.points = []

        self.canvas = ctk.CTkCanvas(self, width=900, height=675)
        self.canvas.pack(pady=10)

        # Redimensionar imagem para caber no canvas
        self.img_resized = cv2.resize(self.img_cv, (900, 675))
        self.tk_img = ImageTk.PhotoImage(Image.fromarray(cv2.cvtColor(self.img_resized, cv2.COLOR_BGR2RGB)))
        self.canvas_img = self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)
        self.canvas.bind("<Button-1>", self._on_click)

        self.label_result = ctk.CTkLabel(self, text="Clique nos 4 cantos da folha (ordem: TL, TR, BR, BL)", font=("Arial", 16))
        self.label_result.pack(pady=10)

        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.pack(pady=5)

        self.btn_reset = ctk.CTkButton(self.button_frame, text="🔁 Reiniciar", command=self._reiniciar)
        self.btn_reset.pack(side="left", padx=10)

        self.btn_guardar = ctk.CTkButton(self.button_frame, text="💾 Guardar imagem corrigida", command=self._guardar_imagem)
        self.btn_guardar.pack(side="left", padx=10)

        self.img_corrigida = None

    def _on_click(self, event):
        if len(self.points) < 4:
            x, y = event.x, event.y
            self.points.append([x, y])
            self.canvas.create_oval(x-5, y-5, x+5, y+5, fill="red")

        if len(self.points) == 4:
            self._corrigir_perspectiva()

    def _corrigir_perspectiva(self):
        src_pts = np.array(self.points, dtype="float32")
        dst_pts = np.array([[0, 0], [800, 0], [800, 1000], [0, 1000]], dtype="float32")
        M = cv2.getPerspectiveTransform(src_pts, dst_pts)

        warped = cv2.warpPerspective(self.img_resized, M, (800, 1000))
        self.img_corrigida = warped
        warped_rgb = cv2.cvtColor(warped, cv2.COLOR_BGR2RGB)
        warped_pil = Image.fromarray(warped_rgb)
        warped_tk = ImageTk.PhotoImage(warped_pil)

        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=warped_tk)
        self.canvas.image = warped_tk

        self.label_result.configure(text="✅ Perspectiva corrigida com sucesso")

    def _reiniciar(self):
        self.points.clear()
        self.canvas.delete("all")
        self.tk_img = ImageTk.PhotoImage(Image.fromarray(cv2.cvtColor(self.img_resized, cv2.COLOR_BGR2RGB)))
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)
        self.canvas.image = self.tk_img
        self.label_result.configure(text="Clique nos 4 cantos da folha (ordem: TL, TR, BR, BL)")

    def _guardar_imagem(self):
        if self.img_corrigida is not None:
            base_name = os.path.splitext(os.path.basename(self.image_path))[0]
            output_path = os.path.join("data/output", f"{base_name}_corrigida.jpg")
            os.makedirs("data/output", exist_ok=True)
            cv2.imwrite(output_path, self.img_corrigida)
            self.label_result.configure(text=f"✅ Imagem guardada em: {output_path}")
        else:
            self.label_result.configure(text="⚠️ Nenhuma imagem corrigida para guardar.")