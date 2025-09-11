Raspberry Pi 5 - Configurações Iniciais
=======================================

Autor: Vitor Cunha
Projeto: VisionCameraSheet
Data: Setembro 2025

---

0. Arranque inicial pelo cartão SD
----------------------------------
- Primeira instalação do Raspberry Pi OS (Bookworm) no cartão SD.
- Arranque inicial do Raspberry Pi 5 feito a partir do SD para garantir boot funcional.
- Configurações iniciais do sistema aplicadas pelo cartão SD.

---

1. Clonagem para SSD NVMe
--------------------------
- SSD NVMe preparado e ligado via slot M.2 no Pi 5.
- Sistema do SD clonado para o SSD.
- Raspberry Pi configurado para arrancar diretamente do SSD (mais rápido e estável).
- Verificação do espaço disponível no SSD após clonagem:
  df -h /mnt/ssd

---

2. Atualização do sistema
--------------------------
sudo apt update && sudo apt full-upgrade -y
sudo reboot

---

3. Instalação de ferramentas básicas
------------------------------------
sudo apt install -y git wget curl vim htop net-tools build-essential

---

4. Configuração de rede (eth0 com IP fixo)
------------------------------------------
- Endereço: 10.30.40.250
- Máscara: /20
- Gateway: 10.30.47.250
- DNS: 10.30.10.199 e 10.28.100.4

Comandos usados:
sudo nmcli con delete "Wired connection 1"
sudo nmcli con add type ethernet ifname eth0 con-name eth0 \
  ipv4.addresses 10.30.40.250/20 \
  ipv4.gateway 10.30.47.250 \
  ipv4.dns "10.30.10.199 10.28.100.4" \
  ipv4.method manual

sudo nmcli connection modify eth0 ipv4.ignore-auto-dns yes
sudo nmcli con up eth0

Verificação:
ip addr show eth0
ip route
cat /etc/resolv.conf

---

5. Configuração de DNS limpa
-----------------------------
/etc/resolv.conf final:
nameserver 10.30.10.199
nameserver 10.28.100.4

---

6. Instalação das aplicações de câmara
--------------------------------------
# Pacote de apps antigo (libcamera) é apenas um "dummy".
# No Raspberry Pi OS Bookworm usa-se rpicam-apps.

sudo apt install -y rpicam-apps

Testes:
rpicam-hello        # Preview rápido
rpicam-hello -t 0   # Preview infinito
rpicam-still -o test.jpg   # Captura de imagem
rpicam-vid -o test.h264 -t 5000   # Grava 5 segundos de vídeo

---

7. Configuração de Python e ambiente virtual
--------------------------------------------
sudo apt install -y python3-venv python3-pip

cd ~/projects
git clone https://github.com/cunhavitor/VisionCameraSheet.git
cd VisionCameraSheet

python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
# Instalar dependências do projeto:
pip install -r requirements.txt

---

8. Estrutura de pastas do projeto
---------------------------------
~/projects/VisionCameraSheet
  ├── data/
  ├── logs/
  ├── outputs/
  ├── venv/   (ambiente virtual Python)

---

9. Abrir o VS Code com venv ativado
-----------------------------------
Para abrir o projeto já com o ambiente virtual Python ativado:

```bash
cd ~/projects/VisionCameraSheet
source venv/bin/activate
code .
