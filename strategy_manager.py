#!/usr/bin/env python3
"""
🎯 KALI STRATEGY ENGINE - MANAGEMENT UTILITY
Manage dynamic position sizing, view tiered performance, and analyze strategy effectiveness
"""

import sys
import os
from datetime import datetime, timedelta
import json
from termcolor import cprint
import nice_funcs as n
from config import *

class StrategyManager:
    def __init__(self):
        self.state_file = OPEN_POSITIONS_STATE_FILE
        self.snipes_file = './data/speed_engine_snipes.txt'
        
    def show_strategy_overview(self):
        """Display comprehensive strategy overview"""
        cprint("🎯 KALI STRATEGY ENGINE - OVERVIEW", 'white', 'on_blue', attrs=['bold'])
        
        # Current configuration
        cprint(f"\n⚙️ Strategy Configuration:", 'white', 'on_cyan')
        cprint(f"   Dynamic Sizing: {'✅ Enabled' if ENABLE_DYNAMIC_SIZING else '❌ Disabled'}", 'cyan')
        cprint(f"   Tiered Exits: {'✅ Enabled' if ENABLE_TIERED_EXITS else '❌ Disabled'}", 'cyan')
        cprint(f"   LP Target %: {USDC_BUY_TARGET_PERCENT_OF_LP*100:.1f}%", 'cyan')
        cprint(f"   Size Range: ${USDC_MIN_BUY_SIZE} - ${USDC_MAX_BUY_SIZE}", 'cyan')
        cprint(f"   Stop Loss: {STOP_LOSS_PERCENTAGE*100:+.0f}%", 'cyan')
        
        # Profit tiers
        cprint(f"\n🎯 Profit Tiers ({len(SELL_TIERS)} levels):", 'white', 'on_green')
        for i, tier in enumerate(SELL_TIERS):
            profit_percent = (tier['profit_multiple'] - 1) * 100
            sell_percent = tier['sell_portion'] * 100
            cprint(f"   Tier {i+1}: {tier['name']}", 'green', attrs=['bold'])
            cprint(f"     Trigger: {profit_percent:+.0f}% profit ({tier['profit_multiple']:.1f}x)", 'green')
            cprint(f"     Action: Sell {sell_percent:.0f}% of position", 'green')
        
        # Current positions
        self.show_active_positions()
        
        # Performance metrics
        self.show_performance_metrics()
        
    def show_active_positions(self):
        """Display currently tracked positions"""
        cprint(f"\n📊 Active Position Tracking:", 'white', 'on_cyan')
        
        try:
            states = n.load_position_states()
            
            if not states:
                cprint("   No positions currently tracked", 'yellow')
                return
                
            total_invested = 0
            total_current_value = 0
            
            for token, state in states.items():
                initial = state.get('initial_investment_usdc', 0)
                liquidity = state.get('initial_liquidity', 0)
                tiers_sold = state.get('tiers_sold', [])
                total_sold = state.get('total_sold_usdc', 0)
                entry_time = datetime.fromtimestamp(state.get('entry_timestamp', 0))
                
                total_invested += initial
                
                cprint(f"\n   🎯 Position: {token[-6:]}", 'white', 'on_blue', attrs=['bold'])
                cprint(f"      Entry: ${initial:.2f} | LP: ${liquidity:,.0f} | Entry Time: {entry_time.strftime('%m/%d %H:%M')}", 'blue')
                cprint(f"      Tiers Hit: {len(tiers_sold)}/{len(SELL_TIERS)} | Total Sold: ${total_sold:.2f}", 'blue')
                
                if tiers_sold:
                    cprint(f"      Executed: ", 'green', end='')
                    for tier_idx in tiers_sold:
                        if tier_idx < len(SELL_TIERS):
                            cprint(f"{SELL_TIERS[tier_idx]['name']} ", 'green', end='')
                    print()  # New line
                    
            cprint(f"\n   📈 Portfolio Summary:", 'white', 'on_blue')
            cprint(f"      Active Positions: {len(states)}", 'blue')
            cprint(f"      Total Invested: ${total_invested:.2f}", 'blue')
            
        except Exception as e:
            cprint(f"   ❌ Error reading position states: {e}", 'red')
    
    def show_performance_metrics(self):
        """Display strategy performance metrics"""
        cprint(f"\n📈 Strategy Performance (Last 24h):", 'white', 'on_green')
        
        try:
            # Analyze speed engine snipes for dynamic sizing performance
            dynamic_trades = self.analyze_dynamic_trades()
            
            if dynamic_trades['total'] > 0:
                avg_size = dynamic_trades['total_invested'] / dynamic_trades['total']
                avg_lp_impact = dynamic_trades['avg_lp_impact']
                
                cprint(f"   Dynamic Trades: {dynamic_trades['total']}", 'green')
                cprint(f"   Average Size: ${avg_size:.2f} (vs ${USDC_SIZE:.2f} fixed)", 'green')
                cprint(f"   LP Impact: {avg_lp_impact:.3f}% average", 'green')
                cprint(f"   Size Factor Range: {dynamic_trades['min_factor']:.2f}x - {dynamic_trades['max_factor']:.2f}x", 'green')
            else:
                cprint("   No dynamic trades in last 24 hours", 'yellow')
                
            # Position state analysis
            states = n.load_position_states()
            if states:
                tier_stats = self.analyze_tier_performance(states)
                cprint(f"\n   Tier Performance:", 'green')
                for i, tier in enumerate(SELL_TIERS):
                    executions = tier_stats.get(i, 0)
                    cprint(f"     {tier['name']}: {executions} executions", 'green')
                    
        except Exception as e:
            cprint(f"   ❌ Error calculating performance: {e}", 'red')
    
    def analyze_dynamic_trades(self):
        """Analyze dynamic trading performance from logs"""
        stats = {
            'total': 0,
            'total_invested': 0.0,
            'avg_lp_impact': 0.0,
            'min_factor': float('inf'),
            'max_factor': 0.0
        }
        
        try:
            if not os.path.exists(self.snipes_file):
                return stats
                
            cutoff_time = datetime.now() - timedelta(hours=24)
            
            with open(self.snipes_file, 'r') as f:
                for line in f:
                    try:
                        parts = line.strip().split(',')
                        if len(parts) >= 6:  # New format with size and liquidity
                            timestamp_str = parts[0]
                            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                            
                            if timestamp >= cutoff_time:
                                size_str = parts[4]  # Format: $X.XX
                                liquidity_str = parts[5]  # Format: $X
                                
                                size = float(size_str.replace('$', ''))
                                liquidity = float(liquidity_str.replace('$', ''))
                                
                                stats['total'] += 1
                                stats['total_invested'] += size
                                
                                if liquidity > 0:
                                    lp_impact = (size / liquidity) * 100
                                    stats['avg_lp_impact'] += lp_impact
                                    
                                size_factor = size / USDC_SIZE
                                stats['min_factor'] = min(stats['min_factor'], size_factor)
                                stats['max_factor'] = max(stats['max_factor'], size_factor)
                                
                    except Exception:
                        continue
                        
            if stats['total'] > 0:
                stats['avg_lp_impact'] /= stats['total']
                if stats['min_factor'] == float('inf'):
                    stats['min_factor'] = 1.0
                    
        except Exception:
            pass
            
        return stats
    
    def analyze_tier_performance(self, states):
        """Analyze tier execution frequency"""
        tier_stats = {}
        
        for token, state in states.items():
            tiers_sold = state.get('tiers_sold', [])
            for tier_idx in tiers_sold:
                tier_stats[tier_idx] = tier_stats.get(tier_idx, 0) + 1
                
        return tier_stats
    
    def adjust_strategy_settings(self, setting, value):
        """Adjust strategy settings (for advanced users)"""
        cprint(f"⚙️ Strategy Setting Adjustment", 'white', 'on_yellow')
        cprint(f"   This would modify {setting} to {value}", 'yellow')
        cprint(f"   Manual config editing required in config.py", 'yellow')
    
    def export_performance_report(self):
        """Export detailed performance report"""
        cprint("📊 Exporting Strategy Performance Report...", 'white', 'on_blue')
        
        try:
            report = {
                "generated_at": datetime.now().isoformat(),
                "strategy_config": {
                    "dynamic_sizing_enabled": ENABLE_DYNAMIC_SIZING,
                    "tiered_exits_enabled": ENABLE_TIERED_EXITS,
                    "lp_target_percent": USDC_BUY_TARGET_PERCENT_OF_LP,
                    "size_range": [USDC_MIN_BUY_SIZE, USDC_MAX_BUY_SIZE],
                    "stop_loss_percent": STOP_LOSS_PERCENTAGE,
                    "profit_tiers": SELL_TIERS
                },
                "active_positions": n.load_position_states(),
                "dynamic_trades_24h": self.analyze_dynamic_trades()
            }
            
            report_file = f"./data/strategy_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
                
            cprint(f"✅ Report exported: {report_file}", 'green')
            
        except Exception as e:
            cprint(f"❌ Export error: {e}", 'red')
    
    def simulate_strategy_scenarios(self):
        """Simulate different strategy scenarios"""
        cprint("🎮 Strategy Scenario Simulation", 'white', 'on_blue')
        
        scenarios = [
            {"name": "Small Pool ($1K LP)", "liquidity": 1000},
            {"name": "Medium Pool ($10K LP)", "liquidity": 10000},
            {"name": "Large Pool ($100K LP)", "liquidity": 100000},
            {"name": "Mega Pool ($1M LP)", "liquidity": 1000000}
        ]
        
        cprint("\n📊 Dynamic Sizing Simulation:", 'cyan')
        
        for scenario in scenarios:
            liquidity = scenario["liquidity"]
            name = scenario["name"]
            
            # Calculate what size would be used
            target_size = liquidity * USDC_BUY_TARGET_PERCENT_OF_LP
            actual_size = max(USDC_MIN_BUY_SIZE, min(target_size, USDC_MAX_BUY_SIZE))
            lp_impact = (actual_size / liquidity) * 100
            size_factor = actual_size / USDC_SIZE
            
            cprint(f"\n   {name}:", 'white', 'on_cyan')
            cprint(f"     Size: ${actual_size:.2f} ({size_factor:.2f}x factor)", 'cyan')
            cprint(f"     LP Impact: {lp_impact:.3f}%", 'cyan')
            
        # Profit tier simulation
        cprint("\n🎯 Profit Tier Simulation (${} investment):".format(USDC_MIN_BUY_SIZE), 'green')
        
        for i, tier in enumerate(SELL_TIERS):
            profit_value = USDC_MIN_BUY_SIZE * tier['profit_multiple']
            profit_amount = profit_value - USDC_MIN_BUY_SIZE
            sell_portion = tier['sell_portion']
            
            cprint(f"\n   Tier {i+1}: {tier['name']}", 'white', 'on_green')
            cprint(f"     Trigger: ${profit_value:.2f} value (+${profit_amount:.2f})", 'green')
            cprint(f"     Action: Sell {sell_portion*100:.0f}% of remaining position", 'green')

def main():
    """Main CLI interface"""
    manager = StrategyManager()
    
    if len(sys.argv) < 2:
        cprint("🎯 KALI STRATEGY ENGINE - MANAGEMENT UTILITY", 'white', 'on_blue', attrs=['bold'])
        cprint("\nUsage:", 'white')
        cprint("  python strategy_manager.py overview          # Show strategy overview", 'cyan')
        cprint("  python strategy_manager.py positions         # Show active positions", 'cyan')
        cprint("  python strategy_manager.py performance       # Show performance metrics", 'cyan')
        cprint("  python strategy_manager.py simulate          # Run strategy simulations", 'cyan')
        cprint("  python strategy_manager.py export            # Export performance report", 'cyan')
        return
    
    command = sys.argv[1].lower()
    
    if command == "overview":
        manager.show_strategy_overview()
    elif command == "positions":
        manager.show_active_positions()
    elif command == "performance":
        manager.show_performance_metrics()
    elif command == "simulate":
        manager.simulate_strategy_scenarios()
    elif command == "export":
        manager.export_performance_report()
    else:
        cprint(f"❌ Unknown command: {command}", 'red')
        cprint("Use 'python strategy_manager.py' for help", 'yellow')

if __name__ == "__main__":
    main()