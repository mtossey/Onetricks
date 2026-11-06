// Password gate for the Cloudflare Pages prototype.
//
// Cloudflare Pages runs this before every request (that is what a file named
// _middleware in functions/ does), so no page, data file or image is served
// without the username and password. The champion data includes Riot IDs, and
// Riot's policy says development key projects are prototypes for review, not
// public sites, so the whole site stays behind the login until it is approved.
//
// The username and password are Cloudflare secrets (BASIC_AUTH_USER and
// BASIC_AUTH_PASSWORD), set with "npx wrangler pages secret put", never in the repo.

const REALM = "lolmains prototype";

async function sha256(text) {
  return new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text)));
}

function askForLogin() {
  return new Response("Password required.", {
    status: 401,
    headers: { "WWW-Authenticate": `Basic realm="${REALM}", charset="UTF-8"`, "X-Robots-Tag": "noindex, nofollow" },
  });
}

export async function onRequest({ request, env, next }) {
  const user = env.BASIC_AUTH_USER;
  const password = env.BASIC_AUTH_PASSWORD;
  // Fail closed: if the secrets are missing, serve nothing rather than everything
  if (!user || !password) return new Response("Site is not configured yet.", { status: 503 });

  // The browser sends "Basic " + base64("username:password")
  const header = request.headers.get("Authorization") ?? "";
  if (!header.startsWith("Basic ")) return askForLogin();
  let given = "";
  try {
    given = atob(header.slice("Basic ".length));
  } catch {
    return askForLogin();
  }

  // Compare hashes of equal length in constant time, so the response time
  // does not reveal how much of a guess was right
  const [a, b] = await Promise.all([sha256(given), sha256(`${user}:${password}`)]);
  if (!crypto.subtle.timingSafeEqual(a, b)) return askForLogin();

  // Logged in: serve the file, marked so search engines never index it
  const response = await next();
  const marked = new Response(response.body, response);
  marked.headers.set("X-Robots-Tag", "noindex, nofollow");
  return marked;
}
