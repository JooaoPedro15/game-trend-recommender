# Lógica do Ranking

Como cada número do ranking é calculado, do vídeo individual até a ação recomendada.

> **Aviso:** todos os pesos e limiares abaixo são **heurísticas iniciais do MVP** —
> escolhidos com critério, mas ainda não calibrados contra resultados reais do canal.
> A calibração (comparar o ranking com o que de fato performou) é trabalho futuro.
> Ajustar qualquer peso é editar uma constante em `src/ranker.py`.

## 1. Score de um vídeo individual

```text
score_video = (views + likes*5 + comentarios*20
               + bonus_engajamento + bonus_velocidade) * peso_plataforma
```

### Engajamento
`taxa = (likes + comentarios) / views` (0 se views = 0), centralizado em
`metricas_video.calcular_taxa_engajamento`. Bônus no score: `views * taxa * 2`.
Vídeo com público que interage vale mais que view passiva.

### Velocidade (views por dia)
`views / max(idade_em_dias, 1)`, em `metricas_video.calcular_views_por_dia`
(data inválida → 0). Bônus no score: `min(velocidade * 0.5, views * 0.5)` — o teto
impede que um vídeo postado hoje conte duas vezes as próprias views. Velocidade
aparece no terminal e nos relatórios como `views/dia`.

### Peso por plataforma
Views de autoplay (TikTok/Reels) valem um pouco menos que views do YouTube:

| plataforma | peso |
|---|---|
| youtube | 1.0 |
| shorts | 0.9 |
| tiktok | 0.8 |
| instagram | 0.8 |
| desconhecida | 1.0 (neutro) |

## 2. Sub-scores por jogo (todos 0–100)

### Tendência (peso 0.40 no final)
Soma dos `score_video` do jogo, cada um multiplicado por:
- **peso do canal** (`canais_referencia.csv`, padrão 1.0);
- **peso de recência**: ≤7 dias ×1.3 · ≤30 ×1.1 · ≤90 ×0.9 · mais antigo ×0.6
  (data inválida ×1.0).

O total é normalizado pelo maior valor entre os jogos → o líder de tendência
marca 100 e os demais ficam proporcionais.

### Fit com o canal (0.35)
`fit_inicial` (0–10, definido em `jogos_seed.csv`) reescalado para 0–100.
É o único sub-score que não vem dos vídeos: é o seu julgamento de quanto o jogo
combina com o canal.

### Descoberta (0.15)
Procura frases de curiosidade ("qual o nome", "what game", "tem na steam"...) no
título + comentários. `proporcao_de_videos_com_sinal * 70 + min(total_sinais, 3) * 10`.
Público perguntando pelo jogo = demanda não atendida.

### Saturação (0.10)
Quantos canais de referência já cobriram: 1 canal → 90 · 2 → 75 · 3 → 55 ·
depois −10 por canal (piso 20). Score **alto = pouca saturação** = janela aberta.

## 3. Scores compostos

```text
score_final        = tendencia*0.40 + fit*0.35 + descoberta*0.15 + saturacao*0.10
score_oportunidade = tendencia*0.40 + saturacao*0.40 + descoberta*0.20
```

- **score_final** ordena o ranking: "qual o melhor jogo pro canal, no geral?"
  (fit pesa 35%).
- **score_oportunidade** é um sinal complementar: "onde está a janela de entrada?"
  (saturação pesa 40%, fit não entra — a oportunidade é do mercado, não sua).
  Velocidade e recência entram indiretamente, via tendência (sem contar duas vezes).

## 4. Motivo

Texto explicativo escolhido por uma cadeia de regras sobre os sub-scores
(`_gerar_motivo`). Os dois casos de maior prioridade são os de janela:

- oportunidade ≥75 + poucos canais + engajamento alto →
  *"...indicando oportunidade antes da saturacao."*
- alta performance + 3 ou mais canais →
  *"...vale entrar apenas com um angulo diferente."*

Há ainda casos para fit + pouca evidência, engajamento recente, curiosidade etc.

## 5. Ação recomendada

Tradução dos scores em próximo passo prático (`_gerar_acao_recomendada`),
em ordem de prioridade — o veto vem primeiro:

| # | condição | ação |
|---|---|---|
| 1 | saturação ≤40 (4+ canais) | Evitar por saturacao alta |
| 2 | oportunidade ≥75 e fit ≥80 | Priorizar para video longo |
| 3 | oportunidade ≥75 | Testar em Short |
| 4 | 1 vídeo só e tendência <70 | Pesquisar mais videos antes de gravar |
| 5 | caso contrário | Monitorar por mais alguns dias |

Os limiares são os mesmos do motivo — número, explicação e ação nunca se contradizem.

## Onde tudo aparece

Terminal (`ranking`), Markdown e CSV (`exportar_ranking`) mostram: os 4 sub-scores,
score final, oportunidade, motivo, ação recomendada e, por vídeo, views, likes,
comentários, % de engajamento, views/dia, data e título.
