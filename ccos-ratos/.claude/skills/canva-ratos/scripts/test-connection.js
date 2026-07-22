const { readEnv } = require('./env');

async function main() {
  const env = readEnv();
  if (!env.CANVA_ACCESS_TOKEN) {
    console.error('CANVA_ACCESS_TOKEN vazio no .env — rode primeiro: node scripts/auth.js');
    process.exit(1);
  }

  const res = await fetch('https://api.canva.com/rest/v1/users/me', {
    headers: { Authorization: `Bearer ${env.CANVA_ACCESS_TOKEN}` },
  });

  const data = await res.json();

  if (!res.ok) {
    console.error(`Erro ${res.status}:`, data);
    process.exit(1);
  }

  console.log('Conectado com sucesso ao Canva:');
  console.log(data);
}

main();
