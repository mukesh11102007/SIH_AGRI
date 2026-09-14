import React, { useState, useRef } from 'react';
import type { MouseEvent, ChangeEvent } from 'react';

export interface Zone {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  crop: string;
}

interface FarmZoneMapProps {
  zones: Zone[];
  activeZoneId: string | null;
  onZonesChange: (zones: Zone[]) => void;
  onActiveZoneChange: (id: string) => void;
}

export function FarmZoneMap({ zones, activeZoneId, onZonesChange, onActiveZoneChange }: FarmZoneMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [startPoint, setStartPoint] = useState<{ x: number, y: number } | null>(null);
  const [currentRect, setCurrentRect] = useState<{ x: number, y: number, width: number, height: number } | null>(null);
  
  const [bgImage, setBgImage] = useState<string | null>(null);
  const [pendingRect, setPendingRect] = useState<{ x: number, y: number, width: number, height: number } | null>(null);
  
  const handleMouseDown = (e: MouseEvent) => {
    if (pendingRect || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    setIsDrawing(true);
    setStartPoint({ x, y });
    setCurrentRect({ x, y, width: 0, height: 0 });
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (!isDrawing || !startPoint || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const currentX = e.clientX - rect.left;
    const currentY = e.clientY - rect.top;
    
    setCurrentRect({
      x: Math.min(startPoint.x, currentX),
      y: Math.min(startPoint.y, currentY),
      width: Math.abs(currentX - startPoint.x),
      height: Math.abs(currentY - startPoint.y),
    });
  };

  const handleMouseUp = () => {
    if (!isDrawing || !currentRect) return;
    setIsDrawing(false);
    
    if (currentRect.width > 20 && currentRect.height > 20) {
      setPendingRect(currentRect);
    }
    setCurrentRect(null);
  };

  const handleFileUpload = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setBgImage(URL.createObjectURL(e.target.files[0]));
    }
  };

  const confirmZone = (crop: string) => {
    if (pendingRect) {
      const newZone = {
        id: Math.random().toString(36).substring(7),
        ...pendingRect,
        crop,
      };
      onZonesChange([...zones, newZone]);
      onActiveZoneChange(newZone.id);
    }
    setPendingRect(null);
  };

  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: 'var(--space-4)', borderBottom: '1px solid var(--color-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
         <div>
           <h2 style={{ fontSize: 'var(--text-base)', fontWeight: 600 }}>Farm Topography</h2>
           <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>Click & Drag to map a new zone</span>
         </div>
         <label className="btn btn-sm" style={{ cursor: 'pointer', background: 'var(--color-surface-2)', border: '1px solid var(--color-border)' }}>
           Upload Map Image
           <input type="file" accept="image/*" onChange={handleFileUpload} style={{ display: 'none' }} />
         </label>
      </div>
      <div 
        ref={containerRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={() => { setIsDrawing(false); setCurrentRect(null); }}
        style={{ 
          position: 'relative', 
          width: '100%', 
          height: '350px', 
          backgroundColor: bgImage ? '#000' : '#dcfce7',
          backgroundImage: bgImage ? `url(${bgImage})` : 'url("https://www.transparenttextures.com/patterns/cubes.png")',
          backgroundSize: bgImage ? 'cover' : 'auto',
          backgroundPosition: 'center',
          cursor: pendingRect ? 'default' : 'crosshair',
          userSelect: 'none'
        }}
      >
        {!bgImage && (
          <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', opacity: 0.3, fontWeight: 'bold', fontSize: '1.2rem', color: '#166534', pointerEvents: 'none' }}>
             UPLOAD A FARM IMAGE OR USE DEFAULT SATELLITE VIEW
          </div>
        )}

        {/* Draw existing zones */}
        {zones.map(zone => (
          <div 
            key={zone.id}
            onClick={(e) => { e.stopPropagation(); onActiveZoneChange(zone.id); }}
            style={{
              position: 'absolute',
              left: zone.x,
              top: zone.y,
              width: zone.width,
              height: zone.height,
              backgroundColor: activeZoneId === zone.id ? 'rgba(16, 185, 129, 0.4)' : 'rgba(255, 255, 255, 0.4)',
              border: `2px solid ${activeZoneId === zone.id ? 'var(--color-brand)' : '#94a3b8'}`,
              borderRadius: '4px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: pendingRect ? 'default' : 'pointer',
              boxShadow: activeZoneId === zone.id ? '0 0 10px rgba(16, 185, 129, 0.5)' : 'none',
              transition: 'all 0.2s'
            }}
          >
             <span style={{ background: 'rgba(0,0,0,0.6)', color: 'white', padding: '2px 8px', borderRadius: '4px', fontSize: '10px', textTransform: 'uppercase', fontWeight: 'bold' }}>
                {zone.crop}
             </span>
             {activeZoneId === zone.id && !pendingRect && (
               <button 
                 onClick={(e) => {
                   e.stopPropagation();
                   onZonesChange(zones.filter(z => z.id !== zone.id));
                   if (zones.length === 1) onActiveZoneChange(''); // Unset active if it was the last one
                 }}
                 style={{ position: 'absolute', top: -10, right: -10, background: 'var(--color-status-critical)', color: 'white', border: 'none', borderRadius: '50%', width: 20, height: 20, cursor: 'pointer', fontSize: '10px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
               >
                 ✕
               </button>
             )}
          </div>
        ))}

        {/* Draw current rect */}
        {isDrawing && currentRect && (
          <div style={{
            position: 'absolute',
            left: currentRect.x,
            top: currentRect.y,
            width: currentRect.width,
            height: currentRect.height,
            backgroundColor: 'rgba(59, 130, 246, 0.2)',
            border: '2px dashed #3b82f6',
            pointerEvents: 'none'
          }} />
        )}

        {/* Crop Selection Overlay for pending rect */}
        {pendingRect && (
          <div 
            style={{
              position: 'absolute',
              left: pendingRect.x,
              top: pendingRect.y,
              width: pendingRect.width,
              height: pendingRect.height,
              backgroundColor: 'rgba(255,255,255,0.9)',
              border: '2px solid var(--color-brand)',
              borderRadius: '4px',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 'var(--space-2)',
              zIndex: 10,
              padding: 'var(--space-2)'
            }}
            onClick={(e) => e.stopPropagation()}
            onMouseDown={(e) => e.stopPropagation()}
          >
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-primary)' }}>Select Crop</span>
            <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap', justifyContent: 'center' }}>
              {['wheat', 'rice', 'green_gram'].map(c => (
                <button
                  key={c}
                  onClick={() => confirmZone(c)}
                  style={{
                    padding: '4px 8px',
                    fontSize: '10px',
                    background: 'var(--color-brand-glow)',
                    color: 'var(--color-brand)',
                    border: '1px solid var(--color-brand)',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    textTransform: 'uppercase',
                    fontWeight: 600
                  }}
                >
                  {c.replace('_', ' ')}
                </button>
              ))}
            </div>
            <button 
              onClick={() => setPendingRect(null)}
              style={{ position: 'absolute', top: -10, right: -10, background: 'var(--color-surface-2)', border: '1px solid var(--color-border)', borderRadius: '50%', width: 20, height: 20, cursor: 'pointer', fontSize: '10px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--color-text-secondary)' }}
            >
              ✕
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
