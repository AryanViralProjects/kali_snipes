#!/usr/bin/env python3
"""
🧠 KALI INTELLIGENCE ENGINE - MANAGEMENT UTILITY
Manage deployer blacklists, view statistics, and analyze token vetting performance
"""

import sys
import os
from datetime import datetime, timedelta
import pandas as pd
from termcolor import cprint
import nice_funcs as n

class IntelligenceManager:
    def __init__(self):
        self.deployer_blacklist_file = './data/deployer_blacklist.txt'
        self.rejections_file = './data/intelligence_rejections.txt'
        self.snipes_file = './data/speed_engine_snipes.txt'
        
    def show_statistics(self):
        """Display intelligence engine statistics"""
        cprint("🧠 KALI INTELLIGENCE ENGINE - STATISTICS", 'white', 'on_blue', attrs=['bold'])
        
        # Deployer blacklist stats
        blacklist_count = self.get_blacklist_count()
        cprint(f"\n📋 Deployer Blacklist:", 'white', 'on_cyan')
        cprint(f"   Total blacklisted deployers: {blacklist_count}", 'cyan')
        
        # Rejection stats
        rejection_stats = self.get_rejection_stats()
        cprint(f"\n🚫 Token Rejections (Last 24 hours):", 'white', 'on_red')
        cprint(f"   Total rejected: {rejection_stats['total']}", 'red')
        cprint(f"   Security failures: {rejection_stats['security']}", 'red')
        cprint(f"   Liquidity failures: {rejection_stats['liquidity']}", 'red')
        cprint(f"   Deployer blacklisted: {rejection_stats['deployer']}", 'red')
        
        # Success stats
        success_stats = self.get_success_stats()
        cprint(f"\n✅ Successful Snipes (Last 24 hours):", 'white', 'on_green')
        cprint(f"   Total successful: {success_stats['total']}", 'green')
        cprint(f"   Intelligence approval rate: {success_stats['approval_rate']:.1f}%", 'green')
        
    def get_blacklist_count(self):
        """Count blacklisted deployers"""
        try:
            if not os.path.exists(self.deployer_blacklist_file):
                return 0
            
            count = 0
            with open(self.deployer_blacklist_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        count += 1
            return count
        except Exception:
            return 0
    
    def get_rejection_stats(self):
        """Get rejection statistics"""
        stats = {'total': 0, 'security': 0, 'liquidity': 0, 'deployer': 0}
        
        try:
            if not os.path.exists(self.rejections_file):
                return stats
                
            cutoff_time = datetime.now() - timedelta(hours=24)
            
            with open(self.rejections_file, 'r') as f:
                for line in f:
                    try:
                        parts = line.strip().split(',')
                        if len(parts) >= 3:
                            timestamp_str = parts[0]
                            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                            
                            if timestamp >= cutoff_time:
                                stats['total'] += 1
                                # Could add more detailed categorization here
                                
                    except Exception:
                        continue
        except Exception:
            pass
            
        return stats
    
    def get_success_stats(self):
        """Get success statistics"""
        stats = {'total': 0, 'approval_rate': 0.0}
        
        try:
            if not os.path.exists(self.snipes_file):
                return stats
                
            cutoff_time = datetime.now() - timedelta(hours=24)
            
            with open(self.snipes_file, 'r') as f:
                for line in f:
                    try:
                        parts = line.strip().split(',')
                        if len(parts) >= 4:
                            timestamp_str = parts[0]
                            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                            
                            if timestamp >= cutoff_time:
                                stats['total'] += 1
                                
                    except Exception:
                        continue
                        
            # Calculate approval rate (successes vs total attempts)
            rejections = self.get_rejection_stats()['total']
            total_attempts = stats['total'] + rejections
            if total_attempts > 0:
                stats['approval_rate'] = (stats['total'] / total_attempts) * 100
                
        except Exception:
            pass
            
        return stats
    
    def add_deployer_to_blacklist(self, deployer_address, reason="manual_add"):
        """Add a deployer to the blacklist"""
        cprint(f"🚫 Adding deployer to blacklist...", 'white', 'on_red')
        
        if not deployer_address:
            cprint("❌ Error: No deployer address provided", 'red')
            return False
            
        # Validate address format (basic check)
        if len(deployer_address) < 40 or len(deployer_address) > 50:
            cprint("❌ Error: Invalid Solana address format", 'red')
            return False
            
        n.add_deployer_to_blacklist(deployer_address, reason)
        cprint(f"✅ Deployer {deployer_address[-6:]} added to blacklist", 'green')
        return True
    
    def view_blacklist(self):
        """View current deployer blacklist"""
        cprint("🚫 DEPLOYER BLACKLIST", 'white', 'on_red', attrs=['bold'])
        
        try:
            if not os.path.exists(self.deployer_blacklist_file):
                cprint("   No blacklist file found", 'yellow')
                return
                
            with open(self.deployer_blacklist_file, 'r') as f:
                lines = f.readlines()
                
            blacklisted_count = 0
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split(',')
                    address = parts[0].strip()
                    reason = parts[1].strip() if len(parts) > 1 else "no reason given"
                    cprint(f"   {address[-6:]}...{address[:6]} - {reason}", 'red')
                    blacklisted_count += 1
                    
            if blacklisted_count == 0:
                cprint("   No deployers currently blacklisted", 'yellow')
            else:
                cprint(f"\n   Total: {blacklisted_count} blacklisted deployers", 'white', 'on_red')
                
        except Exception as e:
            cprint(f"❌ Error reading blacklist: {e}", 'red')
    
    def view_recent_rejections(self, hours=24):
        """View recent intelligence rejections"""
        cprint(f"🚫 RECENT REJECTIONS (Last {hours} hours)", 'white', 'on_red', attrs=['bold'])
        
        try:
            if not os.path.exists(self.rejections_file):
                cprint("   No rejections file found", 'yellow')
                return
                
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            with open(self.rejections_file, 'r') as f:
                lines = f.readlines()
                
            recent_rejections = []
            for line in lines:
                try:
                    parts = line.strip().split(',')
                    if len(parts) >= 3:
                        timestamp_str = parts[0]
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                        
                        if timestamp >= cutoff_time:
                            token_address = parts[1]
                            reason = parts[3] if len(parts) > 3 else "INTELLIGENCE_REJECTED"
                            recent_rejections.append((timestamp_str, token_address, reason))
                            
                except Exception:
                    continue
                    
            if not recent_rejections:
                cprint("   No recent rejections", 'yellow')
            else:
                for timestamp, token, reason in recent_rejections[-10:]:  # Show last 10
                    cprint(f"   {timestamp} - {token[-6:]} - {reason}", 'red')
                cprint(f"\n   Total: {len(recent_rejections)} rejections", 'white', 'on_red')
                
        except Exception as e:
            cprint(f"❌ Error reading rejections: {e}", 'red')

def main():
    """Main CLI interface"""
    manager = IntelligenceManager()
    
    if len(sys.argv) < 2:
        cprint("🧠 KALI INTELLIGENCE ENGINE - MANAGEMENT UTILITY", 'white', 'on_blue', attrs=['bold'])
        cprint("\nUsage:", 'white')
        cprint("  python intelligence_manager.py stats              # Show statistics", 'cyan')
        cprint("  python intelligence_manager.py blacklist          # View deployer blacklist", 'cyan')
        cprint("  python intelligence_manager.py rejections         # View recent rejections", 'cyan')
        cprint("  python intelligence_manager.py add <address> <reason>  # Add deployer to blacklist", 'cyan')
        cprint("\nExamples:", 'white')
        cprint("  python intelligence_manager.py add [DEPLOYER_ADDRESS] rug_pull", 'yellow')
        return
    
    command = sys.argv[1].lower()
    
    if command == "stats":
        manager.show_statistics()
    elif command == "blacklist":
        manager.view_blacklist()
    elif command == "rejections":
        manager.view_recent_rejections()
    elif command == "add":
        if len(sys.argv) < 3:
            cprint("❌ Error: Deployer address required", 'red')
            cprint("Usage: python intelligence_manager.py add <address> <reason>", 'yellow')
            return
        
        address = sys.argv[2]
        reason = sys.argv[3] if len(sys.argv) > 3 else "manual_add"
        manager.add_deployer_to_blacklist(address, reason)
    else:
        cprint(f"❌ Unknown command: {command}", 'red')
        cprint("Use 'python intelligence_manager.py' for help", 'yellow')

if __name__ == "__main__":
    main()