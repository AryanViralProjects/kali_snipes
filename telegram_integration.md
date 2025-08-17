Build Guide: Kali Bot Automation & Telegram AlertsObjective: This guide provides step-by-step instructions to integrate a complete automation and real-time alerting system into the Kali Sniper Bot project. This involves creating a Telegram bot for notifications and using the PM2 process manager to run all bot components as a persistent, auto-restarting service.Part 1: Setup & PrerequisitesStep 1.1: Create the Telegram Bot & Get CredentialsCreate the Bot with BotFather:In Telegram, start a chat with the official @BotFather.Send the command /newbot.Follow the prompts to choose a name (e.g., "Kali Sniper Ops") and a username (e.g., KaliSniperOpsBot).BotFather will provide you with a unique HTTP API token. Copy this token immediately.Get Your Personal Chat ID:In Telegram, start a chat with @userinfobot.Send the command /start.The bot will reply with your information, including your Id. This is your personal Chat ID. Copy this number.Step 1.2: Install Required Python LibraryOpen your terminal in the kali_sniper_bot project directory and install the necessary library for Telegram integration.pip install python-telegram-bot
Step 1.3: Update dontshare.py with New SecretsOpen the dontshare.py file and add your new Telegram credentials to the bottom.# In dontshare.py

# ... (your existing sol_key, rpc_url, etc.)

# --- TELEGRAM ALERT CREDENTIALS ---
telegram_bot_token = "YOUR_HTTP_API_TOKEN_FROM_BOTFATHER"
telegram_chat_id = "YOUR_USER_ID_FROM_USERINFOBOT"
Part 2: Code ImplementationStep 2.1: Create the Telegram ManagerCreate a new file in the root of your project named telegram_manager.py. This module will contain the function responsible for sending alerts.# telegram_manager.py

import telegram
import dontshare as d
from termcolor import cprint

def send_telegram_alert(message: str):
    """
    Sends a formatted message to your Telegram account via the bot.
    Handles missing credentials gracefully.
    """
    try:
        bot_token = getattr(d, 'telegram_bot_token', None)
        chat_id = getattr(d, 'telegram_chat_id', None)

        if not bot_token or not chat_id:
            # This check prevents crashes if credentials aren't set.
            # The bot will still run, just without alerts.
            cprint("⚠️ Telegram alerts disabled: Credentials not found in dontshare.py", 'yellow')
            return

        bot = telegram.Bot(token=bot_token)
        
        # Send the message using MarkdownV2 for rich formatting.
        # Note: MarkdownV2 requires special characters like '.', '-', '(', ')' to be escaped with a '\'.
        bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode='MarkdownV2'
        )
        cprint(f"✅ Telegram alert sent successfully!", 'green')

    except Exception as e:
        cprint(f"❌ Failed to send Telegram alert: {e}", 'red')
        # Log the problematic message for debugging
        cprint(f"   -> Failed message content: {message}", 'yellow')

Part 3: Integrating Alerts into the BotNow, we will modify the existing bot files to call the send_telegram_alert function at critical moments.Step 3.1: Alert on Successful BuyFile to edit: nice_funcs.pyFunction to edit: market_buy_fast# In nice_funcs.py

# Add this import at the top of the file
from telegram_manager import send_telegram_alert

# ... inside the market_buy_fast function ...

def market_buy_fast(token_to_buy, usdc_amount_in_lamports, keypair, http_client):
    # ... (existing logic for getting quote and sending transaction) ...

    try:
        # ... (existing try block for sending the transaction) ...
        tx_receipt = http_client.send_raw_transaction(bytes(signed_tx), opts=opts)
        tx_signature = tx_receipt.value
        
        cprint(f"✅ Kali Speed Engine: ULTRA-FAST BUY SUCCESS! 🚀", 'white', 'on_green', attrs=['bold'])
        cprint(f"💎 Token: {token_to_buy[-6:]} | TX: [https://solscan.io/tx/](https://solscan.io/tx/){str(tx_signature)}", 'green', attrs=['bold'])
        
        # --- ADD THIS BLOCK FOR TELEGRAM ALERT ---
        try:
            token_name = get_token_overview(token_to_buy).get('name', 'Unknown Token')
            buy_size_usd = usdc_amount_in_lamports / 1_000_000
            solscan_link = f"[https://solscan.io/tx/](https://solscan.io/tx/){tx_signature}"
            
            # Escape special characters for MarkdownV2
            token_name_safe = token_name.replace('-', '\\-').replace('.', '\\.')
            
            message = (
                f"*🔥 KALI SNIPE SUCCESS 🔥*\n\n"
                f"*Token:* `{token_name_safe}`\n"
                f"*Address:* `{token_to_buy}`\n"
                f"*Action:* BUY\n"
                f"*Size:* ${buy_size_usd:.2f} USD\n\n"
                f"[View on Solscan]({solscan_link})"
            )
            send_telegram_alert(message)
        except Exception as alert_error:
            cprint(f"⚠️ Failed to format or send BUY Telegram alert: {alert_error}", 'yellow')
        # --- END OF TELEGRAM ALERT BLOCK ---
            
        return str(tx_signature)
    
    # ... (rest of the function's error handling) ...
Step 3.2: Alert on Stop-Loss and Take-ProfitFile to edit: position_tracker_v2.py (or wherever your advanced_pnl_management logic resides)Function to edit: advanced_pnl_management# In position_tracker_v2.py

# Add this import at the top of the file
from telegram_manager import send_telegram_alert

# ... inside the advanced_pnl_management function's main loop ...

def advanced_pnl_management():
    # ... (existing logic to loop through positions) ...

    # === 1. STOP-LOSS CHECK (HIGHEST PRIORITY) ===
    if current_usd_value < stop_loss_value:
        cprint(f'🚨 Kali Strategy: STOP-LOSS triggered for {mint[-6:]}!', 'white', 'on_red', attrs=['bold'])
        # ... (existing cprint statements for logging to console) ...

        # --- ADD THIS BLOCK FOR TELEGRAM ALERT ---
        try:
            loss_usd = current_usd_value - initial_investment
            loss_pct = (loss_usd / initial_investment * 100) if initial_investment > 0 else 0
            message = (
                f"🚨 *KALI STOP\\-LOSS* 🚨\n\n"
                f"*Token:* `{mint}`\n"
                f"*Action:* SELL ALL\n"
                f"*Initial:* ${initial_investment:.2f} USD\n"
                f"*Current:* ${current_usd_value:.2f} USD\n"
                f"*P/L:* `${loss_usd:,.2f} USD ({loss_pct:.1f}%)`\n\n"
                f"Executing full exit now\\."
            )
            send_telegram_alert(message)
        except Exception as alert_error:
            cprint(f"⚠️ Failed to format or send STOP-LOSS Telegram alert: {alert_error}", 'yellow')
        # --- END OF TELEGRAM ALERT BLOCK ---

        kill_switch(mint)
        remove_position_state(mint)
        continue

    # === 2. TIERED TAKE-PROFIT CHECK ===
    for tier_index, tier in enumerate(SELL_TIERS):
        if current_usd_value >= tier_profit_value and tier_index not in tiers_sold:
            # ... (existing cprint statements for logging to console) ...

            # --- ADD THIS BLOCK FOR TELEGRAM ALERT ---
            try:
                profit_usd = current_usd_value - initial_investment
                profit_pct = (profit_usd / initial_investment * 100) if initial_investment > 0 else 0
                message = (
                    f"💰 *KALI TAKE PROFIT TIER {tier_index + 1}* 💰\n\n"
                    f"*Token:* `{mint}`\n"
                    f"*Action:* SELL {tier['sell_portion']*100:.0f}% of position\n"
                    f"*Current Value:* ${current_usd_value:,.2f} USD\n"
                    f"*Total P/L:* `${profit_usd:,.2f} USD ({profit_pct:+.1f}%)`\n\n"
                    f"Executing partial sell now\\."
                )
                send_telegram_alert(message)
            except Exception as alert_error:
                cprint(f"⚠️ Failed to format or send TAKE-PROFIT Telegram alert: {alert_error}", 'yellow')
            # --- END OF TELEGRAM ALERT BLOCK ---
            
            success = execute_tiered_sell(mint, tier_index, current_usd_value)
            # ... (rest of the tiered sell logic) ...
Part 4: Automation with PM2Step 4.1: Install PM2If you haven't already, ensure Node.js and npm are installed on your server/machine. Then install PM2.npm install pm2 -g
Step 4.2: Create the PM2 ecosystem.config.js FileIn the root of your kali_sniper_bot directory, create a file named ecosystem.config.js. This file will define all the services that PM2 needs to manage.// ecosystem.config.js
module.exports = {
  apps: [
    {
      name: 'KALI-Speed-Engine',
      script: 'main_speed_engine.py',
      args: 'multi', // Use 'multi' to launch all listeners (raydium, pump, virtuals)
      interpreter: 'python3',
      restart_delay: 5000, // Wait 5 seconds before restarting on crash
      autorestart: true,
      max_restarts: 10, // Attempt to restart 10 times
    },
    {
      name: 'KALI-Position-Tracker',
      script: 'position_tracker_v2.py',
      interpreter: 'python3',
      restart_delay: 5000,
      autorestart: true,
      max_restarts: 10,
    },
    {
      name: 'SARSA-Operator',
      script: 'sarsa_operator.py',
      interpreter: 'python3',
      restart_delay: 30000, // Restart Sarsa less frequently
      autorestart: true,
      max_restarts: 5,
    },
  ],
};
Step 4.3: Running and Managing the BotYou can now manage your entire bot suite with these simple commands from your terminal:Start all services: pm2 start ecosystem.config.jsMonitor logs and status: pm2 monitList all running services: pm2 listStop all services: pm2 stop allRestart all services: pm2 restart allDelete all services: pm2 delete allTo ensure the bot starts automatically if your server reboots:Run pm2 save to save the current process list.Run pm2 startup and follow the on-screen instructions to register PM2 as a startup service.


Use this token to access the HTTP API:
7430950662:AAEgQHzFFkd065x7sXD3HeL_nWFiBSs_Tr0