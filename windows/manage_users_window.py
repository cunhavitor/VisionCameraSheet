import customtkinter as ctk
import tkinter as tk
import json
import os

from config.utils import center_window


class ManageUserWindow(ctk.CTkToplevel):
    def __init__(self, parent, users_file="users.json"):
        super().__init__(parent)
        self.users_data = None
        self.title("Gerenciar Usuários")
        #self.geometry("400x500")
        self.users_file = users_file
        center_window(self, 600, 400)
        ctk.CTkLabel(self, text="Usuários", font=("Arial", 18)).pack(pady=20)

        # Frame para conter a Listbox
        list_frame = ctk.CTkFrame(self)
        list_frame.pack(pady=10, padx=20, fill="both", expand=False)

        # Scrollbar
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        # Listbox
        self.user_listbox = tk.Listbox(list_frame, selectmode=tk.SINGLE, height=15, yscrollcommand=scrollbar.set, font=("Arial", 12)
)
        self.user_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.user_listbox.yview)

        # Botão de eliminar
        ctk.CTkButton(self, text="Eliminar Selecionado", command=self.delete_selected_users).pack(pady=20)

        self.load_users()

    def load_users(self):
        self.user_listbox.delete(0, tk.END)

        if not os.path.exists(self.users_file):
            self.user_listbox.insert(tk.END, "Arquivo users.json não encontrado.")
            return

        try:
            with open(self.users_file, "r") as f:
                self.users_data = json.load(f)
        except json.JSONDecodeError:
            self.user_listbox.insert(tk.END, "Erro ao ler JSON.")
            return

        for username, info in self.users_data.items():
            user_type = info.get("type", "Desconhecido")
            self.user_listbox.insert(tk.END, f"{username} ({user_type})")

    def delete_selected_users(self):
        selected_indices = self.user_listbox.curselection()
        if not selected_indices:
            return

        # Recuperar nomes (antes do espaço) dos selecionados
        selected_users = [self.user_listbox.get(i).split(" ")[0] for i in selected_indices]

        # Remover do dicionário
        for user in selected_users:
            self.users_data.pop(user, None)

        # Atualizar o ficheiro
        with open(self.users_file, "w") as f:
            json.dump(self.users_data, f, indent=4)

        self.load_users()
