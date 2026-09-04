from fastapi import APIRouter, HTTPException, Query

from api import dependencies
from api.schemas import EvidenciaVideoOut, EvidenciasJogoOut
from evidencias_jogo import (
    calcular_score_evidencia_criadores,
    gerar_evidencias,
    resumir_evidencia_criadores,
)

router = APIRouter(tags=["evidencias"])


@router.get("/evidencias/{jogo}", response_model=EvidenciasJogoOut)
def obter_evidencias(jogo: str, tipo: str | None = Query(None)):
    ranking = dependencies.carregar_ranking()
    canais = dependencies.carregar_canais()
    evidencias_por_jogo = gerar_evidencias(ranking, canais)

    alvo = jogo.strip().casefold()
    encontrado = next(
        (nome for nome in evidencias_por_jogo if nome.casefold() == alvo), None
    )
    if encontrado is None or not evidencias_por_jogo[encontrado]:
        raise HTTPException(status_code=404, detail=f"Jogo nao encontrado: {jogo}")

    evidencias = evidencias_por_jogo[encontrado]
    if tipo:
        evidencias = [e for e in evidencias if e.tipo_video == tipo]
        if not evidencias:
            raise HTTPException(
                status_code=404,
                detail=f"Nenhum video do tipo '{tipo}' encontrado para o jogo: {encontrado}",
            )

    return EvidenciasJogoOut(
        jogo=encontrado,
        score_evidencia=calcular_score_evidencia_criadores(evidencias),
        resumo=resumir_evidencia_criadores(evidencias),
        videos=[EvidenciaVideoOut.model_validate(e) for e in evidencias],
    )
