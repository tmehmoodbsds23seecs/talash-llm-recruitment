import axios from 'axios';

const API_BASE = '/api';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 180000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const uploadCV = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const listCandidates = async () => {
  const response = await api.get('/candidates');
  return response.data;
};

export const getCandidate = async (id: number) => {
  const response = await api.get(`/candidates/${id}`);
  return response.data;
};

export const loadSectionFacts = async (candidateId: number, section: string) => {
  const response = await api.get(`/candidates/${candidateId}/section/${section}`);
  return response.data;
};

export const runAnalysis = async (candidateId: number, section: string) => {
  console.log(`[API] Running analysis for candidate ${candidateId}, section: ${section}`);
  const response = await api.post(`/candidates/${candidateId}/analyze/${section}`);
  console.log(`[API] Analysis response:`, response.data);
  return response.data;
};

export const getAnalysis = async (candidateId: number, section: string) => {
  const response = await api.get(`/candidates/${candidateId}/analysis/${section}`);
  return response.data;
};

export const draftEmail = async (candidateId: number, missingFields: object) => {
  const response = await api.post(`/candidates/${candidateId}/email-draft`, { missing_fields: missingFields });
  return response.data;
};

export const deleteCandidate = async (id: number) => {
  const response = await api.delete(`/candidates/${id}`);
  return response.data;
};

export const verifySection = async (candidateId: number, section: string) => {
  const response = await api.post(`/candidates/${candidateId}/verify/${section}`);
  return response.data;
};

export const searchPublications = async (candidateId: number) => {
  const response = await api.post(`/candidates/${candidateId}/esearch`);
  return response.data;
};

export const getOverallScore = async (candidateId: number) => {
  const response = await api.get(`/candidates/${candidateId}/score`);
  return response.data;
};