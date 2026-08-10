"""Leitura de mídias enviadas pelo cliente: IMAGEM e DOCUMENTO.

O áudio tem caminho próprio (transcrição via Whisper em `assistente.transcrever_audio`)
e é NATIVO — sempre ligado. Imagem e documento são capacidades OPCIONAIS por
assistente (`ler_imagem` / `ler_documento`), porque têm custo extra de tokens:

  • Imagem   → o modelo de visão descreve o conteúdo (foto, comprovante, print) e a
               descrição entra na conversa como texto.
  • Documento→ o texto do arquivo (PDF, Word, txt/csv) é extraído localmente e
               injetado no contexto, truncado em `LIMITE_DOC_CHARS`.

Em ambos os casos o resultado vira TEXTO — o resto do fluxo (histórico da thread,
coleta, handoff) continua exatamente igual ao de uma mensagem escrita.
"""

import base64
import io
import logging

from app.services.saldo import registrar_resultado_openai

logger = logging.getLogger("uvicorn.error")

# Teto de caracteres extraídos de um documento. Alinhado com o que o painel
# promete ("até 8.000 caracteres") — evita estourar contexto/custo com PDFs longos.
LIMITE_DOC_CHARS = 8000

# Modelo de visão. O mesmo usado no atendimento, para não introduzir outro custo.
MODELO_VISAO = "gpt-4.1-mini"

_PROMPT_VISAO = (
    "Descreva objetivamente, em português do Brasil, a imagem que um cliente enviou "
    "pelo WhatsApp para um atendimento comercial. Diga o que aparece e, se for um "
    "documento, comprovante, print de conversa, tabela ou etiqueta, TRANSCREVA os "
    "textos e números legíveis (valores, datas, nomes, códigos). Não invente nada: "
    "o que estiver ilegível, diga que está ilegível. Seja direto, sem introduções."
)

_IMAGEM_HINTS = ("image", "imagem", "jpeg", "jpg", "png", "webp", "heic")
_DOC_HINTS = (
    "document", "documento", "pdf", "msword", "wordprocessing", "officedocument",
    "text/plain", "csv", ".docx", ".doc", ".txt",
)


def _campos(msg: dict) -> str:
    """Concatena os campos onde a UAzAPI indica o tipo/mimetype da mensagem."""
    return " ".join(
        str(msg.get(k) or "")
        for k in ("messageType", "type", "mediaType", "mimetype", "mimeType", "fileName", "filename")
    ).lower()


def eh_imagem(msg: dict) -> bool:
    """True para imagens de verdade. Figurinha (sticker) NÃO conta: é reação/piada,
    descrevê-la só gastaria tokens e poluiria a conversa."""
    campos = _campos(msg)
    if "sticker" in campos:
        return False
    return any(h in campos for h in _IMAGEM_HINTS) or bool(msg.get("image"))


def eh_documento(msg: dict) -> bool:
    campos = _campos(msg)
    return any(h in campos for h in _DOC_HINTS) or bool(msg.get("document"))


def nome_arquivo(msg: dict) -> str:
    return str(msg.get("fileName") or msg.get("filename") or msg.get("title") or "arquivo").strip()


def decodificar_base64(valor) -> bytes:
    """Converte o base64 da UAzAPI em bytes, aceitando data URI (`data:...;base64,`)."""
    if not valor:
        return b""
    if isinstance(valor, (bytes, bytearray)):
        return bytes(valor)
    texto = str(valor)
    if texto.startswith("data:") and "," in texto:
        texto = texto.split(",", 1)[1]
    try:
        return base64.b64decode(texto)
    except Exception as e:
        logger.warning("[midia] base64 inválido: %s", e)
        return b""


# ── Imagem (visão) ───────────────────────────────────────────────────────────

async def descrever_imagem(
    *,
    imagem_bytes: bytes,
    mimetype: str,
    api_key: str,
    usuario_id: str | None = None,
) -> str:
    """Descreve a imagem usando o modelo de visão da OpenAI. Retorna '' se falhar.

    Nunca levanta exceção: uma imagem que não pôde ser lida não pode derrubar o
    atendimento — o webhook apenas segue sem a descrição.
    """
    if not imagem_bytes or not api_key:
        return ""

    mime = (mimetype or "").split(";")[0].strip() or "image/jpeg"
    if not mime.startswith("image/"):
        mime = "image/jpeg"
    b64 = base64.b64encode(imagem_bytes).decode()

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=api_key)
        resp = await client.chat.completions.create(
            model=MODELO_VISAO,
            temperature=0.2,
            max_tokens=600,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": _PROMPT_VISAO},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                ],
            }],
        )
        texto = (resp.choices[0].message.content or "").strip()
        await registrar_resultado_openai(usuario_id, sucesso=True)
        logger.info("[midia] imagem descrita (%d chars)", len(texto))
        return texto
    except Exception as e:
        await registrar_resultado_openai(usuario_id, sucesso=False, erro=e)
        logger.exception("[midia] erro ao descrever imagem: %s", e)
        return ""


# ── Documento (extração de texto local) ──────────────────────────────────────

def _texto_pdf(conteudo: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        logger.warning("[midia] pypdf não instalado — PDF não pode ser lido")
        return ""
    try:
        reader = PdfReader(io.BytesIO(conteudo))
        partes: list[str] = []
        for pagina in reader.pages:
            partes.append(pagina.extract_text() or "")
            # Para de ler assim que já temos texto suficiente (PDF de 200 páginas
            # não precisa ser percorrido inteiro para ser truncado depois).
            if sum(len(p) for p in partes) >= LIMITE_DOC_CHARS:
                break
        return "\n".join(partes)
    except Exception as e:
        logger.warning("[midia] falha ao extrair texto do PDF: %s", e)
        return ""


def _texto_docx(conteudo: bytes) -> str:
    try:
        import docx  # python-docx
    except ImportError:
        logger.warning("[midia] python-docx não instalado — Word não pode ser lido")
        return ""
    try:
        doc = docx.Document(io.BytesIO(conteudo))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as e:
        logger.warning("[midia] falha ao extrair texto do Word: %s", e)
        return ""


def _texto_plano(conteudo: bytes) -> str:
    for encoding in ("utf-8", "latin-1"):
        try:
            return conteudo.decode(encoding)
        except UnicodeDecodeError:
            continue
    return ""


def extrair_texto_documento(*, conteudo: bytes, filename: str = "", mimetype: str = "") -> str:
    """Extrai o texto de PDF / Word (.docx) / txt-csv. Retorna '' se não suportado.

    Formatos legados (.doc binário) e planilhas não são suportados — melhor devolver
    vazio e o assistente seguir sem o conteúdo do que injetar lixo binário no prompt.
    """
    if not conteudo:
        return ""
    alvo = f"{filename} {mimetype}".lower()

    if "pdf" in alvo or conteudo[:5] == b"%PDF-":
        texto = _texto_pdf(conteudo)
    elif "wordprocessing" in alvo or "officedocument" in alvo or alvo.rstrip().endswith(".docx"):
        texto = _texto_docx(conteudo)
    elif "text/" in alvo or "csv" in alvo or alvo.rstrip().endswith((".txt", ".csv", ".md")):
        texto = _texto_plano(conteudo)
    else:
        # Sem pista pelo nome/mimetype: tenta como texto puro e descarta se vier binário.
        texto = _texto_plano(conteudo)
        if texto and texto.count("�") > len(texto) * 0.05:
            texto = ""

    texto = " ".join(texto.split()) if texto else ""
    if not texto:
        logger.info("[midia] documento sem texto extraível (%s / %s)", filename, mimetype)
        return ""
    if len(texto) > LIMITE_DOC_CHARS:
        texto = texto[:LIMITE_DOC_CHARS] + "\n[...conteúdo truncado...]"
    return texto
