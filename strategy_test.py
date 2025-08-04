#!/usr/bin/env python3
"""
🎯 KALI STRATEGY ENGINE - COMPREHENSIVE TEST
Test dynamic position sizing and tiered profit management system
"""

import sys
import time
from termcolor import cprint
import nice_funcs as n
import dontshare as d
from config import *

def test_strategy_imports():
    """Test strategy engine function imports"""
    cprint("🔧 Testing Strategy Engine imports...", 'white', 'on_blue')
    
    try:
        # Test strategy functions
        from nice_funcs import (
            calculate_dynamic_position_size,
            load_position_states,
            save_position_states,
            record_new_position,
            remove_position_state,
            execute_tiered_sell,
            advanced_pnl_management,
            get_position_performance_summary
        )
        
        cprint("✅ Strategy Engine functions imported successfully", 'green')
        return True
    except ImportError as e:
        cprint(f"❌ Import error: {e}", 'red')
        return False

def test_dynamic_position_sizing():
    """Test dynamic position sizing calculations"""
    cprint("📏 Testing dynamic position sizing...", 'white', 'on_blue')
    
    try:
        test_cases = [
            {"liquidity": 1000, "expected_min": USDC_MIN_BUY_SIZE, "expected_max": USDC_MAX_BUY_SIZE},
            {"liquidity": 100000, "expected_min": USDC_MIN_BUY_SIZE, "expected_max": USDC_MAX_BUY_SIZE},
            {"liquidity": 500, "expected_min": USDC_MIN_BUY_SIZE, "expected_max": USDC_MAX_BUY_SIZE},
            {"liquidity": 0, "expected_min": USDC_MIN_BUY_SIZE, "expected_max": USDC_MIN_BUY_SIZE}
        ]
        
        for i, case in enumerate(test_cases):
            liquidity = case["liquidity"]
            test_token = f"Test{i}Token123456789012345678901234567890123456789"
            
            size = n.calculate_dynamic_position_size(test_token, liquidity)
            
            if case["expected_min"] <= size <= case["expected_max"]:
                cprint(f"   ✅ Test {i+1}: Liquidity ${liquidity:,} → Size ${size:.2f} (valid)", 'green')
            else:
                cprint(f"   ❌ Test {i+1}: Liquidity ${liquidity:,} → Size ${size:.2f} (invalid)", 'red')
                return False
                
        cprint("✅ Dynamic position sizing working correctly", 'green')
        return True
        
    except Exception as e:
        cprint(f"❌ Dynamic sizing test error: {e}", 'red')
        return False

def test_position_state_management():
    """Test position state tracking system"""
    cprint("📊 Testing position state management...", 'white', 'on_blue')
    
    try:
        test_token = "StrategyTestToken123456789012345678901234567890"
        test_size = 7.5
        test_liquidity = 15000
        
        # Test recording new position
        cprint("   Testing position recording...", 'cyan')
        n.record_new_position(test_token, test_size, test_liquidity)
        
        # Test loading states
        cprint("   Testing state loading...", 'cyan')
        states = n.load_position_states()
        
        if test_token in states:
            state = states[test_token]
            if (state['initial_investment_usdc'] == test_size and 
                state['initial_liquidity'] == test_liquidity and
                state['strategy_type'] == "tiered_dynamic"):
                cprint("   ✅ Position state recorded correctly", 'green')
            else:
                cprint("   ❌ Position state data incorrect", 'red')
                return False
        else:
            cprint("   ❌ Position not found in states", 'red')
            return False
            
        # Test tier update
        cprint("   Testing tier execution recording...", 'cyan')
        n.update_position_tier_sold(test_token, 0, 15.0)
        
        updated_states = n.load_position_states()
        if (test_token in updated_states and 
            0 in updated_states[test_token]['tiers_sold'] and
            updated_states[test_token]['total_sold_usdc'] == 15.0):
            cprint("   ✅ Tier execution recorded correctly", 'green')
        else:
            cprint("   ❌ Tier execution recording failed", 'red')
            return False
            
        # Test position removal
        cprint("   Testing position removal...", 'cyan')
        n.remove_position_state(test_token)
        
        final_states = n.load_position_states()
        if test_token not in final_states:
            cprint("   ✅ Position removed correctly", 'green')
        else:
            cprint("   ❌ Position removal failed", 'red')
            return False
            
        cprint("✅ Position state management working", 'green')
        return True
        
    except Exception as e:
        cprint(f"❌ Position state test error: {e}", 'red')
        return False

def test_strategy_configuration():
    """Test strategy configuration parameters"""
    cprint("⚙️ Testing strategy configuration...", 'white', 'on_blue')
    
    try:
        # Test configuration parameters exist
        required_configs = [
            'USDC_BUY_TARGET_PERCENT_OF_LP',
            'USDC_MAX_BUY_SIZE', 
            'USDC_MIN_BUY_SIZE',
            'SELL_TIERS',
            'OPEN_POSITIONS_STATE_FILE',
            'ENABLE_DYNAMIC_SIZING',
            'ENABLE_TIERED_EXITS'
        ]
        
        for config in required_configs:
            if hasattr(sys.modules['config'], config):
                value = getattr(sys.modules['config'], config)
                cprint(f"   ✅ {config}: {value}", 'green')
            else:
                cprint(f"   ❌ Missing config: {config}", 'red')
                return False
                
        # Test SELL_TIERS structure
        if isinstance(SELL_TIERS, list) and len(SELL_TIERS) > 0:
            for i, tier in enumerate(SELL_TIERS):
                if ('profit_multiple' in tier and 
                    'sell_portion' in tier and 
                    'name' in tier):
                    cprint(f"   ✅ Tier {i+1}: {tier['name']} at {tier['profit_multiple']}x", 'green')
                else:
                    cprint(f"   ❌ Tier {i+1} missing required fields", 'red')
                    return False
        else:
            cprint("   ❌ SELL_TIERS not properly configured", 'red')
            return False
            
        cprint("✅ Strategy configuration valid", 'green')
        return True
        
    except Exception as e:
        cprint(f"❌ Configuration test error: {e}", 'red')
        return False

def test_integration_with_speed_engine():
    """Test strategy integration with speed engine"""
    cprint("⚡ Testing Strategy + Speed Engine integration...", 'white', 'on_blue')
    
    try:
        # Test imports from raydium_listener
        import raydium_listener
        
        # Test that strategy functions are used in speed engine
        cprint("   Testing raydium_listener integration...", 'cyan')
        
        # Verify the strategy integration exists
        import inspect
        source = inspect.getsource(raydium_listener.trigger_fast_snipe)
        
        integration_checks = [
            ("calculate_dynamic_position_size", "Dynamic sizing integration"),
            ("record_new_position", "Position state tracking"),
            ("get_token_overview", "Liquidity data fetching")
        ]
        
        for func_name, description in integration_checks:
            if func_name in source:
                cprint(f"   ✅ {description} integrated", 'green')
            else:
                cprint(f"   ❌ {description} not found", 'red')
                return False
                
        cprint("✅ Strategy Engine integrated with Speed Engine", 'green')
        return True
        
    except Exception as e:
        cprint(f"❌ Speed Engine integration test error: {e}", 'red')
        return False

def test_file_system_setup():
    """Test required files and directories"""
    cprint("📁 Testing file system setup...", 'white', 'on_blue')
    
    try:
        import os
        
        # Test data directory exists
        if not os.path.exists('./data'):
            os.makedirs('./data')
            cprint("   📁 Created ./data directory", 'yellow')
        else:
            cprint("   ✅ ./data directory exists", 'green')
            
        # Test position state file can be created
        test_states = {"test": {"initial_investment_usdc": 5.0}}
        n.save_position_states(test_states)
        
        loaded_states = n.load_position_states()
        if "test" in loaded_states:
            cprint("   ✅ Position state file read/write working", 'green')
            
            # Clean up test data
            del loaded_states["test"]
            n.save_position_states(loaded_states)
        else:
            cprint("   ❌ Position state file system not working", 'red')
            return False
            
        cprint("✅ File system setup complete", 'green')
        return True
        
    except Exception as e:
        cprint(f"❌ File system test error: {e}", 'red')
        return False

def run_comprehensive_strategy_test():
    """Run all strategy engine tests"""
    cprint("🎯 KALI STRATEGY ENGINE - COMPREHENSIVE TEST", 'white', 'on_blue', attrs=['bold'])
    cprint("📈 Testing dynamic sizing and tiered profit management...", 'white', 'on_blue', attrs=['bold'])
    
    tests = [
        ("Strategy Function Imports", test_strategy_imports),
        ("Dynamic Position Sizing", test_dynamic_position_sizing),
        ("Position State Management", test_position_state_management),
        ("Strategy Configuration", test_strategy_configuration),
        ("Speed Engine Integration", test_integration_with_speed_engine),
        ("File System Setup", test_file_system_setup)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        cprint(f"\n📋 Running: {test_name}", 'white', 'on_cyan')
        try:
            if test_func():
                passed += 1
            time.sleep(1)  # Brief pause between tests
        except Exception as e:
            cprint(f"❌ Test crashed: {e}", 'red')
    
    cprint(f"\n📊 STRATEGY TEST RESULTS: {passed}/{total} PASSED", 'white', 'on_blue', attrs=['bold'])
    
    if passed == total:
        cprint("\n🎯 STRATEGY ENGINE IS READY!", 'white', 'on_green', attrs=['bold'])
        cprint("📈 Your bot now has sophisticated dynamic trading strategy!", 'white', 'on_green', attrs=['bold'])
        
        cprint("\n🚀 Strategy Features Active:", 'white', 'on_cyan')
        cprint("   ✅ Dynamic position sizing (liquidity-based)", 'cyan')
        cprint("   ✅ Tiered profit taking (2x, 5x, 11x)", 'cyan')
        cprint("   ✅ Tight stop-losses (-25%)", 'cyan')
        cprint("   ✅ Position state tracking", 'cyan')
        cprint("   ✅ Advanced PNL management", 'cyan')
        cprint("   ✅ Speed engine integration", 'cyan')
        
        cprint(f"\n📊 Current Strategy Settings:", 'white', 'on_cyan')
        cprint(f"   Target LP %: {USDC_BUY_TARGET_PERCENT_OF_LP*100:.1f}%", 'cyan')
        cprint(f"   Size Range: ${USDC_MIN_BUY_SIZE} - ${USDC_MAX_BUY_SIZE}", 'cyan')
        cprint(f"   Stop Loss: {STOP_LOSS_PERCENTAGE*100:+.0f}%", 'cyan')
        cprint(f"   Profit Tiers: {len(SELL_TIERS)} levels", 'cyan')
        
        cprint(f"\n🎯 To launch with Strategy:", 'white', 'on_cyan')
        cprint("   python main_speed_engine.py speed", 'cyan', attrs=['bold'])
        
        return True
    else:
        cprint(f"\n❌ {total - passed} TESTS FAILED", 'white', 'on_red', attrs=['bold'])
        cprint("🔧 Please fix the issues above before deploying Strategy Engine", 'white', 'on_red')
        return False

if __name__ == "__main__":
    success = run_comprehensive_strategy_test()
    sys.exit(0 if success else 1)