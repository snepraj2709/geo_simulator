import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { AlertCircle, CheckCircle2, Clock } from 'lucide-react';
import { PipelineState } from '@/types/pipeline';
import { websocketService } from '@/services/websocket';
import PipelineStage from './PipelineStage';

interface PipelineProgressProps {
  pipelineId: string;
  websiteId: string;
  onComplete?: () => void;
  onError?: (error: string) => void;
}

export default function PipelineProgress({
  pipelineId,
  onComplete,
  onError,
}: PipelineProgressProps) {
  const [pipelineState, setPipelineState] = useState<PipelineState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    // Check connection status
    setIsConnected(websocketService.isConnected());

    // Subscribe to pipeline updates
    const unsubscribe = websocketService.subscribe(pipelineId, (state) => {
      setPipelineState(state);

      // Check if pipeline is complete
      const allCompleted = state.stages.every((stage) => stage.status === 'completed');
      if (allCompleted && onComplete) {
        onComplete();
      }
    });

    // Subscribe to errors
    const unsubscribeError = websocketService.onError((errorMsg) => {
      setError(errorMsg);
      if (onError) {
        onError(errorMsg);
      }
    });

    return () => {
      unsubscribe();
      unsubscribeError();
    };
  }, [pipelineId, onComplete, onError]);

  const formatEstimatedCompletion = (timestamp?: string) => {
    if (!timestamp) return null;
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = date.getTime() - now.getTime();
    const diffMins = Math.ceil(diffMs / 60000);

    if (diffMins < 1) return 'Less than a minute';
    if (diffMins === 1) return '1 minute';
    if (diffMins < 60) return `${diffMins} minutes`;

    const hours = Math.floor(diffMins / 60);
    const mins = diffMins % 60;
    return `${hours}h ${mins}m`;
  };

  const getOverallStatus = () => {
    if (!pipelineState) return 'pending';
    
    const hasError = pipelineState.stages.some((stage) => stage.status === 'error');
    if (hasError) return 'error';

    const allCompleted = pipelineState.stages.every((stage) => stage.status === 'completed');
    if (allCompleted) return 'completed';

    const hasInProgress = pipelineState.stages.some((stage) => stage.status === 'in-progress');
    if (hasInProgress) return 'in-progress';

    return 'pending';
  };

  const overallStatus = getOverallStatus();

  if (error) {
    return (
      <div className="card p-6">
        <div className="flex items-center gap-3 text-red-600 dark:text-red-400">
          <AlertCircle className="w-6 h-6" />
          <div>
            <h3 className="font-semibold">Pipeline Error</h3>
            <p className="text-sm mt-1">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  if (!pipelineState) {
    return (
      <div className="card p-6">
        <div className="flex items-center gap-3 text-neutral-600 dark:text-neutral-400">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-current" />
          <p>Loading pipeline status...</p>
        </div>
        {!isConnected && (
          <p className="text-sm text-yellow-600 dark:text-yellow-400 mt-2">
            WebSocket not connected. Attempting to reconnect...
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Overall Progress Header */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            {overallStatus === 'completed' ? (
              <CheckCircle2 className="w-8 h-8 text-green-600 dark:text-green-400" />
            ) : overallStatus === 'error' ? (
              <AlertCircle className="w-8 h-8 text-red-600 dark:text-red-400" />
            ) : (
              <Clock className="w-8 h-8 text-blue-600 dark:text-blue-400" />
            )}
            <div>
              <h2 className="text-2xl font-bold">
                {overallStatus === 'completed'
                  ? 'Pipeline Complete'
                  : overallStatus === 'error'
                  ? 'Pipeline Error'
                  : 'Processing Pipeline'}
              </h2>
              <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">
                {overallStatus === 'completed'
                  ? 'All stages completed successfully'
                  : overallStatus === 'error'
                  ? 'One or more stages encountered errors'
                  : pipelineState.estimatedCompletion
                  ? `Estimated completion: ${formatEstimatedCompletion(pipelineState.estimatedCompletion)}`
                  : 'Processing your request...'}
              </p>
            </div>
          </div>

          <div className="text-right">
            <div className="text-3xl font-bold text-blue-600 dark:text-blue-400">
              {pipelineState.overallProgress}%
            </div>
            <div className="text-sm text-neutral-600 dark:text-neutral-400">Overall Progress</div>
          </div>
        </div>

        {/* Overall Progress Bar */}
        <div className="h-3 bg-neutral-200 dark:bg-neutral-700 rounded-full overflow-hidden">
          <motion.div
            className={`h-full ${
              overallStatus === 'completed'
                ? 'bg-green-500'
                : overallStatus === 'error'
                ? 'bg-red-500'
                : 'bg-blue-500'
            }`}
            initial={{ width: 0 }}
            animate={{ width: `${pipelineState.overallProgress}%` }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
          />
        </div>

        {/* Pipeline metadata */}
        <div className="mt-4 flex items-center gap-6 text-sm text-neutral-600 dark:text-neutral-400">
          <div>
            <span className="font-medium">Started:</span>{' '}
            {new Date(pipelineState.startedAt).toLocaleString()}
          </div>
          <div>
            <span className="font-medium">Pipeline ID:</span> {pipelineState.id}
          </div>
        </div>
      </div>

      {/* Stage Stepper */}
      <div className="card p-6">
        <h3 className="text-xl font-semibold mb-6">Pipeline Stages</h3>
        <div className="space-y-6">
          {pipelineState.stages.map((stage, index) => (
            <PipelineStage
              key={stage.stage}
              stageData={stage}
              isFirst={index === 0}
              isLast={index === pipelineState.stages.length - 1}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
