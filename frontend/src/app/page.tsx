'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useWebSocket } from '@/hooks/useWebSocket';
import { Proposal, Position, PortfolioSummary, WSMessage } from '@/types';

export default function Dashboard() {
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // WebSocket for real-time updates
  useWebSocket({
    onMessage: (data: WSMessage) => {
      if (data.type === 'proposal_update') {
        fetchData();
      } else if (data.type === 'position_update') {
        fetchData();
      }
    },
  });

  const fetchData = async () => {
    try {
      const [proposalsRes, positionsRes, summaryRes] = await Promise.all([
        fetch('/api/proposals?page_size=5'),
        fetch('/api/positions?is_open=true&page_size=5'),
        fetch('/api/positions/summary'),
      ]);

      if (proposalsRes.ok) {
        const data = await proposalsRes.json();
        setProposals(data.proposals);
      }
      if (positionsRes.ok) {
        const data = await positionsRes.json();
        setPositions(data.positions);
      }
      if (summaryRes.ok) {
        const data = await summaryRes.json();
        setSummary(data);
      }
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const getStatusBadge = (status: string) => {
    const variants: Record<string, 'default' | 'secondary' | 'destructive' | 'success' | 'warning'> = {
      pending: 'warning',
      approved: 'success',
      rejected: 'destructive',
      executed: 'default',
      failed: 'destructive',
      cancelled: 'secondary',
    };
    return <Badge variant={variants[status] || 'secondary'}>{status}</Badge>;
  };

  if (isLoading) {
    return <div className="flex items-center justify-center h-64">Loading...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <Button onClick={() => window.location.href = '/proposals'}>
          New Analysis
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Open Positions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{summary?.total_positions || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Value</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ${summary?.total_value?.toFixed(2) || '0.00'}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Unrealized PnL</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${(summary?.total_unrealized_pnl || 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
              ${summary?.total_unrealized_pnl?.toFixed(2) || '0.00'}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Realized PnL</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${(summary?.total_realized_pnl || 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
              ${summary?.total_realized_pnl?.toFixed(2) || '0.00'}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Proposals */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Proposals</CardTitle>
          <CardDescription>Latest trade proposals from agents</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {proposals.length === 0 ? (
              <p className="text-muted-foreground">No proposals yet</p>
            ) : (
              proposals.map((proposal) => (
                <div key={proposal.id} className="flex items-center justify-between border-b pb-4">
                  <div className="flex items-center space-x-4">
                    <div>
                      <p className="font-medium">{proposal.symbol}</p>
                      <p className="text-sm text-muted-foreground">
                        {proposal.side.toUpperCase()} {proposal.quantity}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    {getStatusBadge(proposal.status)}
                    <span className="text-sm text-muted-foreground">
                      {new Date(proposal.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      {/* Open Positions */}
      <Card>
        <CardHeader>
          <CardTitle>Open Positions</CardTitle>
          <CardDescription>Current open positions</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {positions.length === 0 ? (
              <p className="text-muted-foreground">No open positions</p>
            ) : (
              positions.map((position) => (
                <div key={position.id} className="flex items-center justify-between border-b pb-4">
                  <div className="flex items-center space-x-4">
                    <div>
                      <p className="font-medium">{position.symbol}</p>
                      <p className="text-sm text-muted-foreground">
                        {position.side.toUpperCase()} {position.quantity} @ ${position.entry_price}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className={`font-medium ${position.unrealized_pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                      ${position.unrealized_pnl?.toFixed(2) || '0.00'}
                    </p>
                    <p className="text-sm text-muted-foreground">{position.exchange}</p>
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