import time
import math
import random
import requests
from datetime import datetime
from colorama import init, Fore, Style
import os

init(autoreset=True)

# ========================= CONFIG =========================
STARTING_BALANCE = 1000.0
DEMO_MODE = True

SHARES_SCHEDULE = [10, 10, 20, 50]   # Buys at \~0s, 60s, 120s, 180s
GAMMA_API = "https://gamma-api.polymarket.com"

balance = STARTING_BALANCE
total_pnl = 0.0
previous_outcome = "Up"

print(f"{Fore.CYAN}=== Polymarket 5-Min BTC Momentum Bot (DEMO ONLY) ==={Style.RESET_ALL}")
print(f"Starting Capital: ${STARTING_BALANCE:,.2f}")
print(f"Buy timing: Every 60 seconds for first 4 minutes (t=0s, 60s, 120s, 180s)\n")

def get_current_window_ts():
    now = int(time.time())
    return math.floor(now / 300) * 300

def discover_btc_5m_market():
    ts = get_current_window_ts()
    slug = f"btc-updown-5m-{ts}"
    
    # Try direct slug first (most reliable)
    try:
        resp = requests.get(f"{GAMMA_API}/markets", params={"slug": slug}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data and isinstance(data, list) and len(data) > 0:
                market = data[0]
                if market.get("active", False):
                    return market
    except:
        pass
    
    # Fallback: search recent active markets
    try:
        resp = requests.get(f"{GAMMA_API}/markets", 
                           params={"active": "true", "closed": "false", "limit": 20}, 
                           timeout=10)
        if resp.status_code == 200:
            markets = resp.json()
            for m in markets:
                slug_lower = m.get("slug", "").lower()
                if "btc-updown-5m" in slug_lower:
                    return m
    except:
        pass
    
    print(f"{Fore.YELLOW}Using fallback market data.{Style.RESET_ALL}")
    return {"slug": slug, "tokens": [{"outcome": "Up", "price": 0.50}, {"outcome": "Down", "price": 0.50}]}

def get_live_prices(market):
    tokens = market.get("tokens", [])
    up_price = down_price = 0.50
    for t in tokens:
        price = float(t.get("price", 0.5))
        outcome = t.get("outcome", "").lower()
        if "up" in outcome:
            up_price = price
        elif "down" in outcome:
            down_price = price
    return round(up_price, 4), round(down_price, 4)

def colored_print(text, color=Fore.WHITE):
    print(f"{color}{text}{Style.RESET_ALL}")

# ========================= MAIN LOOP =========================
try:
    while True:
        window_ts = get_current_window_ts()
        colored_print(f"\n=== New 5-Min Window: {datetime.utcfromtimestamp(window_ts)} UTC ===", Fore.CYAN)
        
        market = discover_btc_5m_market()
        up_price, down_price = get_live_prices(market)
        direction = previous_outcome
        
        colored_print(f"Previous outcome: {previous_outcome} → Buying {direction}", Fore.YELLOW)
        colored_print(f"Live Prices → Up: ${up_price:.4f} | Down: ${down_price:.4f}", Fore.WHITE)
        
        total_cost = 0.0
        buy_prices = []
        
        # Staggered buys every 60 seconds (at t≈0s, 60s, 120s, 180s)
        for i, shares in enumerate(SHARES_SCHEDULE):
            buy_second = i * 60
            colored_print(f"\nBuy at \~{buy_second}s (Minute {i+1}): {shares} {direction}", Fore.BLUE)
            
            base_price = up_price if direction == "Up" else down_price
            drift = random.uniform(-0.008, 0.012) * (1 + i * 0.4)
            price = round(max(0.01, min(0.99, base_price * (1 + drift))), 4)
            
            cost = shares * price
            colored_print(f"  → Bought {shares} {direction} @ ${price:.4f} | Cost: ${cost:.2f}", Fore.GREEN)
            
            total_cost += cost
            buy_prices.append(price)
            
            if i < len(SHARES_SCHEDULE) - 1:
                time.sleep(60)  # Wait exactly 60s between buys
        
        avg_price = sum(buy_prices) / len(buy_prices)
        colored_print(f"\nTotal invested: ${total_cost:.2f} | Avg entry: ${avg_price:.4f}", Fore.WHITE)
        
        # Wait until end of window for resolution
        colored_print("Waiting for window resolution...", Fore.MAGENTA)
        time.sleep(300 - (len(SHARES_SCHEDULE) * 60) + 10)  # Safe remaining time
        
        # Simulate resolution
        import random
        resolved_outcome = "Up" if random.random() > 0.465 else "Down"
        won = (resolved_outcome == direction)
        payout = 90.0 if won else 0.0
        pnl = payout - total_cost
        
        total_pnl += pnl
        balance += pnl
        previous_outcome = resolved_outcome
        
        color = Fore.GREEN if pnl >= 0 else Fore.RED
        sign = "+" if pnl >= 0 else ""
        
        colored_print(f"Resolved as: {resolved_outcome}", Fore.YELLOW)
        colored_print(f"This window P&L: {sign}${abs(pnl):.2f}", color)
        colored_print(f"Live Balance: \( {balance:,.2f}   |   Total P&L: {sign} \){abs(total_pnl):.2f}", color)
        
        if balance < 100:
            colored_print("Balance too low. Stopping.", Fore.RED)
            break
        
        time.sleep(5)

except KeyboardInterrupt:
    colored_print("\nBot stopped by user.", Fore.YELLOW)
except Exception as e:
    colored_print(f"Error: {e}", Fore.RED)
