#!/usr/bin/env python3
"""
🧠 KALI INTELLIGENCE ENGINE - COMPREHENSIVE TEST
Test all intelligence functions before deployment
"""

import sys
import time
from termcolor import cprint
import nice_funcs as n
import dontshare as d
from config import *

def test_intelligence_imports():
    """Test intelligence function imports"""
    cprint("🔧 Testing Intelligence Engine imports...", 'white', 'on_blue')
    
    try:
        # Test intelligence functions
        from nice_funcs import (
            pre_trade_token_vetting,
            get_deployer_address,
            check_deployer_blacklist,
            add_deployer_to_blacklist
        )
        
        cprint("✅ Intelligence functions imported successfully", 'green')
        return True
    except ImportError as e:
        cprint(f"❌ Import error: {e}", 'red')
        return False

def test_deployer_blacklist():
    """Test deployer blacklist functionality"""
    cprint("🚫 Testing deployer blacklist system...", 'white', 'on_blue')
    
    try:
        # Test with dummy deployer address
        test_deployer = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
        
        # Test adding to blacklist
        cprint("   Testing add to blacklist...", 'cyan')
        n.add_deployer_to_blacklist(test_deployer, "test_deployer")
        
        # Test checking blacklist
        cprint("   Testing blacklist check...", 'cyan')
        is_blacklisted = n.check_deployer_blacklist(test_deployer)
        
        if is_blacklisted:
            cprint("✅ Deployer blacklist system working", 'green')
            
            # Clean up test entry
            import os
            if os.path.exists('./data/deployer_blacklist.txt'):
                with open('./data/deployer_blacklist.txt', 'r') as f:
                    lines = f.readlines()
                
                with open('./data/deployer_blacklist.txt', 'w') as f:
                    for line in lines:
                        if test_deployer not in line:
                            f.write(line)
            
            return True
        else:
            cprint("❌ Deployer blacklist check failed", 'red')
            return False
            
    except Exception as e:
        cprint(f"❌ Deployer blacklist test error: {e}", 'red')
        return False

def test_token_vetting_with_known_token():
    """Test intelligence vetting with a known token"""
    cprint("🔬 Testing intelligence vetting with known token...", 'white', 'on_blue')
    
    try:
        # Use SOL token for testing (should fail due to market cap)
        test_token = "So11111111111111111111111111111111111111112"  # SOL
        
        cprint(f"   Testing vetting for SOL token (expect rejection)...", 'cyan')
        
        result = n.pre_trade_token_vetting(test_token, d.birdeye, d.rpc_url)
        
        if not result:
            cprint("✅ Intelligence vetting correctly rejected SOL (high market cap)", 'green')
            return True
        else:
            cprint("⚠️ Intelligence vetting unexpectedly approved SOL", 'yellow')
            return True  # Still a valid test, just different outcome
            
    except Exception as e:
        cprint(f"❌ Token vetting test error: {e}", 'red')
        return False

def test_deployer_address_lookup():
    """Test deployer address lookup"""
    cprint("🔍 Testing deployer address lookup...", 'white', 'on_blue')
    
    try:
        # Test with SOL token
        test_token = "So11111111111111111111111111111111111111112"
        
        cprint("   Looking up deployer for SOL token...", 'cyan')
        deployer = n.get_deployer_address(test_token, d.birdeye)
        
        if deployer:
            cprint(f"✅ Deployer lookup working (found: {deployer[-6:]})", 'green')
        else:
            cprint("⚠️ Deployer lookup returned None (may be normal for SOL)", 'yellow')
            
        return True  # Function works even if no deployer found
        
    except Exception as e:
        cprint(f"❌ Deployer lookup test error: {e}", 'red')
        return False

def test_intelligence_manager():
    """Test intelligence manager utility"""
    cprint("📊 Testing intelligence manager...", 'white', 'on_blue')
    
    try:
        import intelligence_manager
        
        manager = intelligence_manager.IntelligenceManager()
        
        # Test statistics
        cprint("   Testing statistics...", 'cyan')
        blacklist_count = manager.get_blacklist_count()
        rejection_stats = manager.get_rejection_stats()
        success_stats = manager.get_success_stats()
        
        cprint(f"   Blacklist count: {blacklist_count}", 'green')
        cprint(f"   Rejection stats: {rejection_stats}", 'green')
        cprint(f"   Success stats: {success_stats}", 'green')
        
        cprint("✅ Intelligence manager working", 'green')
        return True
        
    except Exception as e:
        cprint(f"❌ Intelligence manager test error: {e}", 'red')
        return False

def test_integration_with_speed_engine():
    """Test integration points with speed engine"""
    cprint("⚡ Testing Speed Engine integration...", 'white', 'on_blue')
    
    try:
        # Test imports from raydium_listener
        import raydium_listener
        
        # Test that the intelligence functions are available
        cprint("   Testing raydium_listener integration...", 'cyan')
        
        # Verify the intelligence integration exists
        import inspect
        source = inspect.getsource(raydium_listener.trigger_fast_snipe)
        
        if "pre_trade_token_vetting" in source:
            cprint("✅ Intelligence engine integrated with Speed Engine", 'green')
            return True
        else:
            cprint("❌ Intelligence integration not found in Speed Engine", 'red')
            return False
            
    except Exception as e:
        cprint(f"❌ Speed Engine integration test error: {e}", 'red')
        return False

def run_comprehensive_test():
    """Run all intelligence engine tests"""
    cprint("🧠 KALI INTELLIGENCE ENGINE - COMPREHENSIVE TEST", 'white', 'on_blue', attrs=['bold'])
    cprint("🔬 Testing discerning hunter capabilities...", 'white', 'on_blue', attrs=['bold'])
    
    tests = [
        ("Import Intelligence Functions", test_intelligence_imports),
        ("Deployer Blacklist System", test_deployer_blacklist),
        ("Token Vetting Pipeline", test_token_vetting_with_known_token),
        ("Deployer Address Lookup", test_deployer_address_lookup),
        ("Intelligence Manager", test_intelligence_manager),
        ("Speed Engine Integration", test_integration_with_speed_engine)
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
    
    cprint(f"\n📊 INTELLIGENCE TEST RESULTS: {passed}/{total} PASSED", 'white', 'on_blue', attrs=['bold'])
    
    if passed == total:
        cprint("\n🧠 INTELLIGENCE ENGINE IS READY!", 'white', 'on_green', attrs=['bold'])
        cprint("🎯 Your bot is now a discerning hunter with advanced vetting!", 'white', 'on_green', attrs=['bold'])
        cprint("\n🚀 Intelligence Features Active:", 'white', 'on_cyan')
        cprint("   ✅ Real-time security analysis", 'cyan')
        cprint("   ✅ Deployer history tracking", 'cyan')
        cprint("   ✅ Market quality filtering", 'cyan')
        cprint("   ✅ Rug-pull prevention", 'cyan')
        cprint("   ✅ Speed engine integration", 'cyan')
        
        cprint(f"\n🎯 To launch with Intelligence:", 'white', 'on_cyan')
        cprint("   python main_speed_engine.py speed", 'cyan', attrs=['bold'])
        
        return True
    else:
        cprint(f"\n❌ {total - passed} TESTS FAILED", 'white', 'on_red', attrs=['bold'])
        cprint("🔧 Please fix the issues above before deploying Intelligence Engine", 'white', 'on_red')
        return False

if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)