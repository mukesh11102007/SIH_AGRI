/**
 * App Layout — sidebar navigation + main content area.
 * Responsive: sidebar collapses to bottom bar on mobile.
 */
import React, { useState } from 'react';
import { NavLink, Outlet, useParams } from 'react-router-dom';
import type { DataSource } from '../../types';

const NAV_ITEMS = [
  { path: '',        icon: '⊞', label: 'Dashboard' },
  { path: 'health',  icon: '◎', label: 'Crop Intelligence' },
  { path: 'history', icon: '↗', label: 'Analytics & History' },
  { path: 'alerts',  icon: '⚠', label: 'Alerts & Logs' },
  { path: 'devices', icon: '⬡', label: 'System & Devices' },
  { path: 'setup',   icon: '⚙', label: 'Settings' },
];

interface LayoutProps {
  dataSource?: DataSource;
  farmName?: string;
}

export function AppLayout({ dataSource = 'simulator', farmName = 'Demo Farm' }: LayoutProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const isSimulation = dataSource === 'simulator' || dataSource === 'no_data';

  return (
    <div style={{ display: 'flex', minHeight: '100vh', flexDirection: 'column' }}>
      {/* Top header */}
      <header style={{
        height: 'var(--header-height)',
        background: 'var(--color-surface-1)',
        borderBottom: '1px solid var(--color-border)',
        display: 'flex',
        alignItems: 'center',
        padding: '0 var(--space-6)',
        gap: 'var(--space-4)',
        position: 'sticky',
        top: 0,
        zIndex: 100,
      }}>
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', flexShrink: 0 }}>
          <span style={{ fontWeight: 'var(--font-bold)', fontSize: 'var(--text-base)', color: 'var(--color-brand)', letterSpacing: '-0.01em' }}>
            SmartFarm
          </span>
        </div>

        <div style={{ height: 20, width: 1, background: 'var(--color-border)', margin: '0 var(--space-2)' }} />

        <span style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--text-sm)', flex: 1 }}>
          {farmName}
        </span>



        {/* Mobile menu toggle */}
        <button
          className="btn btn-ghost btn-sm"
          style={{ display: 'none' }}
          id="mobile-nav-toggle"
          onClick={() => setMobileMenuOpen(o => !o)}
          aria-label="Toggle navigation"
        >
          ☰
        </button>
      </header>

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Sidebar */}
        <nav style={{
          width: 'var(--sidebar-width)',
          background: 'var(--color-surface-1)',
          borderRight: '1px solid var(--color-border)',
          padding: 'var(--space-4) 0',
          display: 'flex',
          flexDirection: 'column',
          gap: 2,
          flexShrink: 0,
          overflowY: 'auto',
        }} aria-label="Main navigation">
          {NAV_ITEMS.map(item => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === ''}
              style={({ isActive }) => ({
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-3)',
                padding: 'var(--space-2) var(--space-4)',
                color: isActive ? 'var(--color-brand)' : 'var(--color-text-secondary)',
                background: isActive ? 'var(--color-brand-glow)' : 'transparent',
                borderRight: isActive ? '2px solid var(--color-brand)' : '2px solid transparent',
                fontSize: 'var(--text-sm)',
                fontWeight: isActive ? 'var(--font-medium)' : 'var(--font-regular)',
                textDecoration: 'none',
                transition: 'all var(--transition-fast)',
                borderRadius: '0',
              })}
            >
              <span style={{ width: 16, textAlign: 'center', flexShrink: 0 }}>{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* Main content */}
        <main style={{
          flex: 1,
          overflow: 'auto',
          padding: 'var(--space-6)',
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--space-6)',
        }}>
          <Outlet />
        </main>
      </div>

      <style>{`
        @media (max-width: 768px) {
          nav[aria-label="Main navigation"] { display: none; }
          #mobile-nav-toggle { display: flex !important; }
        }
      `}</style>
    </div>
  );
}
