import asyncio
import json
import MetaTrader5 as mt5
from datetime import datetime
import websockets
import numpy as np

class MT5Server:
    def __init__(self):
        self.clients = set()
        self.running = False
        
    async def init_mt5(self):
        """Initialize MT5 connection"""
        if not mt5.initialize():
            print(f"MT5 initialization failed: {mt5.last_error()}")
            return False
        print(f"MT5 initialized. Version: {mt5.version()}")
        return True
    
    def get_rates(self, symbol, timeframe, count=500):
        """Fetch historical rates from MT5"""
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
        if rates is None:
            return None
        
        return [{
            'time': int(rate[0]) * 1000,  # Convert to milliseconds
            'open': float(rate[1]),
            'high': float(rate[2]),
            'low': float(rate[3]),
            'close': float(rate[4]),
            'volume': int(rate[5])
        } for rate in rates]
    
    def get_tick(self, symbol):
        """Get latest tick data"""
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return None
        
        return {
            'time': tick.time * 1000,
            'bid': tick.bid,
            'ask': tick.ask,
            'last': tick.last,
            'volume': tick.volume
        }
    
    def get_positions(self):
        """Get open positions"""
        positions = mt5.positions_get()
        if positions is None:
            return []
        
        return [{
            'ticket': pos.ticket,
            'symbol': pos.symbol,
            'type': 'BUY' if pos.type == 0 else 'SELL',
            'volume': pos.volume,
            'price_open': pos.price_open,
            'price_current': pos.price_current,
            'profit': pos.profit,
            'sl': pos.sl,
            'tp': pos.tp
        } for pos in positions]
    
    def place_order(self, symbol, order_type, volume, price=None, sl=None, tp=None):
        """Place market or pending order"""
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return {'success': False, 'error': 'Symbol not found'}
        
        if not symbol_info.visible:
            if not mt5.symbol_select(symbol, True):
                return {'success': False, 'error': 'Failed to select symbol'}
        
        point = symbol_info.point
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": mt5.ORDER_TYPE_BUY if order_type == 'BUY' else mt5.ORDER_TYPE_SELL,
            "deviation": 20,
            "magic": 234000,
            "comment": "Trading Terminal",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        if price:
            request["price"] = price
        
        if sl:
            request["sl"] = sl
        
        if tp:
            request["tp"] = tp
        
        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return {'success': False, 'error': f'Order failed: {result.comment}'}
        
        return {
            'success': True,
            'ticket': result.order,
            'volume': result.volume,
            'price': result.price
        }
    
    def close_position(self, ticket):
        """Close position by ticket"""
        positions = mt5.positions_get(ticket=ticket)
        if not positions:
            return {'success': False, 'error': 'Position not found'}
        
        position = positions[0]
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": mt5.ORDER_TYPE_SELL if position.type == 0 else mt5.ORDER_TYPE_BUY,
            "position": ticket,
            "deviation": 20,
            "magic": 234000,
            "comment": "Close position",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return {'success': False, 'error': f'Close failed: {result.comment}'}
        
        return {'success': True, 'ticket': ticket}
    
    async def handle_client(self, websocket, path):
        """Handle WebSocket client connections"""
        self.clients.add(websocket)
        print(f"Client connected. Total clients: {len(self.clients)}")
        
        try:
            async for message in websocket:
                data = json.loads(message)
                action = data.get('action')
                
                if action == 'get_rates':
                    symbol = data.get('symbol', 'XAUUSDc')
                    timeframe_map = {
                        'M1': mt5.TIMEFRAME_M1,
                        'M5': mt5.TIMEFRAME_M5,
                        'M15': mt5.TIMEFRAME_M15,
                        'M30': mt5.TIMEFRAME_M30,
                        'H1': mt5.TIMEFRAME_H1,
                        'H4': mt5.TIMEFRAME_H4,
                        'D1': mt5.TIMEFRAME_D1
                    }
                    timeframe = timeframe_map.get(data.get('timeframe', 'M15'), mt5.TIMEFRAME_M15)
                    count = data.get('count', 500)
                    
                    rates = self.get_rates(symbol, timeframe, count)
                    await websocket.send(json.dumps({
                        'type': 'rates',
                        'data': rates
                    }))
                
                elif action == 'get_tick':
                    symbol = data.get('symbol', 'XAUUSDc')
                    tick = self.get_tick(symbol)
                    await websocket.send(json.dumps({
                        'type': 'tick',
                        'data': tick
                    }))
                
                elif action == 'get_positions':
                    positions = self.get_positions()
                    await websocket.send(json.dumps({
                        'type': 'positions',
                        'data': positions
                    }))
                
                elif action == 'place_order':
                    result = self.place_order(
                        data.get('symbol'),
                        data.get('order_type'),
                        data.get('volume'),
                        data.get('price'),
                        data.get('sl'),
                        data.get('tp')
                    )
                    await websocket.send(json.dumps({
                        'type': 'order_result',
                        'data': result
                    }))
                
                elif action == 'close_position':
                    result = self.close_position(data.get('ticket'))
                    await websocket.send(json.dumps({
                        'type': 'close_result',
                        'data': result
                    }))
                
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.remove(websocket)
            print(f"Client disconnected. Total clients: {len(self.clients)}")
    
    async def broadcast_ticks(self):
        """Broadcast real-time ticks to all connected clients"""
        symbols = ['XAUUSDc']  # Add more symbols as needed
        
        while self.running:
            for symbol in symbols:
                tick = self.get_tick(symbol)
                if tick and self.clients:
                    message = json.dumps({
                        'type': 'tick_update',
                        'symbol': symbol,
                        'data': tick
                    })
                    await asyncio.gather(
                        *[client.send(message) for client in self.clients],
                        return_exceptions=True
                    )
            await asyncio.sleep(0.1)  # Update every 100ms
    
    async def start(self):
        """Start the WebSocket server"""
        if not await self.init_mt5():
            return
        
        self.running = True
        
        # Start WebSocket server
        server = await websockets.serve(self.handle_client, "localhost", 8765)
        print("WebSocket server started on ws://localhost:8765")
        
        # Start broadcasting ticks
        await self.broadcast_ticks()

if __name__ == "__main__":
    server = MT5Server()
    asyncio.run(server.start())