import asyncio
from agents.speed_agent import SpeedAgent
from agents.intelligence_agent import IntelligenceAgent
from agents.strategy_agent import StrategyAgent
from common.utils import get_sol_balance, get_usdc_balance
from config import MY_SOLANA_ADDERESS
from termcolor import cprint

class Orchestrator:
    def __init__(self):
        self.agents = {
            "speed": SpeedAgent(),
            "intelligence": IntelligenceAgent(),
            "strategy": StrategyAgent(),
        }

    async def start(self):
        cprint("--- 🎯 KALI MULTI-AGENT SYSTEM STARTING ---", 'white', 'on_blue', attrs=['bold'])
        sol_amount, sol_value = get_sol_balance(MY_SOLANA_ADDERESS)
        usdc_balance = get_usdc_balance(MY_SOLANA_ADDERESS)

        if sol_amount is None:
            cprint("❌ CRITICAL: Cannot get SOL balance. Check your RPC connection!", 'white', 'on_red')
            return

        cprint(f"\n✅ Initial SOL Balance: {sol_amount} SOL (${sol_value:.2f})", 'white', 'on_green')
        cprint(f"✅ Initial USDC Balance: {usdc_balance:.2f} USDC", 'white', 'on_green')

        if float(sol_amount) < 0.005:
            cprint(f"🚨 CRITICAL: SOL balance too low ({sol_amount} SOL). Need at least 0.005 SOL for fees!", 'white', 'on_red')
            return

        tasks = [
            asyncio.create_task(agent.run())
            for name, agent in self.agents.items()
        ]
        await asyncio.gather(*tasks)

    async def stop(self):
        print("\n--- 🎯 KALI MULTI-AGENT SYSTEM SHUTTING DOWN ---")
        for agent in self.agents.values():
            await agent.close()

if __name__ == "__main__":
    orchestrator = Orchestrator()
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(orchestrator.start())
    except KeyboardInterrupt:
        print("Shutdown signal received.")
    finally:
        loop.run_until_complete(orchestrator.stop())
        loop.close()
