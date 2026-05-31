# Lotogen

Gerador interativo de bilhetes para loterias numéricas da Caixa, com suporte a Loteca usando odds 1X2.

## O que o projeto faz

- Gera bilhetes para Mega-Sena, Lotofácil, Quina, Lotomania, Timemania, Dupla-Sena, Dia de Sorte, Super Sete e +Milionária.
- Gera palpites da Loteca a partir de odds de mandante, empate e visitante.
- Lê dados da Loteca em `loteca_atual.csv` ou em uma planilha `.xlsx`.
- Inclui um script auxiliar para atualizar o `loteca_atual.csv`.
- Inclui uma consulta da programação da Loteca na API pública da Caixa.
- Pode buscar odds 1X2 automaticamente pela The Odds API.
- Salva resultados e frequências em um banco SQLite local (`lotogen.db`).

## Requisitos

- Python 3.11 ou superior.
- Dependências listadas em `requirements.txt`.

## Instalação

Crie e ative um ambiente virtual:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Instale as dependências:

```powershell
pip install -r requirements.txt
```

## Como usar

Execute o gerador principal:

```powershell
python lotogen.py
```

O programa mostra um menu com as modalidades disponíveis. Informe os números das modalidades desejadas, a quantidade de bilhetes e, quando aplicável, a quantidade de números por aposta múltipla.

Nas perguntas de sim/não, o programa aceita `S` ou `1` para sim e `N` ou `0` para não.

Ao escolher Loteca, o programa pergunta se você deseja atualizar `loteca_atual.csv` antes de gerar os bilhetes. Se `THE_ODDS_API_KEY` estiver configurada, ele tenta buscar as odds automaticamente; caso contrário, ou se alguma odd não for encontrada, pergunta os valores manualmente.

Nas modalidades numéricas, o programa também permite escolher entre geração aleatória, números mais sorteados ou números menos sorteados. Para as opções históricas, ele sincroniza os resultados da Caixa com o banco local; por padrão usa todos os concursos disponíveis, mas você pode informar um número para limitar a consulta. Se não conseguir atualizar pela internet, usa o histórico local disponível.
Ao iniciar, depois da escolha das modalidades, o programa mostra a cobertura local de cada banco escolhido. Para modalidades numéricas, oferece atualização quando o banco histórico está vazio ou com menos de 75% dos concursos disponíveis. Se a Loteca for escolhida, também compara o concurso local com o concurso atual da Caixa e oferece atualizar quando estiver defasada.
Depois de imprimir os bilhetes gerados, o programa pergunta se você deseja salvar algum deles nos favoritos.
Bilhetes da Loteca tambem podem ser salvos; nesse caso o favorito guarda os 14 jogos com as colunas escolhidas.

## Loteca

Para a Loteca, o programa usa primeiro o banco local. O arquivo `loteca_atual.csv` continua sendo exportado apenas por compatibilidade, com 14 jogos nas linhas 2 a 15:

Quando houver mais de um concurso da Loteca salvo no banco local, o gerador lista os concursos e pergunta qual deles deve ser usado. Isso cobre periodos com concursos concomitantes, como uma edicao normal e uma edicao especial da Copa.

```csv
odd_mandante;odd_empate;odd_visitante;time_mandante;time_visitante
1.80;3.20;4.50;TIME A;TIME B
```

As três primeiras colunas são obrigatórias e devem conter odds maiores que 1. As colunas dos times são opcionais, mas ajudam a imprimir os palpites com nomes dos confrontos.

Também é possível usar uma planilha `.xlsx` com as mesmas colunas:

- Coluna A: odd do mandante
- Coluna B: odd do empate
- Coluna C: odd do visitante
- Coluna D: time mandante
- Coluna E: time visitante

## Atualizar o CSV da Loteca

Você pode atualizar pelo próprio `lotogen.py` ao escolher Loteca, ou usar o script auxiliar:

```powershell
python gera_loteca.py
```

Ele busca os 14 jogos oficiais na API da Caixa, pergunta as odds se necessário, salva no banco local e atualiza `loteca_atual.csv`.
Se a Caixa retornar mais de um concurso disponivel, o script pergunta qual deles deve atualizar. Tambem e possivel informar o concurso diretamente com `--concurso`.
Se o banco local já tiver esse concurso, o script não consulta a The Odds API novamente; ele apenas atualiza o CSV de compatibilidade quando necessário.

Para tentar preencher as odds automaticamente pela The Odds API, configure a chave antes de rodar:

```powershell
$env:THE_ODDS_API_KEY="sua_chave_aqui"
python gera_loteca.py
```

Consulte a documentação oficial da The Odds API em <https://the-odds-api.com/liveapi/guides/v4/>. No momento, a The Odds API oferece um plano gratuito limitado para testes e protótipos, sem cartão de crédito, mas os limites e condições podem mudar. O limite atual do plano gratuito é suficiente para o uso neste programa.

Se alguma odd não for encontrada, o programa pergunta manualmente apenas os jogos pendentes.

Variáveis opcionais:

- `THE_ODDS_API_SPORT_KEYS`: lista de competições separadas por vírgula. Padrão: `soccer_brazil_campeonato,soccer_brazil_serie_b,soccer_epl`.
- `THE_ODDS_API_ALL_SOCCER`: consulta todas as competições de futebol ativas da The Odds API. Padrão: desligado.
- `THE_ODDS_API_REGIONS`: regiões de casas de aposta. Padrão: `eu,uk`.
- `THE_ODDS_API_BOOKMAKERS`: filtra casas de aposta específicas e substitui `THE_ODDS_API_REGIONS`.
- `THE_ODDS_API_DEBUG`: mostra detalhes técnicos das chamadas da The Odds API. Padrão: desligado.
- `THE_ODDS_API_MATCH_MIN_SCORE`: pontuação mínima para casar nomes de times. Padrão: `0.78`.
- `LOTOGEN_COBERTURA_MINIMA`: cobertura mínima do banco histórico antes de oferecer atualização. Padrão: `0.75`.

Opções úteis:

```powershell
python gera_loteca.py --concurso 1255
python gera_loteca.py --manual --concurso 1253
python gera_loteca.py --saida outro_arquivo.csv
```

## Consulta da API da Caixa

O arquivo `consulta_loteca.py` consulta a programação da Loteca na API da Caixa:

```powershell
python consulta_loteca.py
```

Com `THE_ODDS_API_KEY` configurada, ele também tenta exibir as odds 1X2 encontradas.

Esse script depende de acesso a internet e da disponibilidade da API.

## Bilhetes Favoritos

O arquivo `favoritos.py` permite cadastrar, listar e remover bilhetes favoritos no banco local:

```powershell
python favoritos.py adicionar timemania 04 06 08 09 10 27 46 75 76 79 Internacional/RS
python favoritos.py adicionar mega 03 04 09 12 23 51
python favoritos.py adicionar loteca 1 X 2 1/X 1 2 X 1 X 2 1 1/X X 2
python favoritos.py listar
python favoritos.py remover 1
```

Ao executar `python favoritos.py` sem subcomando, ele abre um menu interativo.

## Estrutura

- `lotogen.py`: gerador principal e leitura de CSV/XLSX da Loteca.
- `gera_loteca.py`: assistente para gerar ou atualizar `loteca_atual.csv`.
- `consulta_loteca.py`: consulta reutilizável da programação da Loteca.
- `favoritos.py`: gerenciador de bilhetes favoritos.
- `historico_loterias.py`: consulta resultados históricos das modalidades numéricas.
- `banco_lotogen.py`: cria e acessa o banco SQLite local.
- `lotogen.db`: banco local criado automaticamente.
- `loteca_atual.csv`: arquivo atual de odds e confrontos da Loteca, exportado por compatibilidade.
