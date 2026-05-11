import { useState, useEffect } from 'react';

interface Candidate {
  id: number;
  name: string;
  score: number;
}

export default function Dashboard({ candidates, onBack, onRefresh }: { candidates: any[]; onBack: () => void, onRefresh: () => void }) {
  const sorted = [...candidates].sort((a, b) => b.score - a.score);
  const maxScore = 100;

  useEffect(() => {
    onRefresh();
  }, []);

  return (
    <div className="app-container">
      <header className="header" style={{ marginBottom: 30 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 20, width: '100%' }}>
          <button onClick={onBack} className="btn" style={{ background: 'rgba(255,255,255,0.05)', color: '#94A3B8' }}>
            ← Back
          </button>
          <h1 style={{ fontSize: 28, fontWeight: 800 }}>Comparative <span className="logo-accent">Dashboard</span></h1>
          <button onClick={onRefresh} className="btn" style={{ marginLeft: 'auto', background: 'rgba(16,185,129,0.1)', color: '#34D399', border: '1px solid rgba(16,185,129,0.2)' }}>
            🔄 Sync Data
          </button>
        </div>
      </header>

      <div className="glass-card" style={{ padding: 30 }}>
        <h3 style={{ marginBottom: 24, color: '#F8FAFC', fontSize: 20 }}>Candidate Rankings</h3>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          {sorted.map((c, index) => (
            <div key={c.id} style={{ position: 'relative' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8, fontSize: 14 }}>
                <div style={{ fontWeight: 600, color: '#F8FAFC', display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ width: 24, height: 24, borderRadius: '50%', background: index < 3 ? 'rgba(14,165,233,0.2)' : 'rgba(255,255,255,0.05)', color: index < 3 ? '#0EA5E9' : '#64748B', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11 }}>
                    {index + 1}
                  </span>
                  {c.name}
                </div>
                <div style={{ fontWeight: 800, color: c.score > 70 ? '#34D399' : c.score > 40 ? '#F59E0B' : '#64748B' }}>
                  {c.score} / 100
                </div>
              </div>
              
              <div style={{ height: 12, background: 'rgba(255,255,255,0.05)', borderRadius: 6, overflow: 'hidden' }}>
                <div 
                  style={{ 
                    height: '100%', 
                    width: `${c.score}%`, 
                    background: c.score > 70 ? 'linear-gradient(90deg, #10B981, #34D399)' : 'linear-gradient(90deg, #0EA5E9, #38BDF8)',
                    transition: 'width 1s ease-out',
                    boxShadow: '0 0 10px rgba(14,165,233,0.3)'
                  }} 
                />
              </div>
            </div>
          ))}

          {sorted.length === 0 && (
            <p style={{ textAlign: 'center', color: '#64748B', padding: '40px 0' }}>No candidate data available for comparison.</p>
          )}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 20, marginTop: 24 }}>
        <div className="glass-card" style={{ padding: 24, textAlign: 'center' }}>
          <div style={{ fontSize: 12, color: '#64748B', textTransform: 'uppercase', marginBottom: 8 }}>Total Candidates</div>
          <div style={{ fontSize: 32, fontWeight: 900, color: '#F8FAFC' }}>{candidates.length}</div>
        </div>
        <div className="glass-card" style={{ padding: 24, textAlign: 'center' }}>
          <div style={{ fontSize: 12, color: '#64748B', textTransform: 'uppercase', marginBottom: 8 }}>Avg. Platform Score</div>
          <div style={{ fontSize: 32, fontWeight: 900, color: '#0EA5E9' }}>
            {candidates.length > 0 ? (candidates.reduce((acc, curr) => acc + curr.score, 0) / candidates.length).toFixed(1) : '0'}
          </div>
        </div>
        <div className="glass-card" style={{ padding: 24, textAlign: 'center' }}>
          <div style={{ fontSize: 12, color: '#64748B', textTransform: 'uppercase', marginBottom: 8 }}>Top Candidate</div>
          <div style={{ fontSize: 20, fontWeight: 700, color: '#34D399', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {sorted[0]?.name || 'N/A'}
          </div>
        </div>
      </div>
    </div>
  );
}
