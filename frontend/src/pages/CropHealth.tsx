/**
 * Crop Health — ML model status and future vision service placeholder.
 * Honest about what is and isn't available yet.
 */
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import type { FieldConditionSummary } from '../types';

const FIELD_ID = 'field-north-01';

export default function CropHealth() {
  const { data: condition } = useQuery<FieldConditionSummary>({
    queryKey: ['field-condition', FIELD_ID],
    queryFn: () => api.fields.condition(FIELD_ID),
    refetchInterval: 15000,
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', maxWidth: 800 }}>
      <div>
        <h1 style={{ fontSize: 'var(--text-2xl)', marginBottom: 4 }}>Crop Health</h1>
        <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-sm)' }}>
          Sensor-based crop stress indicators and ML model status.
        </p>
      </div>

      {/* Sensor-based stress summary */}
      {condition && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          <StressGaugeCard
            title="Water Stress Level"
            severity={condition.water_stress_level}
            explanation={condition.water_stress_level !== 'none'
              ? `Soil moisture and environmental conditions indicate ${condition.water_stress_level} water stress. Timely irrigation can prevent crop damage.`
              : 'Soil moisture is adequate. No water stress detected.'}
          />
          <StressGaugeCard
            title="Heat Stress Level"
            severity={condition.heat_stress_level}
            explanation={condition.heat_stress_level !== 'none'
              ? `Temperature conditions are placing stress on the crop canopy. Combined with water stress, this can rapidly damage the crop.`
              : 'Temperature is within the acceptable range.'}
          />
        </div>
      )}



      {/* Vision service section */}
      <div className="card">
        <div style={{ fontWeight: 600, fontSize: 'var(--text-base)', marginBottom: 'var(--space-3)' }}>
          ML Vision Diagnostics
        </div>
        
        <VisionUploader />
        
      </div>
    </div>
  );
}

function VisionUploader() {
  const [file, setFile] = React.useState<File | null>(null);
  const [preview, setPreview] = React.useState<string | null>(null);
  const [isUploading, setIsUploading] = React.useState(false);
  const [result, setResult] = React.useState<any>(null);
  const [cropName, setCropName] = React.useState('green_gram');

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      setFile(selected);
      setPreview(URL.createObjectURL(selected));
      setResult(null); // Clear previous result
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setIsUploading(true);
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('crop_name', cropName);
    
    try {
      // Direct fetch to backend since this is a new endpoint
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${API_URL}/api/v1/vision/detect`, {
        method: 'POST',
        body: formData,
      });
      
      const data = await response.json();
      setResult(data);
    } catch (err) {
      console.error("Upload failed", err);
      alert("Failed to reach ML Vision service");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
      {/* Crop Selector */}
      <div style={{ display: 'flex', gap: 'var(--space-2)', marginBottom: 'var(--space-2)' }}>
        {['wheat', 'rice', 'green_gram'].map(c => (
          <button
            key={c}
            onClick={() => { setCropName(c); setResult(null); }}
            className={`btn btn-sm ${cropName === c ? 'btn-primary' : 'btn-secondary'}`}
            style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}
          >
            {c.replace('_', ' ')}
          </button>
        ))}
      </div>

      {!preview ? (
        <label style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 'var(--space-4)',
          padding: 'var(--space-8)',
          background: 'linear-gradient(145deg, var(--color-surface-2) 0%, var(--color-surface-1) 100%)',
          borderRadius: 'var(--radius-lg)',
          border: '2px dashed var(--color-brand)',
          cursor: 'pointer',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)',
          transition: 'transform 0.2s ease, box-shadow 0.2s ease',
        }}
        onMouseEnter={(e) => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = '0 12px 40px rgba(0, 0, 0, 0.15)'; }}
        onMouseLeave={(e) => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = '0 8px 32px rgba(0, 0, 0, 0.1)'; }}
        >
          <div style={{ padding: 'var(--space-4)', background: 'var(--color-brand-glow)', borderRadius: '50%', color: 'var(--color-brand)' }}>
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="17 8 12 3 7 8"></polyline>
              <line x1="12" y1="3" x2="12" y2="15"></line>
            </svg>
          </div>
          <div style={{ fontWeight: 700, color: 'var(--color-text-primary)', fontSize: 'var(--text-lg)' }}>Drop Image or Click to Upload</div>
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)', textAlign: 'center' }}>
            Upload a photo of a {cropName.replace('_', ' ')} leaf to run ML diagnostics.
          </div>
          <input type="file" accept="image/*" onChange={handleFileChange} style={{ display: 'none' }} />
        </label>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          <div style={{ display: 'flex', gap: 'var(--space-4)', alignItems: 'center', background: 'var(--color-surface-2)', padding: 'var(--space-4)', borderRadius: 'var(--radius-lg)' }}>
            <img src={preview} alt="Crop preview" style={{ width: 100, height: 100, objectFit: 'cover', borderRadius: 'var(--radius-md)', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }} />
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)', flex: 1 }}>
              <div style={{ fontWeight: 600, color: 'var(--color-text-primary)', fontSize: 'var(--text-md)' }}>{file?.name}</div>
              <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
                <button className="btn btn-primary" onClick={handleUpload} disabled={isUploading} style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
                  {isUploading ? (
                    <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                      <span className="spinner"></span> Analyzing Model...
                    </span>
                  ) : 'Run Deep Learning Analysis'}
                </button>
                <button className="btn btn-secondary" onClick={() => { setFile(null); setPreview(null); setResult(null); }} disabled={isUploading}>
                  ✕
                </button>
              </div>
            </div>
          </div>
          
          {result && (
            <div style={{
              marginTop: 'var(--space-2)', padding: 'var(--space-6)', 
              borderRadius: 'var(--radius-lg)', 
              border: `1px solid ${result.disease_detected ? 'var(--color-status-critical)' : result.status === 'training' ? 'var(--color-status-warning)' : 'var(--color-status-normal)'}`,
              background: 'linear-gradient(145deg, var(--color-surface-2) 0%, var(--color-surface-1) 100%)',
              boxShadow: '0 8px 32px rgba(0, 0, 0, 0.05)',
              animation: 'fadeIn 0.5s ease-out'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--space-4)' }}>
                <div>
                  <div style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>AI Prediction</div>
                  <div style={{ fontWeight: 800, fontSize: 'var(--text-2xl)', color: result.disease_detected ? 'var(--color-status-critical)' : result.status === 'training' ? 'var(--color-status-warning)' : 'var(--color-status-normal)' }}>
                    {result.prediction}
                  </div>
                </div>
                {result.status !== 'training' && (
                  <div className={`badge ${result.disease_detected ? 'badge-critical' : 'badge-normal'}`} style={{ fontSize: 'var(--text-lg)', padding: '8px 16px' }}>
                    {(result.confidence * 100).toFixed(1)}% Match
                  </div>
                )}
              </div>
              <div style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'flex-start', background: 'var(--color-surface-3)', padding: 'var(--space-4)', borderRadius: 'var(--radius-md)' }}>
                <span style={{ fontSize: '1.5rem' }}>💡</span>
                <div>
                  <div style={{ fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: '4px' }}>Recommendation</div>
                  <p style={{ fontSize: 'var(--text-md)', color: 'var(--color-text-secondary)', lineHeight: 1.6, margin: 0 }}>
                    {result.recommendation}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}


function StressGaugeCard({ title, severity, explanation }: { title: string, severity: string, explanation: string }) {
  const isNormal = severity === 'none' || severity === 'low';
  const color = isNormal ? 'var(--color-status-normal)' : severity === 'medium' ? 'var(--color-status-warning)' : 'var(--color-status-critical)';
  const percent = isNormal ? 15 : severity === 'medium' ? 50 : 85;

  return (
    <div className="card" style={{ display: 'flex', gap: 'var(--space-6)', alignItems: 'center', flexWrap: 'wrap' }}>
      <div style={{ flex: 1, minWidth: 250 }}>
        <h3 style={{ fontSize: 'var(--text-lg)', fontWeight: 600, marginBottom: 'var(--space-2)' }}>{title}</h3>
        <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--text-sm)', lineHeight: 1.5 }}>
          {explanation}
        </p>
      </div>
      
      {/* Visual Gauge */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', minWidth: 150, padding: 'var(--space-2)' }}>
        <div style={{ width: 120, height: 60, position: 'relative' }}>
          <svg viewBox="0 0 100 50" style={{ width: '100%', height: '100%' }}>
            <path d="M 10 50 A 40 40 0 0 1 90 50" fill="none" stroke="var(--color-surface-2)" strokeWidth="12" strokeLinecap="round" />
            <path d="M 10 50 A 40 40 0 0 1 90 50" fill="none" stroke={color} strokeWidth="12" strokeLinecap="round" strokeDasharray="125.6" strokeDashoffset={125.6 - (125.6 * percent) / 100} style={{ transition: 'stroke-dashoffset 1s ease-out' }} />
          </svg>
          <div style={{ position: 'absolute', bottom: -5, left: 0, width: '100%', textAlign: 'center', fontSize: '1.2rem', fontWeight: 700, color, letterSpacing: '0.05em' }}>
            {(severity || 'NONE').toUpperCase()}
          </div>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', width: 120, fontSize: '10px', color: 'var(--color-text-muted)', marginTop: 'var(--space-2)', fontWeight: 600 }}>
          <span>LOW</span>
          <span>HIGH</span>
        </div>
      </div>
    </div>
  );
}
