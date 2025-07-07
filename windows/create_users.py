import customtkinter as ctk
import json
import os
from tkinter import messagebox


class NewUserWindow(ctk.CTkToplevel):
    def __init__(self, parent, users_file="users.json"):
        super().__init__(parent)
        self.title("Criar Novo Usuário")
        self.geometry("400x400")
        self.users_file = users_file

        ctk.CTkLabel(self, text="Novo Utilizador", font=("Arial", 18)).pack(pady=20)

        # Nome de utilizador
        ctk.CTkLabel(self, text="Username:").pack()
        self.username_entry = ctk.CTkEntry(self)
        self.username_entry.pack(pady=5)

        # Palavra-passe
        ctk.CTkLabel(self, text="Password:").pack()
        self.password_entry = ctk.CTkEntry(self, show="*")
        self.password_entry.pack(pady=5)

        # Confirmar palavra-passe
        ctk.CTkLabel(self, text="Confirmar Password:").pack()
        self.confirm_entry = ctk.CTkEntry(self, show="*")
        self.confirm_entry.pack(pady=5)

        # Tipo de utilizador
        ctk.CTkLabel(self, text="Tipo de Utilizador:").pack()
        self.user_type_option = ctk.CTkOptionMenu(self, values=["User", "Admin", "SuperAdmin"])
        self.user_type_option.set("User")
        self.user_type_option.pack(pady=5)

        # Botão para criar
        ctk.CTkButton(self, text="Criar Usuário", command=self._criar_usuario).pack(pady=20)

    def _criar_usuario(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        confirm = self.confirm_entry.get()
        user_type = self.user_type_option.get()

        if not username or not password:
            messagebox.showerror("Erro", "Preencha todos os campos.")
            return

        if password != confirm:
            messagebox.showerror("Erro", "As senhas não coincidem.")
            return

        # Carrega os usuários existentes
        if os.path.exists(self.users_file):
            with open(self.users_file, "r") as f:
                users = json.load(f)
        else:
            users = {}

        if username in users:
            messagebox.showerror("Erro", "Usuário já existe.")
            return

        # Salva novo usuário
        users[username] = {
            "password": password,
            "type": user_type
        }

        with open(self.users_file, "w") as f:
            json.dump(users, f, indent=4)

        messagebox.showinfo("Sucesso", f"Usuário '{username}' criado com sucesso!")
