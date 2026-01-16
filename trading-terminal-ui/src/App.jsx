import React, { useState, useEffect, useRef } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { TrendingUp, TrendingDown, X, Activity } from 'lucide-react';

const TradingTerminal = () => {
  const [ws, setWs] = useState(null);
  const [connected, setConnected] = useState(false);
  const [symbol, setSymbol] = useState('XAUUSDc');
  const [timeframe, setTimeframe] = useState('M15');
  const [chartData, setChartData] = useState([]);
  const [tick, setTick] = useState(null);
  const [positions, setPositions] = useState([]);
  const [volume, setVolume] = useState(0.01);
  const [sl, setSl] = useState('');
  const [tp, setTp] = useState('');
  
  useEffect(() => {
    const socket = new WebSocket('ws://localhost:8765');
    
    socket.onopen = () => {
      setConnected(true);
      console.log('Connected to MT5 server');
      
      socket.send(JSON.stringify({
        action: 'get_rates',
        symbol: symbol,
        timeframe: timeframe,
        count: 500
      }));
      
      socket.send(JSON.stringify({ action: 'get_positions' }));
    };
    
    socket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      
      if (message.type === 'rates') {
        setChartData(message.data || []);
      } else if (message.type === 'tick_update' || message.type === 'tick') {
        setTick(message.data);
      } else if (message.type === 'positions') {
        setPositions(message.data || []);
      } else if (message.type === 'order_result') {
        if (message.data.success) {
          alert('Order placed successfully!');
          socket.send(JSON.stringify({ action: 'get_positions' }));
        } else {
          alert('Order failed: ' + message.data.error);
        }
      } else if (message.type === 'close_result') {
        if (message.data.success) {
          alert('Position closed!');
          socket.send(JSON.stringify({ action: 'get_positions' }));
        } else {
          alert('Close failed: ' + message.data.error);
        }
      }
    };
    
    socket.onerror = (error) => {
      console.error('WebSocket error:', error);
      setConnected(false);
    };
    
    socket.onclose = () => {
      setConnected(false);
      console.log('Disconnected from MT5 server');
    };
    
    setWs(socket);
    
    return () => {
      socket.close();
    };
  }, []);
  
  const placeOrder = (type) => {
    if (!ws || !connected) return;
    
    ws.send(JSON.stringify({
      action: 'place_order',
      symbol: symbol,
      order_type: type,
      volume: parseFloat(volume),
      sl: sl ? parseFloat(sl) : null,
      tp: tp ? parseFloat(tp) : null
    }));
  };
  
  const closePosition = (ticket) => {
    if (!ws || !connected) return;
    
    ws.send(JSON.stringify({
      action: 'close_position',
      ticket: ticket
    }));
  };
  
  const changeTimeframe = (tf) => {
    setTimeframe(tf);
    if (ws && connected) {
      ws.send(JSON.stringify({
        action: 'get_rates',
        symbol: symbol,
        timeframe: tf,
        count: 500
      }));
    }
  };
  
  const formatPrice = (price) => {
    return price ? price.toFixed(2) : '-';
  };
  
  const totalPnL = positions.reduce((sum, pos) => sum + pos.profit, 0);

  return (
    <div className="w-full h-screen bg-neutral-950 text-neutral-200 flex flex-col">
      {/* Header */}
      <div className="h-12 bg-neutral-900 border-b border-yellow-600/20 flex items-center justify-between px-4">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${connected ? 'bg-yellow-500' : 'bg-neutral-600'}`}></div>
            <span className="text-sm font-medium text-yellow-500">{symbol}</span>
          </div>
          
          {tick && (
            <div className="flex items-center gap-4 text-sm">
              <span className="text-neutral-400">BID: <span className="text-yellow-500 font-mono">{formatPrice(tick.bid)}</span></span>
              <span className="text-neutral-400">ASK: <span className="text-yellow-500 font-mono">{formatPrice(tick.ask)}</span></span>
            </div>
          )}
        </div>
        
        <div className="flex items-center gap-2">
          <span className={`text-sm font-mono ${totalPnL >= 0 ? 'text-green-500' : 'text-red-500'}`}>
            P&L: ${totalPnL.toFixed(2)}
          </span>
        </div>
      </div>
      
      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Chart Area */}
        <div className="flex-1 flex flex-col">
          {/* Timeframe Selector */}
          <div className="h-10 bg-neutral-900 border-b border-yellow-600/20 flex items-center px-4 gap-2">
            {['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1'].map(tf => (
              <button
                key={tf}
                onClick={() => changeTimeframe(tf)}
                className={`px-3 py-1 text-xs font-medium transition-colors ${
                  timeframe === tf 
                    ? 'bg-yellow-600 text-neutral-950' 
                    : 'text-neutral-400 hover:text-yellow-500'
                }`}
              >
                {tf}
              </button>
            ))}
          </div>
          
          {/* Chart */}
          <div className="flex-1 bg-neutral-950 p-4">
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <XAxis 
                    dataKey="time" 
                    tickFormatter={(time) => new Date(time).toLocaleTimeString()}
                    stroke="#525252"
                    style={{ fontSize: 10 }}
                  />
                  <YAxis 
                    domain={['auto', 'auto']}
                    stroke="#525252"
                    style={{ fontSize: 10 }}
                  />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#171717', 
                      border: '1px solid #ca8a04',
                      borderRadius: 0,
                      fontSize: 12
                    }}
                    labelFormatter={(time) => new Date(time).toLocaleString()}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="close" 
                    stroke="#ca8a04" 
                    dot={false}
                    strokeWidth={1}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-neutral-600">
                Loading chart data...
              </div>
            )}
          </div>
        </div>
        
        {/* Right Panel */}
        <div className="w-80 bg-neutral-900 border-l border-yellow-600/20 flex flex-col">
          {/* Trade Panel */}
          <div className="p-4 border-b border-yellow-600/20">
            <div className="text-xs font-medium text-yellow-500 mb-3">NEW ORDER</div>
            
            <div className="space-y-2">
              <div>
                <label className="text-xs text-neutral-400">Volume</label>
                <input
                  type="number"
                  step="0.01"
                  value={volume}
                  onChange={(e) => setVolume(e.target.value)}
                  className="w-full bg-neutral-950 border border-yellow-600/20 px-2 py-1 text-sm text-neutral-200 focus:outline-none focus:border-yellow-600"
                />
              </div>
              
              <div>
                <label className="text-xs text-neutral-400">Stop Loss</label>
                <input
                  type="number"
                  step="0.01"
                  value={sl}
                  onChange={(e) => setSl(e.target.value)}
                  placeholder="Optional"
                  className="w-full bg-neutral-950 border border-yellow-600/20 px-2 py-1 text-sm text-neutral-200 focus:outline-none focus:border-yellow-600 placeholder:text-neutral-700"
                />
              </div>
              
              <div>
                <label className="text-xs text-neutral-400">Take Profit</label>
                <input
                  type="number"
                  step="0.01"
                  value={tp}
                  onChange={(e) => setTp(e.target.value)}
                  placeholder="Optional"
                  className="w-full bg-neutral-950 border border-yellow-600/20 px-2 py-1 text-sm text-neutral-200 focus:outline-none focus:border-yellow-600 placeholder:text-neutral-700"
                />
              </div>
              
              <div className="flex gap-2 pt-2">
                <button
                  onClick={() => placeOrder('BUY')}
                  className="flex-1 bg-green-700 hover:bg-green-600 text-white py-2 text-sm font-medium transition-colors flex items-center justify-center gap-1"
                  disabled={!connected}
                >
                  <TrendingUp size={14} />
                  BUY
                </button>
                <button
                  onClick={() => placeOrder('SELL')}
                  className="flex-1 bg-red-700 hover:bg-red-600 text-white py-2 text-sm font-medium transition-colors flex items-center justify-center gap-1"
                  disabled={!connected}
                >
                  <TrendingDown size={14} />
                  SELL
                </button>
              </div>
            </div>
          </div>
          
          {/* Positions Panel */}
          <div className="flex-1 overflow-auto">
            <div className="p-4">
              <div className="text-xs font-medium text-yellow-500 mb-3">POSITIONS ({positions.length})</div>
              
              {positions.length === 0 ? (
                <div className="text-xs text-neutral-600 text-center py-8">No open positions</div>
              ) : (
                <div className="space-y-2">
                  {positions.map((pos) => (
                    <div key={pos.ticket} className="bg-neutral-950 border border-yellow-600/20 p-3">
                      <div className="flex items-start justify-between mb-2">
                        <div>
                          <div className="text-xs font-medium text-neutral-200">{pos.symbol}</div>
                          <div className={`text-xs ${pos.type === 'BUY' ? 'text-green-500' : 'text-red-500'}`}>
                            {pos.type} {pos.volume}
                          </div>
                        </div>
                        <button
                          onClick={() => closePosition(pos.ticket)}
                          className="text-neutral-400 hover:text-red-500 transition-colors"
                        >
                          <X size={14} />
                        </button>
                      </div>
                      
                      <div className="space-y-1 text-xs">
                        <div className="flex justify-between text-neutral-400">
                          <span>Entry:</span>
                          <span className="font-mono">{formatPrice(pos.price_open)}</span>
                        </div>
                        <div className="flex justify-between text-neutral-400">
                          <span>Current:</span>
                          <span className="font-mono">{formatPrice(pos.price_current)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-neutral-400">P&L:</span>
                          <span className={`font-mono font-medium ${pos.profit >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                            ${pos.profit.toFixed(2)}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TradingTerminal;