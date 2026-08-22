"""Gravação da timeline de conversa (public.mensagens) para canais vinculados a
um profissional — o modelo novo, separado do fluxo de campanha/IA existente.

Só é chamado quando `repo.get_profissional_by_instancia` encontra um vínculo;
para qualquer outra instância, este módulo nunca é acionado — o comportamento
atual do webhook (campanha, IA por usuário) fica 100% intocado.
"""

import base64
import logging
import mimetypes
import re

import httpx

from app.services import repo, storage
from app.services.uazapi import baixar_midia, buscar_foto_perfil

logger = logging.getLogger("uvicorn.error")

_TYPE_MAP = {
    "conversation": "text", "extendedtextmessage": "text",
    "audiomessage": "audio", "imagemessage": "image",
    "documentmessage": "document", "videomessage": "video",
    "stickermessage": "sticker", "reactionmessage": "reaction",
}

_TIPO_MIDIA = {"audio": "audio", "image": "imagem", "sticker": "imagem", "document": "pdf", "video": "video"}

# `mimetypes.guess_extension` do stdlib não conhece vários tipos modernos neste
# ambiente (ex.: o mimetype de .docx cai em None) e o upload virava ".bin" —
# cobre aqui os formatos que realmente circulam num atendimento.
_EXT_POR_MIME = {
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.ms-powerpoint": ".ppt",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "text/csv": ".csv",
    "text/plain": ".txt",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "audio/mpeg": ".mp3",
    "audio/ogg": ".ogg",
    "audio/mp4": ".m4a",
    "video/mp4": ".mp4",
}


def _extensao_midia(*, mimetype: str, arquivo_nome: str | None) -> str:
    """Decide a extensão do arquivo no Storage.

    Prioriza a extensão do NOME ORIGINAL enviado pelo cliente (é o que ele de
    fato mandou, mais confiável que o mimetype que a UAzAPI devolve) e só cai
    pro mimetype/`.bin` quando o nome não tem extensão utilizável.
    """
    if arquivo_nome and "." in arquivo_nome:
        candidata = "." + arquivo_nome.rsplit(".", 1)[-1].lower().strip()
        if 1 < len(candidata) <= 6 and candidata[1:].isalnum():
            return candidata
    mime_limpo = (mimetype or "").split(";")[0].strip()
    if mime_limpo in _EXT_POR_MIME:
        return _EXT_POR_MIME[mime_limpo]
    return (mimetypes.guess_extension(mime_limpo) if mime_limpo else None) or ".bin"


def kind_da_mensagem(msg: dict) -> str:
    """Mapeia o tipo da mensagem da UAzAPI para o `kind` canônico do banco."""
    tipo = str(msg.get("messageType") or msg.get("type") or "").lower()
    if tipo in _TYPE_MAP:
        return _TYPE_MAP[tipo]
    campos = " ".join(str(msg.get(k) or "") for k in ("mediaType", "mimetype", "mimeType")).lower()
    if "audio" in campos:
        return "audio"
    if "sticker" in campos or "webp" in campos:
        return "sticker"
    if "image" in campos:
        return "image"
    if "video" in campos:
        return "video"
    if any(h in campos for h in ("document", "pdf", "word", "text/plain", "officedocument")):
        return "document"
    return "text"


def _message_id(msg: dict) -> str | None:
    key = msg.get("key") if isinstance(msg.get("key"), dict) else {}
    return msg.get("messageid") or msg.get("id") or msg.get("messageId") or key.get("id")


# Campos onde o nome do CONTATO pode vir, em ordem de confiança — `chat.*`
# descreve o contato (mais confiável); `message.*` descreve quem MANDOU a
# mensagem (só é lido para RECEIVED, então aqui sempre é o cliente). Ver
# foto-nome-contato-e-badges-conversas.md §2.
_NOME_CHAT_KEYS = ("wa_name", "wa_contactName", "name")
_NOME_MSG_KEYS = ("senderName", "pushName", "notifyName", "verifiedBizName")


def _nome_util(valor, telefone: str) -> str | None:
    """Descarta candidatos inúteis: vazio, só dígitos, ou o próprio telefone."""
    if not isinstance(valor, str):
        return None
    nome = valor.strip()
    if not nome:
        return None
    digitos = re.sub(r"\D", "", nome)
    if digitos == nome:  # só dígitos (ex.: pushName vindo igual ao telefone)
        return None
    if telefone and digitos and digitos in telefone:
        return None
    return nome[:120]


def _extrair_nome_contato(*, chat: dict, msg: dict, telefone: str) -> str | None:
    """Nome do CONTATO (cliente) — varre `chat.*` primeiro, depois `message.*`."""
    for chave in _NOME_CHAT_KEYS:
        nome = _nome_util((chat or {}).get(chave), telefone)
        if nome:
            return nome
    for chave in _NOME_MSG_KEYS:
        nome = _nome_util(msg.get(chave), telefone)
        if nome:
            return nome
    return None


async def _resolver_midia_para_arquivo(
    *, msg: dict, token: str, kind: str, usuario_id: str,
) -> tuple[str | None, str | None]:
    """Baixa a mídia da UAzAPI e sobe pro Storage. Retorna (storage_path, arquivo_nome).

    Nunca lança: falha em download/upload vira (None, None) — a mensagem é
    gravada mesmo assim, só sem mídia anexada (melhor perder a mídia do que
    perder a mensagem inteira do histórico).
    """
    message_id = _message_id(msg)
    if not message_id:
        return None, None
    try:
        data = await baixar_midia(token=token, message_id=message_id)
    except Exception as e:
        logger.warning("[conversas] falha ao baixar mídia %s: %s", message_id, e)
        return None, None
    if not isinstance(data, dict) or data.get("error"):
        return None, None

    b64 = data.get("base64Data") or data.get("base64")
    mimetype = str(data.get("mimetype") or msg.get("mimetype") or "")
    arquivo_nome = msg.get("fileName") or msg.get("filename")
    if not b64:
        return None, arquivo_nome
    try:
        if isinstance(b64, str) and b64.startswith("data:") and "," in b64:
            b64 = b64.split(",", 1)[1]
        conteudo = base64.b64decode(b64)
    except Exception:
        return None, arquivo_nome

    ext = _extensao_midia(mimetype=mimetype, arquivo_nome=arquivo_nome)
    path = storage.caminho_storage(
        usuario_id=usuario_id, kind=kind, identificador=message_id, ext=ext,
    )
    ok = await storage.upload_midia(path=path, conteudo=conteudo, content_type=mimetype)
    return (path, arquivo_nome) if ok else (None, arquivo_nome)


# Nomes de campo tentados, em ordem — a UAzAPI não documenta um único nome
# estável pra foto de perfil do contato (varia por versão/endpoint). `imagePreview`
# é o campo real observado no bloco `chat` do webhook (ver
# foto-nome-contato-e-badges-conversas.md) — vem primeiro por ser o mais
# confiável; os demais ficam como fallback para variações de payload.
# Best-effort por natureza: se nenhum bater, a sincronização simplesmente não
# acontece e `conversas.photo` fica null (o avatar cai pras iniciais no painel).
_CAMPOS_FOTO_CONTATO = (
    "imagePreview", "photo", "imgUrl", "profilePicUrl",
    "wa_contact_photo", "contactPhoto", "chatPhoto",
)


async def sincronizar_foto_perfil(
    *, chat: dict, usuario_id: str, conversa_id: str, token: str | None = None, numero: str | None = None,
) -> None:
    """Baixa a foto de perfil do CONTATO e sobe pro Storage, gravando o path em
    conversas.photo — só na 1ª vez (repo já filtra por `photo is null`). Nunca
    lança: é puramente cosmético.

    Duas fontes, nessa ordem:
    1. Passivo: campo de foto que já veio no `chat` do próprio payload do webhook
       (`imagePreview` etc.) — mais rápido, mas intermitente (nem toda mensagem
       traz esse bloco preenchido).
    2. Ativo (fallback): se nada veio no passo 1 e temos `token`+`numero`, chama
       a UAzAPI direto (`/chat/details`) — é a fonte confiável de verdade (mesmo
       endpoint que o Agzap usa, ver foto-nome-contato-e-badges-conversas.md §3.2).

    `imagePreview`/`image` podem vir como URL http(s) OU como data URI base64
    (miniatura embutida) — os dois formatos são tratados aqui.
    """
    valor = next((chat.get(campo) for campo in _CAMPOS_FOTO_CONTATO if chat.get(campo)), None) if chat else None
    if not isinstance(valor, str) or not valor.strip():
        if token and numero:
            valor = await buscar_foto_perfil(token=token, numero=numero)
        if not isinstance(valor, str) or not valor.strip():
            # Diagnóstico: nenhuma das duas fontes trouxe foto — mostra as chaves
            # reais de `chat` pra mapear o campo certo sem precisar de tcpdump
            # (mesmo raciocínio do handoff: sem isso a causa fica invisível no log).
            logger.info(
                "[conversas] sem foto de perfil (conversa=%s, chat_keys=%s, fallback_ativo=%s)",
                conversa_id, sorted((chat or {}).keys())[:30], bool(token and numero),
            )
            return
    valor = valor.strip()
    try:
        if valor.startswith("data:"):
            cabecalho, _, b64data = valor.partition(",")
            if not b64data:
                logger.warning("[conversas] foto veio como data URI sem conteúdo base64 (conversa=%s)", conversa_id)
                return
            match = re.match(r"data:([^;,]+)", cabecalho)
            content_type = match.group(1) if match else "image/jpeg"
            conteudo = base64.b64decode(b64data)
        else:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(valor)
            if resp.status_code >= 400 or not resp.content:
                logger.warning(
                    "[conversas] falha ao baixar foto de perfil (conversa=%s, status=%s, url=%s)",
                    conversa_id, resp.status_code, valor[:120],
                )
                return
            content_type = resp.headers.get("content-type", "image/jpeg")
            conteudo = resp.content
        if not conteudo:
            return
        ext = mimetypes.guess_extension(content_type.split(";")[0].strip()) or ".jpg"
        path = storage.caminho_foto_perfil(usuario_id=usuario_id, conversa_id=conversa_id, ext=ext)
        ok = await storage.upload_midia(path=path, conteudo=conteudo, content_type=content_type)
        if not ok:
            logger.warning("[conversas] upload da foto de perfil falhou (conversa=%s, path=%s)", conversa_id, path)
            return
        await repo.atualizar_foto_conversa(conversa_id=conversa_id, path=path)
        logger.info("[conversas] foto de perfil sincronizada (conversa=%s, path=%s)", conversa_id, path)
    except Exception as e:
        logger.warning("[conversas] falha ao sincronizar foto de perfil: %s", e)


async def gravar_mensagem(
    *,
    usuario_id: str,
    instancia_id: str,
    phone: str,
    msg: dict,
    token: str,
    direcao: str,                       # 'RECEIVED' | 'SENT'
    enviado_por: str,                   # 'user' | 'assistant' | 'celular'
    profissional: dict | None,
    texto_legenda: str | None = None,   # override do texto (ex.: resposta da IA)
    chat: dict | None = None,           # bloco "chat" do payload — usado pra foto de perfil
) -> None:
    """Grava 1 mensagem na timeline da conversa (mensagens + mídia, se houver) e,
    para o profissional respondendo pelo celular, abre o atendimento se for a
    1ª mensagem da conversa.

    Best-effort e nunca lança: é sempre um efeito colateral do webhook, nunca
    pode derrubar a resposta da IA, a pausa ou o registro de campanha.
    """
    try:
        kind = kind_da_mensagem(msg)
        wa_id = _message_id(msg)

        nome_contato = None
        chatlid = None
        if direcao == "RECEIVED":
            # Em fromMe=true esses campos descrevem a EMPRESA, não o cliente — só
            # são confiáveis quando a mensagem é do cliente (ver handoff §3.2).
            nome_contato = _extrair_nome_contato(chat=chat or {}, msg=msg, telefone=phone)
            chatlid = msg.get("chatlid")

        quoted = msg.get("quoted") if isinstance(msg.get("quoted"), dict) else None
        reply_to_wa_id = quoted.get("id") if quoted else None
        reply_to_from_me = quoted.get("fromMe") if quoted else None

        storage_path, arquivo_nome = (None, None)
        if kind in ("audio", "image", "document", "video", "sticker"):
            storage_path, arquivo_nome = await _resolver_midia_para_arquivo(
                msg=msg, token=token, kind=kind, usuario_id=usuario_id,
            )

        texto = texto_legenda if texto_legenda is not None else (msg.get("text") or "").strip()

        gravado = await repo.inserir_mensagem_conversa(
            usuario_id=usuario_id,
            instancia_id=instancia_id,
            numero=phone,
            nome_contato=nome_contato,
            chatlid=chatlid,
            mensagem=texto or None,
            direcao=direcao,
            enviado_por=enviado_por,
            enviado_por_profissional_id=(profissional or {}).get("id") if enviado_por == "celular" else None,
            kind=kind,
            arquivo_nome=arquivo_nome,
            wa_message_id=wa_id,
            reply_to_wa_id=reply_to_wa_id,
            reply_to_text=None,
            reply_to_from_me=reply_to_from_me,
        )
        if not gravado:
            return  # duplicata (idempotência por wa_message_id)

        if storage_path:
            tipo = _TIPO_MIDIA.get(kind)
            if tipo:
                await repo.inserir_midia_conversa(
                    mensagem_id=str(gravado["id"]),
                    usuario_id=usuario_id,
                    instancia_id=instancia_id,
                    storage_path=storage_path,
                    tipo=tipo,
                    url_original=None,
                    url_storage=storage_path,
                )

        if direcao == "RECEIVED":
            await sincronizar_foto_perfil(
                chat=chat or {}, usuario_id=usuario_id, conversa_id=str(gravado["conversa_id"]),
                token=token, numero=phone,
            )

        if direcao == "SENT" and enviado_por == "celular" and profissional:
            await repo.abrir_atendimento_automatico(
                conversa_id=str(gravado["conversa_id"]), profissional_id=profissional["id"],
            )
    except Exception as e:
        logger.exception("[conversas] falha ao gravar mensagem (%s/%s): %s", direcao, enviado_por, e)
