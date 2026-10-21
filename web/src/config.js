export function validarConfig(url, chave) {
  if (!url && !chave) return false;
  if (!url || !chave) throw Error('Preencha a URL e a chave pública juntas.');
  if (!/^https:\/\/[a-z0-9-]+\.supabase\.co\/?$/.test(url))
    throw Error('Use a URL HTTPS do projeto Supabase.');
  if (chave.startsWith('sb_secret_'))
    throw Error(
      'Chave secreta não pode entrar no aplicativo. Use a chave publishable ou anon.'
    );
  if (chave.startsWith('sb_publishable_')) return true;
  try {
    const parte = chave.split('.')[1].replaceAll('-', '+').replaceAll('_', '/');
    const dados = JSON.parse(atob(parte));
    if (dados.role === 'anon') return true;
  } catch {
    /* Uma chave malformada também é recusada. */
  }
  throw Error(
    'Use apenas a chave pública publishable ou a anon key. Nunca use service_role.'
  );
}
