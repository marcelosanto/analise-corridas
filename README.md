
# Sports Tracker Analyzer 🏃‍♂️📊

O **Sports Tracker Analyzer** é uma aplicação desktop desenvolvida em Python para entusiastas de corrida e ciclismo. Ela permite importar arquivos de atividades (GPX e TCX), visualizar o trajeto em um mapa interativo nativo e analisar o desempenho através de gráficos de Frequência Cardíaca e Pace, tudo correlacionado pela distância.

## ✨ Funcionalidades

-   **Importação Multi-Formato:** Suporte completo para arquivos `.gpx` (Strava, Garmin, etc) e `.tcx`.
    
-   **Dashboard Responsivo:** Interface moderna desenvolvida com Flet, adaptável a diferentes tamanhos de janela.
    
-   **Gráficos de Performance:** Visualização unificada de Batimentos Cardíacos (BPM) e Ritmo (Pace min/km) por Quilômetro.
    
-   **Mapa Nativo:** Visualização do percurso diretamente na aplicação com marcadores de início e fim.
    
-   **Análise Inteligente:** Tratamento automático de fusos horários e filtragem de ruídos de GPS para dados precisos.
    

## 🚀 Tecnologias Utilizadas

-   [Flet](https://flet.dev/) - Framework de UI baseado em Flutter.
    
-   [Flet Map](https://flet.dev/docs/controls/map) - Integração de mapas OpenStreetMap.
    
-   [Matplotlib](https://matplotlib.org/) - Geração de gráficos de alta fidelidade.
    
-   [Gpxpy](https://github.com/tkrajina/gpxpy) - Parser de arquivos GPX.
    
-   [Tcxreader](https://www.google.com/search?q=https://github.com/firefly-cpp/tcxreader) - Parser de arquivos TCX.
    
-   [Poetry](https://python-poetry.org/) - Gerenciamento de dependências.
    

## 📦 Como Instalar

1.  **Clone o repositório:**
    
    Bash
    
    ```
    git clone https://github.com/seu-usuario/analise-corridas.git
    cd analise-corridas
    
    ```
    
2.  **Instale as dependências com Poetry:**
    
    Bash
    
    ```
    poetry install
    
    ```
    
3.  **Adicione o plugin de mapas (se necessário):**
    
    Bash
    
    ```
    poetry add flet-map
    
    ```
    

## 🛠️ Como Usar

1.  **Inicie a aplicação:**
    
    Bash
    
    ```
    poetry run python main.py
    
    ```
    
2.  Clique no botão **"Carregar Arquivos"** e selecione suas atividades.
    
3.  Selecione uma corrida na lista lateral para ver os detalhes, gráficos e mapa.
    

## 🗺️ Roadmap de Desenvolvimento

-   [x] Fase 1: Leitura de GPX/TCX.
    
-   [x] Fase 2: Gráficos de FC e Pace por KM.
    
-   [x] Fase 3: Mapa nativo com marcadores.
    
-   [ ] Fase 4: Integração com API do Strava.
    
-   [ ] Fase 5: Comparação direta entre duas atividades sobrepostas.
    

----------

Desenvolvido por Marcelo Santos - 2026.
