/**
 * Server-side proxy to the FastAPI backend.
 *
 * The browser only ever talks to same-origin `/api/*`. This route forwards the
 * request to the backend, attaching the optional bearer token from the server
 * environment. Nothing secret is exposed to the client bundle.
 */

import { NextRequest, NextResponse } from 'next/server';

const API_URL = (process.env.SYNAX_API_URL ?? 'http://127.0.0.1:8000').replace(
  /\/$/,
  '',
);

const TOKEN = process.env.SYNAX_API_TOKEN ?? '';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

async function proxy(req: NextRequest, path: string[]): Promise<NextResponse> {
  // The backend serves everything under /api, so keep that prefix.
  const target = `${API_URL}/api/${path.join('/')}${req.nextUrl.search}`;

  const headers = new Headers();
  const contentType = req.headers.get('content-type');
  if (contentType) headers.set('content-type', contentType);
  if (TOKEN) headers.set('authorization', `Bearer ${TOKEN}`);

  const method = req.method.toUpperCase();
  const hasBody = !['GET', 'HEAD'].includes(method);

  let body: ArrayBuffer | undefined;
  if (hasBody) {
    body = await req.arrayBuffer();
  }

  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method,
      headers,
      body,
      cache: 'no-store',
      // @ts-expect-error duplex is required by undici for streamed bodies
      duplex: hasBody ? 'half' : undefined,
    });
  } catch {
    return NextResponse.json(
      {
        detail:
          'Cannot reach the SYNAX backend. Start it with: uvicorn app.main:app --reload --port 8000',
      },
      { status: 502 },
    );
  }

  const text = await upstream.text();
  return new NextResponse(text, {
    status: upstream.status,
    headers: {
      'content-type':
        upstream.headers.get('content-type') ?? 'application/json; charset=utf-8',
      'cache-control': 'no-store',
    },
  });
}

type Params = { params: Promise<{ path: string[] }> };

export async function GET(req: NextRequest, { params }: Params) {
  const { path } = await params;
  return proxy(req, path);
}

export async function POST(req: NextRequest, { params }: Params) {
  const { path } = await params;
  return proxy(req, path);
}

export async function PATCH(req: NextRequest, { params }: Params) {
  const { path } = await params;
  return proxy(req, path);
}

export async function PUT(req: NextRequest, { params }: Params) {
  const { path } = await params;
  return proxy(req, path);
}

export async function DELETE(req: NextRequest, { params }: Params) {
  const { path } = await params;
  return proxy(req, path);
}
