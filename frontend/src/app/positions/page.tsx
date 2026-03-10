'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useWebSocket } from '@/hooks/useWebSocket';
import { Position, PortfolioSummary, WSMessage } from '@/types';

export default function PositionsPage() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'open' | 'closed'>('open');

  useWebSocket({
    onMessage: (data: WSMessage) => {
      if (data.type === 'position_update') {
        fetchPositions();
      }
    },
  });

  const fetchPositions = async () => {
    try {
      const isOpen = filter === 'open' ? true : filter === 'closed' ? false : undefined;
      const url = isOpen !== undefined 
        ? `/api/positions?is_open=${isOpen}` 
        : '/api/positions';
      
      const [positionsRes, summaryRes] = await Promise.all([
        fetch(url),
        fetch('/api/positions/summary'),
      ]);

      if (positionsRes.ok) {
        const data = await positionsRes.json();
        setPositions(data.positions);
      }
      if (summaryRes.ok) {
        const data = await summaryRes.json();
        setSummary(data);
      }
    } catch (error) {
      console.error('Failed to fetch positions:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchPositions();
  }, [filter]);

  const handleClosePosition = async (positionId: number) => {
    try {
      await fetch(`/api/positions/${positionId}/close`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: 'manual_close' }),
      });
      fetchPositions();
    } catch (error) {
      console.error('Failed to close position:', error);
    }
  };

  if (isLoading) {
    return <div className="flex items-center justify-center h-64">Loading...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Positions</h1>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Open Positions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{summary?.total_positions || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total Value</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${summary?.total_value?.toFixed(2) || '0.00'}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Unrealized PnL</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${(summary?.total_unrealized_pnl || 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
              ${summary?.total_unrealized_pnl?.toFixed(2) || '0.00'}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filter Tabs */}
      <div className="flex space-x-2">
        <Button 
          variant={filter === 'open' ? 'default' : 'outline'} 
          onClick={() => setFilter('open')}
        >
          Open
        </Button>
        <Button 
          variant={filter === 'closed' ? 'default' : 'outline'} 
          onClick={() => setFilter('closed')}
        >
          Closed
        </Button>
        <Button 
          variant={filter === 'all' ? 'default' : 'outline'} 
          onClick={() => setFilter('all')}
        >
          All
        </Button>
      </div>

      {/* Positions List */}
      <Card>
        <CardHeader>
          <CardTitle>Positions</CardTitle>
          <CardDescription>Manage your trading positions</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {positions.length === 0 ? (
              <p className="text-muted-foreground">No positions found.</p>
            ) : (
              positions.map((position) => (
                <div key={position.id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      <div>
                        <p className="font-medium text-lg">{position.symbol}</p>
                        <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                          <Badge variant={position.side === 'long' ? 'success' : 'destructive'}>
                            {position.side.toUpperCase()}
                          </Badge>
                          <span>{position.quantity} shares</span>
                          <span>@ ${position.entry_price}</span>
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className={`font-medium text-lg ${position.unrealized_pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                        ${position.unrealized_pnl?.toFixed(2) || '0.00'}
                      </p>
                      <p className="text-sm text-muted-foreground">{position.exchange}</p>
                    </div>
                  </div>
                  <div className="mt-4 flex items-center justify-between text-sm">
                    <div className="text-muted-foreground">
                      Opened: {new Date(position.opened_at).toLocaleString()}
                      {position.closed_at && (
                        <span className="ml-4">Closed: {new Date(position.closed_at).toLocaleString()}</span>
                      )}
                    </div>
                    {position.is_open && (
                      <Button 
                        variant="destructive" 
                        size="sm"
                        onClick={() => handleClosePosition(position.id)}
                      >
                        Close Position
                      </Button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}