import { useEffect, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { ICP } from '../types';
import { Message, modelConfig } from '@/data/constants';
import { generateMockResponse } from '@/data';

interface LLMSimulationScreenProps {
  icps: ICP[];
  onComplete: () => void;
}

export function LLMSimulationScreen({ icps, onComplete }: LLMSimulationScreenProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Create messages for all prompts across all ICPs
    const allMessages: Message[] = [];
    const models: Array<'gpt' | 'gemini' | 'claude' | 'perplexity'> = ['gpt', 'gemini', 'claude', 'perplexity'];

    icps.forEach(icp => {
      // Only use first 2 prompts per ICP to keep simulation manageable
      icp.prompts.slice(0, 2).forEach(prompt => {
        models.forEach(model => {
          allMessages.push({
            id: `${icp.id}-${prompt.id}-${model}`,
            model,
            prompt: prompt.text,
            response: generateMockResponse(model, prompt.text),
            status: 'queued',
          });
        });
      });
    });

    setMessages(allMessages);
  }, [icps]);

  useEffect(() => {
    if (currentIndex >= messages.length) {
      // All messages processed
      setTimeout(onComplete, 2000);
      return;
    }

    // Process next message
    const timer = setTimeout(() => {
      setMessages(prev =>
        prev.map((msg, idx) =>
          idx === currentIndex ? { ...msg, status: 'processing' } : msg
        )
      );

      // Complete after typing animation
      setTimeout(() => {
        setMessages(prev =>
          prev.map((msg, idx) =>
            idx === currentIndex ? { ...msg, status: 'complete' } : msg
          )
        );
        setCurrentIndex(prev => prev + 1);
      }, 2000);
    }, 500);

    return () => clearTimeout(timer);
  }, [currentIndex, messages.length, onComplete]);

  useEffect(() => {
    // Auto-scroll to bottom
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const queuedCount = messages.filter(m => m.status === 'queued').length;
  const completeCount = messages.filter(m => m.status === 'complete').length;

  return (
    <div className="min-h-screen flex flex-col px-4 py-8 relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-violet-600/10 rounded-full blur-[100px] animate-pulse"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-cyan-600/10 rounded-full blur-[100px] animate-pulse delay-700"></div>
      </div>

      <div className="relative z-10 max-w-6xl mx-auto w-full flex flex-col h-screen max-h-screen">
        {/* Header */}
        <div className="flex-shrink-0 text-center space-y-3 mb-6 mt-5">
          <h2 className="text-4xl text-white">Running AI Simulations</h2>
          <p className="text-gray-400">
            Testing prompts across multiple language models
          </p>
          <div className="flex items-center justify-center gap-6 mt-4">
            <div className="text-sm">
              <span className="text-gray-500">Queued:</span>{' '}
              <span className="text-white tabular-nums">{queuedCount}</span>
            </div>
            <div className="text-sm">
              <span className="text-gray-500">Complete:</span>{' '}
              <span className="text-green-400 tabular-nums">{completeCount}</span>
            </div>
            <div className="text-sm">
              <span className="text-gray-500">Total:</span>{' '}
              <span className="text-white tabular-nums">{messages.length}</span>
            </div>
          </div>
        </div>

        {/* Chat Messages */}
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto space-y-6 pb-6 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent"
        >
          <AnimatePresence>
            {messages.map((message, index) => {
              if (index > currentIndex) return null;
              
              const config = modelConfig[message.model];

              return (
                <motion.div
                  key={message.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3 }}
                  className="space-y-3"
                >
                  {/* User Prompt */}
                  <div className="flex justify-end">
                    <div className="max-w-2xl p-4 rounded-2xl bg-white/5 border border-white/10">
                      <p className="text-sm text-gray-300">{message.prompt}</p>
                    </div>
                  </div>

                  {/* AI Response */}
                  <div className="flex items-start gap-3">
                    {/* Model Badge */}
                    <div
                      className={`flex-shrink-0 px-3 py-1.5 rounded-lg ${config.bgColor} border ${config.borderColor}`}
                    >
                      <span className={`text-xs ${config.textColor}`}>
                        {config.name}
                      </span>
                    </div>

                    {/* Response Content */}
                    <div className={`flex-1 p-4 rounded-2xl ${config.bgColor} border ${config.borderColor}`}>
                      {message.status === 'processing' ? (
                        <div className="space-y-2">
                          <div className="h-3 w-3/4 bg-white/10 rounded animate-pulse"></div>
                          <div className="h-3 w-full bg-white/10 rounded animate-pulse delay-75"></div>
                          <div className="h-3 w-2/3 bg-white/10 rounded animate-pulse delay-150"></div>
                        </div>
                      ) : (
                        <div className="relative">
                          <p className="text-sm text-gray-300 leading-relaxed blur-sm select-none">
                            {message.response}
                          </p>
                          <div className="absolute inset-0 flex items-center justify-center">
                            <div className={`px-3 py-1.5 rounded-lg bg-black/50 border ${config.borderColor} backdrop-blur-sm`}>
                              <span className={`text-xs ${config.textColor}`}>
                                Response captured
                              </span>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
