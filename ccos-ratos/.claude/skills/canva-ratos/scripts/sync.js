const { readEnv } = require('./env');
const { refreshAccessToken, listFolderItems } = require('./canva');
const { exportDesign } = require('./export-design');
const { createTask, attachFile } = require('./clickup');
const { readState, writeState } = require('./state');

const BRANDS = [
  { key: 'CANVA_FOLDER_ARTTICO', label: 'ARTTICO' },
  { key: 'CANVA_FOLDER_TASTTO', label: 'TASTTO' },
];

async function downloadBuffer(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Erro ${res.status} ao baixar arquivo exportado.`);
  return Buffer.from(await res.arrayBuffer());
}

async function main() {
  let env = readEnv();

  if (!env.CANVA_CLIENT_ID || !env.CLICKUP_API_TOKEN || !env.CLICKUP_LIST_ID) {
    console.error('Faltam variáveis no .env (Canva client/secret ou ClickUp token/list).');
    process.exit(1);
  }

  console.log('Renovando token do Canva...');
  const accessToken = await refreshAccessToken(env);
  env = readEnv();

  const state = readState();
  let totalNovos = 0;

  for (const brand of BRANDS) {
    const folderId = env[brand.key];
    if (!folderId) {
      console.warn(`Aviso: ${brand.key} não definido no .env, pulando ${brand.label}.`);
      continue;
    }

    console.log(`\nVerificando pasta ${brand.label} (${folderId})...`);
    const items = await listFolderItems(folderId, accessToken, ['design']);
    const designs = items.filter((i) => i.type === 'design').map((i) => i.design);

    const novos = designs.filter((d) => !state[d.id]);
    console.log(`  ${designs.length} designs na pasta, ${novos.length} novo(s).`);

    for (const design of novos) {
      console.log(`  Exportando "${design.title}" (${design.id})...`);
      const urls = await exportDesign(design.id, accessToken, { type: 'png' });

      const task = await createTask(
        env.CLICKUP_API_TOKEN,
        env.CLICKUP_LIST_ID,
        `[${brand.label}] ${design.title}`,
        `Design puxado automaticamente da pasta **Posts ${brand.label === 'ARTTICO' ? 'Arttico' : 'Tastto'}** no Canva (via canva-ratos, sync automático).\n\nCanva design ID: \`${design.id}\``
      );

      for (let i = 0; i < urls.length; i++) {
        const buffer = await downloadBuffer(urls[i]);
        const suffix = urls.length > 1 ? `-${i + 1}` : '';
        await attachFile(env.CLICKUP_API_TOKEN, task.id, buffer, `${design.title}${suffix}.png`);
      }

      state[design.id] = {
        brand: brand.label,
        title: design.title,
        task_id: task.id,
        task_url: task.url,
        synced_at: new Date(design.updated_at * 1000).toISOString(),
      };
      writeState(state);
      totalNovos++;
      console.log(`  -> Task criada: ${task.url}`);
    }
  }

  console.log(`\nSincronização concluída. ${totalNovos} design(s) novo(s) enviado(s).`);
}

main().catch((err) => {
  console.error('Erro na sincronização:', err.message);
  process.exit(1);
});
