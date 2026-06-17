# Coleta e Aprendizado do Meu Canal

Como o sistema coleta automaticamente os vídeos do **meu próprio canal**, detecta o
jogo de cada um, mede o resultado real e confronta isso com o que ele recomendou — para
aprender **quais jogos e formatos funcionaram comigo**, não só no mercado.

> **Aviso:** o sistema **não cria roteiro, gancho, ângulo criativo nem tom de voz**. Ele
> coleta, detecta o jogo, mede performance e organiza o aprendizado. A decisão criativa é
> sempre sua. As recomendações dos relatórios são **operacionais** ("priorize curtos",
> "revisite o jogo X", "corrija um alias") — nunca sobre *como* gravar.
>
> Sem IA/LLM: tudo é casamento de texto, aritmética e ordenação.

## 1. Vídeos próprios vs. vídeos de referência

São duas fontes com papéis diferentes:

| Fonte | Arquivo | Papel |
|---|---|---|
| Referência (terceiros) | `data/videos_coletados.csv` | sinal de mercado — o que está bombando lá fora; alimenta o ranking |
| Meu canal (resultado) | `data/meus_videos.csv` | resultado real — o que de fato performou comigo; alimenta o aprendizado |

Ficam separados de propósito: misturar meus vídeos no ranking poluiria a "tendência de
mercado" com o meu próprio viés. O ranking principal **não muda** com esses comandos.

## 2. Variáveis de ambiente

| Variável | Para que serve |
|---|---|
| `YOUTUBE_API_KEY` | chave da YouTube Data API v3, usada em toda coleta de rede |
| `MEU_CANAL_YOUTUBE_ID` | ID do meu canal (ex: `UCxxxxxxxxxxxxxxxxxxxxxx`), para coletar os meus vídeos |

```bash
export YOUTUBE_API_KEY=your_key            # bash / zsh
export MEU_CANAL_YOUTUBE_ID=UCxxxx
# PowerShell:  $env:YOUTUBE_API_KEY = "your_key"
#              $env:MEU_CANAL_YOUTUBE_ID = "UCxxxx"
```

**Segurança da chave — o `.env` nunca é commitado:**

- `.env.example` guarda apenas os **nomes** das variáveis, nunca valores reais.
- O valor real vai em `.env` / `.env.local`, que estão no `.gitignore` (fora do Git).
- O código só **lê** do ambiente; a chave nunca é escrita no código, README ou testes.
- O `.env` **não é auto-carregado** — exporte as variáveis no shell antes de rodar.

Os comandos avisam de forma clara (sem quebrar) quando falta `YOUTUBE_API_KEY` ou
`MEU_CANAL_YOUTUBE_ID`.

## 3. O fluxo de ponta a ponta

```text
coletar_meu_canal          # lista meus vídeos -> detalhes + comentários ->
                           # detecta jogo -> mede resultado -> salva em meus_videos.csv
  -> meus_videos_sem_jogo  # mostra onde a detecção falhou (corrigir alias/descrição)
  -> comparar_recomendacoes_meu_canal   # ranking x resultado real: a aposta funcionou?
  -> relatorio_meu_canal   # panorama: melhores jogos, formatos e ações operacionais
```

## 4. Comandos

### `listar_meus_videos_youtube [--limite N]`
Lista os IDs e títulos dos meus vídeos recentes, **sem salvar nada**. Útil para conferir
o canal antes de coletar. Padrão `--limite 10`.
```bash
python src/main.py listar_meus_videos_youtube --limite 20
```

### `coletar_meu_canal [--limite N] [--comentarios M]`
O comando principal: lista os meus vídeos recentes, busca detalhes e comentários, detecta
o jogo de cada um, calcula o `score_resultado_real` e salva/atualiza `data/meus_videos.csv`.
No fim, mostra um resumo (analisados, jogos detectados, não detectados, novos, atualizados,
erros).
```bash
python src/main.py coletar_meu_canal --limite 20 --comentarios 50
```
- `--limite` (padrão 5) — quantos vídeos recentes analisar.
- `--comentarios` (padrão 20) — quantos comentários por vídeo puxar para a detecção.

**Quota:** o custo é `2 + 2·N` unidades, onde `N` é o `--limite` (`channels.list` +
`playlistItems.list` + por vídeo `videos.list` + `commentThreads.list`). O `--comentarios`
**não pesa** na quota — `commentThreads.list` custa 1 unidade fixa por vídeo, não importa
quantos comentários. Por isso o `--limite` padrão é pequeno; suba quando precisar.

Rodar de novo **atualiza** os vídeos já conhecidos (mesmas linhas, métricas e score novos),
sem duplicar — o de-duplicação é por `video_id`.

### `meus_videos_sem_jogo`
Lista os meus vídeos em que o jogo **não foi detectado**, ordenados por views (ataca
primeiro o buraco que mais custa). Para cada um, mostra título, data, views, URL,
confiança/fonte e uma **sugestão operacional**:
- *"adicionar alias"* — quando o título já cita o jogo, mas o seed não conhece o nome.
- *'usar padrão "Jogo: Nome" na descrição'* — quando não há sinal claro.

Não re-detecta nada: lê a detecção já salva no CSV (filtro de string, sem IA).

### `comparar_recomendacoes_meu_canal [--plataforma] [--desde] [--top]`
Cruza o ranking atual com `meus_videos.csv` por jogo e, para cada jogo recomendado, acha o
meu melhor vídeo daquele jogo e dá um **veredicto** (ver seção 6). É o feedback loop: mede
se a aposta do sistema funcionou comigo.

### `relatorio_meu_canal`
Gera um relatório Markdown datado em `reports/meu_canal_YYYY-MM-DD_HH-MM.md` com: melhores
vídeos por resultado real, jogos que mais funcionaram, vídeos sem jogo, formatos que
performaram melhor (curto/longo/live) e recomendações operacionais — com links dos vídeos.

## 5. Como o jogo é detectado

A detecção combina várias fontes, em ordem de confiança:

1. **Descrição com o padrão `Jogo: Nome do Jogo`** → confiança **alta**. É o jeito mais
   confiável: escreva uma linha `Jogo: Nome do Jogo` (ou `Game:` / `Nome do jogo:`) na
   descrição do vídeo no YouTube.
2. **Tags** → confiança média.
3. **Título** → confiança média.
4. **Comentários** → confiança **baixa**.

Em todos os casos, o nome/alias precisa existir no `jogos_seed.csv`. Se a detecção falhar,
use `adicionar_alias` (se o jogo existe no seed) ou marque `Jogo: Nome` na descrição, e
rode `coletar_meu_canal` de novo.

**Comentários ajudam, mas têm ruído.** O público costuma perguntar o nome do jogo nos
comentários ("qual o nome?", "que jogo é esse?"), o que ajuda a detectar — por isso são uma
fonte. Mas comentário é texto livre: tem brincadeira, nome errado, jogo diferente, spam. Por
isso a confiança dele é **baixa** e ele entra por último. Não confie só em comentário;
prefira o padrão `Jogo: Nome` na descrição quando quiser detecção garantida.

## 6. O arquivo `data/meus_videos.csv`

Uma linha por vídeo meu. Colunas:

`video_id, data_coleta, data_publicacao, titulo, jogo_detectado, confianca_jogo,
fonte_deteccao, url, views, likes, comentarios, tipo_video, score_resultado_real,
status_analise`

- `score_resultado_real` (0–100) — quanto o vídeo performou, na **mesma escala** do score
  de viralidade do ranking (volume + engajamento + velocidade + recência). Assim "meu
  resultado" e "tendência de mercado" são comparáveis.
- A de-duplicação é por `video_id`: recoletar atualiza métricas/score/`data_coleta` e
  **preserva** o `status_analise` já registrado.

## 7. Os veredictos da comparação

`comparar_recomendacoes_meu_canal` classifica cada jogo recomendado, cruzando a aposta do
sistema (`score_final`) com o resultado real do meu melhor vídeo:

| Veredicto | Quando | Leitura |
|---|---|---|
| `recomendacao_confirmada` | apostou alto **e** funcionou | o sistema acertou para esse perfil |
| `prometia_mas_nao_funcionou` | apostou alto **mas** foi fraco | bomba no mercado, morre comigo — desconfie |
| `funcionou_melhor_que_o_esperado` | não apostou alto **mas** funcionou | o sistema subestima esse nicho |
| `precisa_de_mais_testes` | zona cinzenta (resultado mediano) | grave mais 1–2 vídeos antes de concluir |
| `ainda_nao_testado` | sem nenhum vídeo meu do jogo | candidato a testar |

Os limiares são **heurísticas do MVP**, ainda não calibradas contra muitos resultados
reais — ajustá-los é editar constantes em `src/comparacao_meu_canal.py`.
