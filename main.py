import flet as ft
import gpxpy
from tcxreader.tcxreader import TCXReader
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
import folium
import os
import webbrowser 
import matplotlib.pyplot as plt
import io
import base64

# ==========================================
# MODELO DE DADOS PADRONIZADO
# ==========================================
@dataclass
class PontoTreino:
    latitude: float
    longitude: float
    elevacao: Optional[float]
    tempo: datetime
    frequencia_cardiaca: Optional[int]
    cadencia: Optional[int]

@dataclass
class Atividade:
    nome: str
    tipo: str
    distancia_total_km: float
    tempo_total_minutos: float
    frequencia_cardiaca_media: Optional[int]
    pontos: List[PontoTreino]

# ==========================================
# FUNÇÕES DE LEITURA E MAPA
# ==========================================
def ler_gpx(caminho_ficheiro: str) -> Atividade:
    with open(caminho_ficheiro, 'r', encoding='utf-8') as gpx_file:
        gpx = gpxpy.parse(gpx_file)
        pontos = []
        soma_fc = contagem_fc = 0

        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    fc = cadencia = None
                    if point.extensions:
                        for ext in point.extensions[0].iter():
                            if 'hr' in ext.tag:
                                fc = int(ext.text)
                                soma_fc += fc
                                contagem_fc += 1
                            if 'cad' in ext.tag:
                                cadencia = int(ext.text)
                    pontos.append(PontoTreino(point.latitude, point.longitude, point.elevation, point.time, fc, cadencia))
        
        fc_media = (soma_fc // contagem_fc) if contagem_fc > 0 else None
        return Atividade(
            gpx.tracks[0].name if gpx.tracks and gpx.tracks[0].name else "Atividade GPX",
            gpx.tracks[0].type if gpx.tracks and gpx.tracks[0].type else "Desconhecido",
            gpx.length_3d() / 1000, (gpx.get_duration() or 0.0) / 60, fc_media, pontos
        )

def ler_tcx(caminho_ficheiro: str) -> Atividade:
    dados_tcx = TCXReader().read(caminho_ficheiro)
    pontos = []
    for tp in dados_tcx.trackpoints:
        if tp.latitude and tp.longitude:
            pontos.append(PontoTreino(tp.latitude, tp.longitude, tp.elevation, tp.time, tp.hr_value, tp.cadence))
            
    return Atividade("Atividade TCX", dados_tcx.activity_type, (dados_tcx.distance or 0.0) / 1000, 
                     (dados_tcx.duration or 0.0) / 60, dados_tcx.hr_avg, pontos)

def gerar_mapa(atividade: Atividade) -> str:
    coordenadas = [(p.latitude, p.longitude) for p in atividade.pontos if p.latitude and p.longitude]
    if not coordenadas:
        return ""

    lat_centro = sum(c[0] for c in coordenadas) / len(coordenadas)
    lon_centro = sum(c[1] for c in coordenadas) / len(coordenadas)

    m = folium.Map(location=[lat_centro, lon_centro], zoom_start=14, tiles="CartoDB positron")
    folium.PolyLine(coordenadas, color="#FF5722", weight=4, opacity=0.8).add_to(m)
    folium.Marker(coordenadas[0], tooltip="Início", icon=folium.Icon(color="green", icon="play")).add_to(m)
    folium.Marker(coordenadas[-1], tooltip="Fim", icon=folium.Icon(color="red", icon="stop")).add_to(m)

    caminho_absoluto = os.path.abspath("mapa_atividade.html")
    m.save(caminho_absoluto)
    return caminho_absoluto

# ==========================================
# GERAÇÃO DE GRÁFICOS MATPLOTLIB (NOVO!)
# ==========================================
def criar_grafico_fc(atividade: Atividade) -> ft.Control:
    pontos_com_fc = [p for p in atividade.pontos if p.frequencia_cardiaca is not None]
    
    if not pontos_com_fc:
        return ft.Text("Sem dados de Frequência Cardíaca registados.", color=ft.Colors.GREY_500, italic=True)

    tempo_inicial = pontos_com_fc[0].tempo
    
    # Extrair os dados para listas do Python
    minutos = [(p.tempo - tempo_inicial).total_seconds() / 60.0 for p in pontos_com_fc]
    fcs = [p.frequencia_cardiaca for p in pontos_com_fc]

    # Criar a figura do Matplotlib (Tamanho e Fundo Transparente)
    fig, ax = plt.subplots(figsize=(8, 3), dpi=100)
    fig.patch.set_alpha(0.0) # Fundo da imagem transparente
    ax.set_facecolor('#1E1E1E') # Cor de fundo do gráfico para combinar com o modo Dark do Flet

    # Desenhar o gráfico de linha e preencher a parte de baixo com cor
    ax.plot(minutos, fcs, color='#EF5350', linewidth=1.5)
    ax.fill_between(minutos, fcs, color='#EF5350', alpha=0.3)

    # Estilização dos eixos para ficar com visual de Dashboard
    ax.set_xlabel('Tempo (minutos)', color='white')
    ax.set_ylabel('BPM', color='white')
    ax.tick_params(colors='white', which='both')
    ax.spines['bottom'].set_color('#555555')
    ax.spines['left'].set_color('#555555')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(True, linestyle='--', alpha=0.2, color='white')

    plt.tight_layout()

    # Converter a imagem do gráfico num Base64 para injetar direto no Flet
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', transparent=True)
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)

    # Devolve a imagem renderizada para a interface
    return ft.Image(src=f"data:image/png;base64,{img_base64}", fit="contain", expand=True)
    #return ft.Image(src_base64=img_base64, fit=ft.ImageFit.CONTAIN, expand=True)

# ==========================================
# INTERFACE DO UTILIZADOR (FLET) - FASE 3
# ==========================================
def main(page: ft.Page):
    page.title = "Análise de Corridas - Fase 3"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.scroll = "auto"

    lista_de_atividades: List[Atividade] = []

    texto_estado = ft.Text(value="A aguardar ficheiros...", italic=True, color=ft.Colors.GREY_400)
    coluna_historico = ft.Column(spacing=10)
    painel_detalhes = ft.Column(spacing=10)

    def mostrar_detalhes(atividade: Atividade):
        painel_detalhes.controls.clear()
        
        caminho_mapa = gerar_mapa(atividade)
        grafico_fc = criar_grafico_fc(atividade)
        
        data_formatada = atividade.pontos[0].tempo.strftime("%d/%m/%Y às %H:%M") if atividade.pontos else "Data desconhecida"

        painel_detalhes.controls.append(
            ft.Card(
                content=ft.Container(
                    padding=20,
                    content=ft.Column([
                        ft.Text(atividade.nome, size=24, weight=ft.FontWeight.BOLD),
                        ft.Text(f"Realizado em: {data_formatada}", size=14, color=ft.Colors.GREY_400),
                        ft.Divider(),
                        ft.Row([
                            ft.Icon(ft.Icons.ROUTE, color=ft.Colors.BLUE), ft.Text(f"{atividade.distancia_total_km:.2f} km"),
                            ft.Icon(ft.Icons.TIMER, color=ft.Colors.GREEN), ft.Text(f"{atividade.tempo_total_minutos:.2f} min"),
                            ft.Icon(ft.Icons.FAVORITE, color=ft.Colors.RED), ft.Text(f"{atividade.frequencia_cardiaca_media or '--'} bpm")
                        ], wrap=True),
                        
                        # GRÁFICO MATPLOTLIB INSERIDO AQUI
                        ft.Divider(),
                        ft.Text("Evolução Cardíaca", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_400),
                        ft.Container(content=grafico_fc, alignment=ft.Alignment.CENTER)
                    ])
                )
            )
        )

        if caminho_mapa:
            def abrir_e_minimizar(e):
                page.window.minimized = True
                page.update()
                webbrowser.open(f"file://{caminho_mapa}")

            botao_externo = ft.Button(
                content="Ver Percurso no Navegador",
                icon=ft.Icons.MAP,
                on_click=abrir_e_minimizar
            )
            painel_detalhes.controls.append(ft.Row([botao_externo], alignment=ft.MainAxisAlignment.CENTER))
        
        page.update()

    def atualizar_historico_ui():
        coluna_historico.controls.clear()
        
        atividades_ordenadas = sorted(
            lista_de_atividades, 
            key=lambda a: a.pontos[0].tempo if a.pontos else datetime.min, 
            reverse=True
        )

        for ativ in atividades_ordenadas:
            data_curta = ativ.pontos[0].tempo.strftime("%d/%m") if ativ.pontos else "--/--"
            
            item = ft.ListTile(
                leading=ft.Icon(ft.Icons.DIRECTIONS_RUN, color=ft.Colors.ORANGE_500),
                title=ft.Text(ativ.nome, weight=ft.FontWeight.BOLD),
                subtitle=ft.Text(f"{data_curta} • {ativ.distancia_total_km:.1f} km"),
                on_click=lambda e, a=ativ: mostrar_detalhes(a)
            )
            coluna_historico.controls.append(ft.Card(content=item))

    def processar_ficheiros(ficheiros_selecionados):
        try:
            texto_estado.value = f"A processar {len(ficheiros_selecionados)} ficheiro(s)..."
            page.update()

            for f in ficheiros_selecionados:
                caminho = f.path
                if caminho.lower().endswith('.gpx') or caminho.lower().endswith('.tcx'):
                    atividade = ler_gpx(caminho) if caminho.lower().endswith('.gpx') else ler_tcx(caminho)
                    lista_de_atividades.append(atividade)

            atualizar_historico_ui()
            texto_estado.value = f"{len(ficheiros_selecionados)} atividade(s) carregada(s) com sucesso!"

        except Exception as e:
            texto_estado.value = f"Erro ao processar: {str(e)}"
            texto_estado.color = ft.Colors.RED_400

        page.update()

    async def abrir_seletor(e: ft.Event[ft.Button]):
        files = await ft.FilePicker().pick_files(allow_multiple=True, allowed_extensions=["gpx", "tcx"])
        if files:
            processar_ficheiros(files)
        else:
            texto_estado.value = "Seleção cancelada."
            page.update()

    layout_principal = ft.ResponsiveRow(
        controls=[
            ft.Column(col={"sm": 12, "md": 5, "lg": 4}, controls=[
                ft.Text("Histórico de Corridas", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.ORANGE_500),
                ft.Divider(),
                coluna_historico
            ]),
            ft.Column(col={"sm": 12, "md": 7, "lg": 8}, controls=[
                ft.Text("Detalhes", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_400),
                ft.Divider(),
                painel_detalhes
            ])
        ]
    )

    page.add(
        ft.Row([
            ft.Icon(ft.Icons.DIRECTIONS_RUN, size=40, color=ft.Colors.ORANGE_500),
            ft.Text("Sports Tracker Analyzer", size=32, weight=ft.FontWeight.BOLD)
        ], alignment=ft.MainAxisAlignment.CENTER),
        
        ft.Divider(height=20),
        
        ft.Row([
            ft.Button(content="Carregar Arquivos (GPX/TCX)", icon=ft.Icons.UPLOAD_FILE, on_click=abrir_seletor),
        ], alignment=ft.MainAxisAlignment.CENTER),
        
        ft.Row([texto_estado], alignment=ft.MainAxisAlignment.CENTER),
        
        ft.Container(height=20),
        
        layout_principal 
    )

if __name__ == "__main__":
    ft.run(main)