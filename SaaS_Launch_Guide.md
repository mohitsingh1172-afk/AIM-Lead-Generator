# Hostinger & GoDaddy SaaS Deployment & Monetization Plan

This guide provides the exact steps to link GoDaddy and Hostinger, set up your Google Maps API key, deploy the backend, and monetize the service.

---

## 🌐 Part 1: Linking GoDaddy Domain to Hostinger Server

You need to tell GoDaddy to send website visitors to your Hostinger server.

### Step 1.1: Find your Hostinger Server IP Address
1. Log in to your **Hostinger hPanel**.
2. Go to **VPS** (or **Hosting** if using cloud hosting) on the top menu.
3. Select your active server instance.
4. Locate the **IPv4 Address** (e.g., `185.123.45.67`) on the dashboard and copy it.

### Step 1.2: Update GoDaddy DNS Settings
1. Log in to your **GoDaddy Control Center**.
2. Go to **My Products** -> **Domains** -> Click your domain name -> Click **Manage DNS**.
3. Under the **DNS Records** table, look for the record with:
   - **Type**: `A`
   - **Name**: `@` (represents your main domain, e.g., `yourdomain.com`)
4. Click **Edit** on this record, replace the existing IP address with your **Hostinger IPv4 Address**, and click **Save**.
5. *(Optional)* Look for a CNAME record with Name: `www` and make sure it points to `@`.
> [!NOTE]
> DNS changes can take anywhere from 10 minutes to a few hours to propagate globally.

---

## 🛠️ Part 2: Deploying to Hostinger (VPS vs Shared Hosting)

> [!IMPORTANT]
> Because this application runs a persistent Python server (`web_app.py` listening on port `8765`), you must use a **VPS (Virtual Private Server)**. Standard shared hosting does not allow running persistent background processes.

If you have a **Hostinger VPS**:
1. Open your terminal (or PowerShell) and connect to your server using the SSH details from Hostinger:
   ```bash
   ssh root@your_hostinger_ip
   ```
2. Enter the root password provided by Hostinger hPanel.
3. Follow the installation commands:
   ```bash
   # 1. Update the system and install packages
   apt update && apt install -y git python3 python3-pip python3-venv nginx certbot python3-certbot-nginx

   # 2. Clone the code into /var/www/
   mkdir -p /var/www && cd /var/www
   git clone https://github.com/mohitsingh1172-afk/AIM-Lead-Generator.git lead-generator
   cd lead-generator

   # 3. Setup systemd background process
   cp aim-lead-generator.service /etc/systemd/system/aim-lead-generator.service
   systemctl daemon-reload
   systemctl enable aim-lead-generator.service
   systemctl start aim-lead-generator.service

   # 4. Configure Nginx reverse proxy
   cp nginx.conf /etc/nginx/sites-available/lead-generator
   # Edit domain name in Nginx
   nano /etc/nginx/sites-available/lead-generator
   # (Replace yourdomain.com with your actual domain, save using Ctrl+O, exit using Ctrl+X)

   # 5. Enable the site and restart Nginx
   ln -s /etc/nginx/sites-available/lead-generator /etc/nginx/sites-enabled/
   rm -f /etc/nginx/sites-enabled/default
   nginx -t && systemctl restart nginx

   # 6. Apply SSL certificate
   certbot --nginx -d yourdomain.com
   ```

---

## 🔑 Part 3: Google Maps Platform API Setup

To get leads from Google Maps, you must set up a Google Cloud Developer account.

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project named `AIM Lead Generator`.
3. **Set up Billing**: Go to **Billing** in the sidebar menu and link a credit card. Google will not charge you immediately; they provide **$200 of free usage credits every single month**, which is more than enough for testing and initial launch.
4. **Enable APIs**: Go to the search bar at the top, search for **Places API**, select it, and click **Enable**.
5. **Get the Key**:
   - Go to **APIs & Services** -> **Credentials**.
   - Click **+ Create Credentials** -> **API Key**.
   - Copy the generated API Key.
6. **Restrict the Key (Security Best Practice)**:
   - Click **Edit API Key** next to your new key.
   - Under **API restrictions**, select **Restrict key** and check **Places API** from the list. This prevents anyone from stealing your key to use it on other expensive Google services.
7. **Add the Key to the App**:
   - Open your deployed website (`https://yourdomain.com`).
   - Paste the API Key in the **Google API Key** field.
   - Check **Save API key on this computer** and click **Generate leads** once. It will save the key locally on your server in `app_settings.json` so you can leave the box empty in the future.

---

## 💰 Part 4: Monetization Plan & SaaS Pricing Tiers

Since you are running a service, you want to charge users a subscription fee while ensuring your Google API costs remain minimal.

### 📊 API Costs vs. Pricing Margins
Google charges **$25 per 1,000 Text Search requests** ($0.025 per query). 
- One query returns up to 60 leads. 
- Generating 100 leads takes approximately 2 queries ($0.05 cost to you).
- Web scraping websites for emails uses your server's network connection and is **completely free**.

Here is the proposed pricing structure to secure a **98%+ profit margin**:

| Subscription Tier | Monthly Price | Leads Included / Mo | Queries Allowed | Cost to You | Your Profit margin |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Free / Trial** | $0 | 25 leads | 1 | $0.025 | N/A |
| **Starter** | **$29 / mo** | 500 leads | ~10 | $0.25 | **99.1%** |
| **Professional** | **$79 / mo** | 2,500 leads | ~50 | $1.25 | **98.4%** |
| **Growth/Agency** | **$149 / mo** | 6,000 leads | ~120 | $3.00 | **97.9%** |

### 🛠️ Execution Plan for Payments (Stripe)
To implement payment restrictions on the web app:
1. Register for a free account at [Stripe](https://stripe.com).
2. Integrate **Supabase** or **Firebase** for backend database and user login.
3. Use Stripe's pre-built **Stripe Billing portal** so you do not have to write credit card entry forms yourself. Users click a button, go to Stripe to pay, and get redirected back as active paid users.
