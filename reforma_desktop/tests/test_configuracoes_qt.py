"""Preferências, temas e backup local da entrada Qt, sem conta ou banco pessoal."""
import ast
from contextlib import closing
from datetime import date
from pathlib import Path
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'prototipos/reforma'))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from reforma_desktop.aplicacao import Janela, preparar_interface
from reforma_desktop.vendas import ServicoVendas
from reforma_desktop.temas import cores, NOMES, PALETAS, contraste
from reforma_desktop.ambiente import MARCADOR, CONTEUDO
from ProgramFeira import preferencias, financeiro, fechamento
from ProgramFeira.database import banco


class ConfiguracoesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = preparar_interface()

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.pasta = Path(temp.name)
        p = patch.object(banco, 'CAMINHO_BANCO', self.pasta / 'vendas.db')
        p.start()
        self.addCleanup(p.stop)
        self.servico = ServicoVendas(lambda: date(2026, 10, 27))
        self.addCleanup(fechamento.definir, {'versao': 0, 'historico': []})

    def janela(self):
        j = Janela(self.servico, self.pasta)
        self.addCleanup(j.deleteLater)
        self.addCleanup(j.close)
        j.show()
        self.app.processEvents()
        return j

    def test_salvar_preferencias_preserva_consulta_pendente_e_selecao(self):
        self.servico.salvar('2026-10-23', '10', '20', '30')
        j = self.janela()
        j.mes.setCurrentIndex(9)
        j.tabela.todos.setChecked(True)
        consulta, ids, resultado = j.consulta, j.tabela.selecionados(), j.resultado
        c = j.configuracoes()
        c.periodo.setCurrentText('Ano atual')
        c.salvar_periodo()
        c.tema.setCurrentIndex(c.tema.findData('aurora'))
        c.salvar_tema()
        self.assertEqual(preferencias.carregar_periodo_inicial(self.pasta), 'Ano atual')
        self.assertEqual(preferencias.carregar_tema(self.pasta), 'aurora')
        self.assertEqual(j.consulta, consulta)
        self.assertEqual(j.mes.currentIndex(), 9)
        self.assertEqual(j.tabela.selecionados(), ids)
        self.assertIs(j.resultado, resultado)
        self.assertIn('próxima abertura', c.tema.accessibleName())
        self.assertIn('Feche e abra', c.status.text())
        c.close()

    def test_periodo_salvo_e_usado_na_reabertura(self):
        j = self.janela()
        c = j.configuracoes()
        c.periodo.setCurrentText('Todas as vendas')
        c.salvar_periodo()
        c.close()
        novo = self.janela()
        self.assertIsNone(novo.consulta.ano)
        preferencias.salvar_periodo_inicial(self.pasta, 'Ano atual')
        outro = self.janela()
        self.assertEqual(outro.consulta.ano, 2026)
        self.assertIsNone(outro.consulta.mes)

    def test_falha_de_preferencia_nao_informa_sucesso_nem_muda_banco(self):
        j = self.janela()
        c = j.configuracoes()
        antes = banco.CAMINHO_BANCO.read_bytes()
        with patch.object(preferencias, 'salvar_tema', side_effect=OSError('Sem acesso')):
            c.salvar_tema()
        self.assertIn('não salvo', c.status.text())
        self.assertFalse((self.pasta / 'preferencias.json').exists())
        self.assertEqual(banco.CAMINHO_BANCO.read_bytes(), antes)
        c.close()

    def test_backup_manual_contem_vendas_financas_e_historico(self):
        self.servico.salvar('2026-10-23', '10', '20', '30')
        financeiro.inicializar()
        financeiro.salvar_lancamento('despesa', '2026-10-23', 'Teste', '12,34')
        financeiro.salvar_taxa_anual(2025, '2025-01-01', '2025-12-31', '100')
        c = self.janela().configuracoes()
        anteriores = set((self.pasta / 'backups').glob('*.db'))
        antes = banco.CAMINHO_BANCO.read_bytes()
        c.backup()
        novas = set((self.pasta / 'backups').glob('*.db')) - anteriores
        self.assertEqual(len(novas), 1)
        with closing(sqlite3.connect(novas.pop())) as db:
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone(), ('ok',))
            for tabela in ['vendas','financeiro_lancamentos','financeiro_taxas_anuais']:
                self.assertEqual(db.execute('SELECT count(*) FROM '+tabela).fetchone(), (1,))
        self.assertEqual(banco.CAMINHO_BANCO.read_bytes(), antes)
        self.assertIn('criado e verificado', c.status.text())
        c.close()

    def test_backup_com_falha_informa_erro(self):
        c = self.janela().configuracoes()
        with patch.object(banco, 'criar_backup', side_effect=OSError('Destino sem acesso')):
            c.backup()
        self.assertIn('não concluído', c.status.text())
        c.close()

    def test_paletas_compativeis_com_o_nucleo_sem_importar_tk(self):
        esperado = {}
        for n in ast.parse((ROOT/'ProgramFeira/interface/visual.py').read_text(encoding='utf-8')).body:
            if isinstance(n, ast.Assign):
                a = n.targets[0]
                if isinstance(a, ast.Name) and a.id == 'PALETAS':
                    esperado.update(ast.literal_eval(n.value))
                elif isinstance(a, ast.Subscript) and isinstance(a.value, ast.Name) and a.value.id == 'PALETAS':
                    esperado[ast.literal_eval(a.slice)] = ast.literal_eval(n.value)
        self.assertEqual(PALETAS, esperado)
        self.assertEqual(cores('aurora')['primary_start'], '#52057B')
        self.assertEqual(cores('grafite')['turquoise'], '#42D5AD')
        self.assertNotIn('ProgramFeira.interface.visual', sys.modules)
        with self.assertRaises(ValueError):
            cores('inexistente')

    def test_cinco_temas_abrem_tres_areas_sem_alterar_registros(self):
        for tema in NOMES:
            pasta = self.pasta / tema
            pasta.mkdir()
            (pasta / MARCADOR).write_text(CONTEUDO, encoding='utf-8')
            preferencias.salvar_tema(pasta, tema)
            for pagina in ('Vendas','Análises','Finanças'):
                with self.subTest(tema=tema,pagina=pagina):
                    captura = self.pasta / (tema+'-'+pagina+'.png')
                    r = subprocess.run([sys.executable, str(ROOT/'executar_reforma.py'), '--pasta-estudo', str(pasta), '--exemplo', '--pagina', pagina, '--captura', str(captura)], capture_output=True, text=True, timeout=45, cwd=ROOT)
                    self.assertEqual(r.returncode, 0, r.stdout+r.stderr)
                    self.assertGreater(captura.stat().st_size, 10000)
                    with closing(sqlite3.connect(pasta/'vendas.db')) as db:
                        self.assertEqual(db.execute('SELECT count(*) FROM vendas').fetchone(), (5,))
                        self.assertEqual(db.execute('SELECT count(*) FROM financeiro_lancamentos').fetchone(), (5,))
                        self.assertEqual(db.execute('PRAGMA integrity_check').fetchone(), ('ok',))
                    self.assertEqual(preferencias.carregar_tema(pasta), tema)


    def test_contraste_textos_e_acoes_nas_cinco_paletas(self):
        for tema in NOMES:
            c = cores(tema)
            for texto, fundo in [('text','panel'),('muted','panel'),('text','primary_start'),('text','primary_end'),('text','primary_hover'),('text','query')]:
                with self.subTest(tema=tema, par=(texto,fundo)):
                    self.assertGreaterEqual(contraste(c[texto], c[fundo]), 4.5)
