import React from 'react';
import { Bot, User, Zap, Database, Clock, ArrowDownLeft, ArrowUpRight, ShieldCheck } from 'lucide-react';

export default function ChatMessage({ message }) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="flex justify-end mb-4">
        <div className="flex items-start max-w-[85%] md:max-w-[75%] gap-2.5 flex-row-reverse">
          <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0 text-white shadow-md">
            <User className="w-4 h-4" />
          </div>
          <div className="rounded-2xl rounded-tr-sm bg-blue-600 px-4 py-3 text-white shadow-sm break-words leading-relaxed text-sm">
            {message.content}
          </div>
        </div>
      </div>
    );
  }

  // Assistant Message
  const meta = message.metadata || {};
  const isCache = meta.resolution_source === 'LLM_CACHE';

  return (
    <div className="flex justify-start mb-6" data-testid="assistant-message">
      <div className="flex items-start max-w-[95%] md:max-w-[85%] gap-3">
        <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-white shadow-md ${
          isCache ? 'bg-emerald-600' : 'bg-slate-700'
        }`}>
          <Bot className="w-4 h-4" />
        </div>

        <div className="flex-1 overflow-hidden">
          {/* Response Bubble */}
          <div className="rounded-2xl rounded-tl-sm bg-slate-800/90 border border-slate-700/80 px-4 py-3.5 text-slate-100 shadow-sm break-words leading-relaxed text-sm">
            {message.content}
          </div>

          {/* Metadata Container */}
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
            {/* Resolution Source Badge */}
            <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md font-medium border ${
              isCache 
                ? 'bg-emerald-950/60 border-emerald-700/60 text-emerald-300' 
                : 'bg-blue-950/60 border-blue-700/60 text-blue-300'
            }`}>
              {isCache ? <Database className="w-3.5 h-3.5" /> : <Zap className="w-3.5 h-3.5" />}
              <span data-testid="meta-source">{meta.resolution_source || 'LIVE_INFERENCE'}</span>
            </div>

            {/* Model Badge */}
            <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-800/80 border border-slate-700/60 text-slate-300">
              <span className="text-slate-400">Model:</span>
              <span data-testid="meta-model" className="font-mono text-[11px] text-slate-200">
                {meta.model || 'gemini/gemini-flash-lite-latest'}
              </span>
            </div>

            {/* Latency Badge */}
            <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-800/80 border border-slate-700/60 text-slate-300">
              <Clock className="w-3 h-3 text-slate-400" />
              <span data-testid="meta-latency">{meta.latency_ms ?? 0} ms</span>
            </div>

            {/* Token Tracking */}
            <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-md bg-slate-800/80 border border-slate-700/60 text-slate-300">
              <span className="inline-flex items-center gap-1" title="Prompt Tokens">
                <ArrowDownLeft className="w-3 h-3 text-slate-400" />
                <span className="text-slate-400">In:</span>
                <span data-testid="meta-input-tokens" className="font-semibold text-slate-200">
                  {meta.input_tokens ?? 0}
                </span>
              </span>
              <span className="text-slate-600">|</span>
              <span className="inline-flex items-center gap-1" title="Completion Tokens">
                <ArrowUpRight className="w-3 h-3 text-slate-400" />
                <span className="text-slate-400">Out:</span>
                <span data-testid="meta-output-tokens" className="font-semibold text-slate-200">
                  {meta.output_tokens ?? 0}
                </span>
              </span>
            </div>

            {/* Key ID / Fallback Information */}
            {meta.key_id && (
              <div className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-slate-800 border border-slate-700/60 text-[11px] text-slate-400">
                <ShieldCheck className="w-3 h-3 text-indigo-400" />
                <span>Key: <span className="font-mono text-slate-200">{meta.key_id}</span></span>
                {meta.fallback_attempts > 0 && (
                  <span className="ml-1 text-amber-400 font-medium">({meta.fallback_attempts} fallback)</span>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
