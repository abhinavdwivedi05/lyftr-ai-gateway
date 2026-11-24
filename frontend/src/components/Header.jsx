import React, { useState } from 'react';
import { Sparkles, RefreshCw, Settings, AlertTriangle, Shield, CheckCircle2 } from 'lucide-react';

export default function Header({
  sessionId,
  health,
  onNewSession,
  systemPrompt,
  setSystemPrompt,
  simulateFailure,
  setSimulateFailure
}) {
  const [showConfig, setShowConfig] = useState(false);

  return (
    <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur-md sticky top-0 z-20">
      <div className="max-w-5xl mx-auto px-4 py-3 sm:px-6 flex items-center justify-between gap-4">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white shadow-lg shadow-blue-500/20">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-semibold text-base tracking-tight text-white">Lyftr AI Gateway</h1>
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20 font-medium">
                Gemini Failover
              </span>
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <span>Session:</span>
              <span className="font-mono text-slate-300 font-medium">{sessionId}</span>
            </div>
          </div>
        </div>

        {/* Actions & Status */}
        <div className="flex items-center gap-2.5">
          {/* Health Pill */}
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-800/80 border border-slate-700/60 text-xs">
            <span className={`w-2 h-2 rounded-full ${health.status === 'ok' ? 'bg-emerald-400 shadow-sm shadow-emerald-400/50' : 'bg-amber-400'}`} />
            <span className="text-slate-300 font-medium">{health.keys_configured} Keys</span>
            <span className="text-slate-500">•</span>
            <span className="text-slate-400">{health.cache_enabled ? 'Cache ON' : 'Cache OFF'}</span>
          </div>

          {/* Toggle System Prompt & Simulation Controls */}
          <button
            onClick={() => setShowConfig(!showConfig)}
            className={`p-2 rounded-lg border text-sm transition-colors flex items-center gap-1.5 ${
              showConfig || systemPrompt || simulateFailure
                ? 'bg-blue-600/20 border-blue-500/40 text-blue-300'
                : 'bg-slate-800/80 border-slate-700 text-slate-300 hover:bg-slate-700'
            }`}
            title="Configure System Prompt & Simulation"
          >
            <Settings className="w-4 h-4" />
            <span className="hidden md:inline text-xs font-medium">Config</span>
          </button>

          {/* New Chat Button */}
          <button
            onClick={onNewSession}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-medium transition-all shadow-sm active:scale-95"
            title="Start New Session"
          >
            <RefreshCw className="w-3.5 h-3.5 text-slate-400" />
            <span>New Chat</span>
          </button>
        </div>
      </div>

      {/* Collapsible Config Drawer */}
      {showConfig && (
        <div className="border-t border-slate-800 bg-slate-900/95 px-4 py-3.5 sm:px-6">
          <div className="max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Optional System Prompt Field */}
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Custom System Prompt <span className="text-slate-500 font-normal">(Optional)</span>
              </label>
              <input
                data-testid="system-prompt-input"
                type="text"
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
                placeholder="e.g. You are an expert Python engineer..."
                className="w-full text-xs rounded-lg border border-slate-700 bg-slate-800/90 px-3 py-2 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
              />
            </div>

            {/* Failure Simulation Hook Selector */}
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5 flex items-center justify-between">
                <span>X-Simulate-Failure Header Hook</span>
                {simulateFailure && (
                  <span className="text-[11px] text-amber-400 font-normal">Simulation Active</span>
                )}
              </label>
              <select
                value={simulateFailure}
                onChange={(e) => setSimulateFailure(e.target.value)}
                className="w-full text-xs rounded-lg border border-slate-700 bg-slate-800/90 px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500 transition-colors"
              >
                <option value="">None (Normal Execution)</option>
                <option value="key_1=429">key_1=429 (Simulate Rate Limit on Key 1 &rarr; Fallback to Key 2)</option>
                <option value="key_1=500">key_1=500 (Simulate Internal Error on Key 1 &rarr; Fallback to Key 2)</option>
                <option value="key_1=429,key_2=500">key_1=429,key_2=500 (Simulate Both Keys Failing &rarr; HTTP 503)</option>
                <option value="*=429">*=429 (Wildcard Fail All Keys &rarr; HTTP 503)</option>
              </select>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
