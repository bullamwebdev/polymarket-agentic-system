#!/usr/bin/env python3
"""
Polymarket CLOB Auth Derivation Script
Usage: python3 derive_polymarket_auth.py

Requires:
  - POLYGON_PRIVATE_KEY env var (or input when prompted)
  - py-clob-client installed

Outputs:
  - Derived API key, secret, passphrase
  - Saves to ~/.config/polymarket/creds.json
"""

import os
import json
import sys

def derive_credentials():
    # Get private key
    private_key = os.environ.get("POLYGON_PRIVATE_KEY")
    if not private_key:
        private_key = input("Enter your Polygon wallet private key (0x...): ").strip()
    
    if not private_key.startswith("0x"):
        print("Error: Private key must start with 0x")
        sys.exit(1)
    
    try:
        from py_clob_client.client import ClobClient
        from py_clob_client.constants import POLYGON
    except ImportError:
        print("Installing py-clob-client...")
        os.system("pip3 install --break-system-packages py-clob-client")
        from py_clob_client.client import ClobClient
        from py_clob_client.constants import POLYGON
    
    # Create client
    client = ClobClient(
        host="https://clob.polymarket.com",
        key=private_key,
        chain_id=POLYGON
    )
    
    print("Deriving API credentials from wallet...")
    
    # Derive credentials
    api_creds = client.create_or_derive_api_creds()
    
    print("\n✅ Credentials derived successfully!")
    print(f"API Key: {api_creds.api_key}")
    print(f"Secret: {api_creds.secret[:10]}...")
    print(f"Passphrase: {api_creds.passphrase[:10]}...")
    
    # Save to file
    creds_dir = os.path.expanduser("~/.config/polymarket")
    os.makedirs(creds_dir, exist_ok=True)
    
    creds_file = os.path.join(creds_dir, "creds.json")
    with open(creds_file, "w") as f:
        json.dump({
            "api_key": api_creds.api_key,
            "secret": api_creds.secret,
            "passphrase": api_creds.passphrase,
            "host": "https://clob.polymarket.com",
            "chain_id": 137  # POLYGON mainnet
        }, f, indent=2)
    
    print(f"\n💾 Saved to: {creds_file}")
    print("\nSet these env vars to use with the trading system:")
    print(f'export POLYMARKET_API_KEY="{api_creds.api_key}"')
    print(f'export POLYMARKET_SECRET="{api_creds.secret}"')
    print(f'export POLYMARKET_PASSPHRASE="{api_creds.passphrase}"')

if __name__ == "__main__":
    derive_credentials()
