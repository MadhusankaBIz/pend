# test_balance.py  (place this in the project root beside docker-compose.yml)

import asyncio
import sys
import os

# Make sure /app/shared resolves correctly inside the container
sys.path.insert(0, "/app/shared")

from deriv_api import DerivAPI  # this will import shared/deriv_api.py

async def main():
    print("[TEST] Initialising DerivAPI...")
    api = DerivAPI(use_auth=True)
    print("[TEST] Calling get_balance()...")
    bal = await api.get_balance()
    print(f"[TEST] BALANCE: {bal:.2f} USD")

if __name__ == "__main__":
    asyncio.run(main())
