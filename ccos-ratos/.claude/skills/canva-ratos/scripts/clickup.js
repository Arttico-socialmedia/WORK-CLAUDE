const CLICKUP_API = 'https://api.clickup.com/api/v2';

async function createTask(apiToken, listId, name, markdownDescription) {
  const res = await fetch(`${CLICKUP_API}/list/${listId}/task`, {
    method: 'POST',
    headers: {
      Authorization: apiToken,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ name, markdown_content: markdownDescription }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(`Erro ${res.status} ao criar task: ${JSON.stringify(data)}`);
  return data;
}

async function attachFile(apiToken, taskId, buffer, fileName) {
  const form = new FormData();
  form.append('attachment', new Blob([buffer]), fileName);

  const res = await fetch(`${CLICKUP_API}/task/${taskId}/attachment`, {
    method: 'POST',
    headers: { Authorization: apiToken },
    body: form,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(`Erro ${res.status} ao anexar arquivo: ${JSON.stringify(data)}`);
  return data;
}

module.exports = { createTask, attachFile };
