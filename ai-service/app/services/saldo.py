"""Detecção de saldo/cota da OpenAI por usuário.

Ponto central para instrumentar TODOS os caminhos que chamam a OpenAI (disparo,
assistente do webhook e follow-up). A ideia é simples e auto-curável:

  • Qualquer chamada que falhe com 429/insufficient_quota  → marca "sem saldo".
  • Qualquer chamada que dê certo                          → limpa a flag.

Como o assistente responde a cada mensagem do cliente, no instante em que a conta
é recarregada a próxima resposta bem-sucedida limpa a flag sozinha — sem precisar
de cron nem de intervenção manual. O painel lê essa flag e mostra o banner.
"""

import logging

from app.services import repo

logger = logging.getLogger("uvicorn.error")


def e_erro_de_saldo(err: object) -> bool:
    """True se a exceção/mensagem indica cota/saldo esgotado na OpenAI (429)."""
    s = str(err).lower()
    return (
        "insufficient_quota" in s
        or "code: 429" in s          # "Error code: 429" / "status code: 429"
        or "exceeded your current quota" in s
    )


async def registrar_resultado_openai(
    usuario_id: str | None, *, sucesso: bool, erro: object = None
) -> None:
    """Atualiza a flag de saldo do usuário a partir do resultado de uma chamada à IA.

    Nunca levanta exceção (não pode derrubar o fluxo de IA por causa do banner).
    """
    if not usuario_id:
        return
    try:
        if sucesso:
            await repo.set_openai_sem_saldo(str(usuario_id), False)
        elif e_erro_de_saldo(erro):
            await repo.set_openai_sem_saldo(str(usuario_id), True)
            logger.warning("[saldo] OpenAI sem saldo/cota — usuário %s", usuario_id)
    except Exception as e:
        logger.warning("[saldo] falha ao atualizar flag de saldo (usuário %s): %s", usuario_id, e)
