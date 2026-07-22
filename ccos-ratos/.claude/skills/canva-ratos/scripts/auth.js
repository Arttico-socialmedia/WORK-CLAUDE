const http = require('http');
const crypto = require('crypto');
const { readEnv, writeEnvUpdates } = require('./env');

const AUTHORIZE_URL = 'https://www.canva.com/api/oauth/authorize';
const TOKEN_URL = 'https://api.canva.com/rest/v1/oauth/token';
const PORT = 8080;

function base64url(buffer) {
  return buffer.toString('base64url');
}

async function main() {
  const env = readEnv();
  const clientId = env.CANVA_CLIENT_ID;
  const clientSecret = env.CANVA_CLIENT_SECRET;
  const redirectUri = env.CANVA_REDIRECT_URI || `http://127.0.0.1:${PORT}/callback`;
  const scopes = env.CANVA_SCOPES || 'folder:read design:meta:read design:content:read profile:read';

  if (!clientId || !clientSecret) {
    console.error('Faltam CANVA_CLIENT_ID / CANVA_CLIENT_SECRET no .env (copie de .env.example).');
    process.exit(1);
  }

  const codeVerifier = base64url(crypto.randomBytes(48));
  const codeChallenge = base64url(crypto.createHash('sha256').update(codeVerifier).digest());
  const state = base64url(crypto.randomBytes(16));

  const authUrl = new URL(AUTHORIZE_URL);
  authUrl.searchParams.set('code_challenge', codeChallenge);
  authUrl.searchParams.set('code_challenge_method', 'S256');
  authUrl.searchParams.set('scope', scopes);
  authUrl.searchParams.set('response_type', 'code');
  authUrl.searchParams.set('client_id', clientId);
  authUrl.searchParams.set('state', state);
  authUrl.searchParams.set('redirect_uri', redirectUri);

  console.log('\nAbra esta URL no navegador e faça login/autorize:\n');
  console.log(authUrl.toString());
  console.log(`\nAguardando callback em ${redirectUri} ...\n`);

  const server = http.createServer(async (req, res) => {
    const reqUrl = new URL(req.url, `http://127.0.0.1:${PORT}`);
    if (reqUrl.pathname !== '/callback') {
      res.writeHead(404);
      res.end();
      return;
    }

    const code = reqUrl.searchParams.get('code');
    const returnedState = reqUrl.searchParams.get('state');
    const error = reqUrl.searchParams.get('error');

    if (error) {
      res.writeHead(400, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end(`<h1>Erro na autorização</h1><p>${error}</p>`);
      console.error('Erro retornado pelo Canva:', error);
      server.close();
      process.exit(1);
    }

    if (returnedState !== state) {
      res.writeHead(400, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end('<h1>State inválido</h1>');
      console.error('State não confere — abortando por segurança.');
      server.close();
      process.exit(1);
    }

    try {
      const basicAuth = Buffer.from(`${clientId}:${clientSecret}`).toString('base64');
      const body = new URLSearchParams({
        grant_type: 'authorization_code',
        code,
        code_verifier: codeVerifier,
        redirect_uri: redirectUri,
      });

      const tokenRes = await fetch(TOKEN_URL, {
        method: 'POST',
        headers: {
          Authorization: `Basic ${basicAuth}`,
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: body.toString(),
      });

      const tokenData = await tokenRes.json();

      if (!tokenRes.ok) {
        throw new Error(`Canva retornou ${tokenRes.status}: ${JSON.stringify(tokenData)}`);
      }

      writeEnvUpdates({
        CANVA_ACCESS_TOKEN: tokenData.access_token,
        CANVA_REFRESH_TOKEN: tokenData.refresh_token,
      });

      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end('<h1>Conectado!</h1><p>Pode fechar esta aba e voltar pro terminal.</p>');

      console.log('Tokens salvos em .env (CANVA_ACCESS_TOKEN / CANVA_REFRESH_TOKEN).');
      console.log(`Access token expira em ${tokenData.expires_in}s.`);
      server.close();
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end('<h1>Erro ao trocar o código por token</h1>');
      console.error(err.message);
      server.close();
      process.exit(1);
    }
  });

  server.listen(PORT);
}

main();
