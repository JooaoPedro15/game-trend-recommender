# Detecção e descoberta nos vídeos de referência — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fazer o vídeo de referência guardar descrição e tags (que a API já devolve de graça), detectar o jogo a partir do texto do autor, e listar os vídeos em que nenhum texto nomeia o jogo mas há gente perguntando.

**Architecture:** Três fases acopladas em ordem obrigatória. A troca a coleta de referência para o coletor em lote (mais barato e mais rico). B tira o comentário da detecção. C liga a coleta de comentário só para descoberta. **Inverter B e C liga um falso positivo conhecido em 220 vídeos.**

**Tech Stack:** Python 3.12, stdlib apenas no runtime (urllib, csv, re, dataclasses). pytest para testes. Sem dependência nova.

**Spec:** `docs/superpowers/specs/2026-08-29-deteccao-referencia-design.md`

---

## Convenções deste repositório

Antes da primeira tarefa, leia isto:

- Código e comentários em **pt-BR, sem acento em identificador**. Comentário explicativo vai **ACIMA** da função e diz o **porquê**, não o que a linha faz.
- Rodar testes: `.venv\Scripts\python.exe -m pytest -q` na raiz. No Windows, prefixe com `$env:PYTHONIOENCODING="utf-8"` na sessão, senão a saída com acento quebra.
- **Nunca** edite CSV como texto: use o módulo `csv`. Há campos com vírgula (`Papers, Please`, `T3ddy, só que Games`).
- **Nunca** use `Get-Content`/`Set-Content` do PowerShell 5.1 para reescrever arquivo com acento — ele lê UTF-8 como ANSI e corrompe. Use Python com `encoding="utf-8"` explícito.
- Commits em **Conventional Commits**, em inglês, **sem** trailer `Co-Authored-By`.
- Baseline: **344 testes passando**. Toda tarefa termina com a suíte verde.

## Estrutura de arquivos

| Arquivo | Responsabilidade | Fase |
|---|---|---|
| `src/modelos.py` | `VideoColetado` ganha `descricao`/`tags`; `DetalheVideoYoutube` ganha `canal` | A |
| `src/leitor_csv.py` | ler os campos novos; helper genérico de cabeçalho | A |
| `src/cadastro_video.py` | escrever os campos novos; migração de cabeçalho | A |
| `src/coletor_youtube.py` | conversão detalhe→video; `coletar_canal` em lote | A |
| `src/validacao_dados.py` | avisar linha de referência sem descrição e sem tags | A |
| `src/main.py` | `--forcar` na coleta de canal; comando da lista | A, C |
| `src/detector_jogo.py` | texto de busca do `detectar_jogos_no_video` | B |
| `src/candidato_jogo.py` | **novo** — extrai nome candidato de prosa e hashtag | C |
| `src/descobertas.py` | **novo** — monta a lista de não resolvidos | C |

---

# FASE A — Coleta para de descartar dado

### Task 1: `VideoColetado` carrega descrição e tags

**Files:**
- Modify: `src/modelos.py:24-35`
- Test: `tests/test_leitor_csv.py`

- [ ] **Step 1: Write the failing test**

Acrescente ao fim de `tests/test_leitor_csv.py`:

```python
# --- Descricao e tags no video de referencia ---
#
# A API devolve os dois na mesma resposta que ja traz titulo e metricas, e o coletor de
# referencia descartava ambos. E na descricao que o canal escreve o nome do jogo.

def test_video_coletado_tem_descricao_e_tags_vazias_por_padrao():
    video = VideoColetado(
        titulo="t",
        canal="c",
        plataforma="youtube",
        url="https://y/1",
        views=1,
        likes=1,
        comentarios=1,
        data_publicacao="2026-08-01",
        texto_comentarios="",
    )

    assert video.descricao == ""
    assert video.tags == []


def test_duas_instancias_nao_compartilham_a_lista_de_tags():
    primeiro = VideoColetado("t", "c", "youtube", "u", 1, 1, 1, "2026-08-01", "")
    segundo = VideoColetado("t", "c", "youtube", "u", 1, 1, 1, "2026-08-01", "")

    primeiro.tags.append("repo")

    assert segundo.tags == []
```

Garanta que o arquivo importa `VideoColetado`; se não importar, acrescente ao topo:

```python
from modelos import VideoColetado
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_leitor_csv.py -k "descricao_e_tags or compartilham" -v`
Expected: FAIL com `TypeError` ou `AttributeError: 'VideoColetado' object has no attribute 'descricao'`

- [ ] **Step 3: Write minimal implementation**

Em `src/modelos.py`, na dataclass `VideoColetado`, acrescente os dois campos **depois** de `tipo_video` (todos os campos novos precisam de padrão, senão quebram as chamadas posicionais que já existem):

```python
@dataclass
class VideoColetado:
    titulo: str
    canal: str
    plataforma: str
    url: str
    views: int
    likes: int
    comentarios: int
    data_publicacao: str
    texto_comentarios: str
    origem: str = ""
    tipo_video: str = "desconhecido"
    # A API ja devolve os dois junto com o resto do snippet. Sao a fonte de deteccao mais
    # confiavel de um video de referencia: texto escrito pelo autor, nao por terceiro.
    descricao: str = ""
    tags: list[str] = field(default_factory=list)
```

Confirme que `field` está importado no topo do arquivo (`from dataclasses import dataclass, field`) — já está, porque `ComentariosColetados` usa.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_leitor_csv.py -k "descricao_e_tags or compartilham" -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Run the whole suite**

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: `346 passed`

- [ ] **Step 6: Commit**

```bash
git add src/modelos.py tests/test_leitor_csv.py
git commit -m "feat(modelos): carry description and tags on reference videos"
```

---

### Task 2: CSV de referência lê e escreve os campos novos

**Files:**
- Modify: `src/cadastro_video.py:8-20` (`CAMPOS_VIDEO`), `src/cadastro_video.py:97-110` (`_video_para_linha`)
- Modify: `src/leitor_csv.py:41-55` (`linha_para_video`)
- Test: `tests/test_leitor_csv.py`

- [ ] **Step 1: Write the failing test**

Acrescente ao fim de `tests/test_leitor_csv.py`:

```python
def test_gravar_e_reler_preserva_descricao_e_tags(tmp_path):
    from cadastro_video import adicionar_video_csv
    from leitor_csv import ler_videos_coletados

    caminho = tmp_path / "videos_coletados.csv"
    video = VideoColetado(
        titulo="MEU BARCO NAUFRAGO",
        canal="Lozao",
        plataforma="youtube",
        url="https://y/RbIxXnNtwBg",
        views=90362,
        likes=100,
        comentarios=10,
        data_publicacao="2026-08-01",
        texto_comentarios="",
        descricao="nesse video eu trouxe How to fish um game de pescaria",
        tags=["pescaria", "how to fish"],
    )

    adicionar_video_csv(caminho, video)
    lido = ler_videos_coletados(caminho)[0]

    assert lido.descricao == "nesse video eu trouxe How to fish um game de pescaria"
    assert lido.tags == ["pescaria", "how to fish"]


def test_linha_sem_as_colunas_novas_le_como_vazio(tmp_path):
    from leitor_csv import ler_videos_coletados

    caminho = tmp_path / "antigo.csv"
    caminho.write_text(
        "titulo,canal,plataforma,url,views,likes,comentarios,data_publicacao,"
        "texto_comentarios,origem,tipo_video\n"
        "t,Canal,youtube,https://y/1,10,1,1,2026-08-01,,youtube,curto\n",
        encoding="utf-8",
    )

    lido = ler_videos_coletados(caminho)[0]

    assert lido.descricao == ""
    assert lido.tags == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_leitor_csv.py -k "preserva_descricao or colunas_novas" -v`
Expected: FAIL — `assert '' == 'nesse video eu trouxe How to fish um game de pescaria'`

- [ ] **Step 3: Write minimal implementation**

Em `src/cadastro_video.py`, acrescente as duas colunas ao fim de `CAMPOS_VIDEO`:

```python
CAMPOS_VIDEO = [
    "titulo",
    "canal",
    "plataforma",
    "url",
    "views",
    "likes",
    "comentarios",
    "data_publicacao",
    "texto_comentarios",
    "origem",
    "tipo_video",
    "descricao",
    "tags",
]
```

E em `_video_para_linha`, acrescente as duas chaves ao dicionário devolvido:

```python
        "tipo_video": video.tipo_video,
        "descricao": video.descricao,
        # Mesma convencao do meus_videos.csv: lista separada por barra vertical.
        "tags": "|".join(video.tags),
    }
```

Em `src/leitor_csv.py`, dentro de `linha_para_video`, acrescente os dois campos:

```python
        tipo_video=linha.get("tipo_video", "").strip() or "desconhecido",
        descricao=linha.get("descricao", "") or "",
        tags=_separar_aliases(linha.get("tags", "") or ""),
    )
```

`_separar_aliases` já existe neste módulo e faz exatamente o split por `|` ignorando vazios — reusar em vez de escrever outro splitter.

**Atenção:** `descricao` **não** leva `.strip()`. A descrição tem quebras de linha significativas e espaços que o detector de marcador explícito usa; `strip()` no fim é inofensivo, mas manter cru evita surpresa.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_leitor_csv.py -k "preserva_descricao or colunas_novas" -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Run the whole suite**

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: `348 passed`

- [ ] **Step 6: Commit**

```bash
git add src/cadastro_video.py src/leitor_csv.py tests/test_leitor_csv.py
git commit -m "feat(csv): persist description and tags for reference videos"
```

---

### Task 3: Migração de cabeçalho do `videos_coletados.csv`

Motivo: `csv.DictReader` **não devolve a chave** de uma coluna ausente, então o leitor cai no padrão vazio e um vídeo coletado antes da coluna existir fica indistinguível de um vídeo que de fato não tem descrição. O `meus_videos.csv` já resolve isso; o `videos_coletados.csv` não tem nada equivalente.

**Files:**
- Modify: `src/leitor_csv.py` (helper genérico, no fim do arquivo)
- Modify: `src/cadastro_video.py` (usa o helper)
- Test: `tests/test_importacao.py`

- [ ] **Step 1: Write the failing test**

Acrescente ao fim de `tests/test_importacao.py`:

```python
# --- Migracao de cabecalho do videos_coletados.csv ---
#
# O DictReader nao devolve a chave de uma coluna ausente, entao o leitor cai no padrao e
# "coletado antes da coluna existir" fica igual a "nao tem descricao". A migracao devolve a
# capacidade de distinguir os dois casos; ela nao inventa dado nenhum.

def test_colunas_faltando_aponta_as_colunas_novas(tmp_path):
    from cadastro_video import colunas_faltando_videos

    caminho = tmp_path / "videos_coletados.csv"
    caminho.write_text(
        "titulo,canal,plataforma,url,views,likes,comentarios,data_publicacao,"
        "texto_comentarios,origem,tipo_video\n",
        encoding="utf-8",
    )

    assert colunas_faltando_videos(caminho) == ["descricao", "tags"]


def test_arquivo_em_dia_nao_reporta_coluna_faltando(tmp_path):
    from cadastro_video import CAMPOS_VIDEO, colunas_faltando_videos

    caminho = tmp_path / "videos_coletados.csv"
    caminho.write_text(",".join(CAMPOS_VIDEO) + "\n", encoding="utf-8")

    assert colunas_faltando_videos(caminho) == []


def test_migrar_preserva_as_linhas_e_deixa_as_colunas_novas_vazias(tmp_path):
    from cadastro_video import migrar_videos_coletados
    from leitor_csv import ler_videos_coletados

    caminho = tmp_path / "videos_coletados.csv"
    caminho.write_text(
        "titulo,canal,plataforma,url,views,likes,comentarios,data_publicacao,"
        "texto_comentarios,origem,tipo_video\n"
        "MEU BARCO,Lozao,youtube,https://y/1,90362,100,10,2026-08-01,,youtube,longo\n",
        encoding="utf-8",
    )

    novas = migrar_videos_coletados(caminho)

    assert novas == ["descricao", "tags"]
    lido = ler_videos_coletados(caminho)[0]
    assert lido.titulo == "MEU BARCO"
    assert lido.views == 90362
    assert lido.descricao == ""


def test_migrar_arquivo_inexistente_nao_quebra(tmp_path):
    from cadastro_video import migrar_videos_coletados

    assert migrar_videos_coletados(tmp_path / "nao_existe.csv") == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_importacao.py -k "colunas_faltando or migrar" -v`
Expected: FAIL com `ImportError: cannot import name 'colunas_faltando_videos'`

- [ ] **Step 3: Write minimal implementation**

Em `src/leitor_csv.py`, acrescente ao fim do arquivo:

```python
# Le so o cabecalho gravado no arquivo (lista vazia se ele nao existe ou esta vazio).
def cabecalho_do_csv(caminho: str | Path) -> list[str]:
    caminho = Path(caminho)
    if not caminho.exists() or caminho.stat().st_size == 0:
        return []

    with caminho.open("r", encoding="utf-8-sig", newline="") as arquivo:
        return next(csv.reader(arquivo), [])


# Colunas de `campos` que faltam no arquivo gravado, na ordem de `campos`. Generico de
# proposito: o meus_videos.csv ja tinha essa checagem so para ele, e o mesmo problema vale
# para qualquer CSV do projeto que ganhe coluna depois de ja ter linhas.
def colunas_faltando(caminho: str | Path, campos: list[str]) -> list[str]:
    cabecalho = cabecalho_do_csv(caminho)
    if not cabecalho:
        return []

    return [campo for campo in campos if campo not in cabecalho]
```

Confirme que `csv` está importado no topo de `leitor_csv.py` — está.

Em `src/cadastro_video.py`, acrescente depois de `importar_videos_csv`:

```python
# Colunas do formato atual que faltam no videos_coletados.csv gravado.
def colunas_faltando_videos(caminho: str | Path) -> list[str]:
    return colunas_faltando(caminho, CAMPOS_VIDEO)


# Reescreve o CSV com o cabecalho atual, preservando as linhas existentes e deixando as
# colunas novas vazias. Devolve as colunas acrescentadas ([] quando ja estava em dia).
# Nao inventa dado: descricao e tags so sao preenchidas por uma nova coleta.
def migrar_videos_coletados(caminho: str | Path) -> list[str]:
    caminho = Path(caminho)
    faltando = colunas_faltando_videos(caminho)
    if not faltando:
        return []

    linhas = _ler_linhas(caminho)
    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=CAMPOS_VIDEO, extrasaction="ignore")
        escritor.writeheader()
        escritor.writerows(linhas)

    return faltando
```

Ajuste o import no topo de `src/cadastro_video.py`:

```python
from leitor_csv import _ler_linhas, colunas_faltando, ler_videos_coletados, linha_para_video
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_importacao.py -k "colunas_faltando or migrar" -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Run the whole suite**

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: `352 passed`

- [ ] **Step 6: Commit**

```bash
git add src/leitor_csv.py src/cadastro_video.py tests/test_importacao.py
git commit -m "feat(csv): migrate the reference CSV header when columns are added"
```

---

### Task 4: `DetalheVideoYoutube` carrega o nome do canal

Motivo: `_item_para_detalhe` já busca o `channelTitle` (via `_item_para_video`) e joga fora. Sem esse campo não dá para converter um detalhe em `VideoColetado`, porque o ranker casa os pesos do canal **por nome**.

**Files:**
- Modify: `src/modelos.py` (dataclass `DetalheVideoYoutube`)
- Modify: `src/coletor_youtube.py` (`_item_para_detalhe`)
- Test: `tests/test_coletor_youtube.py`

- [ ] **Step 1: Write the failing test**

Acrescente ao fim de `tests/test_coletor_youtube.py`:

```python
# --- O detalhe precisa saber de que canal veio ---
#
# O ranker casa peso e peso_similaridade pelo NOME do canal. Um detalhe sem canal nao pode
# virar VideoColetado sem perder a calibracao inteira, em silencio.

def test_detalhe_guarda_o_nome_do_canal(monkeypatch):
    import coletor_youtube

    def _fake(url):
        return {
            "items": [
                {
                    "id": "VID1",
                    "snippet": {
                        "title": "MEU BARCO NAUFRAGO",
                        "channelTitle": "Lozao",
                        "description": "nesse video eu trouxe How to fish",
                        "tags": ["pescaria"],
                        "publishedAt": "2026-08-01T00:00:00Z",
                        "liveBroadcastContent": "none",
                    },
                    "statistics": {"viewCount": "90362", "likeCount": "100", "commentCount": "10"},
                    "contentDetails": {"duration": "PT8M"},
                }
            ]
        }

    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    monkeypatch.setattr(coletor_youtube, "_get_json", _fake)

    detalhe = coletor_youtube.coletar_detalhe_video("VID1")

    assert detalhe.canal == "Lozao"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_coletor_youtube.py -k "nome_do_canal" -v`
Expected: FAIL com `AttributeError: 'DetalheVideoYoutube' object has no attribute 'canal'`

- [ ] **Step 3: Write minimal implementation**

Em `src/modelos.py`, na dataclass `DetalheVideoYoutube`, acrescente o campo **no fim** (precisa de padrão, porque `_item_para_detalhe` constrói por palavra-chave mas outros testes podem construir posicionalmente):

```python
@dataclass
class DetalheVideoYoutube:
    video_id: str
    titulo: str
    descricao: str
    tags: list[str]
    url: str
    views: int
    likes: int
    comentarios: int
    data_publicacao: str
    duracao_segundos: int
    tipo_video: str
    # O channelTitle ja vem no mesmo snippet. E o ranker casa os pesos do canal por nome,
    # entao perder esse campo na conversao desliga a calibracao sem avisar.
    canal: str = ""
```

Em `src/coletor_youtube.py`, dentro de `_item_para_detalhe`, acrescente ao `return`:

```python
        tipo_video=_inferir_tipo_video(duracao_segundos, item),
        canal=base.canal,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_coletor_youtube.py -k "nome_do_canal" -v`
Expected: PASS

- [ ] **Step 5: Run the whole suite**

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: `353 passed`

- [ ] **Step 6: Commit**

```bash
git add src/modelos.py src/coletor_youtube.py tests/test_coletor_youtube.py
git commit -m "feat(coletor): keep the channel title on the rich video detail"
```

---

### Task 5: Coleta de canal passa a usar o lote

Motivo: `coletar_video_por_id` custa **1 unidade por vídeo**; `coletar_detalhes_em_lote` custa **1 unidade por 50**. Além do preço, o lote traz `descricao`, `tags` e `contentDetails` (que preenche `tipo_video`, hoje `desconhecido` em todos os 220).

**Files:**
- Modify: `src/coletor_youtube.py` (nova função de conversão + `coletar_canal`)
- Test: `tests/test_coletor_youtube.py`

- [ ] **Step 1: Write the failing test**

Acrescente ao fim de `tests/test_coletor_youtube.py`:

```python
# --- Coleta de canal em lote ---
#
# Antes: uma chamada videos.list por video (1 unidade cada) e sem contentDetails, entao
# tipo_video ficava "desconhecido" e descricao/tags eram descartadas. Agora: um lote de 50
# por chamada, com os tres campos.

def _fake_canal_em_lote(chamadas):
    def _fake(url):
        if "/channels" in url:
            return {"items": [{"contentDetails": {"relatedPlaylists": {"uploads": "UU_X"}}}]}
        if "/playlistItems" in url:
            return {
                "items": [
                    {"contentDetails": {"videoId": "VID0"}},
                    {"contentDetails": {"videoId": "VID1"}},
                ]
            }
        if "/videos" in url:
            chamadas.append(url)
            ids = parse_qs(urlparse(url).query)["id"][0].split(",")
            return {
                "items": [
                    {
                        "id": vid,
                        "snippet": {
                            "title": f"video {vid}",
                            "channelTitle": "Lozao",
                            "description": f"nesse video eu trouxe o jogo {vid}",
                            "tags": ["gameplay"],
                            "publishedAt": "2026-08-01T00:00:00Z",
                            "liveBroadcastContent": "none",
                        },
                        "statistics": {
                            "viewCount": "1000",
                            "likeCount": "10",
                            "commentCount": "5",
                        },
                        "contentDetails": {"duration": "PT45S"},
                    }
                    for vid in ids
                ]
            }
        return {"items": []}

    return _fake


def test_coletar_canal_usa_uma_unica_chamada_de_videos(monkeypatch, tmp_path):
    import coletor_youtube

    chamadas = []
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    monkeypatch.setattr(coletor_youtube, "_get_json", _fake_canal_em_lote(chamadas))
    destino = tmp_path / "videos_coletados.csv"

    resumo = coletor_youtube.coletar_canal("UC_X", destino, limite=2, caminho_cache=None)

    assert len(chamadas) == 1  # dois videos, uma chamada
    assert resumo["salvos"] == 2


def test_coletar_canal_guarda_descricao_tags_e_tipo(monkeypatch, tmp_path):
    import coletor_youtube
    from leitor_csv import ler_videos_coletados

    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    monkeypatch.setattr(coletor_youtube, "_get_json", _fake_canal_em_lote([]))
    destino = tmp_path / "videos_coletados.csv"

    coletor_youtube.coletar_canal("UC_X", destino, limite=2, caminho_cache=None)

    videos = {v.url: v for v in ler_videos_coletados(destino)}
    primeiro = videos["https://www.youtube.com/watch?v=VID0"]
    assert primeiro.canal == "Lozao"
    assert primeiro.descricao == "nesse video eu trouxe o jogo VID0"
    assert primeiro.tags == ["gameplay"]
    assert primeiro.tipo_video == "curto"  # PT45S
```

Confirme que o arquivo já importa `parse_qs` e `urlparse`; se não, acrescente ao topo:

```python
from urllib.parse import parse_qs, urlparse
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_coletor_youtube.py -k "uma_unica_chamada or descricao_tags_e_tipo" -v`
Expected: FAIL — `assert 2 == 1` na primeira (duas chamadas, uma por vídeo) e `assert '' == 'nesse video eu trouxe o jogo VID0'` na segunda

- [ ] **Step 3: Write minimal implementation**

Em `src/coletor_youtube.py`, acrescente a conversão logo depois de `_item_para_detalhe`:

```python
# Converte o detalhe rico em VideoColetado, o modelo que o ranking consome. A conversao
# existe para o caminho de referencia poder usar o coletor em lote (1 unidade por 50) em
# vez de uma chamada por video, e de quebra herdar descricao, tags e tipo_video.
def detalhe_para_video_coletado(detalhe: DetalheVideoYoutube) -> VideoColetado:
    return VideoColetado(
        titulo=detalhe.titulo,
        canal=detalhe.canal,
        plataforma="youtube",
        url=detalhe.url,
        views=detalhe.views,
        likes=detalhe.likes,
        comentarios=detalhe.comentarios,
        data_publicacao=detalhe.data_publicacao,
        # Comentario nao e coletado aqui: ele alimenta descoberta, nao identificacao.
        texto_comentarios="",
        origem="youtube",
        tipo_video=detalhe.tipo_video,
        descricao=detalhe.descricao,
        tags=list(detalhe.tags),
    )
```

Substitua a função `coletar_canal` inteira por:

```python
# Coleta os videos recentes de um canal e salva cada um no CSV. Usa videos.list em LOTE:
# uma chamada cobre ate 50 videos, contra uma chamada por video do caminho antigo. O cache
# por id nao entra aqui de proposito — ele economizava 1 unidade por video, e no lote o
# video inteiro ja custa 1/50 de unidade.
def coletar_canal(
    channel_id: str,
    caminho_destino: str | Path,
    limite: int = 5,
    caminho_cache: str | Path | None = CACHE_PADRAO,
) -> dict[str, int]:
    ids = listar_ids_recentes_do_canal(channel_id, limite)
    resumo = {"lidos": len(ids), "encontrados": 0, "salvos": 0, "duplicados": 0, "erros": 0}

    for detalhe in coletar_detalhes_em_lote_varios(ids):
        resumo["encontrados"] += 1
        try:
            adicionar_video_csv(caminho_destino, detalhe_para_video_coletado(detalhe))
            resumo["salvos"] += 1
        except VideoDuplicadoError:
            resumo["duplicados"] += 1
        except ValueError:
            resumo["erros"] += 1

    # Video pedido e nao devolvido pela API (apagado/privado) conta como erro.
    resumo["erros"] += len(ids) - resumo["encontrados"]
    return resumo
```

O parâmetro `caminho_cache` fica na assinatura por compatibilidade com quem já chama, mas não é mais usado — documente isso no comentário acima, como está feito.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_coletor_youtube.py -k "uma_unica_chamada or descricao_tags_e_tipo" -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Run the whole suite**

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: `355 passed`. Se algum teste antigo de `coletar_canal` falhar por contar chamadas, leia o teste: ele provavelmente afirmava o comportamento antigo (uma chamada por vídeo). Atualize o **setup** dele, preservando a intenção, e registre no commit o que mudou e por quê.

- [ ] **Step 6: Commit**

```bash
git add src/coletor_youtube.py tests/test_coletor_youtube.py
git commit -m "perf(coletor): collect reference channels in batches of fifty"
```

---

### Task 6: `--forcar` na coleta de canal e aviso de linha antiga

**Files:**
- Modify: `src/cadastro_video.py` (`adicionar_video_csv` ganha `substituir`)
- Modify: `src/coletor_youtube.py` (`coletar_canal` ganha `forcar`)
- Modify: `src/main.py` (`coletar_canal_youtube_interativo`, argparse)
- Modify: `src/validacao_dados.py` (`_validar_videos`)
- Test: `tests/test_coletor_youtube.py`, `tests/test_validacao_dados.py`

- [ ] **Step 1: Write the failing test**

Acrescente ao fim de `tests/test_coletor_youtube.py`:

```python
def test_forcar_atualiza_a_linha_ja_existente(monkeypatch, tmp_path):
    import coletor_youtube
    from cadastro_video import adicionar_video_csv
    from leitor_csv import ler_videos_coletados
    from modelos import VideoColetado

    destino = tmp_path / "videos_coletados.csv"
    # Linha no formato antigo: sem descricao, sem tags, tipo desconhecido.
    adicionar_video_csv(
        destino,
        VideoColetado(
            titulo="video VID0",
            canal="Lozao",
            plataforma="youtube",
            url="https://www.youtube.com/watch?v=VID0",
            views=1,
            likes=0,
            comentarios=0,
            data_publicacao="2026-08-01",
            texto_comentarios="",
        ),
    )

    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    monkeypatch.setattr(coletor_youtube, "_get_json", _fake_canal_em_lote([]))

    resumo = coletor_youtube.coletar_canal(
        "UC_X", destino, limite=2, caminho_cache=None, forcar=True
    )

    videos = {v.url: v for v in ler_videos_coletados(destino)}
    assert len(videos) == 2  # atualizou, nao duplicou
    assert videos["https://www.youtube.com/watch?v=VID0"].descricao
    assert resumo["duplicados"] == 0
```

Acrescente ao fim de `tests/test_validacao_dados.py`:

```python
# --- Video de referencia coletado antes das colunas descricao/tags existirem ---

def test_video_de_referencia_sem_descricao_e_sem_tags_vira_aviso():
    problemas = _validar_referencia_antiga()

    assert "aviso" in _severidades(problemas)
    assert "sem descricao e sem tags" in _mensagens(problemas)
    assert "--forcar" in _sugestoes(problemas)


def _validar_referencia_antiga():
    antigo = _video()
    antigo.descricao = ""
    antigo.tags = []
    return validar_dados(
        [antigo],
        [_jogo()],
        [_canal()],
        [_meu()],
        chave_configurada=True,
        canal_configurado=True,
    )


def test_video_de_referencia_com_descricao_nao_gera_o_aviso():
    com_descricao = _video()
    com_descricao.descricao = "nesse video eu trouxe Repo"

    problemas = validar_dados(
        [com_descricao],
        [_jogo()],
        [_canal()],
        [_meu()],
        chave_configurada=True,
        canal_configurado=True,
    )

    assert "sem descricao e sem tags" not in _mensagens(problemas)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_coletor_youtube.py tests/test_validacao_dados.py -k "forcar_atualiza or referencia" -v`
Expected: FAIL — `TypeError: coletar_canal() got an unexpected keyword argument 'forcar'` e `assert 'aviso' in {...}`

- [ ] **Step 3: Write minimal implementation**

Em `src/cadastro_video.py`, dê a `adicionar_video_csv` a opção de substituir:

```python
# substituir=True troca a linha de mesma URL em vez de recusar. E a valvula de escape do
# cache: sem ela, um video coletado antes das colunas descricao/tags existirem nunca mais
# e visitado, exatamente como aconteceu com as linhas legadas do meus_videos.csv.
def adicionar_video_csv(
    caminho: str | Path, video: VideoColetado, substituir: bool = False
) -> None:
    caminho = Path(caminho)
    _validar_video(video)
    _garantir_csv(caminho)

    linhas = _ler_linhas(caminho)
    alvo = _normalizar_url(video.url)
    nova_linha = _video_para_linha(video)

    for indice, linha in enumerate(linhas):
        if _normalizar_url(linha.get("url", "")) != alvo:
            continue
        if not substituir:
            raise VideoDuplicadoError("Ja existe um video cadastrado com essa URL.")
        linhas[indice] = nova_linha
        _reescrever_videos(caminho, linhas)
        return

    linhas.append(nova_linha)
    _reescrever_videos(caminho, linhas)


# Reescreve o CSV inteiro (cabecalho + linhas), do mesmo jeito que o meus_videos.csv faz.
def _reescrever_videos(caminho: Path, linhas: list[dict]) -> None:
    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(
            arquivo, fieldnames=CAMPOS_VIDEO, extrasaction="ignore"
        )
        escritor.writeheader()
        escritor.writerows(linhas)
```

Em `src/coletor_youtube.py`, `coletar_canal` ganha o parâmetro e repassa:

```python
def coletar_canal(
    channel_id: str,
    caminho_destino: str | Path,
    limite: int = 5,
    caminho_cache: str | Path | None = CACHE_PADRAO,
    forcar: bool = False,
) -> dict[str, int]:
    ids = listar_ids_recentes_do_canal(channel_id, limite)
    resumo = {"lidos": len(ids), "encontrados": 0, "salvos": 0, "duplicados": 0, "erros": 0}

    for detalhe in coletar_detalhes_em_lote_varios(ids):
        resumo["encontrados"] += 1
        try:
            adicionar_video_csv(
                caminho_destino, detalhe_para_video_coletado(detalhe), substituir=forcar
            )
            resumo["salvos"] += 1
        except VideoDuplicadoError:
            resumo["duplicados"] += 1
        except ValueError:
            resumo["erros"] += 1

    resumo["erros"] += len(ids) - resumo["encontrados"]
    return resumo
```

Em `src/validacao_dados.py`, dentro de `_validar_videos`, acrescente ao fim da função:

```python
    # Linha sem descricao E sem tags so acontece em video coletado antes dessas colunas
    # existirem. A coleta pula quem ja esta no CSV, entao sem --forcar ela nunca se conserta.
    sem_texto_do_autor = [
        video
        for video in videos
        if not video.descricao.strip() and not video.tags
    ]
    if sem_texto_do_autor:
        problemas.append(
            Problema(
                "aviso",
                f"{len(sem_texto_do_autor)} de {len(videos)} video(s) de referencia "
                "sem descricao e sem tags.",
                "Rode coletar_canal_youtube <id> --forcar para recoletar; sem descricao a "
                "deteccao so enxerga o titulo.",
            )
        )
```

Em `src/main.py`, `coletar_canal_youtube_interativo` ganha o parâmetro:

```python
def coletar_canal_youtube_interativo(
    channel_id: str, limite: int, forcar: bool = False
) -> None:
    migrar_videos_coletados(VIDEOS_CSV)
    try:
        resumo = coletar_canal(channel_id, VIDEOS_CSV, limite, forcar=forcar)
    except RuntimeError as erro:
        print(f"Erro: {erro}")
        return

    print("=== Coleta de Canal do YouTube ===")
    print(f"Videos recentes considerados: {resumo['lidos']}")
    print(f"Videos encontrados: {resumo['encontrados']}")
    print(f"Videos salvos: {resumo['salvos']}")
    print(f"Duplicados ignorados: {resumo['duplicados']}")
    print(f"Erros: {resumo['erros']}")
```

Acrescente o import de `migrar_videos_coletados` junto dos outros de `cadastro_video` no topo de `main.py`, e a flag no argparse, logo depois do `--limite` do subcomando `coletar_canal_youtube`:

```python
    canal.add_argument(
        "--forcar",
        action="store_true",
        help="Recoleta tambem os videos ja salvos (atualiza descricao, tags e metricas).",
    )
```

E no despacho de `coletar_canal_youtube`, passe `forcar`:

```python
    if comando == "coletar_canal_youtube":
        coletar_canal_youtube_interativo(channel_id, limite, forcar)
        return 0
```

`forcar` já é lido de `args` no `main()` — foi adicionado quando o `coletar_meu_canal` ganhou a flag.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_coletor_youtube.py tests/test_validacao_dados.py -k "forcar_atualiza or referencia" -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Run the whole suite**

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: `358 passed`

- [ ] **Step 6: Commit**

```bash
git add src/cadastro_video.py src/coletor_youtube.py src/main.py src/validacao_dados.py tests/
git commit -m "feat(coletor): add --forcar to refresh already collected reference videos"
```

---

# FASE B — Detecção usa só texto do autor

> **Esta fase é pré-requisito da Fase C.** Coletar comentário antes dela liga o falso positivo por alias solto em 220 vídeos de uma vez.

### Task 7: `detectar_jogos_no_video` lê título, descrição e tags

**Files:**
- Modify: `src/detector_jogo.py:44-52` (`detectar_jogos_no_video`)
- Test: `tests/test_detector_jogo.py`

- [ ] **Step 1: Write the failing test**

Acrescente ao fim de `tests/test_detector_jogo.py`:

```python
# --- Deteccao de video de referencia usa so texto do autor ---
#
# Amostra real de dois canais de referencia: 400 comentarios, 5 perguntas pelo nome do
# jogo, ZERO respostas. Comentario ali carrega curiosidade, nao identificacao. E incluir
# comentario liga um falso positivo conhecido: um alias solto em 100 comentarios de um
# video sobre "a evolucao das logos do facebook e do youtube" resolvia como Roblox.

def _video_referencia(titulo="", descricao="", tags=None, comentarios=""):
    video = VideoColetado(
        titulo=titulo,
        canal="Lozao",
        plataforma="youtube",
        url="https://y/1",
        views=1000,
        likes=10,
        comentarios=5,
        data_publicacao="2026-08-01",
        texto_comentarios=comentarios,
    )
    video.descricao = descricao
    video.tags = tags or []
    return video


def test_detecta_jogo_citado_na_descricao():
    jogos = _seed_com_alias_curto()

    achados = detectar_jogos_no_video(
        _video_referencia(titulo="MEU BARCO NAUFRAGO", descricao="nesse video eu trouxe Roblox"),
        jogos,
    )

    assert [j.nome for j in achados] == ["Roblox"]


def test_detecta_jogo_citado_nas_tags():
    jogos = _seed_com_alias_curto()

    achados = detectar_jogos_no_video(
        _video_referencia(titulo="sem pista", tags=["gameplay", "roblox"]), jogos
    )

    assert [j.nome for j in achados] == ["Roblox"]


def test_alias_solto_em_comentario_nao_detecta_mais():
    jogos = _seed_com_alias_curto()

    achados = detectar_jogos_no_video(
        _video_referencia(
            titulo="A evolucao das logos do facebook e do youtube",
            comentarios="alguem ai joga roblox? eu jogo minecraft todo dia",
        ),
        jogos,
    )

    assert achados == []


def test_texto_comentarios_continua_no_modelo():
    # A descoberta depende desse campo; so a deteccao parou de le-lo.
    video = _video_referencia(comentarios="qual o nome do jogo")

    assert video.texto_comentarios == "qual o nome do jogo"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_detector_jogo.py -k "citado_na_descricao or citado_nas_tags or alias_solto" -v`
Expected: FAIL — as duas primeiras devolvem `[]` (descrição e tags não são lidas) e `test_alias_solto_em_comentario_nao_detecta_mais` devolve `['Roblox']`

- [ ] **Step 3: Write minimal implementation**

Em `src/detector_jogo.py`, substitua `detectar_jogos_no_video` por:

```python
# Todos os jogos do seed citados no texto que o AUTOR escreveu: titulo, descricao e tags.
# Comentario fica de fora de proposito. Em amostra real de canais de referencia, 400
# comentarios trouxeram 5 perguntas pelo nome do jogo e nenhuma resposta — ali o comentario
# mede curiosidade, nao identidade. E le-lo reintroduz falso positivo: basta um alias solto
# numa conversa qualquer para o video inteiro ser atribuido ao jogo errado.
# O texto_comentarios continua no modelo; quem o consome agora e so o score de descoberta.
def detectar_jogos_no_video(
    video: VideoColetado, jogos: list[JogoSeed]
) -> list[JogoSeed]:
    texto_busca = f"{video.titulo} {video.descricao} {' '.join(video.tags)}"
    encontrados = []

    for jogo in jogos:
        if any(_termo_aparece(texto_busca, termo) for termo in _termos_do_jogo(jogo)):
            encontrados.append(jogo)

    return encontrados
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_detector_jogo.py -k "citado_na_descricao or citado_nas_tags or alias_solto or continua_no_modelo" -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Run the whole suite**

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: `362 passed`. Se um teste antigo do ranker falhar, provavelmente ele montava um `VideoColetado` com o jogo só em `texto_comentarios` — comportamento que esta tarefa remove de propósito. Mova o nome do jogo para o título ou a descrição no **setup** do teste, preservando o que ele afirma.

- [ ] **Step 6: Commit**

```bash
git add src/detector_jogo.py tests/test_detector_jogo.py
git commit -m "fix(detector): identify reference games from author text only"
```

---

# FASE C — Descoberta do que não foi identificado

### Task 8: Extrair nome candidato de prosa e hashtag

**Files:**
- Create: `src/candidato_jogo.py`
- Test: `tests/test_candidato_jogo.py`

- [ ] **Step 1: Write the failing test**

Crie `tests/test_candidato_jogo.py`:

```python
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from candidato_jogo import candidatos_do_video


# Todos os textos abaixo sao verbatim da amostra real de 2026-08-29 nos canais @lozao e
# @ElCamacho24. Os dois ultimos sao os casos ruidosos conhecidos, mantidos de proposito.

def test_template_portugues_um_jogo_chamado():
    achados = candidatos_do_video(
        titulo="Esse caba de calcinha me capturou",
        descricao="nesse vídeo eu trouxe um jogo chamado The lacerator, fui capturado",
    )

    assert "The lacerator" in achados


def test_template_espanhol_en_este_video_jugamos():
    achados = candidatos_do_video(
        titulo="INTENTANDO RESCATAR A UN PINGÜINO",
        descricao="En este video jugamos Super Mario Bros pero no soy mario.",
    )

    assert "Super Mario Bros" in achados


def test_template_espanhol_volvimos_a_jugar():
    achados = candidatos_do_video(
        titulo="ASÍ DEFIENDO EL IMPERIO ROMANO",
        descricao="Volvimos a jugar Shieldwall",
    )

    assert "Shieldwall" in achados


def test_hashtag_do_titulo_vira_candidato():
    achados = candidatos_do_video(
        titulo="Si te caes pierdes | jugando al barnyard del ps2. #barnyard #plays",
        descricao="",
    )

    assert "barnyard" in achados


def test_descricao_vazia_nao_gera_candidato():
    assert candidatos_do_video(titulo="MATAR O VERITY NÃO FOI UMA BOA IDÉIA...", descricao="") == []


def test_link_na_prosa_nao_vira_candidato():
    achados = candidatos_do_video(
        titulo="t", descricao="nesse vídeo eu trouxe https://loja.com/jogo confira"
    )

    assert achados == []


def test_frase_longa_demais_nao_vira_candidato():
    achados = candidatos_do_video(
        titulo="t",
        descricao=(
            "nesse vídeo eu trouxe um monte de coisa que eu queria muito testar faz "
            "tempo e finalmente deu certo hoje"
        ),
    )

    assert achados == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_candidato_jogo.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'candidato_jogo'`

- [ ] **Step 3: Write minimal implementation**

Crie `src/candidato_jogo.py`:

```python
# Extrai NOME CANDIDATO de jogo do texto de um video de referencia, para o caso em que
# nenhum jogo do seed foi identificado. Candidato nunca entra no seed sozinho: ele aparece
# numa lista que uma pessoa le e decide. Por isso o filtro aqui pode ser tolerante — ruido
# numa lista custa um segundo de leitura, ruido no seed contamina ranking e fit_real.
#
# Os templates saem de amostra real (2026-08-29, @lozao e @ElCamacho24). Canal novo que
# escreva de outro jeito nao e coberto ate alguem observar o padrao dele.

import re


# Templates de apresentacao observados. O grupo 1 e o nome candidato.
TEMPLATES = [
    re.compile(r"(?:nesse|neste)\s+v[ií]deo\s+eu\s+trouxe\s+(?:um\s+)?(?:jogo|game)\s+chamado\s+(.+)", re.IGNORECASE),
    re.compile(r"(?:nesse|neste)\s+v[ií]deo\s+eu\s+trouxe\s+(.+)", re.IGNORECASE),
    re.compile(r"(?:en\s+este|neste)\s+v[ií]deo\s+jugamos\s+(.+)", re.IGNORECASE),
    re.compile(r"(?:el\s+d[ií]a\s+de\s+)?hoy\s+jugamos\s+(.+)", re.IGNORECASE),
    re.compile(r"volvimos\s+a\s+jugar\s+(.+)", re.IGNORECASE),
    re.compile(r"continuamos\s+con\s+la\s+serie\s+de\s+(.+)", re.IGNORECASE),
    re.compile(r"terminamos\s+(.+)", re.IGNORECASE),
]

# Hashtag do titulo. O ElCamacho24 marca o jogo assim nos shorts, onde a descricao e vazia.
PADRAO_HASHTAG = re.compile(r"#(\w{3,30})")

# Hashtag generica que nunca e nome de jogo — apareceu na amostra e so gera ruido.
HASHTAG_IGNORADA = {"shorts", "short", "clips", "gameplay", "games", "game", "viral", "fyp"}

# Um nome de jogo tem poucas palavras. Acima disso a captura pegou a frase inteira.
MAXIMO_PALAVRAS = 5
TAMANHO_MAXIMO = 60

# Corta o candidato no primeiro separador forte: virgula, quebra de linha, barra vertical.
# O ponto NAO entra, porque nome como "R.E.P.O." depende dele.
PADRAO_CORTE = re.compile(r"[,\n|]")


# Nomes candidatos encontrados no texto do autor, sem repetir e preservando a ordem em que
# aparecem. Lista vazia quando nada plausivel foi achado — que e o caso mais comum nos
# shorts, onde a descricao e vazia.
def candidatos_do_video(titulo: str, descricao: str) -> list[str]:
    achados: list[str] = []

    for linha in (descricao or "").splitlines():
        for template in TEMPLATES:
            correspondencia = template.search(linha)
            if correspondencia is None:
                continue
            nome = _limpar(correspondencia.group(1))
            if _plausivel(nome):
                _acrescentar(achados, nome)
            break

    for hashtag in PADRAO_HASHTAG.findall(titulo or ""):
        if hashtag.casefold() not in HASHTAG_IGNORADA:
            _acrescentar(achados, hashtag)

    return achados


def _acrescentar(achados: list[str], nome: str) -> None:
    if nome.casefold() not in {existente.casefold() for existente in achados}:
        achados.append(nome)


def _limpar(nome: str) -> str:
    pedaco = PADRAO_CORTE.split(nome or "", maxsplit=1)[0]
    return re.sub(r"\s+", " ", pedaco).strip().strip(" .:-—!?").strip()


# Filtro contra o que claramente nao e nome de jogo. Cada condicao veio de um caso real da
# amostra: "um simulador de salva vidas" (genero, nao nome) e link solto na prosa.
def _plausivel(nome: str) -> bool:
    if not nome or len(nome) > TAMANHO_MAXIMO:
        return False
    if len(nome.split()) > MAXIMO_PALAVRAS:
        return False
    minusculo = nome.casefold()
    if "http" in minusculo or "www." in minusculo:
        return False
    return bool(re.search(r"[A-Za-zÀ-ÿ]", nome))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_candidato_jogo.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Run the whole suite**

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: `369 passed`

- [ ] **Step 6: Commit**

```bash
git add src/candidato_jogo.py tests/test_candidato_jogo.py
git commit -m "feat(descoberta): extract candidate game names from author prose"
```

---

### Task 9: Coleta de canal busca comentário para a descoberta

**Files:**
- Modify: `src/coletor_youtube.py` (`coletar_canal`)
- Test: `tests/test_coletor_youtube.py`

- [ ] **Step 1: Write the failing test**

Acrescente ao fim de `tests/test_coletor_youtube.py`:

```python
# --- Comentario de referencia: alimenta descoberta, nao identificacao ---
#
# Coletado em TODOS os videos, nao so nos sem jogo: descoberta mede hype, e jogo
# identificado tambem tem hype. Restringir daria descoberta zero justamente aos jogos que o
# sistema conhece.

class _RespostaComentarios:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(
            {
                "items": [
                    {"snippet": {"topLevelComment": {"snippet": {"textDisplay": t}}}}
                    for t in ["qual o nome do jogo", "muito bom"]
                ]
            }
        )


def test_coletar_canal_guarda_comentario_para_descoberta(monkeypatch, tmp_path):
    import coletor_youtube
    from leitor_csv import ler_videos_coletados

    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    monkeypatch.setattr(coletor_youtube, "_get_json", _fake_canal_em_lote([]))
    monkeypatch.setattr(
        coletor_youtube, "urlopen", lambda url, timeout=10: _RespostaComentarios()
    )
    destino = tmp_path / "videos_coletados.csv"

    coletor_youtube.coletar_canal(
        "UC_X", destino, limite=2, caminho_cache=None, limite_comentarios=10
    )

    primeiro = ler_videos_coletados(destino)[0]
    assert "qual o nome do jogo" in primeiro.texto_comentarios


def test_limite_de_comentarios_zero_nao_chama_a_api(monkeypatch, tmp_path):
    import coletor_youtube
    from leitor_csv import ler_videos_coletados

    chamou = []
    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    monkeypatch.setattr(coletor_youtube, "_get_json", _fake_canal_em_lote([]))
    monkeypatch.setattr(
        coletor_youtube,
        "urlopen",
        lambda url, timeout=10: chamou.append(url) or _RespostaComentarios(),
    )
    destino = tmp_path / "videos_coletados.csv"

    coletor_youtube.coletar_canal(
        "UC_X", destino, limite=2, caminho_cache=None, limite_comentarios=0
    )

    assert chamou == []
    assert ler_videos_coletados(destino)[0].texto_comentarios == ""


def test_comentario_coletado_liga_o_score_de_descoberta(monkeypatch, tmp_path):
    # O objetivo final da coleta de comentario. score_descoberta vale 15% do score final e
    # hoje le 0.0 para todo jogo, porque texto_comentarios esta vazio nos videos de
    # referencia. Sem esta afirmacao, as duas tarefas anteriores podem passar e a descoberta
    # continuar desligada sem ninguem perceber.
    import coletor_youtube
    from leitor_csv import ler_canais_referencia, ler_videos_coletados
    from modelos import CanalReferencia, JogoSeed
    from ranker import calcular_ranking

    monkeypatch.setenv("YOUTUBE_API_KEY", "CHAVE_FAKE")
    monkeypatch.setattr(coletor_youtube, "_get_json", _fake_canal_em_lote([]))
    monkeypatch.setattr(
        coletor_youtube, "urlopen", lambda url, timeout=10: _RespostaComentarios()
    )
    destino = tmp_path / "videos_coletados.csv"

    coletor_youtube.coletar_canal(
        "UC_X", destino, limite=2, caminho_cache=None, limite_comentarios=10
    )

    # O fake escreve "nesse video eu trouxe o jogo VID0" na descricao, entao um seed com
    # esse termo faz o video entrar no ranking e levar a descoberta junto.
    jogos = [JogoSeed(nome="VID0", aliases=["vid0"], genero="", fit_inicial=5.0)]
    canais = [
        CanalReferencia(
            nome="Lozao", plataforma="youtube", url="https://y/c", peso=1.0
        )
    ]
    ranking = calcular_ranking(jogos, ler_videos_coletados(destino), canais, [])

    assert ranking
    assert ranking[0].score_descoberta > 0
```

Confirme que `json` está importado no topo do arquivo de teste — está.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_coletor_youtube.py -k "guarda_comentario_para_descoberta or limite_de_comentarios_zero or liga_o_score" -v`
Expected: FAIL — `TypeError: coletar_canal() got an unexpected keyword argument 'limite_comentarios'`

- [ ] **Step 3: Write minimal implementation**

Em `src/coletor_youtube.py`, substitua `coletar_canal` por:

```python
# Coleta os videos recentes de um canal e salva cada um no CSV. videos.list vai em LOTE
# (1 unidade por 50). limite_comentarios > 0 busca tambem os comentarios, que aqui servem a
# UM proposito so: alimentar o score de descoberta ("gente perguntando que jogo e esse").
# A deteccao nao le esse campo — ver detectar_jogos_no_video. Custo: 1 unidade por video.
def coletar_canal(
    channel_id: str,
    caminho_destino: str | Path,
    limite: int = 5,
    caminho_cache: str | Path | None = CACHE_PADRAO,
    forcar: bool = False,
    limite_comentarios: int = 0,
) -> dict[str, int]:
    ids = listar_ids_recentes_do_canal(channel_id, limite)
    resumo = {"lidos": len(ids), "encontrados": 0, "salvos": 0, "duplicados": 0, "erros": 0}

    for detalhe in coletar_detalhes_em_lote_varios(ids):
        resumo["encontrados"] += 1
        video = detalhe_para_video_coletado(detalhe)
        if limite_comentarios > 0:
            video.texto_comentarios = " ".join(
                _comentarios_de_referencia(detalhe.video_id, limite_comentarios)
            )
        try:
            adicionar_video_csv(caminho_destino, video, substituir=forcar)
            resumo["salvos"] += 1
        except VideoDuplicadoError:
            resumo["duplicados"] += 1
        except ValueError:
            resumo["erros"] += 1

    resumo["erros"] += len(ids) - resumo["encontrados"]
    return resumo


# Comentario e sinal secundario aqui: qualquer erro de API degrada para lista vazia, para
# nao perder o video. limite_respostas baixo de proposito — medicao mostrou que o padrao 20
# dispara ~3 chamadas extras de comments.list por video sem trazer sinal novo.
def _comentarios_de_referencia(video_id: str, limite: int) -> list[str]:
    try:
        return coletar_textos_comentarios(video_id, limite, limite_respostas=5).textos
    except RuntimeError:
        return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_coletor_youtube.py -k "guarda_comentario_para_descoberta or limite_de_comentarios_zero or liga_o_score" -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Run the whole suite**

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: `372 passed`

- [ ] **Step 6: Commit**

```bash
git add src/coletor_youtube.py tests/test_coletor_youtube.py
git commit -m "feat(coletor): collect reference comments to feed the discovery score"
```

---

### Task 10: Lista dos não resolvidos

**Files:**
- Create: `src/descobertas.py`
- Test: `tests/test_descobertas.py`

- [ ] **Step 1: Write the failing test**

Crie `tests/test_descobertas.py`:

```python
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from descobertas import descobertas_sem_jogo
from modelos import JogoSeed, VideoColetado


def _jogos():
    return [JogoSeed(nome="Roblox", aliases=["roblox"], genero="", fit_inicial=5.0)]


def _video(titulo="t", descricao="", comentarios="", views=1000, canal="Lozao", url="https://y/1"):
    video = VideoColetado(
        titulo=titulo,
        canal=canal,
        plataforma="youtube",
        url=url,
        views=views,
        likes=10,
        comentarios=5,
        data_publicacao="2026-08-01",
        texto_comentarios=comentarios,
    )
    video.descricao = descricao
    return video


def test_video_com_pergunta_e_sem_jogo_entra_na_lista():
    videos = [_video(titulo="MATAR O VERITY", comentarios="qual o nome do jogo", views=724559)]

    achados = descobertas_sem_jogo(videos, _jogos())

    assert len(achados) == 1
    assert achados[0].views == 724559
    assert achados[0].perguntas == 1
    assert achados[0].candidato == ""


def test_video_com_jogo_identificado_fica_de_fora():
    videos = [_video(titulo="joguei Roblox", comentarios="qual o nome do jogo")]

    assert descobertas_sem_jogo(videos, _jogos()) == []


def test_video_sem_sinal_de_descoberta_fica_de_fora():
    videos = [_video(titulo="sem pista", comentarios="video muito bom")]

    assert descobertas_sem_jogo(videos, _jogos()) == []


def test_candidato_da_descricao_aparece_na_lista():
    videos = [
        _video(
            titulo="MEU BARCO NAUFRAGO",
            descricao="nesse vídeo eu trouxe um jogo chamado The lacerator",
            comentarios="que jogo e esse",
        )
    ]

    achados = descobertas_sem_jogo(videos, _jogos())

    assert achados[0].candidato == "The lacerator"


def test_ordena_por_alcance_decrescente():
    videos = [
        _video(titulo="a", comentarios="qual o nome do jogo", views=100, url="https://y/a"),
        _video(titulo="b", comentarios="qual o nome do jogo", views=900, url="https://y/b"),
    ]

    achados = descobertas_sem_jogo(videos, _jogos())

    assert [d.views for d in achados] == [900, 100]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_descobertas.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'descobertas'`

- [ ] **Step 3: Write minimal implementation**

Crie `src/descobertas.py`:

```python
# Lista de descobertas nao resolvidas: video de referencia em que gente perguntou o nome do
# jogo e nenhum jogo do seed foi identificado. E a saida honesta para o caso que nenhuma
# heuristica resolve — short sem descricao, sem hashtag e sem resposta nos comentarios, onde
# o nome do jogo simplesmente nao existe em texto nenhum.
#
# O sistema nao chuta: devolve o link e deixa a pessoa assistir. Sao 5 videos por semana em
# vez de 220. Funcao pura — recebe os dados ja lidos, nao toca disco nem a API.

from dataclasses import dataclass

from candidato_jogo import candidatos_do_video
from detector_jogo import detectar_jogos_no_video
from modelos import JogoSeed, VideoColetado
from ranker import FRASES_DESCOBERTA, _normalizar_texto


# Um video que atraiu curiosidade e continua sem jogo identificado.
# candidato: nome sugerido pela prosa/hashtag do autor; "" quando nao ha nenhum.
@dataclass
class DescobertaSemJogo:
    titulo: str
    canal: str
    url: str
    views: int
    perguntas: int
    candidato: str


def descobertas_sem_jogo(
    videos: list[VideoColetado], jogos: list[JogoSeed]
) -> list[DescobertaSemJogo]:
    achados = []

    for video in videos:
        if detectar_jogos_no_video(video, jogos):
            continue

        perguntas = _contar_perguntas(video)
        if not perguntas:
            continue

        candidatos = candidatos_do_video(video.titulo, video.descricao)
        achados.append(
            DescobertaSemJogo(
                titulo=video.titulo,
                canal=video.canal,
                url=video.url,
                views=video.views,
                perguntas=perguntas,
                candidato=candidatos[0] if candidatos else "",
            )
        )

    achados.sort(key=lambda descoberta: -descoberta.views)
    return achados


# Reusa as frases que o score de descoberta ja conhece, para a lista e o score contarem a
# mesma coisa. Duas listas de frases divergiriam na primeira vez que alguem editasse uma.
def _contar_perguntas(video: VideoColetado) -> int:
    texto = _normalizar_texto(f"{video.titulo} {video.texto_comentarios}")
    return sum(1 for frase in FRASES_DESCOBERTA if frase in texto)


# Mostra a lista no terminal, com o link para a pessoa assistir e decidir.
def imprimir_descobertas(achados: list[DescobertaSemJogo]) -> None:
    print("=== Descobertas sem Jogo Identificado ===")
    print()
    if not achados:
        print("Nenhum video de referencia com sinal de descoberta e sem jogo identificado.")
        return

    print(f"Total: {len(achados)}")
    print()
    for descoberta in achados:
        print(
            f"{descoberta.views:,} views | {descoberta.perguntas} pergunta(s) | "
            f"{descoberta.canal}"
        )
        print(f"  {descoberta.titulo[:70]}")
        print(f"  candidato: {descoberta.candidato or '(nenhum)'}")
        print(f"  {descoberta.url}")
        print()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_descobertas.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Run the whole suite**

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: `377 passed`

- [ ] **Step 6: Commit**

```bash
git add src/descobertas.py tests/test_descobertas.py
git commit -m "feat(descoberta): list reference videos with curiosity and no game"
```

---

### Task 11: Comando `descobertas_sem_jogo` na CLI

**Files:**
- Modify: `src/main.py` (import, despacho, função interativa, argparse, bloco de ajuda)
- Test: `tests/test_cli_erros.py`

- [ ] **Step 1: Write the failing test**

Acrescente ao fim de `tests/test_cli_erros.py`:

```python
# --- descobertas_sem_jogo ---

def test_parser_aceita_descobertas_sem_jogo():
    args = _construir_parser().parse_args(["descobertas_sem_jogo"])

    assert args.comando == "descobertas_sem_jogo"


def test_comando_descobertas_imprime_a_lista(tmp_path, monkeypatch, capsys):
    import main

    (tmp_path / "jogos_seed.csv").write_text(
        "nome,aliases,genero,fit_inicial\nRoblox,roblox,variado,7\n", encoding="utf-8"
    )
    (tmp_path / "videos_coletados.csv").write_text(
        "titulo,canal,plataforma,url,views,likes,comentarios,data_publicacao,"
        "texto_comentarios,origem,tipo_video,descricao,tags\n"
        "MATAR O VERITY,Lozao,youtube,https://y/1,724559,100,10,2026-08-01,"
        "qual o nome do jogo,youtube,curto,,\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(main, "DATA_DIR", tmp_path)
    monkeypatch.setattr(main, "VIDEOS_CSV", tmp_path / "videos_coletados.csv")

    assert main.main(["descobertas_sem_jogo"]) == 0

    saida = capsys.readouterr().out
    assert "MATAR O VERITY" in saida
    assert "724,559 views" in saida
    assert "(nenhum)" in saida
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_cli_erros.py -k "descobertas" -v`
Expected: FAIL — `SystemExit: 2` (`invalid choice: 'descobertas_sem_jogo'`)

- [ ] **Step 3: Write minimal implementation**

Em `src/main.py`, acrescente o import junto dos outros:

```python
from descobertas import descobertas_sem_jogo, imprimir_descobertas
```

Acrescente o despacho, logo depois do bloco de `videos_sem_jogo`:

```python
    if comando == "descobertas_sem_jogo":
        descobertas_sem_jogo_interativo()
        return 0
```

Acrescente a função interativa, ao lado de `videos_sem_jogo_interativo`:

```python
# Lista os videos de referencia que atrairam pergunta sobre o nome do jogo e continuam sem
# jogo identificado. E a fila de trabalho humano: assistir, descobrir o nome e cadastrar
# com adicionar_jogo. Nao toca a rede — le o que ja esta nos CSVs.
def descobertas_sem_jogo_interativo() -> None:
    videos = ler_videos_coletados(VIDEOS_CSV)
    jogos = ler_jogos_seed(DATA_DIR / "jogos_seed.csv")
    imprimir_descobertas(descobertas_sem_jogo(videos, jogos))
```

Acrescente o subcomando no `_construir_parser`, junto dos outros de qualidade:

```python
    subcomandos.add_parser(
        "descobertas_sem_jogo",
        help="Lista videos de referencia com gente perguntando o jogo e sem jogo identificado.",
    )
```

E no bloco de ajuda, acrescente `descobertas_sem_jogo` à linha de `Qualidade:`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_cli_erros.py -k "descobertas" -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Run the whole suite**

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: `379 passed`

- [ ] **Step 6: Commit**

```bash
git add src/main.py tests/test_cli_erros.py
git commit -m "feat(cli): add descobertas_sem_jogo to list unresolved discoveries"
```

---

## Depois do plano: recoleta real

Não faz parte das tarefas porque gasta quota e escreve em `data/`. Fazer com o dono presente:

```bash
python src/main.py coletar_canal_youtube <CHANNEL_ID> --limite 20 --forcar
python src/main.py validar_dados
python src/main.py descobertas_sem_jogo
python src/main.py ranking --top 10
```

Custo estimado para os 11 canais atuais: ~253 unidades de 10.000/dia. Rodar `--forcar` uma vez por canal para preencher `descricao`, `tags` e `tipo_video` nas 220 linhas antigas.

**Atenção antes de rodar:** `data/meus_videos.csv` e `data/meu_canal_ids_checkpoint.json` estão fora do git de propósito (dado do canal em repo público). `data/videos_coletados.csv` e `data/canais_referencia.csv` continuam versionados.

## O que este plano não faz

Registrado para ninguém procurar depois:

- Canais de referência ainda não incluem `@lozao` nem `@ElCamacho24`. Frente separada.
- TikTok (`@lohzao`) não tem caminho de coleta — API não é pública.
- Sem classificação single player / multiplayer.
- Sem foco em jogo recém-lançado contra consolidado.
- `coletar_videos_por_ids` (arquivo de ids) continua no caminho antigo, uma chamada por
  vídeo. Só `coletar_canal` foi para o lote.
