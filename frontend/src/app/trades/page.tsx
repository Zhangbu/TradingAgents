'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { TradeHistory } from '@/types';

export default function TradesPage() {
  const [trades, setTrades] = useState<TradeHistory[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [totalPnL, setTotalPnL] = useState(0);

  const fetchTrades = async () => {
    try {
      const res = await fetch('/api/trades');
      if (res.ok) {
        const data = await res.json();
        setTrades(data.trades);
        setTotalPnL(data.trades.reduce((sum: number, t: TradeHistory) => sum + (t.realized_pnl || 0), 0));
      }
    } catch (error) {
      console.error('Failed to fetch trades:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTrades();
  }, []);

  if (isLoading) {
    return <div className="flex items-center justify-center h-64">Loading...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Trade History</h1>
      </div>

      {/* Summary Card */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Total Realized PnL</CardTitle>
        </CardHeader>
        <CardContent>
          <div className={`text-2xl font-bold ${totalPnL >= 0 ? 'text-green-500' : 'text-red-500'}`}>
            ${totalPnL.toFixed(2)}
          </div>
        </CardContent>
      </Card>

      {/* Trades Table */}
      <Card>
        <CardHeader>
          <CardTitle>Trade History</CardTitle>
          <CardDescription>Completed trades and their results</CardDescription>
        </CardHeader>
        <CardContent>
          {trades.length === 0 ? (
            <p className="text-muted-foreground">No trades yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-3 px-2">Symbol</th>
                    <th className="text-left py-3 px-2">Side</th>
                    <th className="text-right py-3 px-2">Quantity</th>
                    <th className="text-right py-3 px-2">Price</th>
                    <th className="text-right py-3 px-2">Total</th>
                    <th className="text-right py-3 px-2">PnL</th>
                    <th className="text-left py-3 px-2">Exchange</th>
                    <th className="text-left py-3 px-2">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {trades.map((trade) => (
                    <tr key={trade.id} className="border-b hover:bg-muted/50">
                      <td className="py-3 px-2 font-medium">{trade.symbol}</td>
                      <td className="py-3 px-2">
                        <Badge variant={trade.side === 'buy' ? 'success' : 'destructive'}>
                          {trade.side.toUpperCase()}
                        </Badge>
                      </td>
                      <td className="py-3 px-2 text-right">{trade.quantity}</td>
                      <td className="py-3 px-2 text-right">${trade.price.toFixed(2)}</td>
                      <td className="py-3 px-2 text-right">${trade.total_value.toFixed(2)}</td>
                      <td className={`py-3 px-2 text-right font-medium ${trade.realized_pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                        ${trade.realized_pnl?.toFixed(2) || '0.00'}
                      </td>
                      <td className="py-3 px-2">{trade.exchange}</td>
                      <td className="py-3 px-2 text-sm text-muted-foreground">
                        {new Date(trade.executed_at).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}