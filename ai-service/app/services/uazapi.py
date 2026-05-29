"""Cliente da UAzAPI (envio de mensagens de texto)."""

import httpx

from app.config import get_settings


async def enviar_texto(*, token: str, numero: str, texto: str) -> dict:
    """Envia uma mensagem de texto pela UAzAPI usando o token da instância (canal).

    Retorna: {sucesso, status_code, messageid, data}
    """
    settings = get_settings()
    url = f"{settings.UAZAPI_URL.rstrip('/')}/send/text"

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            url,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "token": token,
            },
            json={"number": numero, "text": texto},
        )

    data: dict = {}
    try:
        data = resp.json()
    except Exception:
        pass

    response_block = data.get("response") if isinstance(data, dict) else None
    api_status = (response_block or {}).get("status")
    sucesso = resp.status_code < 400 and api_status != "error"

    return {
        "sucesso": sucesso,
        "status_code": resp.status_code,
        "messageid": data.get("messageid") or data.get("id"),
        "data": data,
    }
