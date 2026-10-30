# Candidata do desktop 2.0

Esta implementação prepara o pacote Qt e sua atualização pelo programa. O executável 1.7.1 e a PWA permanecem separados. A existência deste documento ou da versão no código não significa que a release foi publicada.

## Dados e configuração

A entrada `executar_desktop.py` usa a mesma localização de dados do aplicativo: `%LOCALAPPDATA%\ProgramFeira` no Windows, ou `PROGRAMFEIRA_DATA_DIR` quando explicitamente definido. Não busca dados em outras pastas nem cria exemplos. Antes de inicializar o banco existente, preserva um backup verificado. Requer SQLite ≥ 3.50.2. Tema, período inicial, finanças, vínculo da nuvem, preferências de sincronização, configuração de backup e sessão DPAPI permanecem nessa pasta.

Em Configurações → Conexão com a nuvem, o cliente lê o projeto existente. Na ausência de configuração, as funções locais continuam disponíveis; configure apenas URL e chave pública Publishable/anon, nunca chave administrativa. Um banco vinculado não pode trocar de projeto por essa tela. Login verifica autorização; nenhuma transferência inicial acontece sem conferência e confirmação. A preferência de sincronização automática continua sendo respeitada, após verificar a sessão e o vínculo. O estudo e a entrada de validação mantêm seus modos anteriores.

O adaptador de Drive da entrada de produção usa a configuração existente. Nenhuma conta externa ou pasta pessoal foi acessada para desenvolver esta entrega. Os ensaios usam somente diretórios temporários e serviços fictícios.

## Empacotamento e ensaio automático

No Windows x64, com Python 3.13 e SQLite compatível:

```powershell
python -m pip install -r requirements-build.txt -r prototipos/reforma/requirements.txt
python tools/gerar_desktop_qt.py
```

`GestaoDaFeiraQt.spec` usa a entrada Qt e inclui os recursos, fontes e plugins do PySide6. O build produz `dist-qt/GestaoDaFeira-Windows-x64.zip`, `SHA256.txt` e `VALIDACAO_WINDOWS.json`. O binário real é executado com `--verificar-pacote` e dados temporários antes de gerar o ZIP. O formato e os limites de tamanho continuam compatíveis com o atualizador 1.7.1.

O workflow **Desktop 2 - Pacote e transicao Windows** compila também a referência `v1.7.1` sem modificá-la e executa:

```powershell
python tools/testar_transicao_qt_windows.py --pacote-171 baseline-171/dist/GestaoDaFeira-Windows-x64.zip --pacote-qt dist-qt/GestaoDaFeira-Windows-x64.zip --saida dist-qt/VALIDACAO_ATUALIZADOR.json
```

Esse ensaio abre o binário 1.7.1, confere a candidata Qt, cria backup, troca pastas, verifica o recibo 2.0 e compara todas as tabelas e arquivos de configuração fictícios. Outra execução provoca falha de abertura após o smoke e exige recuperar e reabrir a 1.7.1. Nenhum download ou Supabase real é usado pelo ensaio da troca. Um blob opaco sem projeto configurado é preservado byte a byte; DPAPI nativa é coberta separadamente pelos testes Windows.

O workflow guarda artefatos e registra os JSONs em uma branch separada `evidencias/desktop-2-<execução>`, inclusive quando a execução falha. Não escreve na main. Pushes da branch geram somente a candidata; uma tag `v2.x` dispara novamente todas as verificações e só publica a release estável se elas passarem e a tag corresponder à versão do pacote. Confira a execução/revisão e `sucesso` dos relatórios; uma branch de evidências de falha não aprova o pacote.

## Como a atualização chegará à interface

O atualizador instalado na 1.7.1 consulta a **release estável mais recente**, não branches, commits ou artefatos do Actions. Somente após o pacote Windows e o ensaio de transição aprovados poderá ser disponibilizada a release estável `v2.0.0`, com os quatro arquivos de distribuição e os respectivos relatórios da mesma execução. Uma prerelease ou rascunho não será oferecida pela interface atual.

Após a publicação efetiva, o usuário poderá abrir 1.7.1 → Configurações → Atualizações → verificar, baixar/conferir e confirmar instalação. O auxiliar existente preserva a pasta anterior e recupera a instalação se não receber o recibo de abertura. Os dados permanecem fora da pasta do aplicativo.

`tools/publicar_desktop_qt.py --pasta <dist-qt> --evidencias <evidencias-qt> --commit <SHA-completo>` confere hashes, versão, revisão, regressão Windows, troca e rollback sem publicar. `--criar-rascunho` cria somente um rascunho; `--publicar` disponibiliza a release estável. Não use relatórios Linux nesses comandos. A publicação depende de acesso à API do GitHub; as tags 2.x não acionam o antigo empacotamento Tkinter.

## Pendências explícitas

Os testes manuais Windows foram adiados pelo usuário. Auth/SQL/RLS, PC/PWA e Drive reais continuam sem aprovação; não foram acessados nem reconfigurados. A publicação da release e o ensaio automático Windows precisam de evidências próprias; validação Linux não os substitui. Não há aprovação automática da Etapa 6 nem lançamento apenas por incrementar a versão.
