# Lotogen

Gerador interativo de bilhetes para loterias numericas da Caixa, com suporte a Loteca usando odds 1X2.

## O que o projeto faz

- Gera bilhetes para Mega-Sena, Lotofacil, Quina, Lotomania, Timemania, Dupla-Sena, Dia de Sorte, Super Sete e +Milionaria.
- Gera palpites da Loteca a partir de odds de mandante, empate e visitante.
- Le dados da Loteca em `loteca_atual.csv` ou em uma planilha `.xlsx`.
- Inclui um script auxiliar para atualizar o `loteca_atual.csv`.
- Inclui uma consulta da programacao da Loteca na API publica da Caixa.
- Pode buscar odds 1X2 automaticamente pela The Odds API.
- Salva resultados e frequencias em um banco SQLite local (`lotogen.db`).

## Requisitos

- Python 3.11 ou superior.
- Dependencias listadas em `requirements.txt`.

## Instalacao

Crie e ative um ambiente virtual:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Instale as dependencias:

```powershell
pip install -r requirements.txt
```

## Como usar

Execute o gerador principal:

```powershell
python lotogen.py
```

O programa mostra um menu com as modalidades disponiveis. Informe os numeros das modalidades desejadas, a quantidade de bilhetes e, quando aplicavel, a quantidade de numeros por aposta multipla.

Ao escolher Loteca, o programa pergunta se voce deseja atualizar `loteca_atual.csv` antes de gerar os bilhetes. Se `THE_ODDS_API_KEY` estiver configurada, ele tenta buscar as odds automaticamente; caso contrario, ou se alguma odd nao for encontrada, pergunta os valores manualmente.

Nas modalidades numericas, o programa tambem permite escolher entre geracao aleatoria, numeros mais sorteados ou numeros menos sorteados. Para as opcoes historicas, ele sincroniza os resultados da Caixa com o banco local; por padrao usa os ultimos 200 concursos, mas voce pode informar `0` para usar todos os concursos disponiveis. Se nao conseguir atualizar pela internet, usa o historico local disponivel.
Ao iniciar, depois da escolha das modalidades, o programa mostra a cobertura local de cada banco escolhido. Para modalidades numericas, oferece atualizacao quando o banco historico esta vazio ou com menos de 75% dos concursos disponiveis. Se a Loteca for escolhida, tambem compara o concurso local com o concurso atual da Caixa e oferece atualizar quando estiver defasada.

## Loteca

Para a Loteca, o programa usa primeiro o banco local. O arquivo `loteca_atual.csv` continua sendo exportado apenas por compatibilidade, com 14 jogos nas linhas 2 a 15:

```csv
odd_mandante;odd_empate;odd_visitante;time_mandante;time_visitante
1.80;3.20;4.50;TIME A;TIME B
```

As tres primeiras colunas sao obrigatorias e devem conter odds maiores que 1. As colunas dos times sao opcionais, mas ajudam a imprimir os palpites com nomes dos confrontos.

Tambem e possivel usar uma planilha `.xlsx` com as mesmas colunas:

- Coluna A: odd do mandante
- Coluna B: odd do empate
- Coluna C: odd do visitante
- Coluna D: time mandante
- Coluna E: time visitante

## Atualizar o CSV da Loteca

Voce pode atualizar pelo proprio `lotogen.py` ao escolher Loteca, ou usar o script auxiliar:

```powershell
python gera_loteca.py
```

Ele busca os 14 jogos oficiais na API da Caixa, pergunta as odds se necessario, salva no banco local e atualiza `loteca_atual.csv`.
Se o banco local ou `loteca_atual.csv` ja estiverem no concurso atual, o script nao consulta a The Odds API novamente.

Para tentar preencher as odds automaticamente pela The Odds API, configure a chave antes de rodar:

```powershell
$env:THE_ODDS_API_KEY="sua_chave_aqui"
python gera_loteca.py
```

Se alguma odd nao for encontrada, o programa pergunta manualmente apenas os jogos pendentes.

Variaveis opcionais:

- `THE_ODDS_API_SPORT_KEYS`: lista de competicoes separadas por virgula. Padrao: `soccer_brazil_campeonato,soccer_brazil_serie_b,soccer_epl`.
- `THE_ODDS_API_ALL_SOCCER`: consulta todas as competicoes de futebol ativas da The Odds API. Padrao: desligado.
- `THE_ODDS_API_REGIONS`: regioes de casas de aposta. Padrao: `eu,uk`.
- `THE_ODDS_API_BOOKMAKERS`: filtra casas de aposta especificas e substitui `THE_ODDS_API_REGIONS`.
- `THE_ODDS_API_DEBUG`: mostra detalhes tecnicos das chamadas da The Odds API. Padrao: desligado.
- `THE_ODDS_API_MATCH_MIN_SCORE`: pontuacao minima para casar nomes de times. Padrao: `0.78`.
- `LOTOGEN_COBERTURA_MINIMA`: cobertura minima do banco historico antes de oferecer atualizacao. Padrao: `0.75`.

Opcoes uteis:

```powershell
python gera_loteca.py --manual --concurso 1253
python gera_loteca.py --saida outro_arquivo.csv
```

## Consulta da API da Caixa

O arquivo `consulta_loteca.py` consulta a programacao da Loteca na API da Caixa:

```powershell
python consulta_loteca.py
```

Com `THE_ODDS_API_KEY` configurada, ele tambem tenta exibir as odds 1X2 encontradas.

Esse script depende de acesso a internet e da disponibilidade da API.

## Estrutura

- `lotogen.py`: gerador principal e leitura de CSV/XLSX da Loteca.
- `gera_loteca.py`: assistente para gerar ou atualizar `loteca_atual.csv`.
- `consulta_loteca.py`: consulta reutilizavel da programacao da Loteca.
- `historico_loterias.py`: consulta resultados historicos das modalidades numericas.
- `banco_lotogen.py`: cria e acessa o banco SQLite local.
- `lotogen.db`: banco local criado automaticamente.
- `loteca_atual.csv`: arquivo atual de odds e confrontos da Loteca, exportado por compatibilidade.
