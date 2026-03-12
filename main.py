import flet as ft
import gpxpy
from tcxreader.tcxreader import TCXReader
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
import folium
import os
import webbrowser # <-- A ARMA SECRETA DO PYTHON!

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
# INTERFACE DO UTILIZADOR (FLET)
# ==========================================
def main(page: ft.Page):
    page.title = "Análise de Corridas - Fase 2"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 30
    page.scroll = "auto"

    texto_estado = ft.Text(value="A aguardar ficheiro...", italic=True, color=ft.Colors.GREY_400)
    painel_detalhes = ft.Column(spacing=10)

    def processar_ficheiro(caminho: str):
        try:
            texto_estado.value = f"A processar: {caminho.split('/')[-1]}..."
            page.update()

            atividade = ler_gpx(caminho) if caminho.lower().endswith('.gpx') else ler_tcx(caminho)
            caminho_mapa = gerar_mapa(atividade)

            painel_detalhes.controls.clear()
            
            # Resumo em Cartão
            painel_detalhes.controls.append(
                ft.Card(
                    content=ft.Container(
                        padding=20,
                        content=ft.Column([
                            ft.Text(atividade.nome, size=24, weight=ft.FontWeight.BOLD),
                            ft.Row([
                                ft.Icon(ft.Icons.ROUTE, color=ft.Colors.BLUE), ft.Text(f"{atividade.distancia_total_km:.2f} km"),
                                ft.Icon(ft.Icons.TIMER, color=ft.Colors.GREEN), ft.Text(f"{atividade.tempo_total_minutos:.2f} min"),
                                ft.Icon(ft.Icons.FAVORITE, color=ft.Colors.RED), ft.Text(f"{atividade.frequencia_cardiaca_media or '--'} bpm")
                            ]),
                        ])
                    )
                )
            )

            # Usando o webbrowser do Python, 0% de stresse com o Flet/Wayland!
            if caminho_mapa:
                def abrir_e_minimizar(e):
                    # 1. Minimiza o aplicativo Flet
                    page.window.minimized = True
                    page.update()
                    # 2. Abre o navegador
                    webbrowser.open(f"file://{caminho_mapa}")

                botao_externo = ft.Button(
                    content="Ver Percurso no Navegador",
                    icon=ft.Icons.MAP,
                    on_click=abrir_e_minimizar
                )
                painel_detalhes.controls.append(ft.Row([botao_externo], alignment=ft.MainAxisAlignment.CENTER))

            texto_estado.value = "Carregamento e Mapa gerados com sucesso!"

        except Exception as e:
            texto_estado.value = f"Erro ao processar: {str(e)}"
            texto_estado.color = ft.Colors.RED_400

        page.update()

    async def abrir_seletor(e: ft.Event[ft.Button]):
        files = await ft.FilePicker().pick_files(allow_multiple=False, allowed_extensions=["gpx", "tcx"])
        if files:
            processar_ficheiro(files[0].path)
        else:
            texto_estado.value = "Seleção cancelada."
            page.update()

    page.add(
        ft.Row([
            ft.Icon(ft.Icons.DIRECTIONS_RUN, size=40, color=ft.Colors.ORANGE_500),
            ft.Text("Sports Tracker Analyzer", size=32, weight=ft.FontWeight.BOLD)
        ], alignment=ft.MainAxisAlignment.CENTER),
        ft.Divider(height=30),
        ft.Row([
            ft.Button(content="Selecionar Atividade (GPX/TCX)", icon=ft.Icons.UPLOAD_FILE, on_click=abrir_seletor),
        ], alignment=ft.MainAxisAlignment.CENTER),
        ft.Row([texto_estado], alignment=ft.MainAxisAlignment.CENTER),
        ft.Container(height=20),
        painel_detalhes
    )

if __name__ == "__main__":
    ft.run(main)