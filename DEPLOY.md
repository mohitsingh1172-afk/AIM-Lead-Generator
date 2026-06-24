# Production Server Deployment Guide

This guide describes how to deploy the AIM Lead Generator on a remote Linux server (Ubuntu 20.04/22.04 LTS is recommended) and serve it under your domain name with HTTPS (SSL).

---

## 🛠️ Step 1: Server Preparation
Log in to your server via SSH, update your system packages, and install git, python, and nginx:

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y git python3 python3-pip python3-venv nginx certbot python3-certbot-nginx
```

---

## 📂 Step 2: Clone the Project
Clone the repository to your server (we will put it in `/var/www/lead-generator`):

```bash
sudo mkdir -p /var/www
sudo chown -R $USER:$USER /var/www
cd /var/www
git clone https://github.com/mohitsingh1172-afk/AIM-Lead-Generator.git lead-generator
cd lead-generator
```

---

## ⚙️ Step 3: Configure background service (Systemd)
To ensure the python script runs in the background and restarts automatically if it crashes or the server reboots, create a systemd service:

1. Copy the systemd service template into your system config:
   ```bash
   sudo cp /var/www/lead-generator/aim-lead-generator.service /etc/systemd/system/aim-lead-generator.service
   ```
2. Enable and start the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable aim-lead-generator.service
   sudo systemctl start aim-lead-generator.service
   ```
3. Check the status to ensure it is running:
   ```bash
   sudo systemctl status aim-lead-generator.service
   ```

---

## 🌐 Step 4: Configure Nginx & Domain
We will configure Nginx to direct traffic from your domain name to the Python app running on port 8765.

1. Copy the Nginx configuration template into Nginx's sites-available:
   ```bash
   sudo cp /var/www/lead-generator/nginx.conf /etc/nginx/sites-available/lead-generator
   ```
2. Open the file to add your domain name:
   ```bash
   sudo nano /etc/nginx/sites-available/lead-generator
   ```
   *Find `server_name yourdomain.com;` and replace `yourdomain.com` with your actual domain.*
3. Enable the configuration and test Nginx:
   ```bash
   sudo ln -s /etc/nginx/sites-available/lead-generator /etc/nginx/sites-enabled/
   # Remove default nginx site if active
   sudo rm /etc/nginx/sites-enabled/default
   sudo nginx -t
   ```
4. Restart Nginx to apply changes:
   ```bash
   sudo systemctl restart nginx
   ```

---

## 🔒 Step 5: Secure with SSL (HTTPS)
Use Certbot to generate a free SSL certificate from Let's Encrypt and automatically configure HTTPS in Nginx:

```bash
sudo certbot --nginx -d yourdomain.com
```
*(Replace `yourdomain.com` with your actual domain name).*

Your website will now be live and securely accessible at **`https://yourdomain.com`**!
