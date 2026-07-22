const { readEnv } = require('./env');

const EXPORTS_URL = 'https://api.canva.com/rest/v1/exports';

async function createExportJob(designId, accessToken, format) {
  const res = await fetch(EXPORTS_URL, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ design_id: designId, format }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(`Erro ${res.status} ao criar export: ${JSON.stringify(data)}`);
  return data.job;
}

async function pollExportJob(jobId, accessToken) {
  for (let i = 0; i < 30; i++) {
    const res = await fetch(`${EXPORTS_URL}/${jobId}`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    const data = await res.json();
    if (!res.ok) throw new Error(`Erro ${res.status} ao consultar export: ${JSON.stringify(data)}`);

    if (data.job.status === 'success') return data.job.urls;
    if (data.job.status === 'failed') throw new Error(`Export falhou: ${JSON.stringify(data.job)}`);

    await new Promise((r) => setTimeout(r, 2000));
  }
  throw new Error('Timeout esperando o export terminar.');
}

async function exportDesign(designId, accessToken, format = { type: 'png' }) {
  const job = await createExportJob(designId, accessToken, format);
  return pollExportJob(job.id, accessToken);
}

async function main() {
  const designId = process.argv[2];
  if (!designId) {
    console.error('Uso: node scripts/export-design.js <designId>');
    process.exit(1);
  }

  const env = readEnv();
  if (!env.CANVA_ACCESS_TOKEN) {
    console.error('CANVA_ACCESS_TOKEN vazio no .env — rode primeiro: node scripts/auth.js');
    process.exit(1);
  }

  const urls = await exportDesign(designId, env.CANVA_ACCESS_TOKEN);
  console.log(JSON.stringify(urls));
}

if (require.main === module) {
  main();
}

module.exports = { exportDesign };
