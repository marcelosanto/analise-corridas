import flet as ft
import gpxpy
from tcxreader.tcxreader import TCXReader
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

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
# FUNÇÕES DE LEITURA (PARSERS)
# ==========================================
def ler_gpx(caminho_ficheiro: str) -> Atividade:
    with open(caminho_ficheiro, 'r', encoding='utf-8') as gpx_file:
        gpx = gpxpy.parse(gpx_file)
        
        pontos = []
        soma_fc = 0
        contagem_fc = 0

        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    fc = None
                    cadencia = None
                    
                    # Tentar extrair HR e Cadência das extensões do GPX
                    if point.extensions:
                        for ext in point.extensions[0].iter():
                            if 'hr' in ext.tag:
                                fc = int(ext.text)
                                soma_fc += fc
                                contagem_fc += 1
                            if 'cad' in ext.tag:
                                cadencia = int(ext.text)

                    pontos.append(PontoTreino(
                        latitude=point.latitude,
                        longitude=point.longitude,
                        elevacao=point.elevation,
                        tempo=point.time,
                        frequencia_cardiaca=fc,
                        cadencia=cadencia
                    ))
        
        fc_media = (soma_fc // contagem_fc) if contagem_fc > 0 else None
        
        # O gpxpy pode inferir o tipo e o nome
        nome = gpx.tracks[0].name if gpx.tracks and gpx.tracks[0].name else "Atividade GPX"
        tipo = gpx.tracks[0].type if gpx.tracks and gpx.tracks[0].type else "Desconhecido"

        return Atividade(
            nome=nome,
            tipo=tipo,
            distancia_total_km=gpx.length_3d() / 1000,
            tempo_total_minutos=gpx.get_duration() / 60 if gpx.get_duration() else 0.0,
            frequencia_cardiaca_media=fc_media,
            pontos=pontos
        )

def ler_tcx(caminho_ficheiro: str) -> Atividade:
    leitor = TCXReader()
    dados_tcx = leitor.read(caminho_ficheiro)
    
    pontos = []
    
    for tp in dados_tcx.trackpoints:
        # Apenas adicionar se houver coordenadas válidas
        if tp.latitude and tp.longitude:
            pontos.append(PontoTreino(
                latitude=tp.latitude,
                longitude=tp.longitude,
                elevacao=tp.elevation,
                tempo=tp.time,
                frequencia_cardiaca=tp.hr_value,
                cadencia=tp.cadence
            ))
            
    return Atividade(
        nome="Atividade TCX (Exportada)", # TCX geralmente não tem nome fácil no cabeçalho
        tipo=dados_tcx.activity_type,
        distancia_total_km=dados_tcx.distance / 1000 if dados_tcx.distance else 0.0,
        tempo_total_minutos=dados_tcx.duration / 60 if dados_tcx.duration else 0.0,
        frequencia_cardiaca_media=dados_tcx.hr_avg,
        pontos=pontos
    )

# ==========================================
# INTERFACE DO UTILIZADOR (FLET) - NOVA API
# ==========================================
def main(page: ft.Page):
    page.title = "Análise de Corridas - Fase 1"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 30
    page.scroll = "auto"

    texto_estado = ft.Text(value="A aguardar ficheiro...", italic=True, color=ft.Colors.GREY_400)
    painel_detalhes = ft.Column(spacing=10)

    def processar_ficheiro(caminho: str):
        try:
            texto_estado.value = f"A processar: {caminho.split('/')[-1]}..."
            page.update()

            if caminho.lower().endswith('.gpx'):
                atividade = ler_gpx(caminho)
            elif caminho.lower().endswith('.tcx'):
                atividade = ler_tcx(caminho)
            else:
                raise ValueError("Formato não suportado.")

            painel_detalhes.controls.clear()
            painel_detalhes.controls.append(
                ft.Card(
                    content=ft.Container(
                        padding=20,
                        content=ft.Column([
                            ft.Text(atividade.nome, size=24, weight=ft.FontWeight.BOLD),
                            ft.Text(f"Tipo: {atividade.tipo.capitalize()}", size=16),
                            ft.Divider(),
                            ft.Row([
                                ft.Icon(ft.Icons.ROUTE, color=ft.Colors.BLUE),
                                ft.Text(f"Distância: {atividade.distancia_total_km:.2f} km", size=18)
                            ]),
                            ft.Row([
                                ft.Icon(ft.Icons.TIMER, color=ft.Colors.GREEN),
                                ft.Text(f"Tempo: {atividade.tempo_total_minutos:.2f} min", size=18)
                            ]),
                            ft.Row([
                                ft.Icon(ft.Icons.FAVORITE, color=ft.Colors.RED),
                                ft.Text(f"FC Média: {atividade.frequencia_cardiaca_media or '--'} bpm", size=18)
                            ]),
                            ft.Row([
                                ft.Icon(ft.Icons.LOCATION_ON, color=ft.Colors.AMBER),
                                ft.Text(f"Pontos de GPS registados: {len(atividade.pontos)}", size=18)
                            ]),
                        ])
                    )
                )
            )
            texto_estado.value = "Carregamento concluído com sucesso!"

        except Exception as e:
            texto_estado.value = f"Erro ao processar: {str(e)}"
            texto_estado.color = ft.Colors.RED_400

        page.update()

    # O SEGREDO DA NOVA API ESTÁ AQUI:
    async def abrir_seletor(e: ft.Event[ft.Button]):
        # Chama diretamente o seletor e aguarda o resultado
        files = await ft.FilePicker().pick_files(
            allow_multiple=False,
            allowed_extensions=["gpx", "tcx"]
        )
        
        # Se o utilizador escolheu um ficheiro (não cancelou)
        if files:
            processar_ficheiro(files[0].path)
        else:
            texto_estado.value = "Seleção cancelada."
            page.update()

    # Layout Principal
    page.add(
        ft.Row([
            ft.Icon(ft.Icons.DIRECTIONS_RUN, size=40, color=ft.Colors.ORANGE_500),
            ft.Text("Leitor GPX/TCX Unificado", size=32, weight=ft.FontWeight.BOLD)
        ], alignment=ft.MainAxisAlignment.CENTER),
        
        ft.Divider(height=30),
        
        ft.Row([
            ft.Button(
                content="Selecionar Atividade (GPX/TCX)", # Pode usar text ou content
                icon=ft.Icons.UPLOAD_FILE,
                on_click=abrir_seletor,
            ),
        ], alignment=ft.MainAxisAlignment.CENTER),
        
        ft.Row([texto_estado], alignment=ft.MainAxisAlignment.CENTER),
        
        ft.Container(height=20),
        
        ft.Row([painel_detalhes], alignment=ft.MainAxisAlignment.CENTER)
    )

if __name__ == "__main__":
    ft.run(main)