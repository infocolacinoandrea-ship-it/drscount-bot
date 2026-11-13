#!/usr/bin/env bash
# Configurazione iniziale del server Dr.Scount (mini PC AOOSTAR, Ubuntu Desktop LTS).
# Si lancia UNA volta, dall'utente normale (non root):
#   wget -O setup.sh https://raw.githubusercontent.com/infocolacinoandrea-ship-it/drscount-bot/main/server/setup.sh
#   bash setup.sh
# Rilanciarlo non fa danni: ogni passaggio controlla se è già stato fatto.
set -euo pipefail

if [ "$(id -u)" -eq 0 ]; then
  echo "Lancialo come utente normale (senza sudo): la password te la chiede lui." >&2
  exit 1
fi

step() { printf '\n\033[1;32m==> %s\033[0m\n' "$*"; }
ME="$USER"

step "1/9 Aggiorno il sistema"
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get -y full-upgrade

step "2/9 Strumenti di base"
sudo DEBIAN_FRONTEND=noninteractive apt-get -y install \
  curl wget gnupg ca-certificates git ffmpeg python3-venv python3-pip \
  ufw unattended-upgrades apt-listchanges clamav seahorse htop

step "3/9 Aggiornamenti di sicurezza automatici (riavvio alle 04:00 solo se serve)"
sudo tee /etc/apt/apt.conf.d/20auto-upgrades >/dev/null <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF
sudo tee /etc/apt/apt.conf.d/52drscount-upgrades >/dev/null <<'EOF'
Unattended-Upgrade::Automatic-Reboot "true";
Unattended-Upgrade::Automatic-Reboot-Time "04:00";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
EOF
sudo systemctl enable --now unattended-upgrades

step "4/9 Tailscale (accesso remoto privato)"
if ! command -v tailscale >/dev/null; then
  curl -fsSL https://tailscale.com/install.sh | sh
fi

step "5/9 Firewall: nulla entra da internet, solo dalla rete privata Tailscale"
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow in on tailscale0
sudo ufw --force enable

step "6/9 Docker (contenitori separati per bot e siti)"
sudo DEBIAN_FRONTEND=noninteractive apt-get -y install docker.io docker-compose-v2
sudo systemctl enable --now docker
sudo usermod -aG docker "$ME"

step "7/9 Google Chrome"
if ! command -v google-chrome >/dev/null; then
  tmp=$(mktemp -d)
  wget -qO "$tmp/chrome.deb" https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
  sudo apt-get -y install "$tmp/chrome.deb"
  rm -rf "$tmp"
fi

step "8/9 App Claude Desktop (repository ufficiale Anthropic)"
if ! command -v claude-desktop >/dev/null; then
  sudo curl -fsSLo /usr/share/keyrings/claude-desktop-archive-keyring.asc https://downloads.claude.ai/claude-desktop/key.asc
  if ! gpg --show-keys /usr/share/keyrings/claude-desktop-archive-keyring.asc 2>/dev/null | tr -d ' ' | grep -q 31DDDE24DDFAB679F42D7BD2BAA929FF1A7ECACE; then
    echo "La chiave scaricata non è quella di Anthropic: mi fermo." >&2
    exit 1
  fi
  echo "deb [arch=amd64,arm64 signed-by=/usr/share/keyrings/claude-desktop-archive-keyring.asc] https://downloads.claude.ai/claude-desktop/apt/stable stable main" \
    | sudo tee /etc/apt/sources.list.d/claude-desktop.list >/dev/null
  sudo apt-get update
  sudo apt-get -y install claude-desktop
fi
sudo usermod -aG kvm "$ME"
echo vhost_vsock | sudo tee /etc/modules-load.d/vhost_vsock.conf >/dev/null

step "9/9 Mai in sospensione, schermo mai bloccato"
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
gsettings set org.gnome.desktop.session idle-delay 0 || true
gsettings set org.gnome.desktop.screensaver lock-enabled false || true
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'nothing' || true
mkdir -p "$HOME/drscount"

cat <<'EOF'

==================================================================
 Fatto. Adesso:
   1. Riavvia il computer (serve per Docker e per l'app Claude).
   2. Torna alla guida, Fase 5.
==================================================================
EOF
