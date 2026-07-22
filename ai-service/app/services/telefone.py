"""Normalização de telefone BR — o número que ENVIAMOS nem sempre é o que VOLTA.

O WhatsApp entrega o JID de boa parte dos celulares brasileiros SEM o nono
dígito (comportamento típico de DDD >= 31), enquanto o disparo sai COM ele
(`5531988887777` no envio → `553188887777` no webhook). Como toda a resolução do
webhook é chaveada pelo telefone (`conv:` = contexto da campanha, `echo:` = eco
do nosso envio, `pausa:` e a thread da IA), essa diferença de um dígito fazia a
resposta do cliente não casar com o disparo: a resposta não era registrada em
`disparos.respondido_em` e o contador de respostas da campanha ficava zerado.
"""

import re

# Faixas de celular no Brasil: o nono dígito é sempre 9 e o oitavo (1º do número
# sem DDD, na forma de 10 dígitos) fica entre 6 e 9. Landline nunca ganha o 9.
_INICIO_CELULAR = "6789"


def so_digitos(t: str | None) -> str:
    if not t:
        return ""
    return re.sub(r"\D", "", t.split("@")[0])


def variantes(telefone: str | None) -> list[str]:
    """Formas equivalentes do MESMO número: com/sem 9º dígito e com/sem DDI 55.

    A primeira da lista é sempre a entrada normalizada, para que quem consulta
    tente primeiro a forma exata que recebeu. Números não-brasileiros (ou fora
    dos tamanhos conhecidos) voltam apenas com a própria forma.
    """
    base = so_digitos(telefone)
    if not base:
        return []

    nac = base[2:] if base.startswith("55") and len(base) in (12, 13) else base

    formas = {nac}
    if len(nac) == 11 and nac[2] == "9" and nac[3] in _INICIO_CELULAR:
        formas.add(nac[:2] + nac[3:])            # sem o nono dígito
    elif len(nac) == 10 and nac[2] in _INICIO_CELULAR:
        formas.add(nac[:2] + "9" + nac[2:])      # com o nono dígito

    out: list[str] = []
    for f in sorted(formas):
        # Só prefixa o DDI em números com tamanho nacional plausível — evita
        # inventar chaves como "555511" a partir de um número truncado.
        candidatos = (f"55{f}", f) if len(f) in (10, 11) else (f,)
        for v in candidatos:
            if v not in out:
                out.append(v)

    if base in out:
        out.remove(base)
    out.insert(0, base)
    return out
