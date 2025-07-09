import customtkinter as ctk
import json
import os

from config.utils import center_window

USERS_FILE = "config/users.json"

class LoginWindow(ctk.CTkToplevel):
    def __init__(self, parent, on_login_callback):
        super().__init__(parent)
        self.title("Login")
        center_window(self, 400, 350) #self.geometry("400x350")
        self.resizable(False, False)

        self.on_login_callback = on_login_callback

        self.username_var = ctk.StringVar()
        self.password_var = ctk.StringVar()
        self.error_var = ctk.StringVar()


        # Layout
        ctk.CTkLabel(self, text="Autenticação", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(20, 10))

        ctk.CTkLabel(self, text="Usuário:").pack(pady=(10, 0))
        self.entry_username = ctk.CTkEntry(self, textvariable=self.username_var)
        self.entry_username.pack(pady=5)

        ctk.CTkLabel(self, text="Senha:").pack(pady=(10, 0))
        self.entry_password = ctk.CTkEntry(self, textvariable=self.password_var, show="*", )
        self.entry_password.pack(pady=5)

        self.error_label = ctk.CTkLabel(self, textvariable=self.error_var, text_color="red")
        self.error_label.pack(pady=(5, 0))

        self.btn_login = ctk.CTkButton(self, text="Entrar", command=self._tentar_login)
        self.entry_password.bind("<Return>", lambda event: self._tentar_login())

        self.btn_login.pack(pady=20)

        self.entry_username.focus()

    def _tentar_login(self):
        username = self.entry_username.get()
        password = self.entry_password.get()

        try:
            with open("config/users.json", "r") as f:
                users = json.load(f)
        except Exception as e:
            print("Erro ao ler users.json:", e)
            return

        if username in users and users[username]["password"] == password:
            user_type = users[username]["type"]
            self.destroy()
            self.on_login_callback(username, user_type)
        else:
            self.label_result.configure(text="Login incorreto", text_color="red")

    def _carregar_usuarios(self):
        if not os.path.exists(USERS_FILE):
            return {}
        with open(USERS_FILE, "r") as f:
            return json.load(f)
