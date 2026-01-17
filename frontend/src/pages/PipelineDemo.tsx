import { useState, useEffect } from 'react';
import PipelineProgress from '@/components/PipelineProgress';

export default function PipelineDemo() {
  const [progress, setProgress] = useState(0);
  const [isRunning, setIsRunning] = useState(false);

  useEffect(() => {
    if (!isRunning) return;

    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          setIsRunning(false);
          return 100;
        }
        return prev + 1;
      });
    }, 500); // Update every 500ms

    return () => clearInterval(interval);
  }, [isRunning]);

  const handleStart = () => {
    setProgress(0);
    setIsRunning(true);
  };

  const handleReset = () => {
    setProgress(0);
    setIsRunning(false);
  };


  return (
    <div className="min-h-screen bg-neutral-50 dark:bg-neutral-950 p-6">
      <div className="max-w-5xl mx-auto">
        <div className="mb-6">
          <h1 className="text-4xl font-bold mb-2">Pipeline Progress Demo</h1>
          <p className="text-neutral-600 dark:text-neutral-400">
            Interactive demonstration of the pipeline progress component with all 8 stages
          </p>
        </div>

        {/* Demo Controls */}
        <div className="card p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Demo Controls</h2>
          <div className="flex items-center gap-4">
            <button
              onClick={handleStart}
              disabled={isRunning}
              className="btn btn-primary px-6 py-2"
            >
              {isRunning ? 'Running...' : 'Start Pipeline'}
            </button>
            <button
              onClick={handleReset}
              className="btn btn-outline px-6 py-2"
            >
              Reset
            </button>
            <div className="flex-1" />
            <div className="text-sm text-neutral-600 dark:text-neutral-400">
              Simulated Progress: <span className="font-bold">{progress}%</span>
            </div>
          </div>

          <div className="mt-4">
            <label className="label mb-2">Manual Progress Control:</label>
            <input
              type="range"
              min="0"
              max="100"
              value={progress}
              onChange={(e) => {
                setProgress(Number(e.target.value));
                setIsRunning(false);
              }}
              className="w-full"
            />
          </div>
        </div>

        {/* Pipeline Progress Component */}
        <PipelineProgress
          pipelineId="demo-pipeline-123"
          websiteId="website-456"
          onComplete={() => {
            console.log('Pipeline completed!');
          }}
          onError={(error) => {
            console.error('Pipeline error:', error);
          }}
        />

        {/* Info Card */}
        <div className="card p-6 mt-6">
          <h3 className="text-lg font-semibold mb-3">Component Features</h3>
          <ul className="space-y-2 text-sm text-neutral-600 dark:text-neutral-400">
            <li>✅ Real-time WebSocket updates (simulated in demo)</li>
            <li>✅ 8 pipeline stages from ARCHITECTURE.md</li>
            <li>✅ Status tracking: pending, in-progress, completed, error</li>
            <li>✅ Progress percentages per stage</li>
            <li>✅ Estimated time remaining</li>
            <li>✅ Current action display</li>
            <li>✅ Expandable stage details with metadata</li>
            <li>✅ Pulsing "AI Processing" badge on active stages</li>
            <li>✅ Smooth Framer Motion animations</li>
            <li>✅ Responsive Tailwind CSS styling</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
