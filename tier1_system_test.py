#!/usr/bin/env python3
"""
🎯 KALI TIER 1 SYSTEM - COMPREHENSIVE TEST SUITE
===============================================
Safe testing of Speed, Intelligence, and Strategy Engines before live deployment.

Features:
- Speed Engine connectivity and functionality tests
- Intelligence Engine security filter tests  
- Strategy Engine calculation tests
- Integration tests between all engines
- Configuration validation
- No real trades or fund usage

Usage:
    python tier1_system_test.py
"""

import os
import sys
import json
import time
import asyncio
from datetime import datetime
from termcolor import cprint
import requests

# Import our modules
try:
    from config import *
    import nice_funcs as n
    import dontshare as d
    print("✅ All imports successful")
except ImportError as e:
    cprint(f"❌ Import error: {e}", 'red')
    sys.exit(1)

class Tier1SystemTest:
    def __init__(self):
        self.test_results = {}
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        
    def log_test(self, test_name, result, message=""):
        """Log test results"""
        self.total_tests += 1
        if result:
            self.passed_tests += 1
            status = "✅ PASS"
            color = 'green'
        else:
            self.failed_tests += 1
            status = "❌ FAIL"
            color = 'red'
            
        self.test_results[test_name] = {"result": result, "message": message}
        cprint(f"{status} | {test_name}: {message}", color)
        
    def test_configuration(self):
        """Test configuration validity"""
        cprint("\n🔧 TESTING CONFIGURATION", 'white', 'on_blue', attrs=['bold'])
        cprint("=" * 60, 'blue')
        
        # Test critical configuration values
        self.log_test("Config: MY_SOLANA_ADDRESS", 
                     len(MY_SOLANA_ADDERESS) >= 32, 
                     f"Address: {MY_SOLANA_ADDERESS[-6:]}...")
                     
        self.log_test("Config: USDC_SIZE", 
                     USDC_SIZE > 0, 
                     f"Size: ${USDC_SIZE}")
                     
        self.log_test("Config: Dynamic Sizing", 
                     ENABLE_DYNAMIC_SIZING in [True, False], 
                     f"Enabled: {ENABLE_DYNAMIC_SIZING}")
                     
        self.log_test("Config: Tiered Exits", 
                     ENABLE_TIERED_EXITS in [True, False], 
                     f"Enabled: {ENABLE_TIERED_EXITS}")
                     
        self.log_test("Config: Stop Loss", 
                     -1.0 <= STOP_LOSS_PERCENTAGE <= 0.0, 
                     f"Stop Loss: {STOP_LOSS_PERCENTAGE * 100:.1f}%")
                     
        # Test sell tiers configuration
        tiers_valid = len(SELL_TIERS) > 0 and all('profit_multiple' in tier for tier in SELL_TIERS)
        self.log_test("Config: Sell Tiers", 
                     tiers_valid, 
                     f"{len(SELL_TIERS)} tiers configured")
                     
    def test_api_connectivity(self):
        """Test API connections"""
        cprint("\n🌐 TESTING API CONNECTIVITY", 'white', 'on_cyan', attrs=['bold'])
        cprint("=" * 60, 'cyan')
        
        # Test Helius RPC
        try:
            headers = {'Content-Type': 'application/json'}
            payload = {
                'jsonrpc': '2.0',
                'id': 1,
                'method': 'getHealth'
            }
            response = requests.post(d.rpc_url, headers=headers, json=payload, timeout=10)
            rpc_working = response.status_code == 200
            self.log_test("API: Helius RPC", rpc_working, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("API: Helius RPC", False, f"Error: {str(e)[:50]}")
            
        # Test Birdeye API
        try:
            test_url = f"https://public-api.birdeye.so/defi/token_overview?address={USDC_CA}"
            headers = {'X-API-KEY': d.birdeye}
            response = requests.get(test_url, headers=headers, timeout=10)
            birdeye_working = response.status_code == 200
            self.log_test("API: Birdeye", birdeye_working, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("API: Birdeye", False, f"Error: {str(e)[:50]}")
            
        # Test Jupiter API
        try:
            test_url = "https://quote-api.jup.ag/v6/quote"
            params = {
                'inputMint': USDC_CA,
                'outputMint': 'So11111111111111111111111111111111111111112',
                'amount': 1000000,  # 1 USDC
                'slippageBps': 50
            }
            response = requests.get(test_url, params=params, timeout=10)
            jupiter_working = response.status_code == 200
            self.log_test("API: Jupiter", jupiter_working, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("API: Jupiter", False, f"Error: {str(e)[:50]}")
            
    def test_wallet_connectivity(self):
        """Test wallet and SOL balance"""
        cprint("\n💰 TESTING WALLET CONNECTIVITY", 'white', 'on_green', attrs=['bold'])
        cprint("=" * 60, 'green')
        
        try:
            sol_balance_result = n.get_sol_balance(MY_SOLANA_ADDERESS)
            
            # get_sol_balance returns (sol_amount, usd_value)
            if sol_balance_result and len(sol_balance_result) == 2:
                sol_amount, usd_value = sol_balance_result
                wallet_accessible = sol_amount is not None and sol_amount >= 0
                self.log_test("Wallet: SOL Balance", 
                             wallet_accessible, 
                             f"Balance: {sol_amount:.6f} SOL" if wallet_accessible else "Not accessible")
                             
                # Test if wallet has minimum SOL for transactions
                min_sol_needed = 0.01  # Minimum for transaction fees
                has_enough_sol = sol_amount >= min_sol_needed if sol_amount else False
                self.log_test("Wallet: Minimum SOL", 
                             has_enough_sol, 
                             f"Need {min_sol_needed} SOL, have {sol_amount:.6f}")
            else:
                self.log_test("Wallet: SOL Balance", False, "Invalid response format")
                self.log_test("Wallet: Minimum SOL", False, "Could not check SOL amount")
                         
        except Exception as e:
            self.log_test("Wallet: SOL Balance", False, f"Error: {str(e)[:50]}")
            
    def test_intelligence_engine(self):
        """Test Intelligence Engine functions"""
        cprint("\n🧠 TESTING INTELLIGENCE ENGINE", 'white', 'on_magenta', attrs=['bold'])
        cprint("=" * 60, 'magenta')
        
        # Test security check function exists
        security_func_exists = hasattr(n, 'pre_trade_token_vetting')
        self.log_test("Intelligence: Security Function", 
                     security_func_exists, 
                     "pre_trade_token_vetting function found")
                     
        # Test deployer blacklist functions
        blacklist_func_exists = hasattr(n, 'check_deployer_blacklist')
        self.log_test("Intelligence: Blacklist Function", 
                     blacklist_func_exists, 
                     "check_deployer_blacklist function found")
                     
        # Test blacklist file creation
        blacklist_file = './data/deployer_blacklist.txt'
        try:
            os.makedirs('./data', exist_ok=True)
            if not os.path.exists(blacklist_file):
                with open(blacklist_file, 'w') as f:
                    f.write("# Kali Intelligence Engine - Deployer Blacklist\n")
            blacklist_ready = os.path.exists(blacklist_file)
            self.log_test("Intelligence: Blacklist File", 
                         blacklist_ready, 
                         f"File exists: {blacklist_file}")
        except Exception as e:
            self.log_test("Intelligence: Blacklist File", False, f"Error: {str(e)[:50]}")
            
        # Test security check with a test token (SOL as safe reference)
        try:
            if security_func_exists:
                # Test with SOL (wrapped SOL) which should be safe
                test_token = "So11111111111111111111111111111111111111112"  # Wrapped SOL
                token_safe = n.pre_trade_token_vetting(test_token, d.birdeye, d.rpc_url)
                self.log_test("Intelligence: Token Security Test", 
                             token_safe, 
                             f"Security check completed for test token")
            else:
                self.log_test("Intelligence: Token Security Test", False, "Function not available")
        except Exception as e:
            self.log_test("Intelligence: Token Security Test", False, f"Error: {str(e)[:50]}")
            
    def test_strategy_engine(self):
        """Test Strategy Engine functions"""
        cprint("\n🎯 TESTING STRATEGY ENGINE", 'white', 'on_yellow', attrs=['bold'])
        cprint("=" * 60, 'yellow')
        
        # Test dynamic position sizing function
        sizing_func_exists = hasattr(n, 'calculate_dynamic_position_size')
        self.log_test("Strategy: Dynamic Sizing Function", 
                     sizing_func_exists, 
                     "calculate_dynamic_position_size function found")
                     
        # Test position state functions
        position_func_exists = hasattr(n, 'load_position_states')
        self.log_test("Strategy: Position State Function", 
                     position_func_exists, 
                     "load_position_states function found")
                     
        # Test advanced PNL function
        pnl_func_exists = hasattr(n, 'advanced_pnl_management')
        self.log_test("Strategy: Advanced PNL Function", 
                     pnl_func_exists, 
                     "advanced_pnl_management function found")
                     
        # Test position state file creation
        position_file = OPEN_POSITIONS_STATE_FILE
        try:
            os.makedirs(os.path.dirname(position_file), exist_ok=True)
            if not os.path.exists(position_file):
                with open(position_file, 'w') as f:
                    json.dump({}, f, indent=2)
            position_file_ready = os.path.exists(position_file)
            self.log_test("Strategy: Position State File", 
                         position_file_ready, 
                         f"File exists: {position_file}")
        except Exception as e:
            self.log_test("Strategy: Position State File", False, f"Error: {str(e)[:50]}")
            
        # Test dynamic sizing calculation
        if sizing_func_exists:
            try:
                test_liquidity = 50000  # $50k liquidity
                calculated_size = n.calculate_dynamic_position_size("test_token", test_liquidity)
                size_reasonable = USDC_MIN_BUY_SIZE <= calculated_size <= USDC_MAX_BUY_SIZE
                self.log_test("Strategy: Dynamic Sizing Calc", 
                             size_reasonable, 
                             f"${calculated_size:.2f} for ${test_liquidity:,} liquidity")
            except Exception as e:
                self.log_test("Strategy: Dynamic Sizing Calc", False, f"Error: {str(e)[:50]}")
        else:
            self.log_test("Strategy: Dynamic Sizing Calc", False, "Function not available")
            
    def test_speed_engine(self):
        """Test Speed Engine functions"""
        cprint("\n⚡ TESTING SPEED ENGINE", 'white', 'on_red', attrs=['bold'])
        cprint("=" * 60, 'red')
        
        # Test market buy function exists
        speed_func_exists = hasattr(n, 'market_buy_fast')
        self.log_test("Speed: Fast Buy Function", 
                     speed_func_exists, 
                     "market_buy_fast function found")
                     
        # Test WebSocket URL conversion
        try:
            ws_url = d.rpc_url.replace('https://', 'wss://').replace('http://', 'ws://')
            url_valid = ws_url.startswith('wss://') or ws_url.startswith('ws://')
            self.log_test("Speed: WebSocket URL", 
                         url_valid, 
                         f"WS URL: {ws_url[:30]}...")
        except Exception as e:
            self.log_test("Speed: WebSocket URL", False, f"Error: {str(e)[:50]}")
            
        # Test Raydium listener exists
        try:
            import raydium_listener
            listener_exists = hasattr(raydium_listener, 'trigger_fast_snipe')
            self.log_test("Speed: Raydium Listener", 
                         listener_exists, 
                         "raydium_listener module loaded")
        except ImportError:
            self.log_test("Speed: Raydium Listener", False, "raydium_listener not found")
        except Exception as e:
            self.log_test("Speed: Raydium Listener", False, f"Error: {str(e)[:50]}")
            
    def test_file_system(self):
        """Test required files and directories"""
        cprint("\n📁 TESTING FILE SYSTEM", 'white', 'on_blue', attrs=['bold'])
        cprint("=" * 60, 'blue')
        
        # Test data directory
        data_dir = './data'
        data_exists = os.path.exists(data_dir)
        if not data_exists:
            os.makedirs(data_dir, exist_ok=True)
            data_exists = os.path.exists(data_dir)
        self.log_test("FileSystem: Data Directory", 
                     data_exists, 
                     f"Directory: {data_dir}")
                     
        # Test required files
        required_files = {
            'config.py': 'Configuration file',
            'nice_funcs.py': 'Core functions',
            'main_speed_engine.py': 'Tier 1 launcher',
            'raydium_listener.py': 'Speed Engine',
            'dontshare.py': 'API credentials'
        }
        
        for filename, description in required_files.items():
            file_exists = os.path.exists(filename)
            self.log_test(f"FileSystem: {filename}", 
                         file_exists, 
                         description)
                         
    def test_integration(self):
        """Test integration between engines"""
        cprint("\n🔗 TESTING ENGINE INTEGRATION", 'white', 'on_cyan', attrs=['bold'])
        cprint("=" * 60, 'cyan')
        
        # Test if all engines can work together
        try:
            # Test Intelligence -> Strategy flow
            if hasattr(n, 'pre_trade_token_vetting') and hasattr(n, 'calculate_dynamic_position_size'):
                # Simulate a token passing intelligence checks
                test_liquidity = 25000
                dynamic_size = n.calculate_dynamic_position_size("test_integration", test_liquidity)
                integration_working = dynamic_size > 0
                self.log_test("Integration: Intelligence -> Strategy", 
                             integration_working, 
                             f"Dynamic size: ${dynamic_size:.2f}")
            else:
                self.log_test("Integration: Intelligence -> Strategy", False, "Functions missing")
                
            # Test Strategy -> Speed flow (position recording)
            if hasattr(n, 'record_new_position'):
                # This won't actually record, just test function exists
                record_func_exists = callable(getattr(n, 'record_new_position'))
                self.log_test("Integration: Strategy -> Speed", 
                             record_func_exists, 
                             "Position recording function ready")
            else:
                self.log_test("Integration: Strategy -> Speed", False, "record_new_position missing")
                
        except Exception as e:
            self.log_test("Integration: Engine Flow", False, f"Error: {str(e)[:50]}")
            
    def run_all_tests(self):
        """Run comprehensive test suite"""
        cprint("\n🎯 KALI TIER 1 SYSTEM - COMPREHENSIVE TEST SUITE", 'white', 'on_blue', attrs=['bold'])
        cprint("🔍 Testing all components before live deployment...", 'cyan')
        cprint("⚠️  This is SAFE TESTING - no real trades will be made", 'yellow')
        print("=" * 80)
        
        # Run all test categories
        self.test_configuration()
        self.test_file_system()
        self.test_api_connectivity()
        self.test_wallet_connectivity()
        self.test_intelligence_engine()
        self.test_strategy_engine()
        self.test_speed_engine()
        self.test_integration()
        
        # Show final results
        self.show_test_summary()
        
    def show_test_summary(self):
        """Show comprehensive test results"""
        cprint("\n" + "=" * 80, 'white')
        cprint("🎯 TIER 1 SYSTEM TEST RESULTS", 'white', 'on_blue', attrs=['bold'])
        cprint("=" * 80, 'white')
        
        # Overall stats
        pass_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
        cprint(f"\n📊 OVERALL RESULTS:", 'white', attrs=['bold'])
        cprint(f"   ✅ Passed: {self.passed_tests}/{self.total_tests} tests", 'green')
        cprint(f"   ❌ Failed: {self.failed_tests}/{self.total_tests} tests", 'red' if self.failed_tests > 0 else 'green')
        cprint(f"   📈 Success Rate: {pass_rate:.1f}%", 'green' if pass_rate >= 90 else 'yellow' if pass_rate >= 70 else 'red')
        
        # Deployment recommendation
        print()
        if pass_rate >= 95:
            cprint("🚀 DEPLOYMENT STATUS: READY FOR LIVE TRADING", 'white', 'on_green', attrs=['bold'])
            cprint("   All critical systems operational. Safe to launch Tier 1 system.", 'green')
        elif pass_rate >= 85:
            cprint("⚠️  DEPLOYMENT STATUS: MINOR ISSUES DETECTED", 'white', 'on_yellow', attrs=['bold'])
            cprint("   Most systems working. Review failed tests before launching.", 'yellow')
        else:
            cprint("🛑 DEPLOYMENT STATUS: CRITICAL ISSUES FOUND", 'white', 'on_red', attrs=['bold'])
            cprint("   Major problems detected. DO NOT LAUNCH until fixed.", 'red')
            
        # Show failed tests
        if self.failed_tests > 0:
            cprint(f"\n❌ FAILED TESTS REQUIRING ATTENTION:", 'red', attrs=['bold'])
            for test_name, result in self.test_results.items():
                if not result['result']:
                    cprint(f"   • {test_name}: {result['message']}", 'red')
                    
        # Next steps
        cprint(f"\n🎯 NEXT STEPS:", 'cyan', attrs=['bold'])
        if pass_rate >= 95:
            cprint("   1. Launch with: python main_speed_engine.py speed", 'green')
            cprint("   2. Monitor Intelligence rejections and Speed snipes", 'green')
            cprint("   3. Check Strategy position management", 'green')
        else:
            cprint("   1. Fix all failed tests above", 'yellow')
            cprint("   2. Re-run: python tier1_system_test.py", 'yellow')
            cprint("   3. Only launch when success rate ≥ 95%", 'yellow')
            
        print("=" * 80)

def main():
    """Main test execution"""
    try:
        tester = Tier1SystemTest()
        tester.run_all_tests()
    except KeyboardInterrupt:
        cprint("\n\n⚠️  Testing interrupted by user", 'yellow')
    except Exception as e:
        cprint(f"\n\n❌ Testing error: {e}", 'red')

if __name__ == "__main__":
    main()