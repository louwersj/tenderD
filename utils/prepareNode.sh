#!/bin/bash

###############################################################################
# Ollama Automated Installer Script
#
# Version:       1.2.0
# Author:        Johan Louwers
# Created:       2025-05-15
# License:       GNU General Public License v3.0
#
# Description:
#   This script automates the installation and configuration of Ollama on
#   Oracle Linux. It ensures the following:
#     - System is updated
#     - Ollama is installed via official script
#     - Python >= 3.10.14 is installed
#     - Required Python packages are installed
#     - Firewall is configured to allow both SSH and Ollama
#     - Ollama systemd service is enabled and started
#     - A specified LLM model is pulled
#
# Usage:
#   Run as root or with sudo privileges.
#
###############################################################################

# -------------------------------
# Configurable Variables
# -------------------------------
ollamaPort=11434
ollamaModel="phi3"
ollamaInstallScriptUrl="https://ollama.com/install.sh"
requiredPythonVersion="3.10.14"

# -------------------------------
# Function: updateSystem
# -------------------------------
function updateSystem() {
  echo "[INFO] Updating system packages and installing prerequisites..."
  sudo dnf update -y
  sudo dnf install -y curl firewalld
}

# -------------------------------
# Function: installBuildReq
# -------------------------------
function installBuildReq() {
  echo "[INFO] Installing build requirements..."
  sudo dnf install -y gcc make zlib-devel bzip2 bzip2-devel \
    readline-devel sqlite sqlite-devel openssl-devel tk-devel \
    libffi-devel wget gcc-c++
}

# -------------------------------
# Function: upgradePython
# -------------------------------
function upgradePython() {
  echo "[INFO] Checking Python version..."
  currentVersion=$(python3 --version 2>&1 | awk '{print $2}')
  if [ "$(printf '%s\n' "$requiredPythonVersion" "$currentVersion" | sort -V | head -n1)" != "$requiredPythonVersion" ]; then
    echo "[INFO] Python version is less than $requiredPythonVersion. Upgrading..."
    cd /usr/src || exit
    sudo wget https://www.python.org/ftp/python/${requiredPythonVersion}/Python-${requiredPythonVersion}.tgz
    sudo tar xzf Python-${requiredPythonVersion}.tgz
    cd Python-${requiredPythonVersion} || exit
    sudo ./configure --enable-optimizations
    sudo make altinstall
  else
    echo "[INFO] Python version is already $requiredPythonVersion or newer."
  fi
}

# -------------------------------
# Function: installPythonPackages
# -------------------------------
function installPythonPackages() {
  echo "[INFO] Installing required Python packages with Python $requiredPythonVersion..."
  PYTHON_BIN="/usr/local/bin/python3.10"
  PIP_BIN="$PYTHON_BIN -m pip"

  $PYTHON_BIN -m ensurepip --upgrade
  $PIP_BIN install --upgrade pip
  $PIP_BIN install langchain langchain-community langchain-ollama pypdf torch transformers
}

# -------------------------------
# Function: installOllama
# -------------------------------
function installOllama() {
  echo "[INFO] Installing Ollama..."
  curl -fsSL $ollamaInstallScriptUrl | sh
}

# -------------------------------
# Function: configureFirewall
# -------------------------------
function configureFirewall() {
  echo "[INFO] Configuring firewall for Ollama and SSH..."
  sudo systemctl enable --now firewalld
  sudo firewall-cmd --permanent --add-port=${ollamaPort}/tcp
  sudo firewall-cmd --permanent --add-service=ssh
  sudo firewall-cmd --reload
}

# -------------------------------
# Function: startOllama
# -------------------------------
function startOllama() {
  echo "[INFO] Enabling and starting Ollama service..."
  sudo systemctl enable --now ollama
}

# -------------------------------
# Function: pullModel
# -------------------------------
function pullModel() {
  echo "[INFO] Pulling model: $ollamaModel..."
  ollama pull "$ollamaModel"
}

# -------------------------------
# Main Script Logic
# -------------------------------
updateSystem
installBuildReq
upgradePython
installPythonPackages
installOllama
configureFirewall
startOllama
pullModel

echo "[INFO] Installation complete."
