import type { Metadata, Viewport } from 'next';

import { Workspace } from '@/components/Workspace';
import './globals.css';

export const metadata: Metadata = {
  title: 'SYNAX AI — Multi-agent workspace',
  description:
    'A multi-agent AI workspace: a planner, specialists, a critic and a synthesizer working one request. Next.js, FastAPI, MongoDB, OpenRouter.',
  applicationName: 'SYNAX AI',
  authors: [{ name: 'SYNAX AI' }],
  keywords: [
    'multi-agent',
    'AI',
    'Next.js',
    'FastAPI',
    'MongoDB',
    'OpenRouter',
    'LLM',
  ],
  openGraph: {
    title: 'SYNAX AI',
    description: 'A multi-agent AI workspace built on Next.js, FastAPI and MongoDB.',
    type: 'website',
  },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  themeColor: '#07080c',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body>{children}</body>
    </html>
  );
}
