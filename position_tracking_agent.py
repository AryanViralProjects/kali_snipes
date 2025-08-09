#!/usr/bin/env python3
"""
🎯 KALI POSITION TRACKING AGENT
Monitors snipes from the original Kali Sniper Bot and manages positions

Features:
- Watches for new snipes in speed_engine_snipes.txt
- Automatically records positions to open_positions_state.json
- Tracks PnL every 30 seconds
- Executes exit strategies (stop-loss, profit tiers)
- Works alongside the original bot without modification
"""

import asyncio
import json
import time
import os
from datetime import datetime
from termcolor import cprint
import pandas as pd
import nice_funcs as n
from config import *
import dontshare as d

class PositionTrackingAgent:
    def __init__(self):
        self.positions_file = './data/open_positions_state.json'
        self.snipes_file = './data/speed_engine_snipes.txt'
        self.processed_snipes = set()
        self.check_interval = 30  # Check every 30 seconds
        self.running = True
        
        # Create data directory if it doesn't exist
        os.makedirs('./data', exist_ok=True)
        
        # Load existing positions
        self.positions = self.load_positions()
        
        # Load previously processed snipes to avoid duplicates
        self.load_processed_snipes()
    
    def load_positions(self):
        """Load existing positions from file"""
        try:
            if os.path.exists(self.positions_file):
                with open(self.positions_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            cprint(f"⚠️ Error loading positions: {e}", 'yellow')
            return {}
    
    def save_positions(self):
        """Save positions to file"""
        try:
            with open(self.positions_file, 'w') as f:
                json.dump(self.positions, f, indent=4)
        except Exception as e:
            cprint(f"❌ Error saving positions: {e}", 'red')
    
    def load_processed_snipes(self):
        """Load list of already processed snipes"""
        try:
            if os.path.exists(self.snipes_file):
                with open(self.snipes_file, 'r') as f:
                    for line in f:
                        parts = line.strip().split(',')
                        if len(parts) >= 3:
                            # Use signature as unique identifier
                            signature = parts[2]
                            self.processed_snipes.add(signature)
        except Exception as e:
            cprint(f"⚠️ Error loading snipes history: {e}", 'yellow')
    
    def check_for_new_snipes(self):
        """Check for new snipes from the main bot"""
        try:
            if not os.path.exists(self.snipes_file):
                return []
            
            new_snipes = []
            with open(self.snipes_file, 'r') as f:
                for line in f:
                    parts = line.strip().split(',')
                    if len(parts) >= 6 and parts[3] == 'SUCCESS':
                        signature = parts[2]
                        if signature not in self.processed_snipes:
                            # New successful snipe found!
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
                            self.processed_snipes.add(signature)
            
            return new_snipes
        except Exception as e:
            cprint(f"⚠️ Error checking snipes: {e}", 'yellow')
            return []
    
    def record_position(self, snipe_data):
        """Record a new position from a snipe"""
        token = snipe_data['token']
        
        # Get the current price to record entry price
        try:
            current_price = n.ask_bid(token)
            if not current_price or current_price == 0:
                current_price = 0
        except:
            current_price = 0
        
        if token not in self.positions:
            self.positions[token] = {
                'initial_investment_usdc': snipe_data['amount'],
                'initial_liquidity': snipe_data['liquidity'],
                'entry_timestamp': time.time(),
                'entry_price': current_price,  # Add entry price for PnL calculation
                'signature': snipe_data['signature'],
                'tiers_sold': [],
                'total_sold_usdc': 0.0,
                'strategy_type': 'tiered_dynamic'
            }
            
            self.save_positions()
            
            cprint(f"📊 Position Tracker: NEW POSITION RECORDED", 'white', 'on_green', attrs=['bold'])
            cprint(f"   Token: {token[-6:]}", 'green')
            cprint(f"   Amount: ${snipe_data['amount']:.2f}", 'green')
            cprint(f"   Entry Price: ${current_price:.8f}" if current_price > 0 else "   Entry Price: Unknown", 'green')
            cprint(f"   Liquidity: ${snipe_data['liquidity']:,.0f}", 'green')
            cprint(f"   TX: {snipe_data['signature'][:8]}...", 'green')
            cprint(f"   Saved to: {self.positions_file}", 'green')
        else:
            cprint(f"⚠️ Position already tracked for {token[-6:]}", 'yellow')
    
    def get_current_portfolio(self):
        """Get current wallet holdings"""
        try:
            holdings = n.fetch_wallet_holdings_og(MY_SOLANA_ADDERESS)
            return holdings
        except Exception as e:
            cprint(f"❌ Error fetching portfolio: {e}", 'red')
            return pd.DataFrame()
    
    def calculate_pnl(self, token_address, current_value, initial_investment):
        """Calculate PnL for a position"""
        pnl_usd = current_value - initial_investment
        pnl_pct = ((current_value / initial_investment) - 1) * 100 if initial_investment > 0 else 0
        return pnl_usd, pnl_pct
    
    def check_exit_conditions(self, token_address, current_value, position_data):
        """Check if any exit conditions are met"""
        initial = position_data['initial_investment_usdc']
        tiers_sold = position_data.get('tiers_sold', [])
        
        # Check stop-loss
        stop_loss_value = initial * (1 + STOP_LOSS_PERCENTAGE)
        if current_value < stop_loss_value and current_value > 0:
            return 'STOP_LOSS', stop_loss_value
        
        # Check profit tiers
        for tier_idx, tier in enumerate(SELL_TIERS):
            if tier_idx in tiers_sold:
                continue  # Already sold this tier
            
            tier_value = initial * tier['profit_multiple']
            if current_value >= tier_value:
                return f'TIER_{tier_idx}', tier_value
        
        return None, None
    
    def execute_exit(self, token_address, exit_type, current_value):
        """Execute an exit strategy"""
        try:
            cprint(f"🚨 Position Tracker: EXECUTING {exit_type} for {token_address[-6:]}", 'white', 'on_red', attrs=['bold'])
            
            if exit_type == 'STOP_LOSS':
                # Full exit on stop-loss
                cprint(f"   Stop-loss triggered! Selling 100% of position", 'red')
                n.kill_switch(token_address)
                
                # Remove from tracking
                if token_address in self.positions:
                    del self.positions[token_address]
                    self.save_positions()
                    cprint(f"   Position closed and removed from tracking", 'red')
            
            elif exit_type.startswith('TIER_'):
                tier_idx = int(exit_type.split('_')[1])
                tier = SELL_TIERS[tier_idx]
                
                cprint(f"   Profit tier {tier_idx + 1} hit ({tier['name']})!", 'green')
                cprint(f"   Selling {tier['sell_portion'] * 100:.0f}% of position", 'green')
                
                # Execute tiered sell
                success = n.execute_tiered_sell(token_address, tier_idx, current_value)
                
                if success:
                    # Update position data
                    self.positions[token_address]['tiers_sold'].append(tier_idx)
                    self.save_positions()
                    
                    # Check if this was the last tier
                    if tier_idx == len(SELL_TIERS) - 1:
                        cprint(f"   Final tier executed, closing position", 'green')
                        if token_address in self.positions:
                            del self.positions[token_address]
                            self.save_positions()
            
        except Exception as e:
            cprint(f"❌ Error executing exit: {e}", 'red')
    
    async def monitor_positions(self):
        """Monitor all positions for PnL and exit conditions"""
        if not self.positions:
            return
        
        cprint(f"\n📈 Checking {len(self.positions)} position(s)...", 'cyan')
        
        holdings = self.get_current_portfolio()
        
        positions_to_remove = []
        
        for token_address, position_data in self.positions.items():
            # Get current value directly using the token address
            try:
                # Get token balance
                balance = n.get_position(token_address)
                
                if balance == 0:
                    cprint(f"   ⚠️ {token_address[-6:]} not in wallet (balance: 0) - removing", 'yellow')
                    positions_to_remove.append(token_address)
                    continue
                
                # Get current price
                current_price = n.ask_bid(token_address)
                if not current_price:
                    current_price = 0
                
                current_value = balance * current_price
            except Exception as e:
                cprint(f"   ⚠️ Error getting value for {token_address[-6:]}: {e}", 'yellow')
                current_value = 0
            
            initial = position_data['initial_investment_usdc']
            
            # Calculate PnL
            pnl_usd, pnl_pct = self.calculate_pnl(token_address, current_value, initial)
            
            # Display position status
            if pnl_usd >= 0:
                cprint(f"   {token_address[-6:]}: ${current_value:.2f} (+${pnl_usd:.2f}, +{pnl_pct:.1f}%)", 'green')
            else:
                cprint(f"   {token_address[-6:]}: ${current_value:.2f} (-${abs(pnl_usd):.2f}, {pnl_pct:.1f}%)", 'red')
            
            # Check exit conditions
            exit_type, trigger_value = self.check_exit_conditions(token_address, current_value, position_data)
            
            if exit_type:
                cprint(f"   🎯 EXIT TRIGGER: {exit_type} at ${trigger_value:.2f}", 'yellow', attrs=['bold'])
                await asyncio.sleep(1)  # Small delay before execution
                self.execute_exit(token_address, exit_type, current_value)
        
        # Clean up positions no longer in wallet
        for token in positions_to_remove:
            if token in self.positions:
                del self.positions[token]
        
        if positions_to_remove:
            self.save_positions()
    
    async def run(self):
        """Main loop"""
        print("="*80)
        cprint("🎯 KALI POSITION TRACKING AGENT", 'white', 'on_blue', attrs=['bold'])
        print("="*80)
        
        cprint(f"📊 Configuration:", 'cyan')
        cprint(f"   Stop-loss: {STOP_LOSS_PERCENTAGE:.0%}", 'cyan')
        cprint(f"   Profit Tiers: {len(SELL_TIERS)} levels", 'cyan')
        cprint(f"   Check Interval: {self.check_interval}s", 'cyan')
        cprint(f"   Positions File: {self.positions_file}", 'cyan')
        
        # Show existing positions
        if self.positions:
            cprint(f"\n📈 Tracking {len(self.positions)} existing position(s):", 'yellow')
            for token in self.positions:
                cprint(f"   - {token[-6:]}: ${self.positions[token]['initial_investment_usdc']:.2f}", 'yellow')
        
        cprint(f"\n✅ Agent started. Monitoring for new snipes and tracking PnL...", 'green')
        print("="*80)
        
        while self.running:
            try:
                # Check for new snipes from main bot
                new_snipes = self.check_for_new_snipes()
                for snipe in new_snipes:
                    self.record_position(snipe)
                
                # Monitor existing positions
                await self.monitor_positions()
                
                # Wait before next check
                await asyncio.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                cprint("\n⏹️ Shutting down Position Tracking Agent...", 'yellow')
                self.running = False
                break
            except Exception as e:
                cprint(f"❌ Error in main loop: {e}", 'red')
                await asyncio.sleep(5)
        
        cprint("👋 Position Tracking Agent stopped", 'yellow')

async def main():
    """Entry point"""
    agent = PositionTrackingAgent()
    await agent.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")