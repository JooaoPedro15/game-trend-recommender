# Detecção e descoberta nos vídeos de referência

Data: 2026-08-29
Estado: aprovado, aguardando plano de implementação

## Problema

O ranking responde "que jogo gravar a seguir" a partir de vídeos de **outros** canais. Hoje
ele não responde nada de útil:

```
220 vídeos de referência | 18 com jogo identificado | 202 órfãos
score_descoberta: 0.0 para todos os jogos (peso: 15% do score final)
```

O ranking atual mede **qual canal escreve o nome do jogo no título**, não o que está em
alta. Minecraft lidera com tendência 100 porque um canal escreve "MINECRAFT" em caixa alta;
os canais de melhor encaixe com o dono do projeto (Play Guima, Diogo Matheus, Lozão)
titulam por gancho — "o susto que eu levei no final" — e produzem quase só órfão.

O objetivo declarado do dono é achar **jogo em alta momentânea**: título que estourou porque
um streamer jogou, em geral saído do itch.io, de preferência single player. Esse alvo depende
de dois sinais que hoje não chegam ao sistema.

## Evidência

Amostragem feita em 2026-08-29 nos dois canais que o dono indicou como referência principal
(`@lozao`, `@ElCamacho24`), antes de qualquer decisão de desenho.

**Vídeos longos — 40 vídeos, 180 comentários lidos em 6 deles:**

- 0 comentários perguntando o nome do jogo
- 0 respostas com nome de jogo
- 1 único comentário do dono do canal, e era conversa ("Vai sim, na segunda-feira!")
- O nome do jogo aparece na **descrição, em prosa**: `How to fish`, `moo WHO`,
  `The lacerator`, `house of the locust`, `Backyard Baseball`, `Little Nightmares 2`,
  `Kitty Powers Matchmaker`, `Shieldwall`, `Kinect Sports`
- Cobertura de descrição: 7/20 no Lozão, 11/20 no ElCamacho24

**Vídeos curtos — 10 shorts, 400 comentários:**

- Descrição **sempre vazia**, nos dois canais
- Lozão: 5 perguntas em 200 comentários (`"Nome do jogo"`, `"Como é o nome do jogo"`,
  `"qual é o nome desse jogo eu quero mu[ito]"`), **0 respostas**
- ElCamacho24: 0 perguntas, 0 comentários do dono. O nome do jogo vai em **hashtag no
  título**: `#barnyard`, `#gasncars`

**Conclusão que contraria a hipótese inicial.** A hipótese de trabalho era "as pessoas
respondem qual é o jogo nos comentários dos canais de referência, como o dono responde no
canal dele". O dado diz que **perguntam e ninguém responde**. Comentário de referência
carrega sinal de *curiosidade*, não de *identificação*.

## Não-objetivos

- Não identificar jogo em vídeo onde o nome não existe em texto nenhum. Quando não houver
  dado, o sistema declara "desconhecido" em vez de chutar.
- Não usar LLM nem serviço externo. O projeto é heurística transparente por decisão de
  projeto.
- Não coletar TikTok. Não há API pública; fica para outra frente.
- Não classificar single player / multiplayer. Frente separada, já mapeada.

## Seção A — Coleta para de descartar dado

### Situação

Existem dois coletores para o mesmo trabalho:

| | Chamada | Custo | Campos |
|---|---|---|---|
| `coletar_video_por_id` (referência) | 1 vídeo por chamada | 1 unidade/vídeo | `snippet,statistics` |
| `coletar_detalhes_em_lote` (canal próprio) | 50 vídeos por chamada | 1 unidade/50 vídeos | `snippet,statistics,contentDetails` |

O caminho de referência é 20× mais caro por canal e descarta três campos que a API já
devolve na mesma resposta:

- `descricao` — onde o Lozão escreve o nome do jogo
- `tags` — fonte de detecção exata que o detector já sabe usar
- `duracao` → `tipo_video` — hoje `desconhecido` nos 220, deixando o filtro `--tipo` cego

### Mudança

A coleta de referência passa a usar `coletar_detalhes_em_lote_varios`, convertendo
`DetalheVideoYoutube` em `VideoColetado`.

- `VideoColetado` ganha `descricao: str = ""` e `tags: list[str] = []`
- `videos_coletados.csv` ganha as colunas `descricao` e `tags` (tags separadas por `|`,
  mesma convenção do `meus_videos.csv`)
- `tipo_video` passa a vir preenchido

Nenhuma chamada nova de API. Custo de coletar 20 vídeos de um canal cai de 20 unidades
para 1.

### Migração

Os 220 vídeos já coletados ficam sem `descricao` e sem `tags` até serem recoletados —
mesmo problema das linhas legadas do `meus_videos.csv` na sprint de `--forcar`. Aplicar a
mesma solução: recoleta que ignora o cache por id. Custo ~33 unidades.

Duas peças precisam acompanhar a mudança de schema, e nenhuma existe hoje para o
`videos_coletados.csv` (só o `meus_videos.csv` tem equivalente):

- migração de cabeçalho, no molde de `colunas_faltando` / `migrar_meus_videos`, para
  distinguir "coluna não existia" de "campo vazio de verdade";
- checagem no `validar_dados` para linha de referência sem `descricao` **e** sem `tags`,
  pelo mesmo raciocínio da checagem de "coleta antiga": comparar contra o formato atual,
  não contra o cabeçalho.

`cadastro_video.adicionar_video_csv` e `leitor_csv.linha_para_video` também passam a
conhecer os dois campos novos.

## Seção B — Detecção usa só texto do autor

### Mudança

`detectar_jogos_no_video` troca o texto de busca:

```
antes:  titulo + texto_comentarios
depois: titulo + descricao + tags
```

O campo `texto_comentarios` **continua existindo** no `VideoColetado` e no CSV. O que muda é
só quem o lê: `detectar_jogos_no_video` para de ler; `_calcular_score_descoberta` continua
lendo, e é dele que vem o valor da seção C. Remover o campo quebraria a descoberta.

Comentário sai da detecção **de propósito**. Três razões:

1. **Não carrega o sinal.** 400 comentários amostrados em shorts, 5 perguntas, 0 respostas.
2. **Incluí-lo ativaria um bug conhecido.** Existe hoje um caso documentado em que o
   detector achou `Roblox` a partir de um alias solto em 100 comentários de um vídeo sobre
   "a evolução das logos do facebook e do youtube". Isso é inofensivo enquanto
   `texto_comentarios` está vazio nos 220; no instante em que a seção C começar a coletar,
   dispara em escala. **Cortar comentário da detecção é pré-requisito da seção C.**
3. **Fecha a questão de atribuição múltipla.** `detectar_jogos_no_video` devolve todos os
   jogos que casarem. Sobre texto de terceiro isso é perigoso — um comentário de
   comparação ("parece lethal company") rouba atribuição. Sobre texto do autor, deixa de
   ser: se o autor citou dois jogos, o vídeo cobre dois. A separação é **por fonte**, não
   por peso.

### O que não muda

Casamento por nome/alias, desempate por termo mais longo, normalização sem acento — tudo
permanece. Hashtag de nome de uma palavra **já funciona** sem código novo, porque `#` conta
como fronteira de palavra: `#barnyard` casa com o termo `barnyard`.

Hashtag de nome composto **não** casa (`#gasncars` não bate com `gas n cars`). Isso é
higiene de seed — cadastrar a forma colada como alias —, não código.

### Fora de escopo aqui

Nome de jogo que não está no seed. O ranking é indexado por jogo do seed, então um nome
novo não tem onde morar no modelo do ranker. Vai para a seção C.

## Seção C — Descoberta do que não foi identificado

### C1. Comentário de referência passa a ser coletado, com um único emprego

`score_descoberta` já existe, já lê `texto_comentarios` e já procura as frases certas
(`"qual o nome do jogo"`, `"que jogo e esse"`, `"onde baixa"`, `"link do jogo"`). Nada muda
no ranker: é ligar uma torneira fechada. Os 15% mortos do score voltam a valer.

Decisões:

- **Coletar em todos os vídeos de referência**, não só nos sem jogo. Descoberta mede hype,
  e jogo identificado também tem hype; restringir daria descoberta zero justamente aos
  jogos que o sistema conhece.
- **Guardar o texto, não a contagem.** Texto guardado permite recalcular de graça se as
  frases de descoberta mudarem — o mesmo princípio que motivou o `redetectar_meus_videos`.
- `limite_respostas` baixo (5). Medição anterior mostrou que o padrão 20 dispara ~3
  chamadas extras de `comments.list` por vídeo sem trazer sinal novo.
- Não guardar nenhum dado pessoal de autor. Mesma política já aplicada na detecção por
  comentário do canal próprio: texto e contagens, nunca id, nome ou handle de terceiro.

### C2. Lista do que sobrou

Comando novo. Lista vídeo de referência **sem jogo identificado** que tenha **sinal de
descoberta**, ordenado por alcance:

```
724.559 views | 2 perguntas | Lozão | "MATAR O VERITY NÃO FOI UMA BOA IDÉIA..."
   candidato: (nenhum)              https://youtube.com/watch?v=LVRh34KHoYg

 90.362 views | 0 perguntas | Lozão | "MEU BARCO NÁUFRAGO NESSA ILHA..."
   candidato: "How to fish"         https://youtube.com/watch?v=RbIxXnNtwBg
```

O campo `candidato` sai de templates de apresentação observados na amostra:

- pt: `nesse vídeo eu trouxe X`, `um jogo chamado X`, `um game chamado X`
- es: `hoy jugamos X`, `el día de hoy jugamos X`, `en este video jugamos X`,
  `volvimos a jugar X`, `continuamos con la serie de X`, `terminamos X`

Também entra como candidato a hashtag do título que não casou com o seed.

**Contenção do ruído.** O template é a parte mais suja do desenho. Na amostra devolveu
`"um simulador de salva vidas"` (gênero, não nome) e `"How to fish um game de pescaria"`
(nome grudado em prosa). Duas defesas:

1. Reusar o filtro de plausibilidade já existente (corta link, frase longa, excesso de
   palavras, texto sem letra).
2. **Candidato nunca entra no seed automaticamente.** É sugestão numa lista que uma pessoa
   lê. Ruído numa lista custa um segundo de leitura; ruído no seed contamina ranking e
   fit_real.

Propriedade que ajuda: assim que o jogo é cadastrado, o casamento por alias acha o nome
canônico **dentro** da string suja, e a sujeira desaparece sozinha na redetecção.

### C3. O que fica sem resposta

Short com descrição vazia, sem hashtag, sem resposta nos comentários — como o de 724 mil
views acima — não tem nome de jogo em texto nenhum. Nenhuma heurística resolve, porque o
dado não existe. O sistema declara `candidato: (nenhum)` e devolve o link. A pessoa assiste
5 vídeos por semana em vez de 220.

## Fluxo depois da mudança

```
canal de referência
  └─ playlistItems (1 un./50)  ──> ids
       └─ videos.list em lote (1 un./50) ──> titulo, descricao, tags, duracao, métricas
            ├─ detecção (titulo + descricao + tags) ──> jogo do seed ──> ranking
            └─ commentThreads (1 un./vídeo) ──> texto ──> score_descoberta
                                                     └─> lista de não resolvidos
                                                          + candidato (template/hashtag)
```

## Custo de quota

Para os 11 canais atuais, 20 vídeos cada:

| Etapa | Cálculo | Unidades |
|---|---|---|
| `channels.list` + `playlistItems` | 2 por canal × 11 | ~22 |
| `videos.list` em lote | 1 por canal (20 ids cabem num lote) | ~11 |
| `commentThreads` | 1 por vídeo × 220 | ~220 |
| **Total por refresh completo** | | **~253** |

Orçamento diário: 10.000. No esquema atual só a etapa de detalhes já custaria 220, contra
11 em lote.

## Ordem de implementação

As três seções são acopladas, mas têm valor independente e devem entrar em fases separadas,
cada uma com a suíte verde antes da seguinte:

1. **Seção A** — schema, migração e coleta em lote. Entrega sozinha a queda de quota e o
   conserto do `tipo_video`, sem depender de nada.
2. **Seção B** — troca do texto de detecção. Depende de A ter trazido `descricao` e `tags`,
   e é **pré-requisito** de C: sem ela, coletar comentário ativa o falso positivo por alias
   solto.
3. **Seção C** — coleta de comentário, `score_descoberta` ligado e lista de não resolvidos.

Inverter 2 e 3 introduz um bug conhecido em 220 vídeos.

## Testes

- Detecção não enxerga mais `texto_comentarios`; caso de regressão com alias solto em
  comentário que hoje gera falso positivo.
- Hashtag de uma palavra casa; hashtag composta não casa (documenta o limite).
- Conversão `DetalheVideoYoutube` → `VideoColetado` preserva descrição, tags e tipo_video.
- Migração: linha antiga sem descrição/tags é sinalizada pelo `validar_dados` e some após
  recoleta.
- Extração de candidato: cada template com um exemplo real da amostra, incluindo os dois
  casos ruidosos conhecidos (gênero em vez de nome; nome grudado em prosa).
- Lista de não resolvidos: ordenação por views, contagem de perguntas, e o caso sem
  candidato nenhum.

## Limitações conhecidas

- Cobertura de descrição na amostra: 45% dos longos, 0% dos shorts. Shorts continuam
  dependendo de hashtag ou de leitura humana.
- Templates são específicos dos dois canais amostrados. Canal novo com outro jeito de
  escrever não é coberto até alguém observar o padrão dele.
- `score_descoberta` mede pergunta, e pergunta correlaciona com "vídeo sem contexto", não
  só com "jogo em alta". Um short confuso de um jogo velho gera pergunta igual.
- A lista de não resolvidos só ajuda quem está disposto a assistir vídeo. É trabalho
  humano por desenho, não automação.

## Frentes adjacentes, fora desta spec

1. Canais de referência: revisar a lista, incluir Lozão e ElCamacho24, cortar quem não
   serve. TikTok do Lozão (`@lohzao`) sem caminho de coleta.
2. Categoria single player / multiplayer, com filtro no ranking.
3. Foco em jogo recém-lançado contra jogo consolidado.
4. itch.io como fonte.
