"""Explicações dos dados e cálculos, acessíveis por clique ou teclado."""
import tkinter as tk
from tkinter import ttk, font
from ProgramFeira.interface.visual import CORES

AJUDAS = {
    'financas': ('Finanças e períodos', 'Esta aba tem consulta e indicadores próprios, independentes de Vendas. Os cartões de Vendas ficam ocultos enquanto Finanças está aberta. Semana vai de segunda a domingo. Mês é o mês civil. Escolha mês e ano para o fechamento; ele segue a regra vigente em cada mês. Na regra inicial, outubro = 10/10 a 09/11. Ano vai de 01/01 a 31/12.\n\nOs resultados usam todos os lançamentos do período, inclusive futuros. Não há integração com bancos. Exportações de Vendas continuam sendo valores brutos; ainda não exportam despesas.'),
    'taxas': ('Taxas do cartão', 'As vendas originais permanecem brutas. Vendas menos taxas = dinheiro + Pix + cartão menos as taxas informadas. Não é uma consulta ao saldo bancário nem considera prazos de recebimento.\n\nEm Taxas da maquininha, escolha uma semana e preencha os descontos em reais nas vendas de cada dia. Sexta e domingo podem ser salvos juntos. Totais históricos anuais servem apenas para valores antigos consolidados, com cobertura definida. Não é permitido sobrepor taxas diárias e anuais. Um ajuste anual só é descontado quando sua cobertura inteira cabe na consulta. Em recortes menores, o saldo é provisório e o ajuste não é rateado. Taxa não cadastrada não significa taxa zero. Atualize o total acumulado do ano em andamento, sem somar novamente o que já estava incluído.'),
    'despesas': ('Despesas e organização semanal', 'Registre despesas pessoais e da feira, com categorias opcionais. A semana organiza os registros por segunda-feira; na primeira ou última semana do recorte, o total inclui apenas os dias dentro da consulta.\n\nDinheiro e Pix: data do pagamento. Cartão de crédito: data da fatura (competência) correspondente. Ela é diferente da data da compra e do prazo limite de pagamento. O botão de cálculo usa a compra para sugerir a primeira fatura; compras feitas no próprio fechamento entram no próximo. A data não muda só por escolher o meio de pagamento. Uma compra parcelada cria uma despesa por mês, pelo valor de CADA parcela. A data se ajusta ao último dia de meses mais curtos. Edição e exclusão atingem somente a parcela selecionada.\n\nNão registre o pagamento da fatura como uma nova despesa se suas compras já foram cadastradas. O compromisso inicial é apenas a parte da fatura ainda não registrada, evitando duplicar parcelas. Você pode lançar um total semanal, mas a divisão entre fechamentos só será exata se usar as datas de pagamento corretas.'),
    'saldo': ('Meta de cobertura e saldo', 'Meta = despesas cadastradas no período, inclusive compromissos e parcelas. Vendas menos taxas = faturamento bruto menos taxas conhecidas. Falta cobrir = o que ainda falta dessas vendas para alcançar a meta; depois de coberta, mostra zero. Saldo após despesas = vendas menos taxas menos despesas.\n\nO saldo pode ser negativo. Como inclui despesas pessoais e da feira, não é lucro contábil do negócio nem saldo bancário. Sem despesas cadastradas, não há meta definida pelas contas reais. Sem todas as taxas e despesas, o resultado está incompleto. Taxas não entram também como despesas, evitando desconto duplicado.'),
    'total': ('Total do período', 'É a soma de Dinheiro + Pix + Cartão dos registros que aparecem no filtro aplicado.\n\nExemplo: R$ 100 em dinheiro + R$ 50 em Pix + R$ 25 em cartão = R$ 175.\n\nÉ receita registrada, não lucro: os cartões de Vendas não descontam custos ou taxas. Consulte a aba Finanças para os descontos cadastrados. Datas futuras já cadastradas também entram no total.'),
    'quantidade': ('Dias de feira', 'Cada registro corresponde a uma data de feira. Dias com Dinheiro, Pix e Cartão zerados também contam.\n\nDatas sem registro não são contadas. Uma feira cadastrada em um dia extra da semana também entra na contagem. Os filtros determinam quais registros são considerados.'),
    'media': ('Média por dia', 'Cálculo: total do período dividido por quantidade de dias de feira cadastrados no período.\n\nExemplo: R$ 300 em uma feira e R$ 0 em outra = R$ 150 por dia, pois são dois registros.\n\nNão é a média por cliente nem por venda individual. Sem registros, o programa mostra R$ 0,00.'),
    'dinheiro': ('Dinheiro', 'Soma dos valores registrados no campo Dinheiro, somente para os registros do filtro aplicado. Não é o saldo disponível em caixa, pois não considera despesas ou retiradas.'),
    'pix': ('Pix', 'Soma dos valores registrados no campo Pix, somente para os registros do filtro aplicado. Não é uma consulta ao banco: são os valores cadastrados no programa.'),
    'cartao': ('Cartão', 'Soma dos valores registrados no campo Cartão, somente para os registros do filtro aplicado. Este indicador é bruto. As taxas cadastradas são descontadas separadamente na aba Finanças. A data de recebimento pela operadora não é acompanhada.'),
    'participacao': ('Participação por pagamento', 'Mostra quanto cada forma de pagamento representa do total filtrado.\n\nCálculo: valor da forma de pagamento dividido por total multiplicado por 100. Por exemplo, R$ 50 em Pix num total de R$ 200 representa 25%.\n\nCom total zero não há percentual calculável. O arredondamento pode fazer os percentuais exibidos somarem 99,9% ou 100,1%.'),
    'comparacao': ('Comparação com período anterior', 'Ano compara com o ano anterior; mês compara com o mês anterior; fechamento compara com o fechamento imediatamente anterior. Os mesmos dias da semana são usados nos dois períodos.\n\nDiferença = total atual menos total anterior. Variação = diferença dividido por total anterior multiplicado por 100. Ex.: de R$ 200 para R$ 250, a diferença é R$ 50 e a variação é +25%.\n\nSem registros anteriores ou com total anterior zero, não há percentual comparável. A comparação usa os períodos completos, inclusive registros zerados e datas futuras cadastradas; não é uma projeção. “Todas as vendas” não tem um período anterior definido.'),
    'ano': ('Filtro por ano', 'Escolha um ano e clique em Aplicar filtros para ver seus registros. “Todos os anos” restaura o histórico completo e limpa mês e fechamento. Os resultados só mudam depois de aplicar.'),
    'mes': ('Filtro por mês', 'Escolha o mês e o ano e clique em Aplicar filtros. Sem fechamento marcado, o período vai do primeiro ao último dia do mês.\n\n“Todos os meses” considera o ano inteiro. Escolher um mês sem ano seleciona o ano atual, mostrado no campo Ano.'),
    'fechamento': ('Fechamento e histórico de regras', 'O mês escolhido identifica o fechamento inicial do período. A regra inicial fecha no dia 9; a consulta vai do dia 10 ao dia 9 seguinte. Configurar fechamento permite uma nova regra a partir de uma fatura futura, preservando os períodos já encerrados. O período ainda aberto pode mudar de duração; confira as datas exibidas. Valores e parcelas não são movidos automaticamente.\n\nExemplo: Outubro de 2026, com fechamento marcado, considera de 10/10/2026 até 09/11/2026, incluindo as duas datas.\n\nSem um mês escolhido, marcar fechamento seleciona o mês atual. Confira ano e mês antes de aplicar.'),
    'dias': ('Filtro por dias da semana', 'Marque os dias que deseja consultar. Sexta e domingo, por exemplo, mostram os registros de ambos os dias, dentro do período escolhido.\n\nNenhum dia marcado significa todos os dias. Esse filtro também vale para as análises e para a comparação com o período anterior.'),
    'filtros': ('Filtros aplicados e pendentes', 'O texto junto ao histórico e na aba Análises identifica os filtros dos resultados exibidos.\n\nDepois de mudar uma seleção, aparece “Filtros alterados — clique em Aplicar”. Até aplicar, os indicadores, análises e exportações continuam usando os resultados anteriores. “Limpar filtros” aplica o histórico completo.'),
    'historico': ('Histórico de vendas', 'Cada linha representa uma data cadastrada, com seus pagamentos e total. ID é o identificador interno do registro; não é a quantidade de feiras e pode ter intervalos.\n\nClique em um título para ordenar. Selecione uma linha para editar ou excluir; a exclusão exige confirmação e tem backup automático. Dias zerados são preservados.'),
    'por_dia': ('Resultados por dia da semana', 'Agrupa os registros do filtro aplicado pelo dia da semana da data cadastrada.\n\nDias de feira é a quantidade de registros daquele dia da semana, incluindo os zerados. Total é a soma dos pagamentos. Média é o total dividido pela quantidade de registros daquele grupo.\n\nExemplo: duas sextas-feiras com R$ 100 e R$ 0 têm média de R$ 50. Só registros com data válida podem ser agrupados.'),
    'comparacao_livre': ('Comparar A e B', 'Escolha dois períodos e clique em Comparar A e B. Data consulta um único dia; Mês consulta o mês civil completo; Fechamento usa as regras históricas do mês escolhido e do seguinte; na regra inicial, vai do dia 10 ao dia 9; Intervalo permite informar início e fim, incluindo as duas datas.\n\nA é a referência. Diferença = total de B menos total de A. Variação = diferença dividido pelo total de A multiplicado por 100. Sem registros ou com total de A zero, não há variação percentual calculável. Dias zerados contam na média; datas sem registro não contam. Períodos com números diferentes de feiras podem ter totais diferentes: compare também as médias.\n\nEsta consulta inclui todos os dias da semana e não altera os filtros de Vendas. Os cartões do topo continuam representando Vendas. Intervalos podem se sobrepor; nesse caso, um mesmo registro pode participar de A e B. São períodos completos, inclusive datas futuras cadastradas; não há projeção.'),
    'analises': ('Como ler as análises', 'O Resumo do período usa exatamente a última seleção aplicada na aba Vendas. A subaba Comparar A e B permite uma consulta independente, explicada no seu próprio botão de ajuda. Alterar filtros sem aplicar não muda as análises.\n\nOs valores por forma de pagamento e por dia da semana são agrupamentos dos mesmos registros; não são receitas adicionais. Para mudar o período, volte à aba Vendas e aplique os filtros. A exportação continua levando os registros e o resumo desse período.'),
}


def mostrar_ajuda(parent, chave):
    titulo, texto = AJUDAS[chave]
    popup = tk.Toplevel(parent.winfo_toplevel())
    popup.title(titulo)
    popup.configure(background=CORES['fundo'])
    popup.transient(parent.winfo_toplevel())
    popup.resizable(False, False)
    corpo = ttk.Frame(popup, padding=22)
    corpo.pack(fill='both', expand=True)
    ttk.Label(corpo, text=titulo, font=(font.nametofont('TkDefaultFont').actual('family'), 13, 'bold'), wraplength=490).pack(anchor='w', pady=(0, 14))
    ttk.Label(corpo, text=texto, wraplength=490, justify='left').pack(anchor='w')
    fechar = ttk.Button(corpo, text='Entendi', command=popup.destroy, style='Primary.TButton')
    fechar.pack(anchor='e', pady=(18, 0))
    popup.bind('<Escape>', lambda e: popup.destroy())
    popup.bind('<Return>', lambda e: popup.destroy())
    popup.update_idletasks()
    root = parent.winfo_toplevel()
    x = max(0, root.winfo_rootx() + (root.winfo_width() - popup.winfo_reqwidth()) // 2)
    y = max(0, root.winfo_rooty() + (root.winfo_height() - popup.winfo_reqheight()) // 2)
    popup.geometry(f'+{x}+{y}')
    fechar.focus_set()
    return popup


def botao_ajuda(parent, chave):
    botao = ttk.Button(parent, text='?', width=2, style='Ajuda.TButton', command=lambda: mostrar_ajuda(parent, chave))
    botao.ajuda_chave = chave
    return botao


def rotulo_com_ajuda(parent, texto, chave, estilo='Surface.TLabel'):
    linha = ttk.Frame(parent, style='Surface.TFrame')
    ttk.Label(linha, text=texto, style=estilo).pack(side='left')
    botao_ajuda(linha, chave).pack(side='left', padx=(6, 0))
    return linha


class Dica:
    """Texto breve ao passar o mouse ou focar pelo teclado, sem abrir um diálogo."""
    def __init__(self, widget, texto):
        self.widget, self.texto = widget, texto
        self.tarefa = self.popup = None
        widget.bind('<Enter>', self.agendar, add='+')
        widget.bind('<FocusIn>', self.agendar, add='+')
        for evento in ('<Leave>', '<FocusOut>', '<ButtonPress>', '<Destroy>'):
            widget.bind(evento, self.fechar, add='+')

    def agendar(self, evento=None):
        self.fechar()
        self.tarefa = self.widget.after(350, self.mostrar)

    def mostrar(self):
        self.fechar()
        self.tarefa = None
        if not self.widget.winfo_exists() or not self.widget.winfo_viewable():
            return
        popup = self.popup = tk.Toplevel(self.widget)
        popup.withdraw()
        popup._dica_informativa = True
        popup.overrideredirect(True)
        ttk.Label(popup, text=self.texto, wraplength=330, padding=12, style='Surface.TLabel', relief='solid', borderwidth=1).pack()
        popup.update_idletasks()
        x = min(self.widget.winfo_rootx(), self.widget.winfo_screenwidth() - popup.winfo_reqwidth() - 8)
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        if y + popup.winfo_reqheight() > self.widget.winfo_screenheight():
            y = self.widget.winfo_rooty() - popup.winfo_reqheight() - 6
        popup.geometry(f'+{max(0, x)}+{max(0, y)}')
        popup.deiconify()

    def fechar(self, evento=None):
        if self.tarefa is not None:
            try:
                self.widget.after_cancel(self.tarefa)
            except tk.TclError:
                pass
            self.tarefa = None
        if self.popup is not None:
            try:
                self.popup.destroy()
            except tk.TclError:
                pass
            self.popup = None
