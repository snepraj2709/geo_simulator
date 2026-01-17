import { motion } from 'framer-motion';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { useState } from 'react';
import { PipelineStageData, STAGE_METADATA } from '@/types/pipeline';
import { getStageIcon } from './PipelineIcons.tsx';

interface PipelineStageProps {
  stageData: PipelineStageData;
  isFirst: boolean;
  isLast: boolean;
}

export default function PipelineStage({ stageData, isLast }: PipelineStageProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const metadata = STAGE_METADATA[stageData.stage];
  const Icon = getStageIcon(metadata.icon);

  const getStatusColor = () => {
    switch (stageData.status) {
      case 'completed':
        return 'text-green-600 dark:text-green-400';
      case 'in-progress':
        return 'text-blue-600 dark:text-blue-400';
      case 'error':
        return 'text-red-600 dark:text-red-400';
      default:
        return 'text-neutral-400 dark:text-neutral-600';
    }
  };

  const getStatusBgColor = () => {
    switch (stageData.status) {
      case 'completed':
        return 'bg-green-100 dark:bg-green-900/30';
      case 'in-progress':
        return 'bg-blue-100 dark:bg-blue-900/30';
      case 'error':
        return 'bg-red-100 dark:bg-red-900/30';
      default:
        return 'bg-neutral-100 dark:bg-neutral-800';
    }
  };

  const getStatusBorderColor = () => {
    switch (stageData.status) {
      case 'completed':
        return 'border-green-500';
      case 'in-progress':
        return 'border-blue-500';
      case 'error':
        return 'border-red-500';
      default:
        return 'border-neutral-300 dark:border-neutral-700';
    }
  };

  const formatTime = (seconds?: number) => {
    if (!seconds) return null;
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  };

  return (
    <div className="relative">
      {/* Connector line */}
      {!isLast && (
        <div
          className={`absolute left-6 top-12 w-0.5 h-full ${
            stageData.status === 'completed'
              ? 'bg-green-500'
              : stageData.status === 'in-progress'
              ? 'bg-blue-500'
              : 'bg-neutral-300 dark:bg-neutral-700'
          }`}
        />
      )}

      <div className="relative">
        <div
          className={`flex items-start gap-4 p-4 rounded-lg border-2 transition-all ${getStatusBorderColor()} ${
            stageData.status === 'in-progress' ? 'shadow-lg' : ''
          }`}
        >
          {/* Icon */}
          <motion.div
            className={`flex-shrink-0 w-12 h-12 rounded-full flex items-center justify-center ${getStatusBgColor()}`}
            animate={
              stageData.status === 'in-progress'
                ? {
                    scale: [1, 1.05, 1],
                    boxShadow: [
                      '0 0 0 0 rgba(59, 130, 246, 0.4)',
                      '0 0 0 10px rgba(59, 130, 246, 0)',
                      '0 0 0 0 rgba(59, 130, 246, 0)',
                    ],
                  }
                : {}
            }
            transition={{
              duration: 2,
              repeat: stageData.status === 'in-progress' ? Infinity : 0,
              ease: 'easeInOut',
            }}
          >
            <Icon className={`w-6 h-6 ${getStatusColor()}`} />
          </motion.div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <h4 className="font-semibold text-neutral-900 dark:text-neutral-100">
                    {metadata.name}
                  </h4>
                  {stageData.status === 'in-progress' && (
                    <motion.span
                      className="badge bg-blue-500 text-white px-2 py-1 text-xs"
                      animate={{ opacity: [0.5, 1, 0.5] }}
                      transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
                    >
                      AI Processing
                    </motion.span>
                  )}
                </div>
                <p className="text-sm text-neutral-600 dark:text-neutral-400">
                  {metadata.description}
                </p>

                {/* Current action */}
                {stageData.currentAction && (
                  <p className="text-sm text-blue-600 dark:text-blue-400 mt-2 font-medium">
                    {stageData.currentAction}
                  </p>
                )}

                {/* Error message */}
                {stageData.error && (
                  <p className="text-sm text-red-600 dark:text-red-400 mt-2 font-medium">
                    Error: {stageData.error}
                  </p>
                )}
              </div>

              {/* Progress and time */}
              <div className="flex flex-col items-end gap-2">
                <div className="flex items-center gap-3">
                  {/* Progress percentage */}
                  <span className={`text-lg font-bold ${getStatusColor()}`}>
                    {stageData.progress}%
                  </span>

                  {/* Expand button */}
                  {(stageData.metadata || stageData.startedAt || stageData.completedAt) && (
                    <button
                      onClick={() => setIsExpanded(!isExpanded)}
                      className="p-1 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded transition-colors"
                      aria-label={isExpanded ? 'Collapse details' : 'Expand details'}
                    >
                      {isExpanded ? (
                        <ChevronUp className="w-5 h-5 text-neutral-600 dark:text-neutral-400" />
                      ) : (
                        <ChevronDown className="w-5 h-5 text-neutral-600 dark:text-neutral-400" />
                      )}
                    </button>
                  )}
                </div>

                {/* Time estimate */}
                {stageData.estimatedTimeRemaining !== undefined && stageData.status === 'in-progress' && (
                  <span className="text-xs text-neutral-500 dark:text-neutral-400">
                    ~{formatTime(stageData.estimatedTimeRemaining)} remaining
                  </span>
                )}
              </div>
            </div>

            {/* Progress bar */}
            {stageData.status !== 'pending' && (
              <div className="mt-3 h-2 bg-neutral-200 dark:bg-neutral-700 rounded-full overflow-hidden">
                <motion.div
                  className={`h-full ${
                    stageData.status === 'completed'
                      ? 'bg-green-500'
                      : stageData.status === 'error'
                      ? 'bg-red-500'
                      : 'bg-blue-500'
                  }`}
                  initial={{ width: 0 }}
                  animate={{ width: `${stageData.progress}%` }}
                  transition={{ duration: 0.5, ease: 'easeOut' }}
                />
              </div>
            )}

            {/* Expandable details */}
            <motion.div
              initial={false}
              animate={{ height: isExpanded ? 'auto' : 0, opacity: isExpanded ? 1 : 0 }}
              transition={{ duration: 0.3, ease: 'easeInOut' }}
              className="overflow-hidden"
            >
              <div className="mt-4 pt-4 border-t border-neutral-200 dark:border-neutral-700 space-y-2">
                {/* Timestamps */}
                {stageData.startedAt && (
                  <div className="text-sm">
                    <span className="text-neutral-600 dark:text-neutral-400">Started: </span>
                    <span className="text-neutral-900 dark:text-neutral-100">
                      {new Date(stageData.startedAt).toLocaleString()}
                    </span>
                  </div>
                )}
                {stageData.completedAt && (
                  <div className="text-sm">
                    <span className="text-neutral-600 dark:text-neutral-400">Completed: </span>
                    <span className="text-neutral-900 dark:text-neutral-100">
                      {new Date(stageData.completedAt).toLocaleString()}
                    </span>
                  </div>
                )}

                {/* Metadata */}
                {stageData.metadata && Object.keys(stageData.metadata).length > 0 && (
                  <div className="text-sm">
                    <span className="text-neutral-600 dark:text-neutral-400 block mb-1">Details:</span>
                    <div className="space-y-1 pl-3">
                      {Object.entries(stageData.metadata).map(([key, value]) => (
                        <div key={key} className="flex gap-2">
                          <span className="text-neutral-500 dark:text-neutral-400 capitalize">
                            {key.replace(/([A-Z])/g, ' $1').trim()}:
                          </span>
                          <span className="text-neutral-900 dark:text-neutral-100 font-medium">
                            {String(value)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </motion.div>
          </div>
        </div>
      </div>
    </div>
  );
}
