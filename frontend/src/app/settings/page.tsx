'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface KillSwitchStatus {
  is_active: boolean;
  activated_at?: string;
  activated_by?: string;
  reason?: string;
  positions_closed?: number;
}

export default function SettingsPage() {
  const [killSwitch, setKillSwitch] = useState<KillSwitchStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [killSwitchReason, setKillSwitchReason] = useState('');

  useEffect(() => {
    fetchKillSwitchStatus();
  }, []);

  const fetchKillSwitchStatus = async () => {
    try {
      const res = await fetch('/api/kill-switch');
      if (res.ok) {
        const data = await res.json();
        setKillSwitch(data);
      }
    } catch (error) {
      console.error('Failed to fetch kill switch status:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleActivateKillSwitch = async () => {
    try {
      const res = await fetch('/api/kill-switch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reason: killSwitchReason || 'Manual activation',
          close_all_positions: true,
        }),
      });
      if (res.ok) {
        fetchKillSwitchStatus();
        setKillSwitchReason('');
      }
    } catch (error) {
      console.error('Failed to activate kill switch:', error);
    }
  };

  const handleDeactivateKillSwitch = async () => {
    try {
      const res = await fetch('/api/kill-switch', {
        method: 'DELETE',
      });
      if (res.ok) {
        fetchKillSwitchStatus();
      }
    } catch (error) {
      console.error('Failed to deactivate kill switch:', error);
    }
  };

  if (isLoading) {
    return <div className="flex items-center justify-center h-64">Loading...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Settings</h1>
      </div>

      {/* Kill Switch Section */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Kill Switch</CardTitle>
              <CardDescription>
                Emergency control to stop all agent execution and optionally close positions
              </CardDescription>
            </div>
            {killSwitch?.is_active ? (
              <Badge variant="destructive">ACTIVE</Badge>
            ) : (
              <Badge variant="success">INACTIVE</Badge>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {killSwitch?.is_active ? (
            <div className="space-y-4">
              <div className="p-4 bg-destructive/10 rounded-lg">
                <p className="font-medium text-destructive">Kill Switch is ACTIVE</p>
                {killSwitch.activated_at && (
                  <p className="text-sm text-muted-foreground mt-1">
                    Activated: {new Date(killSwitch.activated_at).toLocaleString()}
                  </p>
                )}
                {killSwitch.reason && (
                  <p className="text-sm text-muted-foreground">Reason: {killSwitch.reason}</p>
                )}
                {killSwitch.positions_closed !== undefined && (
                  <p className="text-sm text-muted-foreground">
                    Positions closed: {killSwitch.positions_closed}
                  </p>
                )}
              </div>
              <Button variant="outline" onClick={handleDeactivateKillSwitch}>
                Deactivate Kill Switch
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex space-x-4">
                <input
                  type="text"
                  value={killSwitchReason}
                  onChange={(e) => setKillSwitchReason(e.target.value)}
                  placeholder="Reason (optional)"
                  className="flex h-10 flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm"
                />
                <Button variant="destructive" onClick={handleActivateKillSwitch}>
                  Activate Kill Switch
                </Button>
              </div>
              <p className="text-sm text-muted-foreground">
                Warning: This will stop all agent execution and close all open positions.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* API Configuration */}
      <Card>
        <CardHeader>
          <CardTitle>API Configuration</CardTitle>
          <CardDescription>Configure API keys and endpoints</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium">LLM Provider</label>
              <p className="text-sm text-muted-foreground">Configured in .env file</p>
            </div>
            <div>
              <label className="text-sm font-medium">Backend URL</label>
              <p className="text-sm text-muted-foreground">http://localhost:8000</p>
            </div>
            <div>
              <label className="text-sm font-medium">WebSocket URL</label>
              <p className="text-sm text-muted-foreground">ws://localhost:8000/ws</p>
            </div>
            <div>
              <label className="text-sm font-medium">Default Exchange</label>
              <p className="text-sm text-muted-foreground">paper (simulation)</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* About */}
      <Card>
        <CardHeader>
          <CardTitle>About</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            TradingAgents is a multi-agent LLM financial trading framework that provides
            intelligent market analysis and trade execution capabilities.
          </p>
          <p className="text-sm text-muted-foreground mt-2">
            Version: 0.1.0
          </p>
        </CardContent>
      </Card>
    </div>
  );
}