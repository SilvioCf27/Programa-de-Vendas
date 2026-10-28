"""Proteções das otimizações: frescor, recortes e apresentação sem I/O repetido."""
from contextlib import closing
from decimal import Decimal
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parent))
import test_vendas_qt as fixtures
from ProgramFeira.database import banco
from ProgramFeira.semanas import semana_atual
from reforma_desktop.vendas import Consulta


class FluidezTests(unittest.TestCase):
    setUpClass=classmethod(fixtures.VendasTests.setUpClass.__func__)
    setUp=fixtures.VendasTests.setUp
    criar=fixtures.VendasTests.criar
    janela=fixtures.VendasTests.janela

    def test_consulta_completa_reutiliza_leitura_da_semana_sem_cache_de_banco(self):
        self.criar('2026-10-23','10');self.criar('2026-10-26','20')
        self.criar('2026-10-28','100')  # futuro não entra na semana atual
        esperado=semana_atual(banco.listar_vendas(),self.servico.hoje())
        with patch.object(banco,'listar_vendas',wraps=banco.listar_vendas) as ler:
            r=self.servico.consultar(Consulta())
            self.assertEqual(ler.call_count,1)
        self.assertEqual(r['semana'],esperado)
        with closing(banco.conectar()) as c,c:c.execute('UPDATE vendas SET dinheiro=21 WHERE data=?',('2026-10-26',))
        novo=self.servico.consultar(Consulta())
        self.assertEqual(novo['semana']['total'],esperado['total']+1)

    def test_recorte_nao_limita_semana_independente(self):
        self.criar('2025-01-03','200');self.criar('2026-10-26','20')
        r=self.servico.consultar(Consulta(2025,1))
        self.assertEqual(r['indicadores']['total'],Decimal(250))
        self.assertEqual(r['semana']['total'],Decimal(70))

    def test_busca_e_ordenacao_reusam_apresentacao_sem_consultar_nem_formatar(self):
        self.criar('2026-10-23','100');self.criar('2026-10-25','2')
        j=self.janela();j.limpar()
        with patch('reforma_desktop.aplicacao.moeda',side_effect=AssertionError('Reformatou sem mudança')),patch.object(banco,'listar_vendas',side_effect=AssertionError('Reconsultou ao buscar')):
            j.busca.setText('23/10/2026')
            self.assertEqual(len(j.tabela.linhas),1)
            j.busca.clear();j.ordenar(4)
            self.assertEqual([r[1][3] for r in j.tabela.linhas],['R$ 2,00','R$ 100,00'])
        self.assertEqual(len(j.resultado['relatorio']['vendas']),2)

    def test_mesmo_id_com_valor_alterado_invalida_apresentacao(self):
        venda=self.criar('2026-10-23','10')
        j=self.janela();j.limpar();j.busca.setText('999,00')
        self.assertEqual(j.tabela.linhas,[])
        with closing(banco.conectar()) as c,c:c.execute('UPDATE vendas SET dinheiro=999 WHERE id=?',(venda[0],))
        j.atualizar()
        self.assertEqual(j.tabela.linhas[0][1][3],'R$ 999,00')
        self.assertEqual(j.resultado['indicadores']['total'],Decimal(1049))
        self.assertEqual(len(j.resultado['relatorio']['vendas']),1)

    def test_cache_so_retem_registros_da_consulta_aplicada(self):
        a=self.criar('2026-10-23');self.criar('2025-01-03')
        j=self.janela();j.limpar()
        self.assertEqual(len(j._apresentacao),2)
        j.ano.setCurrentText('2026');j.mes.setCurrentIndex(10);j.aplicar()
        self.assertEqual(list(j._apresentacao),[a])
        self.servico.excluir([a]);j.atualizar()
        self.assertEqual(j._apresentacao,{})
        self.assertEqual(j.tabela.linhas,[])
