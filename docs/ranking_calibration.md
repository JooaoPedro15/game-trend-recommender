# Calibração com Dados do Meu Canal

Como o sistema usa os **meus próprios vídeos** (`data/meus_videos.csv`) para ajustar as
recomendações — medir se um jogo funcionou comigo, empurrar de leve o ranking, sugerir
formato, refinar a ação e gerar listas operacionais.

> **Aviso:** todos os pesos e limiares abaixo são **heurísticas iniciais do MVP** —
> escolhidos com critério, mas ainda não calibrados contra muitos resultados reais.
> Ajustar qualquer um é editar uma constante (`src/ranker.py`, `src/fit_canal.py`,
> `src/repetir_jogos.py`, `src/jogos_falhos.py`).
>
> O sistema **não decide roteiro, gancho, ângulo nem tom de voz**. Ele mede performance,
> aponta formato operacional (curto/longo/live) e organiza evidência. **A decisão
> criativa continua sendo sua** — o quê falar, como abrir, o tom: tudo seu.
>
> Sem IA/LLM: tudo é casamento de texto, aritmética e ordenação.

## Pré-requisito

A calibração só age quando há `data/meus_videos.csv` (gerado por `coletar_meu_canal` — ver
[`own_channel_learning.md`](own_channel_learning.md)). **Sem esse arquivo, ou para um jogo
que você nunca gravou, o ranking se comporta exatamente como antes** — a calibração só
refina onde existe dado real, nunca penaliza ausência.

## 1. `score_fit_real` — o encaixe medido

Enquanto o `fit_inicial` (em `jogos_seed.csv`) é um **palpite a priori** de quanto um jogo
combina com o canal, o `fit_real` é **medido**: a média do `score_resultado_real` dos meus
vídeos daquele jogo (`fit_canal.calcular_fit_real_jogo`).

- Escala 0–100, a mesma do score de viralidade — meu resultado e a tendência de mercado
  ficam comparáveis.
- Jogo **nunca gravado** → `None` (exibido como `n/d`): "ainda não testado", **sem dado**.
  Não é 0 — ausência de teste é diferente de teste ruim, e não penaliza.

## 2. Ajuste leve no `score_final`

Quando há `fit_real`, o `score_final` ganha um empurrãozinho — nunca um domínio
(`ranker._ajuste_fit_real`):

```text
fit_real >= 60  ->  +0 a +5   (rampa: 0 em 60, +5 em 100)
fit_real <= 30  ->  -5 a 0    (rampa: -5 em 0, 0 em 30)
30 < fit_real < 60  ->  0     (zona morta)
fit_real None       ->  0     (sem histórico)
```

Teto de **±5 pontos** num score 0–100, com zona morta no meio. Por que leve:
`meus_videos.csv` é pequeno e enviesado; se pesasse muito, o ranking viraria espelho do
passado e eu nunca descobriria jogo novo. Os pesos base do ranking
(40/35/15/10, ver [`ranking_logic.md`](ranking_logic.md)) **não mudam** — o fit_real só
desempata na borda: "além de bombar lá fora, já deu certo comigo".

## 3. Formato sugerido por histórico

`formato_sugerido` (no ranking) diz o formato operacional — `curto` / `longo` / `live` —
calibrado pelo que funcionou comigo (`fit_canal.sugerir_formato_por_historico`):

1. Agrupa meus vídeos do jogo por `tipo_video` e tira a média do resultado de cada formato.
2. Se algum formato sugerível teve média boa (≥ 50), sugere o de melhor média.
3. Sem histórico (ou histórico fraco), mantém o formato já implícito na ação recomendada.

Só o **recipiente** (formato), nunca o conteúdo dentro dele.

## 4. Ação recomendada com feedback real

A `acao_recomendada` agora tem duas ramificações (`ranker._gerar_acao_recomendada`):

**Com histórico real do jogo** (`fit_real` existe) — meus dados mandam:

| condição | ação |
|---|---|
| falhou comigo (`fit_real` ≤ 30) | `Monitorar antes de repetir` |
| um formato funcionou e outro não | `Priorizar <formato>` |
| funcionou bem (`fit_real` ≥ 60) | `Repetir teste` |
| resultado mediano | `Monitorar por mais alguns dias` |

**Sem histórico** — evidência externa (comportamento anterior), agora também sensível à
evidência no meu nicho: `Evitar por saturacao alta`, `Priorizar para video longo`,
`Testar em Short` (oportunidade alta **ou** evidência de nicho ≥ 70),
`Pesquisar mais videos antes de gravar`, `Monitorar por mais alguns dias`.

## 5. Listas operacionais

### `jogos_para_repetir` (`repetir_jogos.py`)
Jogos que **já funcionaram comigo e ainda têm janela aberta** — apostas de menor risco que
um jogo novo. Entra quem passa nos três cortes: `score_resultado_real` ≥ 60,
`score_oportunidade` ≥ 50, `score_saturacao` ≥ 45. Mostra jogo, melhor vídeo meu, resultado
real, oportunidade, formato que funcionou, link e um motivo curto.

### `jogos_que_nao_funcionaram` (`jogos_falhos.py`)
O espelho: jogos de **alta evidência externa que renderam pouco comigo** — a armadilha de
repetir só porque viralizou fora. Entra quem tem `score_evidencia_nicho` ≥ 60 **e**
`score_oportunidade` ≥ 60 **mas** o melhor vídeo meu ficou abaixo de 40. Pega o melhor vídeo
de propósito: se até ele flopou, a falha comigo é inequívoca.

## 6. `relatorio_calibracao`

Consolida tudo acima num Markdown datado (`reports/calibracao_ranking_YYYY-MM-DD_HH-MM.md`),
mostrando como o canal influencia o ranking: jogos que o sistema acertou, que prometiam mas
falharam, que funcionaram melhor que o esperado, para monitorar, para repetir, os formatos
que funcionam melhor comigo, o `fit_real` dos principais jogos e os links dos meus vídeos
usados como evidência. É **prestação de contas** — torna o ranking auditável contra a
realidade do meu canal. Pura composição dos blocos acima, sem cálculo novo.

## 7. Limites

- Tudo aqui é **heurístico** e pré-calibração: os cortes (60/30, ±5, 50, 45, etc.) são
  pontos de partida, não verdades. Refinam-se editando constantes conforme o
  `meus_videos.csv` cresce.
- A calibração **mede e aponta**; **não cria** roteiro, gancho ou tom. A escolha do jogo, do
  formato e — sempre — de **como** gravar continua sendo sua.
