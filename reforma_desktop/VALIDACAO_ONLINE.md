# Entrada gráfica de validação online

A entrada separada está implementada para validar o cliente real em um projeto Supabase exclusivo de testes. Não é lançamento da 2.0. A versão 1.7.1, o estudo simulado e a PWA permanecem preservados.

## Abrir

Prepare antes o [perfil offline](PREPARACAO_VALIDACAO.md), indicando um projeto de teste diferente do projeto de origem. O perfil não pode ser alterado. A nova pasta de execução deve ficar fora dele e dos dados do programa em uso.

```powershell
.\.venv-estudo\Scripts\python.exe executar_validacao.py `
  --perfil "D:\Feira2026\perfil-teste-novo\perfil" `
  --pasta-execucao "D:\Feira2026\execucao-online-teste"
```

Na primeira abertura, copia somente tema, período e configuração pública. Não copia banco nem sessão de `preservados`. O banco da execução começa vazio. A pasta pode ser reaberta com o mesmo comando; perfil, configuração/projeto e vínculo do banco são conferidos antes de carregar a interface. Pasta já existente sem marca, projeto alterado, sobreposição ou links são recusados. Não use as pastas de dados da instalação 1.7.1.

O aplicativo não descobre seus projetos de produção. Cabe escolher um projeto separado e conferir a URL exibida antes do login. Não forneça sua conta de produção para este ensaio. Use somente exemplos fictícios; nenhum histórico pessoal é importado automaticamente.

## Login e envio

1. A janela de conexão exibe a URL do projeto. Digite o e-mail e a senha do aplicativo criado **nesse projeto de teste**, não as credenciais da conta administrativa do Supabase. A chave pública vem do perfil e não é um substituto para login/autorização.
2. **Verificar acesso** autentica e confere a autorização. Não transfere registros. A senha fica mascarada e o campo é limpo ao enviar; não é persistida. Somente a sessão renovável é protegida pelo DPAPI do Windows, na pasta de execução.
3. Reabrir não acessa a rede. **Retomar sessão salva** renova e verifica a autorização explicitamente. Sem essa verificação, a sessão não libera operações. Uma tentativa de novo login malsucedida mantém a sessão anterior apenas como pendente, para retomar ou desconectar.
4. Cadastre exemplos manualmente. **Conferir transferência inicial** cria cópia e compara, sem transferir. **Transferir dados conferidos** exige confirmação e mostra o projeto. Cancelar não envia; se os dados mudaram, o núcleo exige nova conferência.
5. Após a transferência, **Sincronizar agora** estabelece o vínculo. Depois disso os envios/recebimentos continuam manuais; salvar uma venda não envia automaticamente. Conflitos mantêm conferência, escolha e reconferência existentes.

Esta entrada não tem controle de simulação nem atualizador fictício. A importação/restauração de bancos é bloqueada nesta validação, para não transportar o arquivo preservado para outro projeto. O pacote e o atualizador reais continuam pendentes. Drive usa somente o conjunto separado existente do estudo se for configurado explicitamente; não foi conferido online nesta entrega.

## Projeto e SQL

O ensaio externo exige projeto de teste, usuário do aplicativo e SQL/políticas compatíveis com a aplicação. A pasta [supabase](../supabase) contém os roteiros versionados; não cole esses roteiros no projeto de produção para executar este teste. A instalação e a auditoria do projeto separado serão a próxima conferência orientada. Nenhuma conta externa ou senha foi acessada pelo agente nesta entrega.

## Testes

[Doze testes novos](tests/test_entrada_online_qt.py) exercitam o modo online com o cliente existente e TLS loopback: login sem transferência, senha limpa, cancelamento/confirmação com projeto identificado, envio manual, retomada/autorização, falhas, perfil/banco de outro projeto e ausência de controles fictícios. Dois processos novos abrem e reabrem a entrada com `--captura`, banco vazio e HTTP bloqueado. Os testes anteriores continuam preservados.

Resultados finais Linux/Windows serão registrados após a regressão. O TLS local usa o servidor fictício de contrato; não comprova o SQL, a RLS, a autorização ou concorrência do Supabase real. A matriz continua 26 I/quatro S até validar os serviços externos.

## Próxima atividade

Conferência online com o usuário em projeto separado: instalar/auditar os roteiros adequados, verificar login, migração, duas direções, conflitos/recibos e datas de compras/fechamentos. Depois permanecem conferências Windows/DPI/acessibilidade, pacote Qt e ensaio da atualização 1.7.1 → 2.0 com recuperação, antes da aprovação/publicação. PWA segue na Etapa 7.
