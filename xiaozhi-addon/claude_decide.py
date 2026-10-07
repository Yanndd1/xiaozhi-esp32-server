"""
Plugin LLM Xiaozhi — validation vocale des demandes de permission Claude Code.

Quand Claude Code demande une autorisation (ex : lancer une commande Bash), le
device Xiaozhi annonce la demande a la voix et termine par "Approuve ou refuse ?".
L'utilisateur repond a la voix. Le LLM detecte l'intention et appelle cette
fonction avec decision="approve" ou decision="deny". La fonction resout la
"decision en attente" partagee (core.connection.CLAUDE_PENDING_DECISIONS) que le
PC (hook on-permission-request.py) interroge par polling.

Ce fichier est COPIE dans plugins_func/functions/ au build (Dockerfile.popllm) et
auto-importe par loadplugins. Pour etre expose au LLM, "claude_decide" doit etre
dans Intent.function_call.functions (ajoute par popllm-entrypoint.sh).
"""
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from config.logger import setup_logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

claude_decide_function_desc = {
    "type": "function",
    "function": {
        "name": "claude_decide",
        "description": (
            "A appeler UNIQUEMENT quand l'utilisateur repond a une demande "
            "d'autorisation de Claude Code en cours (l'assistant vient de dire "
            "'Claude demande l'autorisation pour... Approuve ou refuse ?'). "
            "Detecte si l'utilisateur APPROUVE (approuve, valide, autorise, oui, "
            "d'accord, vas-y, ok, c'est bon, accepte) ou REFUSE (refuse, non, "
            "annule, stop, n'execute pas, surtout pas, laisse tomber). "
            "Ne pas appeler si aucune demande Claude n'est en attente."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "decision": {
                    "type": "string",
                    "enum": ["approve", "deny"],
                    "description": "approve si l'utilisateur autorise, deny s'il refuse",
                }
            },
            "required": ["decision"],
        },
    },
}


@register_function("claude_decide", claude_decide_function_desc, ToolType.SYSTEM_CTL)
def claude_decide(conn: "ConnectionHandler", decision: str = None):
    try:
        from core.connection import (
            CLAUDE_PENDING_DECISIONS,
            CLAUDE_LATEST_DECISION_ID,
        )
    except Exception as e:
        logger.bind(tag=TAG).error(f"claude_decide: import etat partage echoue: {e}")
        return ActionResponse(
            action=Action.RESPONSE, result=None,
            response="Je ne peux pas traiter la demande de Claude pour le moment.",
        )

    did = CLAUDE_LATEST_DECISION_ID[0]
    if not did or did not in CLAUDE_PENDING_DECISIONS:
        return ActionResponse(
            action=Action.RESPONSE, result=None,
            response="Il n'y a aucune demande de Claude en attente.",
        )

    val = "allow" if str(decision).strip().lower() in ("approve", "approuve", "oui", "ok", "valide") else "deny"
    CLAUDE_PENDING_DECISIONS[did]["decision"] = val
    logger.bind(tag=TAG).info(f"claude_decide: decision={val} pour id={did[:8]}")

    if val == "allow":
        reply = "C'est validé, j'autorise Claude."
    else:
        reply = "C'est refusé, je bloque Claude."
    return ActionResponse(action=Action.RESPONSE, result=None, response=reply)
