# analise_combustiveis.py

import os
import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from glob import glob

# ============================================
# CONFIGURAÇÕES GERAIS
# ============================================
BASE_URL = "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/shpc/dsan"
ANOS = [2024, 2025]
PRODUTOS_CONFIG = {
    "GLP": {
        "pasta": "dados_glp",
        "prefixo": "precos-glp"
    },
    "Gasolina_Etanol": {
        "pasta": "dados_gasolina_etanol",
        "prefixo": "precos-gasolina-etanol"
    }
}
OUTPUT_DIR = "graficos"

# ============================================
# FUNÇÕES PRINCIPAIS
# ============================================

def baixar_dados():
    """
    Baixa os arquivos CSV do site da ANP para os anos e produtos configurados.
    Verifica se o arquivo já existe antes de baixar.
    """
    print("--- INICIANDO DOWNLOAD DOS DADOS DA ANP ---")
    for config in PRODUTOS_CONFIG.values():
        os.makedirs(config['pasta'], exist_ok=True)

    for ano in ANOS:
        for mes in range(1, 13):
            mes_str = f"{mes:02d}"
            for config in PRODUTOS_CONFIG.values():
                url = f"{BASE_URL}/{ano}/{config['prefixo']}-{mes_str}.csv"
                destino = os.path.join(config['pasta'], f"{config['prefixo']}-{ano}-{mes_str}.csv")

                if os.path.exists(destino):
                    print(f"🔹 Arquivo já existe: {destino}")
                    continue

                try:
                    print(f"⬇️ Baixando: {url}")
                    resp = requests.get(url, timeout=30)
                    resp.raise_for_status()
                    with open(destino, "wb") as f:
                        f.write(resp.content)
                    print(f"✔ Salvo em: {destino}")
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 404:
                        print(f"⚠️ Arquivo não encontrado (404): {url}")
                    else:
                        print(f"❌ Erro HTTP ao baixar {url}: {e}")
                except requests.exceptions.RequestException as e:
                    print(f"❌ Erro de conexão ao baixar {url}: {e}")
    print("\n--- DOWNLOAD FINALIZADO ---\n")

def carregar_e_limpar_dados(pasta, separador_produto=False):
    """
    Carrega todos os arquivos CSV de uma pasta, os concatena e realiza a limpeza.
    """
    arquivos_csv = glob(os.path.join(pasta, "*.csv"))
    if not arquivos_csv:
        print(f"⚠️ Nenhum arquivo CSV encontrado em '{pasta}'")
        return pd.DataFrame()

    print(f"🔄 Carregando e limpando dados de: {pasta}")
    df_list = [pd.read_csv(f, sep=";", encoding="latin1") for f in arquivos_csv]
    df = pd.concat(df_list, ignore_index=True)

    # Limpeza e conversão de tipos
    df['Valor de Venda'] = pd.to_numeric(df['Valor de Venda'].astype(str).str.replace(',', '.'), errors='coerce')
    df['Data da Coleta'] = pd.to_datetime(df['Data da Coleta'], format='%d/%m/%Y', errors='coerce')
    df.dropna(subset=['Valor de Venda', 'Data da Coleta', 'Produto', 'Estado - Sigla'], inplace=True)

    # O arquivo de gasolina/etanol contém múltiplos produtos que precisam ser distinguidos.
    if separador_produto:
        df = df[df['Produto'].isin(['GASOLINA', 'ETANOL'])]

    print("✔ Dados carregados e limpos com sucesso.")
    return df

def gerar_graficos(df_glp, df_combustiveis):
    """
    Gera e salva os gráficos da análise.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    sns.set_style("whitegrid")
    print("\n--- GERANDO GRÁFICOS ---")

    # --- GRÁFICO 1: Evolução do Preço Médio Mensal ---
    df_glp_monthly = df_glp.set_index('Data da Coleta').resample('M')['Valor de Venda'].mean()
    df_gasolina_monthly = df_combustiveis[df_combustiveis['Produto'] == 'GASOLINA'].set_index('Data da Coleta').resample('M')['Valor de Venda'].mean()
    df_etanol_monthly = df_combustiveis[df_combustiveis['Produto'] == 'ETANOL'].set_index('Data da Coleta').resample('M')['Valor de Venda'].mean()

    plt.figure(figsize=(12, 7))
    plt.plot(df_gasolina_monthly.index, df_gasolina_monthly.values, label='Gasolina', marker='o')
    plt.plot(df_etanol_monthly.index, df_etanol_monthly.values, label='Etanol', marker='o')
    plt.plot(df_glp_monthly.index, df_glp_monthly.values, label='GLP (Botijão 13kg)', marker='o', linestyle='--')
    
    plt.title('Evolução Mensal do Preço Médio dos Combustíveis (2024-2025)', fontsize=16)
    plt.xlabel('Mês/Ano', fontsize=12)
    plt.ylabel('Preço Médio (R$)', fontsize=12)
    plt.legend()
    plt.grid(True)
    caminho_grafico1 = os.path.join(OUTPUT_DIR, '1_evolucao_precos_mensal.png')
    plt.savefig(caminho_grafico1, dpi=300)
    plt.close()
    print(f"✔ Gráfico 1 salvo em: {caminho_grafico1}")

    # --- GRÁFICO 2: Top 5 Estados Mais Caros e Mais Baratos (Gasolina) ---
    media_gasolina_estado = df_combustiveis[df_combustiveis['Produto'] == 'GASOLINA'].groupby('Estado - Sigla')['Valor de Venda'].mean().sort_values()
    
    top5_caros = media_gasolina_estado.tail(5)
    top5_baratos = media_gasolina_estado.head(5)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6), sharey=True)
    fig.suptitle('Preço Médio da Gasolina por Estado', fontsize=16)
    
    sns.barplot(x=top5_caros.values, y=top5_caros.index, ax=ax1, palette='Reds_r')
    ax1.set_title('5 Estados mais Caros')
    ax1.set_xlabel('Preço Médio (R$)')
    
    sns.barplot(x=top5_baratos.values, y=top5_baratos.index, ax=ax2, palette='Greens_r')
    ax2.set_title('5 Estados mais Baratos')
    ax2.set_xlabel('Preço Médio (R$)')
    
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    caminho_grafico2 = os.path.join(OUTPUT_DIR, '2_comparativo_estados_gasolina.png')
    plt.savefig(caminho_grafico2, dpi=300)
    plt.close()
    print(f"✔ Gráfico 2 salvo em: {caminho_grafico2}")

    # --- GRÁFICO 3: Relação de Preço Etanol/Gasolina por Estado ---
    media_combustiveis = df_combustiveis.groupby(['Estado - Sigla', 'Produto'])['Valor de Venda'].mean().unstack()
    media_combustiveis['Relacao_Etanol_Gasolina'] = media_combustiveis['ETANOL'] / media_combustiveis['GASOLINA']
    media_combustiveis.sort_values('Relacao_Etanol_Gasolina', inplace=True)
    
    media_combustiveis['Cor'] = ['#2ca02c' if x <= 0.7 else '#d62728' for x in media_combustiveis['Relacao_Etanol_Gasolina']]

    plt.figure(figsize=(15, 8))
    bars = plt.barh(media_combustiveis.index, media_combustiveis['Relacao_Etanol_Gasolina'], color=media_combustiveis['Cor'])
    
    plt.axvline(x=0.7, color='black', linestyle='--', label='Limite de 70% (Vantajoso para Etanol)')
    plt.title('Relação de Preço Etanol/Gasolina por Estado', fontsize=16)
    plt.xlabel('Relação de Preço (Etanol / Gasolina)', fontsize=12)
    plt.ylabel('Estado', fontsize=12)
    plt.legend()
    
    caminho_grafico3 = os.path.join(OUTPUT_DIR, '3_relacao_etanol_gasolina.png')
    plt.savefig(caminho_grafico3, dpi=300)
    plt.close()
    print(f"✔ Gráfico 3 salvo em: {caminho_grafico3}")


if __name__ == "__main__":
    # 1. Baixar os dados mais recentes
    baixar_dados()

    # 2. Carregar e limpar os dados
    df_glp = carregar_e_limpar_dados(PRODUTOS_CONFIG['GLP']['pasta'])
    df_combustiveis = carregar_e_limpar_dados(PRODUTOS_CONFIG['Gasolina_Etanol']['pasta'], separador_produto=True)

    # 3. Gerar e salvar os gráficos se os dados foram carregados
    if not df_glp.empty and not df_combustiveis.empty:
        gerar_graficos(df_glp, df_combustiveis)
        print("\n--- ANÁLISE CONCLUÍDA ---")
    else:
        print("\n--- ANÁLISE NÃO REALIZADA DEVIDO À AUSÊNCIA DE DADOS ---")