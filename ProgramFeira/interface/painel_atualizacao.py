"""Consulta em segundo plano, instalação consentida e reinício do portátil."""
import json
from pathlib import Path
import queue
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from ProgramFeira import atualizador
from ProgramFeira.interface.coleta import suspender_coleta
from ProgramFeira.interface.visual import CORES
from ProgramFeira.versao import VERSAO


class Atualizacoes:
    def __init__(self, janela, banco, pode_atualizar):
        self.janela, self.banco, self.pode_atualizar = janela, Path(banco), pode_atualizar
        self.popup = None
        self.ocupado = False
        self.release = None
        self.preparacao = None
        self.preferencia = self.banco.parent / 'atualizacoes.json'
        try:
            self.automatica = json.loads(self.preferencia.read_text(encoding='utf-8')).get('consultar', True) is True
        except (OSError, ValueError, AttributeError):
            self.automatica = True
        self.disponivel = sys.platform == 'win32' and getattr(sys, 'frozen', False)
        if self.disponivel and self.automatica and '--verificar-pacote' not in sys.argv:
            janela.after(12000, self.consultar_automaticamente)

    def abrir(self):
        if self.popup and self.popup.winfo_exists():
            self.popup.lift()
            return self.popup
        popup = self.popup = tk.Toplevel(self.janela)
        popup.title('Atualizações')
        popup.configure(background=CORES['fundo'])
        popup.transient(self.janela)
        corpo = ttk.Frame(popup, padding=24)
        corpo.pack(fill='both', expand=True)
        ttk.Label(corpo, text='Mantenha o Gestão da Feira atualizado', style='Title.TLabel').pack(anchor='w')
        ttk.Label(corpo, text=f'Versão instalada: {VERSAO}', style='Muted.TLabel').pack(anchor='w', pady=(6, 14))
        ttk.Label(corpo, text='Somente versões estáveis publicadas no GitHub oficial. O download é conferido e\no novo programa é testado antes da troca. Seus dados e configurações ficam\nna pasta atual; a versão anterior é guardada para recuperação.', justify='left').pack(anchor='w')
        self.status = tk.StringVar(value='Clique em Verificar atualizações.' if self.disponivel else
            'Você está usando o código Python. Atualize pelo Git; este recurso atende ao executável Windows.')
        ttk.Label(corpo, textvariable=self.status, wraplength=550).pack(anchor='w', pady=16)
        self.auto = tk.BooleanVar(value=self.automatica)
        def salvar_preferencia():
            self.automatica = self.auto.get()
            try:
                tmp = self.preferencia.with_suffix('.tmp')
                tmp.write_text(json.dumps({'consultar': self.automatica}), encoding='utf-8')
                tmp.replace(self.preferencia)
            except OSError:
                self.status.set('Não foi possível salvar a preferência. Verifique o acesso à pasta de dados.')
        ttk.Checkbutton(corpo, text='Consultar novas versões ao abrir (a instalação sempre pede sua confirmação)',
                        variable=self.auto, command=salvar_preferencia, state='normal' if self.disponivel else 'disabled').pack(anchor='w')
        acoes = ttk.Frame(corpo)
        acoes.pack(fill='x', pady=(20, 0))
        self.verificar = ttk.Button(acoes, text='Verificar atualizações', command=self.verificar_agora)
        self.verificar.pack(side='left')
        self.atualizar = ttk.Button(acoes, text='Baixar e instalar', style='Primary.TButton', command=self.baixar)
        self.atualizar.pack(side='left', padx=8)
        ttk.Button(acoes, text='Fechar', command=self.fechar).pack(side='right')
        popup.protocol('WM_DELETE_WINDOW', self.fechar)
        popup.bind('<Escape>', lambda e: self.fechar())
        self.controles()
        popup.grab_set()
        if self.release:
            self.status.set(f'Nova versão disponível: {self.release["versao"]}.')
        return popup

    def fechar(self):
        if not self.ocupado and self.popup:
            self.popup.destroy()
            self.popup = None

    def controles(self):
        if self.popup and self.popup.winfo_exists():
            self.verificar.configure(state='normal' if self.disponivel and not self.ocupado else 'disabled')
            self.atualizar.configure(state='normal' if self.release and not self.ocupado else 'disabled')

    def tarefa(self, funcao, concluir, silenciosa=False):
        if self.ocupado:
            return
        self.ocupado = True
        self.controles()
        fila = queue.Queue()
        def executar():
            try:
                fila.put((True, funcao()))
            except Exception as erro:
                fila.put((False, erro))
        retomar = suspender_coleta()
        worker = threading.Thread(target=executar, daemon=True)
        try:
            worker.start()
        except BaseException:
            retomar()
            self.ocupado = False
            self.controles()
            raise
        def acompanhar():
            if worker.is_alive():
                self.janela.after(100, acompanhar)
                return
            worker.join()
            retomar()
            sucesso, resultado = fila.get_nowait()
            self.ocupado = False
            self.controles()
            if sucesso:
                concluir(resultado)
            elif not silenciosa and self.popup and self.popup.winfo_exists():
                self.status.set('Não foi possível atualizar. A versão em uso e os dados foram preservados.\n'
                                'Confira a conexão, o espaço e as permissões da pasta e tente novamente.\n' + str(resultado))
        self.janela.after(100, acompanhar)

    def verificar_agora(self):
        self.status.set('Consultando as versões publicadas no GitHub…')
        def recebeu(release):
            self.release = release
            self.preparacao = None
            self.status.set(f'Nova versão disponível: {release["versao"]}.' if release else 'Você já está na versão mais recente.')
            self.controles()
        self.tarefa(atualizador.consultar, recebeu)

    def consultar_automaticamente(self):
        if not self.automatica or self.ocupado:
            return
        def recebeu(release):
            self.release = release
            if release:
                self.avisar()
        self.tarefa(atualizador.consultar, recebeu, silenciosa=True)

    def avisar(self):
        if self.popup and self.popup.winfo_exists():
            self.status.set(f'Nova versão disponível: {self.release["versao"]}.')
            self.controles()
            return
        try:
            self.pode_atualizar()
        except ValueError:
            self.janela.after(30000, self.avisar)
            return
        if messagebox.askyesno('Atualização disponível', f'Gestão da Feira {self.release["versao"]} está disponível.\nAbrir Atualizações?', parent=self.janela):
            self.abrir()

    def baixar(self):
        if not messagebox.askyesno('Atualizar o programa', 'O programa vai baixar e testar a nova versão, criar um backup e reiniciar.\nFeche outras instâncias antes de continuar. Deseja atualizar agora?', parent=self.popup):
            return
        try:
            self.pode_atualizar(self.popup)
        except ValueError as erro:
            self.status.set(str(erro))
            return
        self.status.set('Baixando e conferindo o pacote. Isso pode levar alguns minutos…')
        def preparado(dados):
            self.preparacao = dados
            self.status.set('Criando o backup e preparando o reinício…')
            # A janela modal impede edições; o agendador de sincronização
            # também aguarda enquanto ela estiver aberta.
            self.tarefa(lambda: atualizador.instalar(dados, self.banco), lambda _: self.janela.destroy())
        self.tarefa(lambda: atualizador.preparar(self.release, sys.executable, self.banco), preparado)
