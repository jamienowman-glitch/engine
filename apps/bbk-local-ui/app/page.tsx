'use client';

import { useRef, useState } from 'react';

export default function Home() {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [status, setStatus] = useState<string>('');

  const handleUploadClick = () => {
    setStatus('');
    fileInputRef.current?.click();
  };

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    setStatus('Uploading…');
    try {
      const resp = await fetch('http://localhost:8081/bbk/upload-and-process', {
        method: 'POST',
        body: formData,
      });
      setStatus('Processing…');
      const data = await resp.json();
      if (!resp.ok || data.status === 'error') {
        setStatus(`Error: ${data.reason || data.status || resp.status}`);
        return;
      }
      setStatus(`Done – runId: ${data.runId}`);
    } catch (err: any) {
      setStatus(`Error: ${err?.message || 'upload failed'}`);
    }
  };

  const handleStartTraining = async () => {
    setStatus('Starting training…');
    try {
      const resp = await fetch('http://localhost:8081/bbk/start-training', { method: 'POST' });
      const data = await resp.json();
      if (!resp.ok || data.status === 'error') {
        setStatus(data.reason === 'no_dataset' ? 'No dataset found yet – upload and process audio first.' : `Error: ${data.reason || resp.status}`);
        return;
      }
      setStatus('Training started (local CPU). Leave this laptop on overnight.');
    } catch (err: any) {
      setStatus(`Error: ${err?.message || 'training failed'}`);
    }
  };

  return (
    <main className="min-h-screen bg-black text-white flex items-center justify-center">
      <div className="w-full max-w-md px-6 flex flex-col items-center gap-6 text-center">
        <img src="/bbk-logo.png" alt="BBK Logo" className="max-w-[240px] w-full h-auto" />
        <div className="flex flex-col w-full gap-3">
          <button
            onClick={handleUploadClick}
            className="w-full py-4 rounded-full bg-white text-black font-bold tracking-wide uppercase"
          >
            Upload & Process Audio
          </button>
          <button
            onClick={handleStartTraining}
            className="w-full py-4 rounded-full bg-black text-white font-bold tracking-wide uppercase shadow-[0_0_0_1px_rgba(255,255,255,0.8)]"
          >
            Start Training
          </button>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".mp3,.mp4,.wav"
            className="hidden"
          />
        </div>
        <p className="text-sm text-white/80 min-h-[1.5rem]">{status}</p>
      </div>
    </main>
  );
}
