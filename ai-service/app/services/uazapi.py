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

    erro = None
    if not sucesso:
        # Mensagem de erro da própria UAzAPI quando houver; senão o HTTP cru.
        erro = (
            (response_block or {}).get("error")
            or (data.get("error") if isinstance(data, dict) else None)
            or (data.get("message") if isinstance(data, dict) else None)
            or f"HTTP {resp.status_code}"
        )

    return {
        "sucesso": sucesso,
        "status_code": resp.status_code,
        "messageid": data.get("messageid") or data.get("id"),
        "erro": erro,
        "data": data,
    }


async def enviar_presenca(
    *,
    token: str,
    numero: str,
    presence: str = "composing",
    delay_ms: int = 3000,
) -> bool:
    """Sinaliza presença no chat (ex.: 'composing' = digitando). Best-effort."""
    settings = get_settings()
    url = f"{settings.UAZAPI_URL.rstrip('/')}/message/presence"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                url,
                headers={"Accept": "application/json", "Content-Type": "application/json", "token": token},
                json={"number": numero, "presence": presence, "delay": delay_ms},
            )
        return resp.status_code < 400
    except Exception:
        return False


async def baixar_midia(
    *,
    token: str,
    message_id: str,
    transcribe: bool = False,
    openai_apikey: str | None = None,
) -> dict:
    """Baixa (e opcionalmente transcreve) uma mídia pelo endpoint /message/download.

    Retorna o JSON da UAzAPI: {fileURL, mimetype, base64Data, transcription}.
    Em caso de erro HTTP, retorna {"error": ...}.
    """
    settings = get_settings()
    url = f"{settings.UAZAPI_URL.rstrip('/')}/message/download"

    body: dict = {"id": message_id, "return_base64": True}
    if transcribe:
        body["transcribe"] = True
        if openai_apikey:
            body["openai_apikey"] = openai_apikey

    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.post(
            url,
            headers={"Accept": "application/json", "Content-Type": "application/json", "token": token},
            json=body,
        )

    try:
        data = resp.json()
    except Exception:
        data = {}
    if resp.status_code >= 400:
        data = {"error": data.get("error") if isinstance(data, dict) else f"HTTP {resp.status_code}", "status_code": resp.status_code}
    return data if isinstance(data, dict) else {}
