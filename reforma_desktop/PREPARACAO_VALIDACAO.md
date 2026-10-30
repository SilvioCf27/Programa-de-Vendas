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

Tema e período inicial são mantidos. Os valores originais das outras preferências ficam arquivados, mas na pasta de aplicação a sincronização e o atualizador ficam desativados, o Drive sem configuração e a sessão ausente. Não há cópia de vendas para o novo projeto. O projeto de teste deve ser diferente tanto da configuração de origem quanto do vínculo existente no banco. Uma sessão do projeto antigo não deve ser reutilizada no novo projeto. Preservar DPAPI não torna a sessão portátil: sua recuperação depende da conta/ambiente Windows que a protegeu.

O perfil é uma preparação imutável; não use `aplicacao` diretamente como pasta de dados em uso, pois arquivos novos ou preferências alteradas invalidam a conferência. A futura entrada deverá conferir o perfil e preparar uma pasta de execução separada.

O manifesto SHA-256 confere os arquivos preservados e ativos. Arquivo extra, conteúdo alterado ou preparação incompleta impedem construir o cliente. Isso detecta alteração acidental; não é criptografia nem proteção contra alguém que possa reescrever os arquivos e o próprio manifesto.

## Como preparar

Antes de preparar, confira os requisitos com **o mesmo interpretador** que executará o comando:

```powershell
.\.venv-estudo\Scripts\python.exe -c "import sys, sqlite3; print('Python:', sys.version.split()[0]); print('SQLite:', sqlite3.sqlite_version); raise SystemExit(0 if sqlite3.sqlite_version_info >= (3, 50, 2) else 1)"
```

O SQLite carregado pelo Python precisa ser **3.50.2 ou mais recente**. Python 3.11.2 com SQLite 3.39.4 não atende ao mínimo de segurança, mesmo com a pasta marcada e `vendas.db` presentes e o destino inexistente. Nesse caso, o preparador informa a versão encontrada e a mínima antes de abrir ou copiar dados. Instale um Python com SQLite compatível e recrie o ambiente virtual, se necessário; repita a conferência acima. Instalar o executável SQLite separado ou atualizar pacotes com pip não garante a atualização do SQLite carregado pelo interpretador. Não reduza o mínimo nem desative as verificações.

Feche o estudo, confirme a pasta de origem marcada e seu `vendas.db`, escolha um destino que ainda não exista e um projeto de teste separado. Não use dados pessoais nem credenciais administrativas. Essa conferência é local e não acessa Supabase ou Drive.

Exemplo com dados fictícios e um projeto separado; substitua os caminhos e a configuração pública:

```powershell
.\.venv-estudo\Scripts\python.exe preparar_validacao.py `
  --origem-estudo "D:\Feira2026\dados-estudo" `
  --destino "D:\Feira2026\perfil-teste-novo" `
  --url-projeto-teste "https://SEU-PROJETO-DE-TESTE.supabase.co" `
  --chave-publica "SUA_CHAVE_PUBLISHABLE"
```

Não use senha, chave secreta ou service_role. A ferramenta não autentica nem envia registros. Requer Python com SQLite compatível com as proteções existentes. O destino não pode existir. A origem deve ter sido criada pelo estudo; não copie seu banco pessoal para contornar essa proteção.

`cliente_preparado()` constrói o cliente existente somente após conferir o perfil. Construir não faz HTTP ou restaura sessão. **A [entrada gráfica online](VALIDACAO_ONLINE.md) agora usa uma pasta de execução separada**: este comando continua preparando somente o perfil, sem login ou envio. `executar_reforma.py` continua usando simulação.

## Verificação

Regressão local completa após a correção: **169 Qt aprovados e dois DPAPI ignorados, 200 estáveis aprovados e dois nativos ignorados, 31 protótipos aprovados; R01–R06 conformes**. [Relatórios e limites da execução](resultados/diagnostico-preparador-linux/README.md). Não aprova a integração externa nem os testes manuais Windows pendentes.

Correção do diagnóstico: [quatro testes locais](tests/test_preparar_validacao_cli.py) aprovados cobrem SQLite abaixo do mínimo (incluindo 3.39.4), limite 3.50.2 e versão superior, preservação dos arquivos e ausência do destino na recusa, falhas sanitizadas e falha de conferência sem anúncio de sucesso. No Linux com Python 3.13.16/SQLite 3.53.1, os 12 testes de perfil tiveram 11 aprovações e um ignorado por exigir DPAPI Windows; a regressão estável teve 200 aprovações e dois ignorados por exigir Windows. `git diff --check` sem erros. A versão antiga foi simulada nos testes; isso não constitui execução no Windows do usuário.

[Doze testes novos](tests/test_perfil_validacao.py) cobrem snapshot/configurações, WAL, sessão DPAPI nativa, recusa de destino existente/projeto de origem/pasta pessoal/sobreposição/links, alteração durante cópia e adulteração. Os ensaios usam somente bases e credenciais fictícias. Linux: 154 testes Qt executados, 152 aprovados e dois de DPAPI ignorados; 200 da versão estável aprovados e dois nativos ignorados; 31 dos protótipos aprovados. Sem falhas ou erros; R01–R06 conformes. [Evidências locais](resultados/perfil-linux), revisão `ee5600e`. O comando completo também foi verificado: preparação concluída e repetição no destino existente recusada, sem substituir a origem. **Windows:** 154/154 Qt, 202/202 estáveis e 31/31 protótipos aprovados, sem falhas, erros ou ignorados. Os 12 testes novos passaram, inclusive DPAPI, WAL e links. R01–R06 conformes. [Execução 40706061854](resultados/windows-40706061854), revisão `ee5600e`; resolução da VM restaurada.

## Próxima atividade

O teste online no Windows do usuário permanece **pendente**; o diagnóstico local e os testes automatizados não o aprovam.

A entrada gráfica está implementada; próxima atividade é testar em projeto separado autorizado: RLS, migração, sincronização/concorrência e PC/PWA. Continuam pendentes Drive, interação/escalas/leitor de tela, pacote Qt, atualização 1.7.1 → 2.0 e recuperação após falha. Publicar depende dessas conferências e da aprovação final.
