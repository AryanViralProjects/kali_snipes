#!/usr/bin/env python3
"""
🚀 KALI SPEED ENGINE - SYSTEM TEST
Quick test to verify all components are ready
"""

import sys
import importlib
from termcolor import cprint

def test_imports():
    """Test all required imports"""
    cprint("🔧 Testing Speed Engine imports...", 'white', 'on_blue')
    
    try:
        # Test WebSocket imports
        import websockets
        import asyncio
        cprint("✅ WebSocket libraries ready", 'green')
        
        # Test Solana imports  
        from solders.keypair import Keypair
        from solders.transaction import VersionedTransaction
        from solana.rpc.api import Client
        from solana.rpc.types import TxOpts, Commitment
        cprint("✅ Solana libraries ready", 'green')
        
        # Test Speed Engine modules
        import raydium_listener
        import main_speed_engine
        import nice_funcs
        cprint("✅ Speed Engine modules ready", 'green')
        
        # Test config
        import config
        cprint("✅ Configuration loaded", 'green')
        
        return True
    except ImportError as e:
        cprint(f"❌ Import error: {e}", 'red')
        return False

def test_rpc_connection():
    """Test RPC connection"""
    cprint("🌐 Testing RPC connection...", 'white', 'on_blue')
    
    try:
        import dontshare as d
        import requests
        
        # Test basic RPC connection
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getHealth"
        }
        
        response = requests.post(d.rpc_url, json=payload, timeout=5)
        
        if response.status_code == 200:
            cprint("✅ RPC connection successful", 'green')
            return True
        else:
            cprint(f"❌ RPC connection failed: HTTP {response.status_code}", 'red')
            return False
            
    except Exception as e:
        cprint(f"❌ RPC test error: {e}", 'red')
        return False

def test_websocket_url():
    """Test WebSocket URL conversion"""
    cprint("🔗 Testing WebSocket URL conversion...", 'white', 'on_blue')
    
    try:
        from raydium_listener import get_helius_wss_url
        
        wss_url = get_helius_wss_url()
        
        if wss_url and wss_url.startswith('wss://'):
            cprint(f"✅ WebSocket URL ready: {wss_url[:50]}...", 'green')
            return True
        else:
            cprint("❌ WebSocket URL conversion failed", 'red')
            return False
            
    except Exception as e:
        cprint(f"❌ WebSocket URL test error: {e}", 'red')
        return False

def test_wallet_connection():
    """Test wallet and balance check"""
    cprint("💰 Testing wallet connection...", 'white', 'on_blue')
    
    try:
        import nice_funcs as n
        from config import MY_SOLANA_ADDERESS
        
        sol_amount, sol_value = n.get_sol_balance(MY_SOLANA_ADDERESS)
        
        if sol_amount is not None:
            cprint(f"✅ Wallet connected: {sol_amount} SOL (${sol_value:.2f})", 'green')
            
            if float(sol_amount) >= 0.005:
                cprint("✅ Sufficient SOL for Speed Engine operation", 'green')
                return True
            else:
                cprint(f"⚠️ Low SOL balance: {sol_amount} SOL (need 0.005+ for fees)", 'yellow')
                return False
        else:
            cprint("❌ Failed to get wallet balance", 'red')
            return False
            
    except Exception as e:
        cprint(f"❌ Wallet test error: {e}", 'red')
        return False

def main():
    """Run all Speed Engine tests"""
    cprint("🚀 KALI SPEED ENGINE - SYSTEM TEST", 'white', 'on_blue', attrs=['bold'])
    cprint("⚡ Verifying Tier 1 sniper readiness...", 'white', 'on_blue', attrs=['bold'])
    
    tests = [
        ("Import Dependencies", test_imports),
        ("RPC Connection", test_rpc_connection), 
        ("WebSocket URL", test_websocket_url),
        ("Wallet Connection", test_wallet_connection)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        cprint(f"\n📋 Running: {test_name}", 'white', 'on_cyan')
        if test_func():
            passed += 1
        
    cprint(f"\n📊 TEST RESULTS: {passed}/{total} PASSED", 'white', 'on_blue', attrs=['bold'])
    
    if passed == total:
        cprint("\n🚀 SPEED ENGINE IS READY!", 'white', 'on_green', attrs=['bold'])
        cprint("⚡ Your bot has been revolutionized to millisecond-level response!", 'white', 'on_green', attrs=['bold'])
        cprint("\n🎯 To start Speed Engine:", 'white', 'on_cyan')
        cprint("   python main_speed_engine.py speed", 'cyan', attrs=['bold'])
        return True
    else:
        cprint(f"\n❌ {total - passed} TESTS FAILED", 'white', 'on_red', attrs=['bold'])
        cprint("🔧 Please fix the issues above before running Speed Engine", 'white', 'on_red')
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)