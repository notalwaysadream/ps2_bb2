import React, { useState } from 'react';

export default function App() {
  const [isRecording, setIsRecording] = useState(false);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center p-4 max-w-lg mx-auto">
      <header className="w-full text-center py-4 border-b border-slate-200">
        <h1 className="text-xl font-bold text-teal-800">ASHA Voice Register</h1>
        <p className="text-xs text-slate-500">Hands-free field entry with Gnani Voice</p>
      </header>

      <main className="w-full flex-1 flex flex-col justify-between py-6">
        {/* Placeholder for live transcript and filled form */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 min-h-[300px]">
          <h2 className="text-sm font-semibold text-slate-700 mb-2">Visit Summary</h2>
          <p className="text-xs text-slate-400 italic">Spoken visit notes will appear here automatically...</p>
        </div>

        {/* Action Button */}
        <div className="flex flex-col items-center gap-3 pt-6">
          <button
            onClick={() => setIsRecording(!isRecording)}
            className={`w-20 h-20 rounded-full flex items-center justify-center shadow-lg transition-all ${
              isRecording ? 'bg-red-500 text-white animate-pulse' : 'bg-teal-600 text-white hover:bg-teal-700'
            }`}
          >
            {isRecording ? 'Listening' : 'Tap to Speak'}
          </button>
          <span className="text-xs text-slate-500">
            {isRecording ? 'Speak your notes in Hindi/English...' : 'Press to start visit recording'}
          </span>
        </div>
      </main>
    </div>
  );
}
