# Publicacao no GitHub

Este repositorio foi pensado para ser publico. Os CSVs versionados em `data/` devem continuar sendo exemplos ficticios ou dados que voce aceita publicar.

## Nao commitar

- Tokens, API keys, cookies, credenciais, arquivos `.env` reais ou exports de ferramentas logadas.
- Dados privados do canal Roberto Careca, como receita, propostas comerciais, negociacoes, contatos de marcas ou metricas internas que nao seriam publicas.
- Planilhas brutas, relatatorios privados, screenshots de dashboards ou arquivos em `data/raw/`, `data/private/`, `data/privado/` e `data/exports/`.
- Comentarios coletados com dados pessoais sensiveis. Mesmo quando o comentario for publico, prefira exemplos resumidos ou anonimizados no repositorio.
- Arquivos gerados localmente, como `__pycache__/`, logs, bancos locais e ambientes virtuais.

## Pode commitar

- Codigo em `src/`.
- Testes em `tests/`.
- CSVs de exemplo pequenos, ficticios e revisados manualmente.
- Documentacao do funcionamento do ranking.

## Checklist antes do push

```bash
git status --short
git diff --cached
python -m unittest discover -s tests
```

Antes de confirmar o push, procure nomes de arquivos suspeitos no `git status`, principalmente `.env`, `secret`, `token`, `private`, `privado`, `raw`, `exports`, `real` e `sensivel`.
