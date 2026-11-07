# Exportação financeira para conferência

Implementação de 07/11/2026, somente PWA. Adiciona JSON versionado (`gestao-da-feira-financas`, versão 1) e CSV UTF-8 com BOM/separador ponto e vírgula. A geração usa o snapshot financeiro completo já recebido pelo cliente, sem solicitar permissões extras ou executar gravações.

Escopos: histórico financeiro completo (padrão) ou período/meio da consulta aplicada. Busca visual e campos ainda não aplicados são ignorados. A seleção por período usa fatura/pagamento e preserva compras originais, sem reatribuir datas. Ajustes anuais sobrepostos ao recorte são exportados com sua cobertura inteira e identificados separadamente; totais de registros não devem ser tratados como deduções adicionais no saldo. Grupos podem estar incompletos no recorte.

Lista explícita de campos exportados: IDs de registros, tipo, datas de compra/fatura, descrição, centavos, meio, categoria, grupo/parcelas e versão; ano/cobertura/natureza/observação dos ajustes anuais. O código não serializa o objeto de sessão, configurações, `user_id` nem campos extras recebidos da API. Metadados guardam escopo e horários de consulta/geração; o JSON não é backup completo nem formato de restauração. Valores monetários do JSON permanecem em centavos inteiros. CSV conserva identificação e protege células textuais iniciadas como fórmulas, incluindo espaços, aspas e quebras de linha.

Sem consulta concluída ou com envio pendente, a exportação é bloqueada. Ao sair da conta, snapshot, seleção e horário de consulta são limpos e os botões desativados. Uma consulta posterior que falhe não altera o horário do snapshot anterior. Exportar não escreve em Supabase/SQLite/Drive nem envia o arquivo para terceiros. Não foi implementada edição por chave temporária nem importação de correções.

Validação: 74 testes de regras/dados e 32 cenários de navegador aprovados, sem falhas ou ignorados; build de revisão aprovado. Quatro testes novos de unidade verificam projeção por campos permitidos, fidelidade/isolamento do snapshot, parcelas/centavos/anuais, recorte por período/meio, CSV protegido e ausência de snapshot/escopo inválido. O navegador baixa e lê ambos os formatos, confronta conteúdo, ignora busca/filtro pendente e verifica bloqueio ao sair. APIs e dados de teste fictícios; não houve acesso ao banco real do usuário ou a seu extrato.

[Captura da exportação](imagens/exportacao-financeira.png). Cache da interface v11. O desktop e os arquivos de dados existentes não foram modificados nesta entrega.
