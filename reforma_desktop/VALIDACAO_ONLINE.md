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

## Projeto de teste recém-criado — preparação guiada

O usuário informou em 28/10/2026 que criou um projeto separado. A conferência externa ainda não foi executada pelo agente. No dashboard, confirme o **projeto de teste** antes de cada operação:

1. Em **Authentication → Users → Add user → Create new user**, crie o usuário do aplicativo de teste e confirme o e-mail nessa tela, se a opção estiver disponível. Pode usar o mesmo e-mail em projetos diferentes; a senha é a definida neste projeto. Não envie senhas.
2. No **SQL Editor desse projeto**, execute separadamente, na ordem, os arquivos `001_vendas.sql` a `006_datas_compras.sql` de [supabase/migrations](../supabase/migrations). Aguarde sucesso de cada arquivo. Se houver erro, interrompa e envie a mensagem antes de continuar. Não execute no projeto em uso pelo programa 1.7.1.
3. Autorize somente o usuário de teste. No bloco abaixo, troque `SEU_EMAIL_DE_TESTE` pelo e-mail criado. O bloco recusa trocar um proprietário já configurado; não desativa RLS ou altera vendas.

```sql
do $$
declare
    usuario uuid;
begin
    select id into strict usuario
    from auth.users
    where lower(email) = lower('SEU_EMAIL_DE_TESTE');

    if exists (select 1 from private.app_config where singleton and owner_id <> usuario) then
        raise exception 'Já existe outro proprietário. Nada foi alterado.';
    end if;

    insert into private.app_config(singleton, owner_id)
    values (true, usuario)
    on conflict (singleton) do nothing;
end $$;
```

4. Execute os blocos de [auditoria somente leitura](../supabase/auditoria_somente_leitura.sql) nesse mesmo projeto. Envie apenas os resultados de permissões/políticas, sem senhas, tokens ou chaves. A validação precisa conferir o servidor real antes de considerar RLS aprovada.
5. A URL HTTPS e a chave **Publishable/anon** desse projeto são usadas localmente no preparador de perfil; não use secret/service_role. Após preparar e abrir a entrada separada, valide primeiro o login, sem vendas reais. Os exemplos e envios serão conferidos na sequência.

Criar o projeto não atualiza o PWA nem muda o projeto de produção. A conferência PC/PWA exigirá posteriormente uma instância web de testes configurada para esse projeto; não trocar a configuração do site em uso.
