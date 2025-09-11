# VisionCameraSheet

Projeto de inspeção de folhas de alumínio usando Raspberry Pi e Picamera2.

---

## Configuração do GitHub

Para subir alterações para o GitHub via HTTPS, você precisa de um **Personal Access Token (Fine-grained)**:

1. Acesse: [GitHub → Settings → Developer settings → Personal Access Tokens → Fine-grained tokens](https://github.com/settings/tokens)
2. Clique em **Generate new token → Fine-grained token**.
3. Em **Repository access**, selecione:
   - **All repositories** ou escolha o repositório específico `VisionCameraSheet`.
4. Em **Permissions** para o repositório selecionado, configure:
   - **Contents → Read & Write**
   - Outras permissões podem ficar como Read.
5. Clique em **Generate token**.
6. Guarde o token, pois ele aparecerá apenas uma vez.

> No push, você usará seu **nome de usuário GitHub** e este **token** como senha.

---

## Baixar atualizações do GitHub

Para atualizar o repositório local com as últimas alterações do GitHub:

```bash
cd ~/projects/VisionCameraSheet
git fetch origin
git pull origin main

Token
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