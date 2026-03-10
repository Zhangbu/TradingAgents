'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface AgentThought {
  id: string;
  agent_name: string;
  thought: string;
  timestamp: Date;
  type: 'thinking' | 'decision' | 'action' | 'error';
}

interface AgentThinkingStreamProps {
  runId: string | null;
  onComplete?: () => void;
}

export default function AgentThinkingStream({ runId, onComplete }: AgentThinkingStreamProps) {
  const [thoughts, setThoughts] = useState<AgentThought[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!runId) return;

    const ws = new WebSocket(`ws://localhost:8000/ws/run/${runId}`);
    
    ws.onopen = () => {
      setConnected(true);
      setIsStreaming(true);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === 'agent_thought') {
          const thought: AgentThought = {
            id: Date.now().toString(),
            agent_name: data.agent_name,
            thought: data.content,
            timestamp: new Date(),
            type: data.thought_type || 'thinking',
          };
          setThoughts(prev => [...prev, thought]);
        } else if (data.type === 'run_complete') {
          setIsStreaming(false);
          onComplete?.();
        }
      } catch (error) {
        console.error('Failed to parse thought:', error);
      }
    };

    ws.onclose = () => {
      setConnected(false);
      setIsStreaming(false);
    };

    return () => {
      ws.close();
    };
  }, [runId, onComplete]);

  const getAgentColor = (agentName: string): string => {
    const colors: Record<string, string> = {
      'market_analyst': 'text-blue-500',
      'fundamentals_analyst': 'text-green-500',
      'news_analyst': 'text-yellow-500',
      'social_media_analyst': 'text-purple-500',
      'bear_researcher': 'text-red-500',
      'bull_researcher': 'text-emerald-500',
      'risk_manager': 'text-orange-500',
      'trader': 'text-cyan-500',
    };
    return colors[agentName] || 'text-gray-500';
  };

  const getTypeBadge = (type: string) => {
    const variants: Record<string, 'default' | 'secondary' | 'destructive' | 'success' | 'warning'> = {
      thinking: 'secondary',
      decision: 'success',
      action: 'default',
      error: 'destructive',
    };
    return <Badge variant={variants[type] || 'secondary'}>{type}</Badge>;
  };

  if (!runId) {
    return null;
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Agent Thinking Stream</CardTitle>
          <div className="flex items-center space-x-2">
            {isStreaming && (
              <div className="flex items-center space-x-2">
                <div className="animate-spin h-4 w-4 border-2 border-primary border-t-transparent rounded-full" />
                <span className="text-sm text-muted-foreground">Thinking...</span>
              </div>
            )}
            <Badge variant={connected ? 'success' : 'secondary'}>
              {connected ? 'Connected' : 'Disconnected'}
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4 max-h-96 overflow-y-auto">
          {thoughts.length === 0 ? (
            <p className="text-muted-foreground text-center py-4">
              {isStreaming ? 'Waiting for agent thoughts...' : 'No thoughts recorded'}
            </p>
          ) : (
            thoughts.map((thought) => (
              <div key={thought.id} className="border-l-2 border-primary/20 pl-4 py-2">
                <div className="flex items-center space-x-2 mb-1">
                  <span className={`font-medium ${getAgentColor(thought.agent_name)}`}>
                    {thought.agent_name}
                  </span>
                  {getTypeBadge(thought.type)}
                  <span className="text-xs text-muted-foreground">
                    {thought.timestamp.toLocaleTimeString()}
                  </span>
                </div>
                <p className="text-sm whitespace-pre-wrap">{thought.thought}</p>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}