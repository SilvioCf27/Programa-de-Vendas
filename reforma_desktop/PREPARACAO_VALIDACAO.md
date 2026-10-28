# Preparação offline da validação

Esta entrega continua a Etapa 6. **Falta concluir essa etapa para lançar o desktop 2.0**: validação das integrações, conferências Windows, pacote/atualização e aprovação final. A Etapa 7 de PWA vem depois.

## Preservação e separação

[preparar_validacao.py](../preparar_validacao.py) recebe explicitamente uma pasta marcada do estudo e um destino novo. Não procura dados pessoais e recusa pastas que coincidam, contenham ou estejam dentro da pasta de dados da instalação ativa. Origem/destino não podem se sobrepor; links/junctions são recusados pelo verificador existente. Use o estudo fechado durante a preparação.

O [preparador](perfil_validacao.py) faz snapshot SQLite verificado e ensaio de recuperação. Preserva todas as tabelas, inclusive parcelas, regras e vínculos. WAL confirmado é incluído; apenas a cópia passa para journal DELETE para tornar o backup independente dos auxiliares. Configurações conhecidas são validadas, limitadas em tamanho e arquivadas byte a byte. DPAPI é preservada opaca, sem decifrar ou registrar credenciais. Se a origem mudar durante a cópia, a preparação para.

O destino contém:

```text
perfil/
  preservados/   banco e configurações originais; sessão DPAPI, se existir
  aplicacao/     tema/período e projeto de teste; sem banco ou sessão ativa
  manifesto.json
  .gestao-feira-perfil-validacao
```

Tema e período inicial são mantidos. Os valores originais das outras preferências ficam arquivados, mas na pasta de aplicação a sincronização e o atualizador ficam desativados, o Drive sem configuração e a sessão ausente. Não há cópia de vendas para o novo projeto. O projeto de teste deve ser diferente tanto da configuração de origem quanto do vínculo existente no banco. Uma sessão do projeto antigo não deve ser reutilizada no novo projeto.

O manifesto SHA-256 confere os arquivos preservados e ativos. Arquivo extra, conteúdo alterado ou preparação incompleta impedem construir o cliente. Isso detecta alteração acidental; não é criptografia nem proteção contra alguém que possa reescrever os arquivos e o próprio manifesto.

## Como preparar

Exemplo com dados fictícios e um projeto separado; substitua os caminhos e a configuração pública:

```powershell
.\.venv-estudo\Scripts\python.exe preparar_validacao.py `
  --origem-estudo "D:\Feira2026\dados-estudo" `
  --destino "D:\Feira2026\perfil-teste-novo" `
  --url-projeto-teste "https://SEU-PROJETO-DE-TESTE.supabase.co" `
  --chave-publica "SUA_CHAVE_PUBLISHABLE"
```

Não use senha, chave secreta ou service_role. A ferramenta não autentica nem envia registros. Requer Python com SQLite compatível com as proteções existentes. O destino não pode existir. A origem deve ter sido criada pelo estudo; não copie seu banco pessoal para contornar essa proteção.

`cliente_preparado()` constrói o cliente existente somente após conferir o perfil. Construir não faz HTTP ou restaura sessão. **A entrada gráfica online ainda será implementada e validada**: este comando prepara o perfil, não abre uma conexão real pronta. `executar_reforma.py` continua usando simulação.

## Verificação

[Doze testes novos](tests/test_perfil_validacao.py) cobrem snapshot/configurações, WAL, sessão DPAPI nativa, recusa de destino existente/projeto de origem/pasta pessoal/sobreposição/links, alteração durante cópia e adulteração. Os ensaios usam somente bases e credenciais fictícias. Regressão completa Linux/Windows em andamento.

## Próxima atividade

Implementar a entrada gráfica de validação com login/configuração reais e identificação clara do projeto, sem controles fictícios. Depois, testar em projeto separado autorizado: RLS, migração, sincronização/concorrência e PC/PWA. Continuam pendentes Drive, interação/escalas/leitor de tela, pacote Qt, atualização 1.7.1 → 2.0 e recuperação após falha. Publicar depende dessas conferências e da aprovação final.
