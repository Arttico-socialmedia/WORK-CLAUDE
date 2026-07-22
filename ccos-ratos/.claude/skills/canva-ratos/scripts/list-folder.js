const { readEnv } = require('./env');

async function listFolder(folderId, accessToken) {
  const url = new URL(`https://api.canva.com/rest/v1/folders/${folderId}/items`);
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(`Erro ${res.status}: ${JSON.stringify(data)}`);
  }
  return data;
}

async function main() {
  const folderId = process.argv[2];
  if (!folderId) {
    console.error('Uso: node scripts/list-folder.js <folderId>');
    process.exit(1);
  }

  const env = readEnv();
  if (!env.CANVA_ACCESS_TOKEN) {
    console.error('CANVA_ACCESS_TOKEN vazio no .env — rode primeiro: node scripts/auth.js');
    process.exit(1);
  }

  const data = await listFolder(folderId, env.CANVA_ACCESS_TOKEN);

  for (const item of data.items) {
    if (item.type === 'folder') {
      console.log(`[folder] ${item.folder.name}  (id: ${item.folder.id})`);
    } else if (item.type === 'design') {
      console.log(`[design] ${item.design.title}  (id: ${item.design.id})`);
    } else {
      console.log(`[${item.type}]`, item);
    }
  }

  if (data.continuation) {
    console.log('\n(há mais itens — paginação com "continuation" ainda não implementada neste script)');
  }
}

main();
