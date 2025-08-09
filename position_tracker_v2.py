#!/usr/bin/env python3
"""
🎯 KALI POSITION TRACKER V2 - Enhanced Version
Improved tracking with better token identification and PnL calculation
"""

import asyncio
import json
import time
import os
from datetime import datetime
from termcolor import cprint
import nice_funcs as n
from config import *
import dontshare as d

class EnhancedPositionTracker:
    def __init__(self):
        self.positions_file = './data/open_positions_state.json'
        self.snipes_file = './data/speed_engine_snipes.txt'
        self.processed_snipes_file = './data/processed_snipes.txt'
        self.check_interval = 30  # Check every 30 seconds
        self.running = True
        
        # Create data directory if needed
        os.makedirs('./data', exist_ok=True)
        
        # Load state
        self.positions = self.load_positions()
        self.processed_snipes = self.load_processed_snipes()
    
    def load_positions(self):
        """Load existing positions"""
        try:
            if os.path.exists(self.positions_file):
                with open(self.positions_file, 'r') as f:
                    data = json.load(f)
                    cprint(f"📂 Loaded {len(data)} existing position(s)", 'cyan')
                    return data
            return {}
        except Exception as e:
            cprint(f"⚠️ Error loading positions: {e}", 'yellow')
            return {}
    
    def save_positions(self):
        """Save positions to file"""
        try:
            with open(self.positions_file, 'w') as f:
                json.dump(self.positions, f, indent=4)
            # cprint(f"💾 Saved {len(self.positions)} position(s)", 'green')
        except Exception as e:
            cprint(f"❌ Error saving positions: {e}", 'red')
    
    def load_processed_snipes(self):
        """Load processed snipes to avoid duplicates"""
        processed = set()
        try:
            if os.path.exists(self.processed_snipes_file):
                with open(self.processed_snipes_file, 'r') as f:
                    for line in f:
                        processed.add(line.strip())
        except:
            pass
        return processed
    
    def save_processed_snipe(self, signature):
        """Mark a snipe as processed"""
        try:
            with open(self.processed_snipes_file, 'a') as f:
                f.write(f"{signature}\n")
            self.processed_snipes.add(signature)
        except:
            pass
    
    def check_for_new_snipes(self):
        """Check for new successful snipes"""
        try:
            if not os.path.exists(self.snipes_file):
                return []
            
            new_snipes = []
            with open(self.snipes_file, 'r') as f:
                for line in f:
                    parts = line.strip().split(',')
                    if len(parts) >= 6 and parts[3] == 'SUCCESS':
                        signature = parts[2]
                        
                        # Skip if already processed
                        if signature in self.processed_snipes:
                            continue
                        
                        token_address = parts[1]
                        amount = float(parts[4].replace('$', ''))
                        liquidity = float(parts[5].replace('$', '')) if len(parts) > 5 else 0
                        
                        new_snipes.append({
                            'token': token_address,
                            'signature': signature,
                            'amount': amount,
                            'liquidity': liquidity,
                            'timestamp': parts[0]
                        })
            
            return new_snipes
        except Exception as e:
            cprint(f"⚠️ Error checking snipes: {e}", 'yellow')
            return []
    
    def get_token_info(self, token_address):
        """Get token price and name"""
        try:
            # Get price
            price = n.ask_bid(token_address)
            
            # Get token overview for name
            overview = n.get_token_overview(token_address)
            name = overview.get('name', token_address[-6:]) if overview else token_address[-6:]
            
            return price, name
        except:
            return 0, token_address[-6:]
    
    def record_position(self, snipe_data):
        """Record a new position"""
        token = snipe_data['token']
        
        # Skip if already tracked
        if token in self.positions:
            return
        
        # Get token info
        entry_price, token_name = self.get_token_info(token)
        
        # Calculate initial token amount from USD investment
        if entry_price > 0:
            token_amount = snipe_data['amount'] / entry_price
        else:
            token_amount = 0
        
        # Record position
        self.positions[token] = {
            'token_name': token_name,
            'initial_investment_usdc': snipe_data['amount'],
            'entry_price': entry_price,
            'token_amount': token_amount,
            'initial_liquidity': snipe_data['liquidity'],
            'entry_timestamp': time.time(),
            'signature': snipe_data['signature'],
            'tiers_sold': [],
            'total_sold_usdc': 0.0,
            'strategy_type': 'tiered_dynamic'
        }
        
        self.save_positions()
        self.save_processed_snipe(snipe_data['signature'])
        
        cprint(f"\n🎯 NEW POSITION RECORDED", 'white', 'on_green', attrs=['bold'])
        cprint(f"   Token: {token_name} ({token[-6:]})", 'green')
        cprint(f"   Investment: ${snipe_data['amount']:.2f} USDC", 'green')
        cprint(f"   Entry Price: ${entry_price:.8f}" if entry_price > 0 else "   Entry Price: Fetching...", 'green')
        cprint(f"   Token Amount: {token_amount:,.2f}" if token_amount > 0 else "   Token Amount: Calculating...", 'green')
        cprint(f"   Liquidity: ${snipe_data['liquidity']:,.0f}", 'green')
        cprint(f"   TX: {snipe_data['signature'][:8]}...", 'green')
    
    async def monitor_positions(self):
        """Monitor positions for PnL and exits"""
        if not self.positions:
            return
        
        print(f"\n📊 Monitoring {len(self.positions)} position(s)...")
        print("-" * 60)
        
        positions_to_remove = []
        
        for token_address, position_data in self.positions.items():
            try:
                # Get current balance
                balance = n.get_position(token_address)
                
                # Check if position still exists
                if balance == 0:
                    cprint(f"❌ {position_data.get('token_name', token_address[-6:])}: Position closed (no balance)", 'yellow')
                    positions_to_remove.append(token_address)
                    continue
                
                # Get current price
                current_price = n.ask_bid(token_address)
                if not current_price:
                    current_price = 0
                
                # Calculate current value
                current_value = balance * current_price
                initial = position_data['initial_investment_usdc']
                entry_price = position_data.get('entry_price', 0)
                
                # Calculate PnL
                pnl_usd = current_value - initial
                pnl_pct = ((current_value / initial) - 1) * 100 if initial > 0 else 0
                
                # Calculate price change
                if entry_price > 0 and current_price > 0:
                    price_change_pct = ((current_price / entry_price) - 1) * 100
                else:
                    price_change_pct = 0
                
                # Display status
                token_name = position_data.get('token_name', token_address[-6:])
                
                if pnl_usd >= 0:
                    cprint(f"📈 {token_name}:", 'white', attrs=['bold'])
                    cprint(f"   Value: ${current_value:.2f} (+${pnl_usd:.2f}, +{pnl_pct:.1f}%)", 'green')
                else:
                    cprint(f"📉 {token_name}:", 'white', attrs=['bold'])
                    cprint(f"   Value: ${current_value:.2f} (-${abs(pnl_usd):.2f}, {pnl_pct:.1f}%)", 'red')
                
                cprint(f"   Price: ${current_price:.8f} ({price_change_pct:+.1f}% from entry)", 'cyan')
                cprint(f"   Balance: {balance:,.2f} tokens", 'cyan')
                
                # Check exit conditions
                stop_loss_value = initial * (1 + STOP_LOSS_PERCENTAGE)
                
                # Stop-loss check
                if current_value < stop_loss_value and current_value > 0:
                    cprint(f"   🚨 STOP-LOSS TRIGGERED! (${current_value:.2f} < ${stop_loss_value:.2f})", 'white', 'on_red')
                    await self.execute_exit(token_address, 'STOP_LOSS', current_value)
                    positions_to_remove.append(token_address)
                    continue
                
                # Profit tier checks
                tiers_sold = position_data.get('tiers_sold', [])
                for tier_idx, tier in enumerate(SELL_TIERS):
                    if tier_idx in tiers_sold:
                        continue
                    
                    tier_value = initial * tier['profit_multiple']
                    if current_value >= tier_value:
                        cprint(f"   🎯 TIER {tier_idx + 1} HIT! ({tier['name']}) - Target: ${tier_value:.2f}", 'white', 'on_green')
                        await self.execute_exit(token_address, f'TIER_{tier_idx}', current_value)
                        
                        # Update position
                        self.positions[token_address]['tiers_sold'].append(tier_idx)
                        self.save_positions()
                        
                        # Check if final tier
                        if tier_idx == len(SELL_TIERS) - 1:
                            positions_to_remove.append(token_address)
                        break
                
            except Exception as e:
                cprint(f"⚠️ Error monitoring {token_address[-6:]}: {e}", 'yellow')
        
        # Clean up closed positions
        for token in positions_to_remove:
            if token in self.positions:
                del self.positions[token]
        
        if positions_to_remove:
            self.save_positions()
            cprint(f"\n🧹 Removed {len(positions_to_remove)} closed position(s)", 'cyan')
    
    async def execute_exit(self, token_address, exit_type, current_value):
        """Execute exit strategy"""
        try:
            if exit_type == 'STOP_LOSS':
                cprint(f"\n💔 Executing STOP-LOSS for {token_address[-6:]}", 'red', attrs=['bold'])
                n.kill_switch(token_address)
            elif exit_type.startswith('TIER_'):
                tier_idx = int(exit_type.split('_')[1])
                cprint(f"\n💰 Executing TIER {tier_idx + 1} exit for {token_address[-6:]}", 'green', attrs=['bold'])
                n.execute_tiered_sell(token_address, tier_idx, current_value)
        except Exception as e:
            cprint(f"❌ Exit execution error: {e}", 'red')
    
    async def run(self):
        """Main loop"""
        print("="*80)
        cprint("🎯 KALI POSITION TRACKER V2", 'white', 'on_blue', attrs=['bold'])
        print("="*80)
        
        print(f"📊 Configuration:")
        print(f"   Stop-loss: {STOP_LOSS_PERCENTAGE:.0%}")
        tier_list = ', '.join([f"{t['profit_multiple']}x" for t in SELL_TIERS])
        print(f"   Profit Tiers: {tier_list}")
        print(f"   Check Interval: {self.check_interval}s")
        print(f"   Tracking: {len(self.positions)} position(s)")
        
        print("\n✅ Tracker started. Monitoring snipes and positions...")
        print("="*80)
        
        while self.running:
            try:
                # Check for new snipes
                new_snipes = self.check_for_new_snipes()
                for snipe in new_snipes:
                    self.record_position(snipe)
                
                # Monitor positions
                await self.monitor_positions()
                
                # Wait
                await asyncio.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                cprint(f"❌ Main loop error: {e}", 'red')
                await asyncio.sleep(5)
        
        print("\n👋 Position Tracker stopped")

if __name__ == "__main__":
    tracker = EnhancedPositionTracker()
    asyncio.run(tracker.run())