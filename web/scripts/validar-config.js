import { loadEnv } from 'vite';
import { validarConfig } from '../src/config.js';
const env = loadEnv('production', process.cwd(), 'VITE_');
const configurado = validarConfig(
  env.VITE_SUPABASE_URL,
  env.VITE_SUPABASE_ANON_KEY
);
if (process.env.EXIGIR_CONFIG_WEB === '1' && !configurado)
  throw Error('Configure o projeto antes de publicar.');
console.log(
  configurado
    ? 'Configuração pública válida.'
    : 'Build de revisão, sem conexão com dados. Não publicar como aplicativo pronto.'
);
