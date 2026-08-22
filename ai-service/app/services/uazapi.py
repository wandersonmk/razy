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


async def consultar_status(*, token: str) -> dict:
    """Consulta o status AO VIVO de uma instância na UAzAPI (GET /instance/status).

    Usado para validar, no início do disparo, se o canal está REALMENTE conectado
    — sem depender do status gravado no banco, que fica defasado quando a instância
    é excluída/reconectada direto no painel da UAzAPI (deixa canal-fantasma no
    roteamento ou de fora um número já conectado).

    Retorna: {conectado: bool, status: str, inconclusivo: bool}.
    - inconclusivo=True → não deu para saber (rede caiu / UAzAPI 5xx). Quem chama
      NÃO deve derrubar um canal por causa disso.
    - inconclusivo=False + conectado=False → a UAzAPI AFIRMA que está fora (inclui
      401/404 = instância não existe mais na UAzAPI, foi excluída lá).
    """
    settings = get_settings()
    url = f"{settings.UAZAPI_URL.rstrip('/')}/instance/status"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers={"Accept": "application/json", "token": token})
    except Exception:
        # Falha de rede transitória: estado real desconhecido → inconclusivo.
        return {"conectado": False, "status": "erro", "inconclusivo": True}

    data: dict = {}
    try:
        data = resp.json()
    except Exception:
        pass
    if not isinstance(data, dict):
        data = {}

    if resp.status_code >= 400:
        # 401/404 = instância não existe mais / token inválido → afirma que está
        # fora (derruba). 5xx e demais = problema transitório → inconclusivo.
        gone = resp.status_code in (401, 404)
        return {
            "conectado": False,
            "status": "inexistente" if gone else "erro",
            "inconclusivo": not gone,
        }

    instance = data.get("instance") or {}
    status_obj = data.get("status") if isinstance(data.get("status"), dict) else None
    inst_status = str(instance.get("status") or "").lower()
    # O booleano autoritativo da UAzAPI vence sobre a string meta
    # (cuidado: "disconnected" contém "connect" como substring).
    if status_obj and isinstance(status_obj.get("connected"), bool):
        conectado = bool(status_obj.get("connected") or status_obj.get("loggedIn"))
    else:
        conectado = inst_status in ("connected", "online")
    return {
        "conectado": conectado,
        "status": inst_status or ("connected" if conectado else "disconnected"),
        "inconclusivo": False,
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


async def buscar_foto_perfil(*, token: str, numero: str) -> str | None:
    """Busca a foto de perfil do contato direto na UAzAPI (POST /chat/details).

    Fallback ATIVO usado quando o payload do webhook não trouxe nenhum campo de
    foto (o campo `chat.imagePreview` do webhook é intermitente/best-effort — ver
    foto-nome-contato-e-badges-conversas.md §3). Retorna a URL da foto (ou None
    se o contato não tiver foto/a chamada falhar) — nunca lança."""
    settings = get_settings()
    url = f"{settings.UAZAPI_URL.rstrip('/')}/chat/details"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                url,
                headers={"Accept": "application/json", "Content-Type": "application/json", "token": token},
                json={"number": numero, "preview": False},
            )
        if resp.status_code >= 400:
            return None
        data = resp.json()
        if not isinstance(data, dict):
            return None
        return data.get("image") or data.get("imagePreview") or None
    except Exception:
        return None


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
