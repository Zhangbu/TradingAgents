'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useWebSocket } from '@/hooks/useWebSocket';
import { Proposal, WSMessage, AgentRunRequest } from '@/types';

export default function ProposalsPage() {
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [symbol, setSymbol] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [selectedProposal, setSelectedProposal] = useState<Proposal | null>(null);

  useWebSocket({
    onMessage: (data: WSMessage) => {
      if (data.type === 'proposal_update') {
        fetchProposals();
      } else if (data.type === 'run_status') {
        const runData = data as { status: string };
        if (runData.status === 'completed' || runData.status === 'failed') {
          setIsRunning(false);
        }
      }
    },
  });

  const fetchProposals = async () => {
    try {
      const res = await fetch('/api/proposals');
      if (res.ok) {
        const data = await res.json();
        setProposals(data.proposals);
      }
    } catch (error) {
      console.error('Failed to fetch proposals:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchProposals();
  }, []);

  const handleRunAgent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!symbol) return;

    setIsRunning(true);
    try {
      const request: AgentRunRequest = {
        symbol: symbol.toUpperCase(),
        exchange: 'paper',
        auto_approve: false,
      };
      const res = await fetch('/api/agent/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      });
      if (res.ok) {
        setSymbol('');
        setShowForm(false);
      }
    } catch (error) {
      console.error('Failed to run agent:', error);
    }
  };

  const handleApprove = async (proposalId: number) => {
    try {
      await fetch(`/api/proposals/${proposalId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approved: true }),
      });
      fetchProposals();
      setSelectedProposal(null);
    } catch (error) {
      console.error('Failed to approve:', error);
    }
  };

  const handleReject = async (proposalId: number, reason?: string) => {
    try {
      await fetch(`/api/proposals/${proposalId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approved: false, rejection_reason: reason }),
      });
      fetchProposals();
      setSelectedProposal(null);
    } catch (error) {
      console.error('Failed to reject:', error);
    }
  };

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
        <h1 className="text-3xl font-bold">Proposals</h1>
        <Button onClick={() => setShowForm(!showForm)} disabled={isRunning}>
          {isRunning ? 'Running...' : 'New Analysis'}
        </Button>
      </div>

      {showForm && (
        <Card>
          <CardHeader>
            <CardTitle>Run Agent Analysis</CardTitle>
            <CardDescription>Enter a stock symbol to analyze</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleRunAgent} className="flex space-x-4">
              <input
                type="text"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                placeholder="Symbol (e.g., AAPL)"
                className="flex h-10 w-48 rounded-md border border-input bg-background px-3 py-2 text-sm"
              />
              <Button type="submit" disabled={!symbol || isRunning}>
                Run Analysis
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      {selectedProposal && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Proposal #{selectedProposal.id}</CardTitle>
              <Button variant="ghost" onClick={() => setSelectedProposal(null)}>Close</Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div><strong>Symbol:</strong> {selectedProposal.symbol}</div>
              <div><strong>Side:</strong> {selectedProposal.side.toUpperCase()}</div>
              <div><strong>Quantity:</strong> {selectedProposal.quantity}</div>
              <div><strong>Exchange:</strong> {selectedProposal.exchange}</div>
            </div>
            {selectedProposal.reasoning && (
              <div>
                <strong>Reasoning:</strong>
                <p className="mt-1 text-muted-foreground">{selectedProposal.reasoning}</p>
              </div>
            )}
            {selectedProposal.status === 'pending' && (
              <div className="flex space-x-2 pt-4">
                <Button onClick={() => handleApprove(selectedProposal.id)}>Approve</Button>
                <Button variant="destructive" onClick={() => handleReject(selectedProposal.id)}>Reject</Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>All Proposals</CardTitle>
          <CardDescription>Trade proposals from agent analysis</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {proposals.length === 0 ? (
              <p className="text-muted-foreground">No proposals yet. Run an analysis to create one.</p>
            ) : (
              proposals.map((proposal) => (
                <div
                  key={proposal.id}
                  className="flex items-center justify-between border-b pb-4 cursor-pointer hover:bg-muted/50 p-2 rounded"
                  onClick={() => setSelectedProposal(proposal)}
                >
                  <div>
                    <p className="font-medium">{proposal.symbol}</p>
                    <p className="text-sm text-muted-foreground">
                      {proposal.side.toUpperCase()} {proposal.quantity} shares
                    </p>
                  </div>
                  <div className="flex items-center space-x-4">
                    {getStatusBadge(proposal.status)}
                    <span className="text-sm text-muted-foreground">
                      {new Date(proposal.created_at).toLocaleString()}
                    </span>
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