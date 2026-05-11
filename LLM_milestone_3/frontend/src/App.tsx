import { useState, useEffect, useRef } from 'react';
import { listCandidates, uploadCV, deleteCandidate } from './api';
import CandidateView from './CandidateView';
import Dashboard from './Dashboard';
import './App.css';

interface CandidateSummary {
  id: number;
  name: string;
  email: string;
  pdf_path: string;
  created_at: string;
  score: number;
}

function App() {
  const [candidates, setCandidates] = useState<CandidateSummary[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [showDashboard, setShowDashboard] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadCandidates = async () => {
    try { setCandidates(await listCandidates()); }
    catch (e) { console.error(e); }
  };

  useEffect(() => { loadCandidates(); }, []);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    
    setUploading(true);
    setMessage('');
    
    let successCount = 0;
    let failCount = 0;

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      setMessage(`Processing ${i + 1}/${files.length}: ${file.name}...`);
      try {
        await uploadCV(file);
        successCount++;
      } catch (err: any) {
        console.error(err);
        failCount++;
      }
    }

    setMessage(`✓ Finished: ${successCount} successful, ${failCount} failed.`);
    loadCandidates();
    setUploading(false);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this candidate?')) return;
    await deleteCandidate(id);
    setMessage('Candidate deleted.');
    loadCandidates();
    if (selectedId === id) setSelectedId(null);
  };

  const getInitials = (name: string) => {
    if (!name) return '?';
    return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
  };

  if (selectedId !== null) {
    return <CandidateView candidateId={selectedId} onBack={() => setSelectedId(null)} />;
  }

  if (showDashboard) {
    return <Dashboard 
      candidates={candidates} 
      onBack={() => setShowDashboard(false)} 
      onRefresh={loadCandidates}
    />;
  }

  return (
    <div className="app-container">
      {/* Header */}
      <header className="header">
        <div className="logo-section">
          <h1>
            <span className="logo-accent">TALASH</span>
            <span className="logo-dot"></span>
          </h1>
        </div>
        <p className="header-tagline">
          Smart HR Recruitment — <span className="tagline-highlight">Talent Acquisition & Learning Automation for Smart Hiring</span>
        </p>

        <div className="top-actions">
          <label className="btn btn-primary" title="Supported formats: PDF">
            <input ref={fileInputRef} type="file" accept=".pdf" multiple onChange={handleUpload} style={{ display: 'none' }} />
            {uploading ? (
              <><span className="spinner"></span> Processing...</>
            ) : (
              <><span className="btn-icon">📂</span> Upload CV</>
            )}
          </label>
          <button className="btn btn-secondary" onClick={() => setShowDashboard(true)} style={{ background: 'rgba(56,189,248,0.1)', color: '#38BDF8', border: '1px solid rgba(56,189,248,0.2)' }}>
            <span className="btn-icon">📊</span> Comparative Dashboard
          </button>
          <button className="btn" onClick={loadCandidates}>
            <span className="btn-icon">🔄</span> Refresh
          </button>
        </div>
      </header>

      {message && (
        <div style={{ marginBottom: 24 }}>
          <span style={{
            display: 'inline-flex', alignItems: 'center', gap: 8,
            padding: '12px 24px', borderRadius: 12, fontSize: 13, fontWeight: 700,
            background: message.startsWith('✓') ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
            border: `1px solid ${message.startsWith('✓') ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)'}`,
            color: message.startsWith('✓') ? '#34D399' : '#F87171'
          }}>
            {message}
          </span>
        </div>
      )}

      {/* Candidate List */}
      <div className="glass-card">
        <div className="table-header-box">
          <h3 className="section-title">Candidates</h3>
          <span className="records-found">
            {candidates.length} Profiles Found
          </span>
        </div>

        {candidates.length === 0 ? (
          <div className="state-message">
            <div className="state-icon">📋</div>
            <p>No candidates yet. Upload a CV to get started.</p>
          </div>
        ) : (
          <div className="candidates-grid">
            {candidates.map(c => (
              <div key={c.id} className="glass-card candidate-card" style={{ padding: 24, background: 'rgba(0,0,0,0.2)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 20 }}>
                  <div className="avatar-large" style={{ width: 48, height: 48, fontSize: 18 }}>
                    {getInitials(c.name)}
                  </div>
                  <div>
                    <div style={{ fontSize: 16, fontWeight: 700 }}>{c.name || 'Unknown'}</div>
                    <div style={{ fontSize: 12, color: 'var(--accent)' }}>{c.email || 'No email'}</div>
                  </div>
                  {c.score > 0 && (
                    <div style={{ marginLeft: 'auto', textAlign: 'right' }}>
                      <div style={{ fontSize: 20, fontWeight: 900, color: c.score >= 60 ? '#34D399' : '#F87171' }}>{c.score}</div>
                      <div style={{ fontSize: 8, fontWeight: 700, color: '#64748B', textTransform: 'uppercase' }}>Rating</div>
                    </div>
                  )}
                </div>
                
                <div style={{ display: 'flex', gap: 12, marginBottom: 20, fontSize: 11, color: 'var(--text-muted)' }}>
                  <span>📅 {new Date(c.created_at).toLocaleDateString()}</span>
                  <span>ID: #{c.id}</span>
                </div>

                <div style={{ display: 'flex', gap: 10 }}>
                  <button className="btn btn-primary" style={{ flex: 1, justifyContent: 'center' }} onClick={() => setSelectedId(c.id)}>
                    View Profile
                  </button>
                  <button className="btn" style={{ padding: '10px 12px' }} onClick={() => handleDelete(c.id)}>
                    🗑
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;