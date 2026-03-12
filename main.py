import flet as ft
import flet_map as ftm 
import gpxpy
from tcxreader.tcxreader import TCXReader
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
import os
import matplotlib.pyplot as plt
import io
import base64
import matplotlib
matplotlib.use('Agg')

# ==========================================
# MODELO DE DADOS PADRONIZADO
# ==========================================
@dataclass
class PontoTreino:
    latitude: float
    longitude: float
    elevacao: Optional[float]
    tempo: Optional[datetime]
    distancia_acumulada_km: float = 0.0
    frequencia_cardiaca: Optional[int] = None
    pace_instantaneo: float = 0.0

@dataclass
class Atividade:
    nome: str
    tipo: str
    distancia_total_km: float
    tempo_total_minutos: float
    frequencia_cardiaca_media: Optional[int]
    pontos: List[PontoTreino]

# ==========================================
# FUNÇÕES DE LEITURA (FIX TIMEZONE E PROTEÇÃO)
# ==========================================
def ler_gpx(caminho_ficheiro: str) -> Atividade:
    with open(caminho_ficheiro, 'r', encoding='utf-8') as gpx_file:
        gpx = gpxpy.parse(gpx_file)
        pontos = []
        soma_fc = contagem_fc = dist_acum = 0.0
        p_ant = None
        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    t_naive = point.time.replace(tzinfo=None) if point.time else None
                    if p_ant and point.time and p_ant.time:
                        d_m = point.distance_2d(p_ant)
                        dist_acum += d_m / 1000.0
                        dt = (point.time - p_ant.time).total_seconds()
                        # Pace (min/km) - Evitamos divisão por zero
                        pace = (dt / 60.0) / (d_m / 1000.0) if d_m > 0.05 else 0
                    else: pace = 0
                    
                    fc = None
                    if point.extensions:
                        for ext in point.extensions[0].iter():
                            if 'hr' in ext.tag:
                                fc = int(ext.text)
                                soma_fc += fc
                                contagem_fc += 1
                    pontos.append(PontoTreino(point.latitude, point.longitude, point.elevation, t_naive, dist_acum, fc, pace))
                    p_ant = point
        return Atividade(gpx.tracks[0].name or "GPX", "Corrida", dist_acum, (gpx.get_duration() or 0)/60, (soma_fc//contagem_fc if contagem_fc > 0 else None), pontos)

def ler_tcx(caminho_ficheiro: str) -> Atividade:
    dados_tcx = TCXReader().read(caminho_ficheiro)
    pontos = []
    p_ant_dist = 0.0
    p_ant_time = None
    for tp in dados_tcx.trackpoints:
        if tp.latitude and tp.longitude:
            t_naive = tp.time.replace(tzinfo=None) if tp.time else None
            dist_km = (tp.distance or 0.0) / 1000.0
            pace = 0
            if p_ant_time and tp.time:
                dt = (tp.time - p_ant_time).total_seconds()
                dd = dist_km - p_ant_dist
                pace = (dt / 60.0) / dd if dd > 0.0001 else 0
            pontos.append(PontoTreino(tp.latitude, tp.longitude, tp.elevation, t_naive, dist_km, tp.hr_value, pace))
            p_ant_dist, p_ant_time = dist_km, tp.time
    return Atividade("TCX", dados_tcx.activity_type, (dados_tcx.distance or 0)/1000, (dados_tcx.duration or 0)/60, dados_tcx.hr_avg, pontos)

# ==========================================
# GRÁFICO COMBINADO (BPM E PACE POR KM)
# ==========================================
def criar_grafico_combinado(atividade: Atividade) -> ft.Control:
    # Filtro relaxado: apenas pontos que tenham distância calculada
    pontos_v = [p for p in atividade.pontos if p.distancia_acumulada_km > 0]
    
    if len(pontos_v) < 10:
        return ft.Container(content=ft.Text("Dados insuficientes para o gráfico.", italic=True), padding=20)

    plt.close('all')
    fig, ax1 = plt.subplots(figsize=(10, 4))
    fig.patch.set_alpha(0.0)
    ax1.set_facecolor('#1E1E1E')

    dist = [p.distancia_acumulada_km for p in pontos_v]
    
    # Eixo 1: BPM (Vermelho)
    fcs = [p.frequencia_cardiaca for p in pontos_v]
    # Plotamos apenas onde há FC para não quebrar a linha
    indices_fc = [i for i, v in enumerate(fcs) if v is not None]
    if indices_fc:
        ax1.plot([dist[i] for i in indices_fc], [fcs[i] for i in indices_fc], 
                 color='#EF5350', linewidth=2, label='Batimentos')
        ax1.set_ylabel('BPM', color='#EF5350', fontweight='bold')
        ax1.tick_params(axis='y', labelcolor='#EF5350')

    # Eixo 2: Pace (Azul - Invertido)
    # Clipamos o pace entre 3 e 15 para o gráfico não ficar ilegível com paragens
    paces = [max(3, min(15, p.pace_instantaneo)) if p.pace_instantaneo > 0 else 15 for p in pontos_v]
    
    ax2 = ax1.twinx()
    ax2.plot(dist, paces, color='#42A5F5', linewidth=1, alpha=0.4, label='Pace')
    ax2.set_ylabel('Pace (min/km)', color='#42A5F5', fontweight='bold')
    ax2.invert_yaxis() 
    ax2.set_ylim(15, 3) # Fixamos a escala para facilitar a leitura
    ax2.tick_params(axis='y', labelcolor='#42A5F5')

    ax1.set_xlabel('Distância (km)', color='white')
    ax1.grid(True, linestyle='--', alpha=0.1)
    ax1.tick_params(axis='x', labelcolor='white')

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', transparent=True)
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    
    return ft.Image(src=f"data:image/png;base64,{img_b64}", fit="contain")

# ==========================================
# INTERFACE PRINCIPAL
# ==========================================
def main(page: ft.Page):
    page.title = "Sports Tracker Pro"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20

    lista_atividades: List[Atividade] = []
    coluna_historico = ft.Column(spacing=10, scroll="auto")
    painel_detalhes = ft.Column(spacing=10, scroll="auto")

    def mostrar_detalhes(ativ: Atividade):
        painel_detalhes.controls.clear()
        
        coords = [ftm.MapLatitudeLongitude(p.latitude, p.longitude) for p in ativ.pontos if p.latitude]
        
        # MUDANÇA: URL do CartoDB Positron para evitar erro 403 e ficar no modo escuro
        mapa = ftm.Map(
            expand=True,
            initial_center=coords[len(coords)//2] if coords else ftm.MapLatitudeLongitude(0,0),
            initial_zoom=14,
            layers=[
                ftm.TileLayer(
                    url_template="https://s.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
                ),
                ftm.PolylineLayer(
                    polylines=[
                        ftm.PolylineMarker(
                            coordinates=coords,
                            color=ft.Colors.ORANGE_500,
                            border_stroke_width=2,
                            border_color=ft.Colors.ORANGE_900,
                        )
                    ]
                )
            ]
        )

        painel_detalhes.controls.append(
            ft.Card(ft.Container(padding=20, content=ft.Column([
                ft.Text(ativ.nome, size=24, weight="bold"),
                ft.Row([
                    ft.Icon(ft.Icons.ROUTE, color=ft.Colors.BLUE), ft.Text(f"{ativ.distancia_total_km:.2f} km"),
                    ft.Icon(ft.Icons.TIMER, color=ft.Colors.GREEN), ft.Text(f"{ativ.tempo_total_minutos:.1f} min"),
                    ft.Icon(ft.Icons.FAVORITE, color=ft.Colors.RED), ft.Text(f"{ativ.frequencia_cardiaca_media or '--'} bpm"),
                ]),
                ft.Divider(),
                # Gráfico
                ft.Container(content=criar_grafico_combinado(ativ), alignment=ft.Alignment.CENTER, height=250),
                # Mapa
                ft.Container(content=mapa, height=350, border_radius=10)
            ])))
        )
        page.update()

    async def abrir_seletor(e):
        files = await ft.FilePicker().pick_files(allow_multiple=True, allowed_extensions=["gpx", "tcx"])
        if files:
            for f in files:
                try:
                    ativ = ler_gpx(f.path) if f.name.lower().endswith('.gpx') else ler_tcx(f.path)
                    lista_atividades.append(ativ)
                except: pass
            
            coluna_historico.controls.clear()
            # Ordenação por data (corrigindo fuso horário)
            def get_time(a): return a.pontos[0].tempo.replace(tzinfo=None) if (a.pontos and a.pontos[0].tempo) else datetime.min
            
            for ativ in sorted(lista_atividades, key=get_time, reverse=True):
                data_label = ativ.pontos[0].tempo.strftime("%d/%m") if ativ.pontos else "--"
                coluna_historico.controls.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.RUN_CIRCLE, color=ft.Colors.ORANGE),
                        title=ft.Text(f"{ativ.nome} ({data_label})"),
                        on_click=lambda e, a=ativ: mostrar_detalhes(a)
                    )
                )
            page.update()

    page.add(
        ft.Row([ft.Text("Sports Tracker Pro", size=32, weight="bold")], alignment="center"),
        ft.Divider(),
        ft.Row([ft.Button(content="Carregar Arquivos", icon=ft.Icons.UPLOAD_FILE, on_click=abrir_seletor)], alignment="center"),
        ft.ResponsiveRow([
            ft.Container(col={"md": 4}, content=coluna_historico, height=600),
            ft.Container(col={"md": 8}, content=painel_detalhes, height=600),
        ])
    )

if __name__ == "__main__":
    ft.run(main)