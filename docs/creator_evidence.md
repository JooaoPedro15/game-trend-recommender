# Evidência de Criadores e Análise por Nicho

Como o sistema usa os vídeos de criadores — e quais deles são parecidos com o seu
nicho — para mostrar o quanto um jogo já foi validado por quem cria conteúdo.

> **Aviso:** todos os pesos e limiares abaixo são **heurísticas iniciais do MVP** —
> escolhidos com critério, mas ainda não calibrados contra resultados reais do canal.
> Ajustar qualquer peso é editar uma constante (`src/ranker.py`,
> `src/evidencias_jogo.py`, `src/metricas_video.py`) ou um valor no `canais_referencia.csv`.
>
> O sistema **não decide tom, roteiro nem estilo** do vídeo. Ele organiza evidência
> (quem fez, em que formato, com que performance) — a decisão criativa é sempre sua.

## 1. Canais de referência (`canais_referencia.csv`)

Colunas: `nome,plataforma,url,peso,nicho,tipo_conteudo,peso_similaridade`

| coluna | o que é | padrão |
|---|---|---|
| `peso` | autoridade do canal como termômetro de tendência | `1.0` |
| `nicho` | categoria do canal (`gaming_humor`, `shorts_games`, `review_games`, `live_games`, `variedades`...) | `desconhecido` |
| `tipo_conteudo` | formato dominante do canal (`gameplay`, `shorts`, `live`, `review`, `cortes`, `misto`) | `desconhecido` |
| `peso_similaridade` | quão parecido o canal é do seu nicho/estilo | `1.0` |

CSV antigo (só `nome,plataforma,url,peso`) continua válido: as colunas novas assumem
os padrões acima.

### `peso` vs `peso_similaridade`
- **`peso` (autoridade)** — o quão confiável aquele canal é como sinal de que algo
  está bombando. Canal grande = sinal mais forte.
- **`peso_similaridade` (encaixe)** — o quão parecido o público dele é com o seu.
  Canal do seu nicho = o que viraliza lá tende a viralizar pra você.

São eixos independentes: um canal pode ter autoridade alta e nicho distante (ex: um
canal de review enorme).

## 2. Onde a similaridade entra no ranking

Na **tendência**, a influência de cada vídeo é:

```text
score_video * peso_canal * peso_similaridade * peso_recencia
```

Vídeo de canal mais parecido com você pesa mais. Canal sem `peso_similaridade` (ou em
`1.0`) não muda nada — comportamento idêntico ao anterior. Mantenha os valores perto de
`1.0` (ex: `1.3`, `0.7`) para amplificar/atenuar de forma suave; valores extremos deixam
um único canal dominar. Detalhes do `score_video` em [`ranking_logic.md`](ranking_logic.md).

## 3. Score de viralidade por vídeo (0–100)

É a base das evidências. Para cada vídeo:

```text
volume(40) + engajamento(30) + velocidade(20) + recencia(10), x peso (limite 100)
```

Referências de "viral" (constantes do MVP): `1.000.000` views, `10%` de engajamento,
`100.000` views/dia.

## 4. Evidência de criadores (geral) — `score_evidencia_criadores`

Quão validado o jogo está por **qualquer** criador (0–100):

```text
media da viralidade dos videos
+ bonus por canais diferentes   (6 por canal extra, teto 18)
+ bonus por varios virais       (5 por viral extra, teto 15; viral = viralidade >= 60)
+ bonus de formato              (6 se ha curto bom, 6 se ha longo bom)
-> limitado a 0..100
```

## 5. Evidência no seu nicho — `score_evidencia_nicho`

Mesma estrutura, mas só com canais **parecidos com você** (`peso_similaridade > 1.0`), e
a média de viralidade é **ponderada pela similaridade** (canal mais parecido pesa mais).
Sem nenhum canal similar entre os vídeos → **0** (o jogo viralizou fora do seu estilo).

### Como ler os dois juntos
- **geral** diz *se* o jogo viralizou; **nicho** diz *se viralizou pra você*.
- `geral` alto + `nicho` baixo = bombou, mas fora do seu estilo → **freio**.
- `geral` ≈ `nicho` = evidência sólida e relevante; o geral basta.
- jogos empatados no geral → desempate pelo nicho.

## 6. Comando `evidencias_jogo`

```bash
python src/main.py evidencias_jogo "Schedule I"
python src/main.py evidencias_jogo "Schedule I" --tipo curto
```

Mostra, para um jogo, os criadores/vídeos que servem de evidência — ordenados por
viralidade — com `nicho`, `tipo_conteudo`, `peso_similaridade`, formato do vídeo,
métricas e link, além dos dois scores de evidência e um resumo.

### Filtro `--tipo`
Mostra só os vídeos de um formato. Valores aceitos: `curto`, `longo`, `live`,
`desconhecido`. Sem `--tipo`, mostra todos. Se não houver vídeo daquele formato, avisa
claramente.

`tipo_video` é o formato **do vídeo** (curto/longo/live), diferente de `tipo_conteudo`,
que é o formato **dominante do canal**.

Separar por formato ajuda a decidir **em que formato testar**: um jogo pode ter
evidência forte em curto mas fraca em longo (ou o contrário). É só evidência — não
define o conteúdo.

## 7. Relatório de evidências

```bash
python src/main.py exportar_evidencias_jogos --top 10
```

Gera `reports/evidencias_jogos_<data>.md` com os jogos e suas evidências (mesma metadata
por vídeo), ordenado pela evidência de nicho. Aceita `--plataforma`, `--desde` e `--top`.

## 8. Onde os scores aparecem

`score_evidencia_criadores` e `score_evidencia_nicho` aparecem no terminal (`ranking`) e
nos relatórios Markdown e CSV (`exportar_ranking`), ao lado dos sub-scores e da
oportunidade. São **sinais de leitura** — não entram no `score_final`, então a ordenação
do ranking não muda por causa deles.
