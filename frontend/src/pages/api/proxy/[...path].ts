import type { NextApiRequest, NextApiResponse } from "next";

const targetBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function readRequestBody(req: NextApiRequest): Promise<Buffer> {
  const chunks: Uint8Array[] = [];
  return await new Promise((resolve, reject) => {
    req.on("data", (chunk) => chunks.push(chunk));
    req.on("end", () => resolve(Buffer.concat(chunks)));
    req.on("error", (err) => reject(err));
  });
}

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const after = (req.url || "").split("/api/proxy/")[1] || "";
  const originalPath = after.split("?")[0];
  const queryPath = Array.isArray((req as any).query?.path) ? (req as any).query.path.join("/") : String((req as any).query?.path || "");
  let path = (originalPath || queryPath).replace(/^\//, "");
  // Preserve trailing slash for collection endpoints (prevents 308 on POST)
  const needsSlash = /^(api\/v1\/)?(employees|auth|client\/metrics|metrics)(\/)?$/.test(path);
  if (needsSlash && !path.endsWith("/")) path = `${path}/`;
  const queryString = (req.url || "").split("?")[1];
  const target = `${targetBase.replace(/\/$/, "")}/${path}${queryString ? `?${queryString}` : ""}`;

  const headers: Record<string, string> = {};
  for (const [k, v] of Object.entries(req.headers)) {
    if (v === undefined) continue;
    const key = k.toLowerCase();
    if (["host", "connection", "content-length"].includes(key)) continue;
    headers[key] = Array.isArray(v) ? v.join(",") : String(v);
  }

  const isBodyless = req.method ? ["GET", "HEAD"].includes(req.method) : true;
  const init: any = { method: req.method, headers, redirect: "manual" };

  try {
    if (!isBodyless) {
      const bodyBuf = await readRequestBody(req);
      if (bodyBuf.length > 0) {
        init.body = bodyBuf;
        init.headers["content-length"] = String(bodyBuf.length);
      } else {
        init.body = undefined;
      }
    }

    let url = target;
    for (let i = 0; i < 3; i++) {
      const response = await fetch(url, init);
      if ([301, 302, 303, 307, 308].includes(response.status)) {
        const loc = response.headers.get("location");
        if (loc) {
          url = loc.startsWith("http") ? loc : `${targetBase.replace(/\/$/, "")}${loc.startsWith("/") ? loc : `/${loc}`}`;
          if (response.status === 303) {
            init.method = "GET";
            delete init.body;
          }
          continue;
        }
      }
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
      return;
    }
    res.status(502).json({ detail: "Proxy error: redirect loop" });
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


