import type { NextApiRequest, NextApiResponse } from "next";

const targetBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const path = Array.isArray(req.query.path) ? req.query.path.join("/") : String(req.query.path || "");
  const url = `${targetBase.replace(/\/$/, "")}/${path}`;

  const headers: HeadersInit = {};
  for (const [k, v] of Object.entries(req.headers)) {
    if (v === undefined) continue;
    // Pass through auth and content headers; omit host and connection specific ones
    const key = k.toLowerCase();
    if (["host", "connection", "content-length"].includes(key)) continue;
    headers[key] = Array.isArray(v) ? v.join(",") : v;
  }

  const init: RequestInit = {
    method: req.method,
    headers,
    // For GET/HEAD, body must be undefined
    body: req.method && ["GET", "HEAD"].includes(req.method) ? undefined : (req as any),
  };

  try {
    const response = await fetch(url, init as any);
    const contentType = response.headers.get("content-type") || "application/octet-stream";
    res.status(response.status);
    if (contentType.includes("application/json")) {
      const json = await response.json();
      res.setHeader("content-type", "application/json");
      res.send(json);
    } else {
      const buffer = Buffer.from(await response.arrayBuffer());
      res.setHeader("content-type", contentType);
      res.send(buffer);
    }
  } catch (err: any) {
    res.status(502).json({ detail: `Proxy error: ${err?.message || String(err)}` });
  }
}

export const config = {
  api: {
    bodyParser: false,
    responseLimit: false,
  },
};


