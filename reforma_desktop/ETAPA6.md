# Etapa 6 — Revisão e validação para produção

A etapa começou após a medição de fluidez. Esta entrega valida o contrato entre Qt e o cliente HTTPS existente e prepara a troca de adaptadores. **Ainda não é a versão 2.0 nem conclusão da Etapa 6.** A instalação 1.7.1, seus dados e a PWA continuam preservados.

## O que mudou

[Janela](aplicacao.py) e [Conexao](conexao_nuvem.py) aceitam um cliente fornecido explicitamente pelo construtor. Sem esse parâmetro, usam exatamente o serviço fictício anterior. A entrada de estudo não ganhou configuração para conexão real e não lê as configurações pessoais.

A sessão estava vinculada à URL fixa do serviço simulado. Salvar e recuperar agora usam `cliente.url`. Isso permite testar o cliente existente e evita persistir a sessão sob o projeto errado na futura integração. Formato, DPAPI, pasta isolada e regra de não gravar senha/token de acesso foram preservados.

## Contrato HTTPS exercitado

[Quinze testes](tests/test_contrato_https_qt.py) instanciam `ProgramFeira.nuvem.ClienteNuvem` sem sobrescrever `_post`. Chamadas passam por JSON, urllib, cabeçalhos, TLS, tratamento de erros e trabalhadores Qt até um [servidor de teste](tests/servidor_https.py). O estado remoto é fictício; não é implementação do Supabase nem substitui validação do SQL.

O servidor escuta somente `127.0.0.1` em porta aleatória. O socket do hostname fictício é roteado para ele e qualquer outra saída falha. Certificado e hostname são verificados; redirecionamentos continuam bloqueados pelo handler do núcleo. O certificado/chave publicados são [recursos exclusivos dos testes](tests/recursos/README.md), confiados somente pelo opener do ensaio. Há contraprova sem essa confiança: TLS falha antes de enviar credenciais HTTP. Um controle negativo remove deliberadamente o handler de redirect apenas num cliente do teste: a tentativa proibida é detectada e recusada pela guarda de saída. Isso impede que a guarda esconda uma eventual regressão do bloqueio de redirects. Nada é instalado na confiança do Windows ou do aplicativo.

| Cenário | Resultado exigido |
| --- | --- |
| Conta não autorizada | Sem sessão e sem transferência. |
| Envio/recebimento | Registros e centavos corretos, backup e filtros pendentes preservados. |
| Sessão expirada | Renovação pelo projeto correto; 401 pausa antes de enviar lote. |
| Reabertura no Windows | DPAPI real recupera sessão e renova sem novo login; apenas pasta fictícia. |
| Resposta perdida depois de gravar | Mesmo recibo é reenviado, sem duplicar registros. |
| HTTP 503, JSON inválido e redirect | Dados locais preservados, UI liberada e nenhuma mensagem bruta/credencial exibida. Redirect não recebe outra chamada. |
| PFS01 / conflitos | Pausa; versão local preservada; revisão antiga recusada; aplicação só após escolha explícita/reconferência. |
| SQL006 ausente | Sem fallback que descarte a data original da compra. |
| Fechamento | Versão concorrente recusada, períodos antigos e parcelas existentes preservados. |
| Consulta demorada | Eventos Qt continuam; formulário aberto adia a aplicação automática. |
| Abertura normal do estudo | Cliente fictício e nenhuma requisição HTTPS. |

Na primeira rodada do instrumento, duas expectativas dos testes precisaram de correção: o núcleo reutiliza uma sessão mais nova já em memória e consulta o fechamento antes do snapshot. Para exercitar renovação foi necessário expirar também essa referência; para conferir requisições, contar ambos os RPCs. Isso não foi defeito do produto nem motivo para mudar suas regras.

## Resultados

Linux: **142 testes Qt executados, 141 aprovados e um ignorado por exigir DPAPI do Windows**. A suíte estável teve **200 aprovados e dois nativos ignorados**, e os protótipos **31/31 aprovados**. As seis verificações da revisão anterior continuam conformes. Sem falhas ou erros. [Evidências locais](resultados/etapa6-linux), revisão `f964cdb`.

Windows nativo: **142/142 Qt, 202/202 estável e 31/31 protótipos aprovados**, sem falhas, erros ou ignorados. Os **15 testes novos** passaram, incluindo DPAPI real, renovação sem novo login e o controle negativo de redirect. As seis verificações R01–R06 continuam conformes. [Evidências da execução 40686915587](resultados/windows-40686915587), revisão `f964cdb`; Python 3.13.16, SQLite 3.50.4 e Qt 6.10.2. A resolução da VM foi restaurada.

A primeira regressão nativa (`e3a6005`, execução 40686463631) também passou: 141 Qt, 202 estável e 31 protótipos. A rodada final acrescentou somente o controle negativo do transporte e documentação; o código da aplicação é o mesmo. Os JSONs finais ficam ligados acima; não houve publicação de executável.

Para reproduzir, com as dependências do estudo e SQLite compatível:

```powershell
.\.venv-estudo\Scripts\python.exe -m unittest discover -s reforma_desktop/tests -p test_contrato_https_qt.py -v
.\.venv-estudo\Scripts\python.exe reforma_desktop/validar.py --saida validacao-qt.json
```

O servidor e as bases são criados/removidos pela suíte, sem conta ou banco existente. Qt offscreen comprova caminhos automatizados, não interação manual nem leitor de tela.

## Pendências antes de publicar

A matriz preserva **26 I e quatro S**. O contrato HTTPS amplia a cobertura de F09/G04/G05; a comprovação do serviço externo permanece aberta. G06 continua como ensaio de atualizador. As etapas seguintes são:

1. Preservação de preferências/configuração/sessão e entrada separada de validação com adaptadores reais e guardas de projeto/pasta. Não copiar dados pessoais automaticamente.
2. Ensaio online autorizado, em projeto separado: migração, autorização/RLS, renovação, concorrência/recibos, duas direções e PC/PWA. O modelo do teste local não prova esses comportamentos do servidor real.
3. Drive/restauro/encerramento controlados; janelas menores, escalas reais 100/125/150%, temas, teclado, leitor de tela e textos.
4. Pacote Qt Windows e protocolo de inicialização/recibo; ensaio 1.7.1 → 2.0 com preservação de dados/configuração/sessão e recuperação após falha.
5. Conferência do usuário, notas e publicação aprovada. A PWA continua na Etapa 7.

O primeiro item avançou com a [preservação offline e preparação do perfil](PREPARACAO_VALIDACAO.md). A próxima atividade é ligar a entrada gráfica de validação aos adaptadores reais; a preparação não habilita conexão online por si só. Não houve acesso às suas contas, alteração de política SQL ou publicação de executável nesta entrega.
