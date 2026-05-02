#!/usr/bin/env python3
"""
Polymarket CLOB Client Wrapper
Handles order lifecycle: create, cancel, monitor
"""

import os
import json
import time
from typing import Optional, Dict, List
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
from py_clob_client.clob_types import ApiCreds, OrderArgs, OrderType, OrderBookSummary

class PolymarketClient:
    def __init__(self, api_key: str = None, secret: str = None, passphrase: str = None):
        self.host = "https://clob.polymarket.com"
        self.chain_id = POLYGON  # 137
        
        # Try env vars first
        self.api_key = api_key or os.environ.get("POLYMARKET_API_KEY")
        self.secret = secret or os.environ.get("POLYMARKET_SECRET")
        self.passphrase = passphrase or os.environ.get("POLYMARKET_PASSPHRASE")
        
        # Try creds file
        if not all([self.api_key, self.secret, self.passphrase]):
            self._load_creds_file()
        
        self.client = ClobClient(
            host=self.host,
            chain_id=self.chain_id,
            api_key=self.api_key,
            api_secret=self.secret,
            api_passphrase=self.passphrase
        )
    
    def _load_creds_file(self):
        creds_file = os.path.expanduser("~/.config/polymarket/creds.json")
        if os.path.exists(creds_file):
            with open(creds_file) as f:
                creds = json.load(f)
                self.api_key = creds.get("api_key")
                self.secret = creds.get("secret")
                self.passphrase = creds.get("passphrase")
    
    def get_market(self, condition_id: str) -> Dict:
        """Get single market details"""
        return self.client.get_market(condition_id)
    
    def get_midpoint(self, token_id: str) -> float:
        """Get current midpoint price for a token"""
        return self.client.get_midpoint(token_id)
    
    def get_orderbook(self, token_id: str) -> OrderBookSummary:
        """Get full orderbook for a token"""
        return self.client.get_order_book(token_id)
    
    def get_balance(self) -> Dict:
        """Get USDC balance and allowances"""
        return self.client.get_balance_allowances(params={"asset_type": "COLLATERAL"})
    
    def create_order(self, token_id: str, side: str, size: float, price: float, 
                     order_type: str = "GTC") -> Dict:
        """
        Create a limit order
        side: 'BUY' or 'SELL'
        size: number of contracts
        price: limit price (0.01 to 0.99)
        order_type: 'GTC' | 'FOK' | 'IOC'
        """
        order_args = OrderArgs(
            token_id=token_id,
            side=side,
            size=size,
            price=price,
            type=order_type
        )
        
        # Create signed order
        signed_order = self.client.create_order(order_args)
        
        # Submit to CLOB
        response = self.client.post_order(signed_order, order_type)
        return response
    
    def cancel_order(self, order_id: str) -> Dict:
        """Cancel an open order"""
        return self.client.cancel_order(order_id)
    
    def cancel_all_orders(self) -> Dict:
        """Cancel all open orders"""
        return self.client.cancel_all()
    
    def get_open_orders(self) -> List[Dict]:
        """List all open orders"""
        return self.client.get_orders_open()
    
    def get_trades(self) -> List[Dict]:
        """Get trade history"""
        return self.client.get_trades()


if __name__ == "__main__":
    # Test connection
    client = PolymarketClient()
    print("CLOB Client initialized")
    print(f"API Key: {client.api_key[:10]}..." if client.api_key else "No API key found")
