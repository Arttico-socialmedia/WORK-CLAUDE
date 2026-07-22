const { writeEnvUpdates } = require('./env');

const TOKEN_URL = 'https://api.canva.com/rest/v1/oauth/token';

async function refreshAccessToken(env) {
  const basicAuth = Buffer.from(`${env.CANVA_CLIENT_ID}:${env.CANVA_CLIENT_SECRET}`).toString('base64');
  const body = new URLSearchParams({
    grant_type: 'refresh_token',
    refresh_token: env.CANVA_REFRESH_TOKEN,
  });

  const res = await fetch(TOKEN_URL, {
    method: 'POST',
    headers: {
      Authorization: `Basic ${basicAuth}`,
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: body.toString(),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(`Erro ${res.status} ao renovar token: ${JSON.stringify(data)}`);

  writeEnvUpdates({
    CANVA_ACCESS_TOKEN: data.access_token,
    CANVA_REFRESH_TOKEN: data.refresh_token,
  });

  return data.access_token;
}

async function listFolderItems(folderId, accessToken, itemTypes) {
  const items = [];
  let continuation;

  do {
    const url = new URL(`https://api.canva.com/rest/v1/folders/${folderId}/items`);
    if (continuation) url.searchParams.set('continuation', continuation);
    if (itemTypes) itemTypes.forEach((t) => url.searchParams.append('item_types', t));

    const res = await fetch(url, { headers: { Authorization: `Bearer ${accessToken}` } });
    const data = await res.json();
    if (!res.ok) throw new Error(`Erro ${res.status} ao listar pasta: ${JSON.stringify(data)}`);

    items.push(...data.items);
    continuation = data.continuation;
  } while (continuation);

  return items;
}

module.exports = { refreshAccessToken, listFolderItems };
