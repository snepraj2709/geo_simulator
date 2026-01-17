import { useState } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { ChevronDown, ChevronUp, Edit2, Check } from 'lucide-react';
import type { ICP } from '../types';

interface PromptGenerationScreenProps {
  icps: ICP[];
  onComplete: (icps: ICP[]) => void;
}

export function PromptGenerationScreen({ icps, onComplete }: PromptGenerationScreenProps) {
  const [expandedICP, setExpandedICP] = useState<string | null>(icps[0]?.id || null);
  const [editingPrompt, setEditingPrompt] = useState<string | null>(null);
  const [editedText, setEditedText] = useState('');
  const [localICPs, setLocalICPs] = useState(icps);

  const handleToggleICP = (icpId: string) => {
    setExpandedICP(expandedICP === icpId ? null : icpId);
  };

  const handleEditPrompt = (promptId: string, currentText: string) => {
    setEditingPrompt(promptId);
    setEditedText(currentText);
  };

  const handleSavePrompt = (icpId: string, promptId: string) => {
    setLocalICPs(prev =>
      prev.map(icp =>
        icp.id === icpId
          ? {
              ...icp,
              prompts: icp.prompts.map(p =>
                p.id === promptId ? { ...p, text: editedText } : p
              ),
            }
          : icp
      )
    );
    setEditingPrompt(null);
  };

  const handleApprove = () => {
    onComplete(localICPs);
  };

  return (
    <div className="min-h-screen flex flex-col px-4 py-5 relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/3 w-96 h-96 bg-blue-600/10 rounded-full blur-[100px] animate-pulse"></div>
      </div>

      <div className="relative z-10 max-w-5xl mx-auto w-full space-y-8">
        {/* Header */}
        <div className="text-center space-y-3">
          <h2 className="text-4xl text-white">Review Generated Prompts</h2>
          <p className="text-gray-400">
            We've generated 10 search prompts for each persona. Review and edit as needed.
          </p>
        </div>

        {/* ICP Accordion */}
        <div className="space-y-4 mt-12">
          {localICPs.map((icp) => {
            const isExpanded = expandedICP === icp.id;

            return (
              <div
                key={icp.id}
                className="rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm overflow-hidden"
              >
                {/* ICP Header */}
                <button
                  onClick={() => handleToggleICP(icp.id)}
                  className="w-full p-6 flex items-center gap-4 hover:bg-white/5 transition-colors"
                >
                  <img
                    src={icp.avatar}
                    alt={icp.name}
                    className="w-12 h-12 rounded-full object-cover ring-2 ring-violet-500/20"
                  />
                  <div className="flex-1 text-left">
                    <h3 className="text-white mb-1">{icp.name}</h3>
                    <p className="text-sm text-gray-400">{icp.description}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-violet-400">
                      {icp.prompts.length} prompts
                    </span>
                    {isExpanded ? (
                      <ChevronUp className="w-5 h-5 text-gray-400" />
                    ) : (
                      <ChevronDown className="w-5 h-5 text-gray-400" />
                    )}
                  </div>
                </button>

                {/* Prompts List */}
                {isExpanded && (
                  <div className="border-t border-white/10 p-6 space-y-3">
                    {icp.prompts.map((prompt, index) => {
                      const isEditing = editingPrompt === prompt.id;

                      return (
                        <div
                          key={prompt.id}
                          className="p-4 rounded-xl bg-white/5 border border-white/10 hover:border-white/20 transition-colors group"
                        >
                          <div className="flex items-start gap-3">
                            <div className="flex-shrink-0 w-6 h-6 rounded-md bg-violet-500/20 text-violet-400 flex items-center justify-center text-sm">
                              {index + 1}
                            </div>

                            {isEditing ? (
                              <div className="flex-1 flex gap-2">
                                <Input
                                  value={editedText}
                                  onChange={(e) => setEditedText(e.target.value)}
                                  className="flex-1 bg-white/10 border-white/20 text-white"
                                  autoFocus
                                />
                                <Button
                                  size="sm"
                                  onClick={() => handleSavePrompt(icp.id, prompt.id)}
                                  className="bg-green-500/20 hover:bg-green-500/30 text-green-400 border border-green-500/30"
                                >
                                  <Check className="w-4 h-4" />
                                </Button>
                              </div>
                            ) : (
                              <>
                                <p className="flex-1 text-sm text-gray-300 leading-relaxed">
                                  {prompt.text}
                                </p>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => handleEditPrompt(prompt.id, prompt.text)}
                                  className="opacity-0 group-hover:opacity-100 transition-opacity"
                                >
                                  <Edit2 className="w-4 h-4 text-gray-400" />
                                </Button>
                              </>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Action Buttons */}
        <div className="flex justify-center gap-4 pt-8">
          <Button
            onClick={handleApprove}
            className="px-8 h-12 bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-700 hover:to-blue-700 text-white shadow-lg shadow-violet-500/25"
          >
            Review & Approve All Prompts
          </Button>
        </div>
      </div>
    </div>
  );
}
