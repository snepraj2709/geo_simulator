import { useEffect, useState, useCallback } from 'react';
import { PipelineState } from '@/types/pipeline';
import { websocketService } from '@/services/websocket';

interface UsePipelineOptions {
  pipelineId: string;
  onComplete?: () => void;
  onError?: (error: string) => void;
}

interface UsePipelineReturn {
  pipelineState: PipelineState | null;
  error: string | null;
  isConnected: boolean;
  isComplete: boolean;
  hasError: boolean;
}

/**
 * Custom hook for managing pipeline state with WebSocket updates
 * 
 * @example
 * ```tsx
 * const { pipelineState, isComplete, hasError } = usePipeline({
 *   pipelineId: 'pipeline-123',
 *   onComplete: () => console.log('Pipeline completed!'),
 *   onError: (error) => console.error('Pipeline error:', error),
 * });
 * ```
 */
export function usePipeline({
  pipelineId,
  onComplete,
  onError,
}: UsePipelineOptions): UsePipelineReturn {
  const [pipelineState, setPipelineState] = useState<PipelineState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  // Memoize callbacks to prevent unnecessary re-subscriptions
  const handleComplete = useCallback(() => {
    if (onComplete) {
      onComplete();
    }
  }, [onComplete]);

  const handleError = useCallback((errorMsg: string) => {
    setError(errorMsg);
    if (onError) {
      onError(errorMsg);
    }
  }, [onError]);

  useEffect(() => {
    // Check connection status
    setIsConnected(websocketService.isConnected());

    // Subscribe to pipeline updates
    const unsubscribe = websocketService.subscribe(pipelineId, (state) => {
      setPipelineState(state);

      // Check if pipeline is complete
      const allCompleted = state.stages.every((stage) => stage.status === 'completed');
      if (allCompleted) {
        handleComplete();
      }

      // Check for errors
      const hasError = state.stages.some((stage) => stage.status === 'error');
      if (hasError) {
        const errorStage = state.stages.find((stage) => stage.status === 'error');
        if (errorStage?.error) {
          handleError(errorStage.error);
        }
      }
    });

    // Subscribe to errors
    const unsubscribeError = websocketService.onError(handleError);

    return () => {
      unsubscribe();
      unsubscribeError();
    };
  }, [pipelineId, handleComplete, handleError]);

  const isComplete = pipelineState
    ? pipelineState.stages.every((stage) => stage.status === 'completed')
    : false;

  const hasError = pipelineState
    ? pipelineState.stages.some((stage) => stage.status === 'error')
    : false;

  return {
    pipelineState,
    error,
    isConnected,
    isComplete,
    hasError,
  };
}
