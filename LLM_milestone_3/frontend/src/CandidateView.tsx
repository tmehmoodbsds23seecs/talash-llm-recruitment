import { useState, useEffect } from 'react';
import { getCandidate, loadSectionFacts, runAnalysis, getAnalysis, draftEmail, verifySection, searchPublications, getOverallScore } from './api';

const SECTIONS = [
  { key: 'education', label: 'Education' },
  { key: 'experience', label: 'Experience' },
  { key: 'skills', label: 'Skills' },
  { key: 'publications', label: 'Research' },
  { key: 'esearch', label: 'eSearch' },
  { key: 'books', label: 'Books' },
  { key: 'patents', label: 'Patents' },
  { key: 'supervision', label: 'Supervision' },
  { key: 'overall', label: 'Status' },
];

export default function CandidateView({ candidateId, onBack }: { candidateId: number; onBack: () => void }) {
  const [candidate, setCandidate] = useState<any>(null);
  const [fullData, setFullData] = useState<any>({});
  const [activeSection, setActiveSection] = useState('education');
  const [sectionData, setSectionData] = useState<any[]>([]);
  const [analysis, setAnalysis] = useState<string | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [emailDraft, setEmailDraft] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [verifyProgress, setVerifyProgress] = useState('');
  const [esearchResults, setEsearchResults] = useState<any[]>([]);
  const [esearchLoading, setEsearchLoading] = useState(false);
  const [sectionScore, setSectionScore] = useState<number>(0);
  const [overallScore, setOverallScore] = useState<any>(null);

  useEffect(() => {
    getCandidate(candidateId)
      .then(data => {
        setCandidate(data.candidate);
        setFullData(data);
      })
      .catch(() => setError('Failed to load candidate profile.'));

    getOverallScore(candidateId)
      .then(data => setOverallScore(data))
      .catch(() => {});
  }, [candidateId]);

  useEffect(() => {
    setError(null);
    setAnalysis(null);
    setSectionScore(0);
    setEmailDraft(null);
    loadSectionFacts(candidateId, activeSection)
      .then(result => {
        setSectionData(result.data || []);
        return getAnalysis(candidateId, mapSection(activeSection));
      })
      .then(existing => {
        if (existing.analysis) setAnalysis(existing.analysis);
        if (existing.score) setSectionScore(existing.score);
      })
      .catch(() => {});
  }, [activeSection, candidateId]);

  const mapSection = (section: string) => {
    if (section === 'publications') return 'research';
    if (section === 'books') return 'books_patents';
    if (section === 'patents') return 'books_patents';
    if (section === 'esearch') return 'research';
    return section;
  };

  useEffect(() => {
    if (activeSection === 'esearch') {
      setEsearchLoading(true);
      setEsearchResults([]);
      searchPublications(candidateId)
        .then(data => {
          setEsearchResults(data.results || []);
        })
        .catch(() => setEsearchResults([]))
        .finally(() => setEsearchLoading(false));
    }
  }, [activeSection, candidateId]);

  const handleVerify = async () => {
    setVerifying(true);
    setVerifyProgress('Starting verification...');
    try {
      const result = await verifySection(candidateId, activeSection);
      setVerifyProgress(`Verified ${result.verified_count} of ${result.total} records`);
      setTimeout(() => {
        loadSectionFacts(candidateId, activeSection).then(r => setSectionData(r.data || []));
      }, 500);
    } catch (e: any) {
      setError(`Verification failed: ${e.message}`);
    } finally {
      setVerifying(false);
      setTimeout(() => setVerifyProgress(''), 3000);
    }
  };

  const handleRunAnalysis = async () => {
    setAnalysisLoading(true);
    setError(null);
    try {
      const result = await runAnalysis(candidateId, mapSection(activeSection));
      setAnalysis(result.analysis);
      setSectionScore(result.score);
      getOverallScore(candidateId).then(data => setOverallScore(data));
    } catch (e: any) {
      setError(`Analysis failed: ${e.response?.data?.detail || e.message || 'Unknown error'}`);
    } finally {
      setAnalysisLoading(false);
    }
  };

  const handleDraftEmail = async () => {
    if (!candidate || !fullData || Object.keys(fullData).length === 0) {
      setError("Please wait, candidate data is still loading...");
      return;
    }
    
    const missing: Record<string, string[]> = {};
    const sections = ['education', 'experience', 'skills', 'publications', 'books', 'patents', 'supervision'];
    
    console.log("[DEBUG] Checking missing info. FullData:", fullData);

    sections.forEach(s => {
      const data = fullData ? fullData[s] : [];
      if (!data || data.length === 0) {
        missing[s] = [`The ${s} section appears to be missing or incomplete in your CV.`];
      }
    });

    if (!candidate.name) missing['personal_info'] = ['Your full name was not clearly identified.'];
    if (!candidate.email) missing['personal_info'] = [...(missing['personal_info'] || []), 'Your contact email address is missing.'];

    console.log("[DEBUG] Missing fields identified:", missing);

    if (Object.keys(missing).length === 0) {
      missing['general'] = ['We would appreciate a general update to ensure your profile is fully complete for our review.'];
    }

    try {
      setError(null);
      console.log(`[DEBUG] Calling draftEmail API for candidate ${candidateId}...`);
      const result = await draftEmail(candidateId, missing);
      console.log("[DEBUG] API Result:", result);
      if (result && result.email_draft) {
        setEmailDraft(result.email_draft);
      } else {
        throw new Error("API returned success but no email draft content.");
      }
    } catch (e: any) {
      console.error("[DEBUG] Email draft error:", e);
      const errMsg = e.response?.data?.detail || e.message || "Unknown error occurred";
      setError(`Email drafting failed: ${errMsg}. Check console for details.`);
    }
  };

  const copyEmail = () => {
    if (emailDraft) {
      navigator.clipboard.writeText(emailDraft);
      alert('Email copied to clipboard!');
    }
  };

  const getInitials = (name: string) => {
    if (!name) return '?';
    return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
  };

  const getFieldLabel = (field: string) => field.replace(/_/g, ' ');

  const getLevelBadge = (level: string) => {
    const l = (level || '').toLowerCase();
    if (l.includes('post')) return 'level-postgrad';
    if (l.includes('under')) return 'level-undergrad';
    return 'level-sse';
  };

  const isVerifiable = activeSection === 'publications' || activeSection === 'books' || activeSection === 'patents';
  const showEsearch = activeSection === 'esearch';

  return (
    <div className="app-container">
      {error && (
        <div style={{ padding: '12px 20px', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: 10, color: '#F87171', marginBottom: 16, fontSize: 13 }}>
          {error}
        </div>
      )}

      <div className="glass-card" style={{ margin: '20px 0 28px', position: 'relative', overflow: 'hidden' }}>
        <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 3, background: 'linear-gradient(90deg, #0EA5E9, #38BDF8, #0EA5E9)' }} />
        <div style={{ display: 'flex', alignItems: 'center', gap: 20, marginBottom: 24 }}>
          <button onClick={onBack} style={{ padding: '10px 20px', background: 'rgba(15,17,23,0.8)', color: '#94A3B8', border: '1.5px solid rgba(255,255,255,0.08)', borderRadius: 12, cursor: 'pointer', fontSize: 13, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8, fontFamily: 'inherit' }}>
            Back
          </button>
          <div style={{ width: 68, height: 68, background: 'linear-gradient(135deg, #0EA5E9, #0369A1)', borderRadius: 16, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 24, fontWeight: 800, color: 'white', flexShrink: 0, boxShadow: '0 0 24px rgba(14,165,233,0.3)' }}>
            {getInitials(candidate?.name || '?')}
          </div>
          <div>
            <h2 style={{ fontSize: 26, fontWeight: 800, color: '#F8FAFC' }}>{candidate?.name || 'Loading...'}</h2>
            <p style={{ fontSize: 14, color: '#38BDF8', marginTop: 4 }}>{candidate?.email || 'No email'}</p>
            <p style={{ fontSize: 12, color: '#64748B', marginTop: 2 }}>ID: #{candidateId}</p>
          </div>
          {overallScore && overallScore.overall_score > 0 && (
            <div style={{ marginLeft: 'auto', textAlign: 'center' }}>
              <div style={{ fontSize: 32, fontWeight: 900, color: '#34D399', textShadow: '0 0 12px rgba(52,211,153,0.4)' }}>
                {overallScore.overall_score}
              </div>
              <div style={{ fontSize: 10, fontWeight: 700, color: '#64748B', textTransform: 'uppercase', letterSpacing: 1, marginTop: -4 }}>
                Overall Score
              </div>
            </div>
          )}
        </div>

        <div className="filter-chips">
          {SECTIONS.map(s => (
            <button key={s.key} className={`chip ${activeSection === s.key ? 'active' : ''}`} onClick={() => setActiveSection(s.key)}>
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {/* Load Facts */}
      {activeSection === 'overall' ? (
        <div style={{ padding: '40px 20px', textAlign: 'center', background: 'rgba(0,0,0,0.2)', borderRadius: 20, marginBottom: 24 }}>
          <div style={{ fontSize: 40, marginBottom: 16 }}>📊</div>
          <h3 style={{ fontSize: 22, fontWeight: 800, color: '#F8FAFC', marginBottom: 12 }}>Candidate Recruitment Status</h3>
          <p style={{ color: '#94A3B8', maxWidth: 500, margin: '0 auto 24px', lineHeight: 1.6 }}>
            Comprehensive evaluation based on AI analysis of education, experience, and research.
          </p>
          {!analysis ? (
            <div>
              <div style={{ padding: '16px 24px', background: 'rgba(56,189,248,0.1)', border: '1px solid rgba(56,189,248,0.2)', borderRadius: 12, color: '#38BDF8', fontSize: 13, marginBottom: 20, display: 'inline-block' }}>
                ℹ️ All sectional analyses will be combined into this final report.
              </div>
              <br/>
              <button 
                className="btn btn-primary" 
                onClick={handleRunAnalysis}
                disabled={analysisLoading}
                style={{ padding: '16px 32px', fontSize: 16, background: 'linear-gradient(135deg, #0EA5E9, #2563EB)' }}
              >
                {analysisLoading ? <><span className="spinner" /> Generating Verdict...</> : '🚀 Generate Final Recommendation'}
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10 }}>
              <div style={{ fontSize: 64, fontWeight: 900, color: sectionScore >= 60 ? '#34D399' : '#F87171', textShadow: `0 0 20px ${sectionScore >= 60 ? 'rgba(52,211,153,0.3)' : 'rgba(248,113,113,0.3)'}` }}>
                {sectionScore}/100
              </div>
              <div style={{ padding: '8px 24px', background: sectionScore >= 60 ? 'rgba(52,211,153,0.1)' : 'rgba(248,113,113,0.1)', border: `1px solid ${sectionScore >= 60 ? 'rgba(52,211,153,0.3)' : 'rgba(248,113,113,0.3)'}`, borderRadius: 50, color: sectionScore >= 60 ? '#34D399' : '#F87171', fontWeight: 800, fontSize: 14, textTransform: 'uppercase', letterSpacing: 1 }}>
                {sectionScore >= 60 ? '✅ Highly Recommended' : '❌ Not Recommended'}
              </div>
              <div style={{ fontSize: 12, fontWeight: 700, color: '#64748B', textTransform: 'uppercase', letterSpacing: 2, marginTop: 10 }}>
                Aggregated Quality Rating
              </div>
            </div>
          )}
        </div>
      ) : (
        <div style={{ margin: '0 0 24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 4 }}>
          <h3 style={{ fontSize: 20, fontWeight: 700, color: '#F8FAFC' }}>Load Facts</h3>
          <span style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 12px', background: 'rgba(14,165,233,0.1)', border: '1px solid rgba(14,165,233,0.2)', borderRadius: 50, fontSize: 12, color: '#38BDF8', fontWeight: 600 }}>
            Database
          </span>
          {isVerifiable && (
            <button
              onClick={handleVerify}
              disabled={verifying || sectionData.length === 0}
              style={{ padding: '6px 16px', background: 'linear-gradient(135deg, #10B981, #059669)', color: 'white', border: 'none', borderRadius: 20, fontSize: 12, fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit', display: 'flex', alignItems: 'center', gap: 6, marginLeft: 'auto' }}
            >
              {verifying ? (
                <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span className="spinner" /> Verifying...
                </span>
              ) : (
                <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>Verify via APIs</span>
              )}
            </button>
          )}
        </div>
        {verifyProgress ? <p style={{ fontSize: 12, color: '#34D399', marginBottom: 8 }}>{verifyProgress}</p> : null}
        <p style={{ fontSize: 13, color: '#64748B', marginBottom: 20 }}>Display extracted data from the database</p>

        <div className="glass-card">
          <div style={{ overflowX: 'auto', borderRadius: 16 }}>
            {showEsearch ? (
              <div style={{ padding: 24 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 12px', background: 'rgba(139,92,246,0.1)', border: '1px solid rgba(139,92,246,0.2)', borderRadius: 50, fontSize: 12, color: '#A78BFA', fontWeight: 600 }}>
                    CrossRef + PubMed
                  </span>
                  <span style={{ fontSize: 13, color: '#64748B' }}>Verifying publications from CrossRef and PubMed</span>
                </div>
                {esearchLoading ? (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 24, justifyContent: 'center' }}>
                    <span className="spinner" />
                    <span style={{ color: '#94A3B8', fontSize: 14 }}>Searching CrossRef and PubMed databases...</span>
                  </div>
                ) : esearchResults.length === 0 ? (
                  <div className="state-message"><div className="state-icon">🔍</div><p>No publications found to verify. Go to Research section first.</p></div>
                ) : (
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>#</th>
                        <th>Title</th>
                        <th>Venue</th>
                        <th>Year</th>
                        <th>DOI</th>
                        <th>CrossRef</th>
                        <th>PubMed</th>
                      </tr>
                    </thead>
                    <tbody>
                      {esearchResults.map((row, idx) => (
                        <tr key={idx}>
                          <td style={{ color: '#0EA5E9', fontWeight: 700 }}>{idx + 1}</td>
                          <td style={{ color: '#94A3B8', maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis' }}>{row.title || '—'}</td>
                          <td style={{ color: '#94A3B8' }}>{row.venue || '—'}</td>
                          <td style={{ color: '#94A3B8' }}>{row.year || '—'}</td>
                          <td style={{ color: '#64748B', fontSize: 12 }}>{row.doi || '—'}</td>
                          <td>
                            <span style={{ fontSize: 11, fontWeight: 700, padding: '4px 10px', borderRadius: 12, background: row.crossref_verified ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)', color: row.crossref_verified ? '#34D399' : '#F87171' }}>
                              {row.crossref_verified ? 'Verified' : 'Not Found'}
                            </span>
                          </td>
                          <td>
                            <span style={{ fontSize: 11, fontWeight: 700, padding: '4px 10px', borderRadius: 12, background: row.pubmed_verified ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)', color: row.pubmed_verified ? '#34D399' : '#F87171' }}>
                              {row.pubmed_verified ? 'Verified' : 'Not Found'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            ) : sectionData.length === 0 ? (
              <div className="state-message"><div className="state-icon">📭</div><p>No {activeSection} data available.</p></div>
            ) : (
              <table className="data-table" style={{ minWidth: 800 }}>
                <thead>
                  <tr>
                    <th>#</th>
                    {Object.keys(sectionData[0]).filter(k => !['id', 'candidate_id', 'verified', 'verification_detail'].includes(k)).map(f => (
                      <th key={f}>{getFieldLabel(f)}</th>
                    ))}
                    {isVerifiable ? <th>Status</th> : null}
                  </tr>
                </thead>
                <tbody>
                  {sectionData.map((row, idx) => (
                    <tr key={idx}>
                      <td style={{ color: '#0EA5E9', fontWeight: 700 }}>{idx + 1}</td>
                      {Object.keys(sectionData[0]).filter(k => !['id', 'candidate_id', 'verified', 'verification_detail'].includes(k)).map(f => (
                        <td key={f} style={{ color: '#94A3B8' }}>
                          {f === 'level' ? <span className={`level-badge ${getLevelBadge(row[f])}`}>{row[f]}</span> : row[f] || '—'}
                        </td>
                      ))}
                      {isVerifiable ? (
                        <td>
                          <span style={{ fontSize: 11, fontWeight: 700, padding: '4px 10px', borderRadius: 12, background: row.verified ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)', color: row.verified ? '#34D399' : '#F87171' }}>
                            {row.verified ? 'Verified' : 'Unverified'}
                          </span>
                          {row.verification_detail ? <div style={{ fontSize: 10, color: '#64748B', marginTop: 4, maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{row.verification_detail}</div> : null}
                        </td>
                      ) : null}
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
          {esearchResults.length > 0 ? (
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 14px', background: 'rgba(139,92,246,0.1)', border: '1px solid rgba(139,92,246,0.2)', borderRadius: 50, fontSize: 12, color: '#A78BFA', fontWeight: 600, marginTop: 16 }}>
              {esearchResults.filter(r => r.crossref_verified).length}/{esearchResults.length} Verified via eSearch
            </div>
          ) : null}
          {!showEsearch && sectionData.length > 0 ? (
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 14px', background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.2)', borderRadius: 50, fontSize: 12, color: '#34D399', fontWeight: 600, marginTop: 16 }}>
              {sectionData.length} record{sectionData.length !== 1 ? 's' : ''} found
            </div>
          ) : null}
        </div>
      </div>
    )}

      {/* Run Analysis */}
      <div style={{ margin: '0 0 24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 4 }}>
          <h3 style={{ fontSize: 20, fontWeight: 700, color: '#F8FAFC' }}>Run Analysis</h3>
          <span style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 12px', background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.2)', borderRadius: 50, fontSize: 12, color: '#34D399', fontWeight: 600 }}>
            LLM
          </span>
          {sectionScore > 0 && (
            <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: '#64748B' }}>Section Score:</span>
              <span style={{ fontSize: 20, fontWeight: 800, color: '#0EA5E9' }}>{sectionScore}/100</span>
            </div>
          )}
        </div>
        <p style={{ fontSize: 13, color: '#64748B', marginBottom: 20 }}>Feed section data to LLM for deep analysis</p>

        <div className="glass-card">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <button
              className="btn btn-primary"
              style={{ padding: '18px 24px', fontSize: 15, justifyContent: 'center', background: 'linear-gradient(135deg, #0EA5E9, #0284C7, #0369A1)', borderRadius: 14 }}
              onClick={handleRunAnalysis}
              disabled={analysisLoading}
            >
              {analysisLoading ? (
                <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}><span className="spinner" /> Analyzing...</span>
              ) : (
                <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>Run LLM Analysis</span>
              )}
            </button>
            <button
              className="btn btn-secondary"
              style={{ padding: '18px 24px', fontSize: 15, justifyContent: 'center', background: 'rgba(30,30,50,0.6)', backdropFilter: 'blur(10px)', border: '1.5px solid rgba(255,255,255,0.08)', borderRadius: 14, color: '#F59E0B' }}
              onClick={handleDraftEmail}
            >
              Draft Missing Information Email
            </button>
          </div>

          {analysis ? (
            <div style={{ marginTop: 24, padding: 30, background: 'rgba(10,10,20,0.8)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 14, textAlign: activeSection === 'overall' ? 'center' : 'left' }}>
              <h4 style={{ fontSize: 13, fontWeight: 700, color: '#38BDF8', textTransform: 'uppercase', letterSpacing: 1.5, marginBottom: 14 }}>
                {activeSection === 'overall' ? 'Final AI Hiring Recommendation' : 'AI Analysis Result'}
              </h4>
              <pre style={{ 
                fontSize: 15, 
                color: '#CBD5E1', 
                lineHeight: 2, 
                fontFamily: 'inherit', 
                whiteSpace: 'pre-wrap', 
                wordWrap: 'break-word',
                textAlign: activeSection === 'overall' ? 'center' : 'left',
                margin: activeSection === 'overall' ? '0 auto' : '0',
                maxWidth: activeSection === 'overall' ? '800px' : 'none'
              }}>{analysis}</pre>
            </div>
          ) : null}

          {emailDraft ? (
            <div style={{ marginTop: 16, padding: 20, background: 'rgba(10,10,20,0.8)', border: '1px solid rgba(245,158,11,0.3)', borderRadius: 14, borderLeft: '4px solid #F59E0B' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
                <h4 style={{ fontSize: 13, fontWeight: 700, color: '#F59E0B', textTransform: 'uppercase', letterSpacing: 1.5 }}>Draft Email</h4>
                <button 
                  onClick={copyEmail}
                  style={{ padding: '4px 12px', background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.3)', borderRadius: 6, color: '#F59E0B', fontSize: 11, cursor: 'pointer', fontWeight: 600 }}
                >
                  Copy to Clipboard
                </button>
              </div>
              <pre style={{ fontSize: 13.5, color: '#94A3B8', lineHeight: 1.9, fontFamily: 'Consolas, Monaco, monospace', whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>{emailDraft}</pre>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}