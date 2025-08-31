# config.py - fill TELEGRAM_TOKEN before running
TELEGRAM_TOKEN = "7717901847:AAHytaN_hObl-6G8IB43r8qhRSZ7svnO6gM"

# WayForPay merchant (you provided these earlier)
MERCHANT_ACCOUNT = "www_instagram_com_84d14"
MERCHANT_SECRET_KEY = "23434a4fff7cd0e1b1b2f928ffa41d40370bc4b1"
MERCHANT_DOMAIN_NAME = "vipfitparkovabot-production.up.railway.app"  # set to your Railway domain (no https)

# Callback URL (public) that WayForPay will call after payment
# Example: "https://your-domain.up.railway.app/wfp-callback"
CALLBACK_URL = "https://vipfitparkovabot-production.up.railway.app/wfp-callback"

# Subscription settings
SUBSCRIPTION_PRICE = 100  # UAH per month
