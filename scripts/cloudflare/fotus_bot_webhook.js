/**
 * HUB Solar — Fotus Bot Webhook (Cloudflare Worker)
 *
 * Recebe mensagens do Telegram via webhook.
 * Se receber um token JWT (accessToken do Fotus), salva no Gist
 * e dispara o GitHub Actions para renovar imediatamente.
 *
 * Variáveis de ambiente (Cloudflare Workers secrets):
 *   TELEGRAM_BOT_TOKEN  — token do @hubsolar_bot
 *   TELEGRAM_CHAT_ID    — ID do chat autorizado (794101727)
 *   GITHUB_PAT          — Personal Access Token (escopo gist + workflow)
 *   GITHUB_REPO         — oliveirarenanfelipe/hub-solar
 *   GIST_ID             — ID do gist privado do token Fotus
 */

export default {
  async fetch(request, env) {
    if (request.method !== "POST") {
      return new Response("HUB Solar Bot - OK", { status: 200 });
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return new Response("OK");
    }

    const message = body?.message;
    if (!message) return new Response("OK");

    const chatId = String(message.chat?.id || "");
    const text   = (message.text || "").trim();

    // Segurança: só processa mensagens do chat autorizado
    if (chatId !== env.TELEGRAM_CHAT_ID) {
      return new Response("OK");
    }

    // Token JWT detectado (accessToken do Fotus começa com eyJ)
    if (text.startsWith("eyJ") && text.length > 100) {
      try {
        await salvarNoGist(text, env);
        await dispararWorkflow(env);
        await telegramEnviar(
          env.TELEGRAM_BOT_TOKEN,
          chatId,
          "✅ *HUB Solar*\n\nToken recebido! Renovando agora...\nConfirmação em instantes."
        );
      } catch (err) {
        await telegramEnviar(
          env.TELEGRAM_BOT_TOKEN,
          chatId,
          `🔴 *HUB Solar*\n\nErro ao processar token: ${err.message}`
        );
      }
      return new Response("OK");
    }

    // Comando /status
    if (text === "/status") {
      const mins = await verificarStatus(env);
      const emoji = mins > 15 ? "✅" : mins > 0 ? "⚠️" : "🔴";
      await telegramEnviar(
        env.TELEGRAM_BOT_TOKEN,
        chatId,
        `${emoji} *HUB Solar — Status Fotus*\n\nToken: ${mins > 0 ? `${Math.round(mins)} min restantes` : "EXPIRADO"}`
      );
      return new Response("OK");
    }

    // Qualquer outra mensagem
    await telegramEnviar(
      env.TELEGRAM_BOT_TOKEN,
      chatId,
      "🤖 *HUB Solar Bot*\n\nComandos:\n• Envie o `accessToken` para renovar o Fotus\n• /status — ver status do token"
    );

    return new Response("OK");
  },
};

// ── Helpers ──────────────────────────────────────────────────────────────────

async function salvarNoGist(token, env) {
  const data = {
    accessToken: token,
    atualizadoEm: new Date().toISOString(),
    telegram_offset: 0,
  };
  const res = await fetch(`https://api.github.com/gists/${env.GIST_ID}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${env.GITHUB_PAT}`,
      Accept: "application/vnd.github+json",
      "Content-Type": "application/json",
      "User-Agent": "HUB-Solar-Bot",
    },
    body: JSON.stringify({
      files: {
        "fotus_token.json": { content: JSON.stringify(data, null, 2) },
      },
    }),
  });
  if (!res.ok) throw new Error(`Gist: HTTP ${res.status}`);
}

async function dispararWorkflow(env) {
  const res = await fetch(
    `https://api.github.com/repos/${env.GITHUB_REPO}/actions/workflows/fotus_token_keeper.yml/dispatches`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.GITHUB_PAT}`,
        Accept: "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "HUB-Solar-Bot",
      },
      body: JSON.stringify({ ref: "main" }),
    }
  );
  if (!res.ok) throw new Error(`Workflow dispatch: HTTP ${res.status}`);
}

async function verificarStatus(env) {
  const res = await fetch(`https://api.github.com/gists/${env.GIST_ID}`, {
    headers: {
      Authorization: `Bearer ${env.GITHUB_PAT}`,
      Accept: "application/vnd.github+json",
      "User-Agent": "HUB-Solar-Bot",
    },
  });
  if (!res.ok) return -1;
  const data = await res.json();
  const content = JSON.parse(data.files["fotus_token.json"].content);
  const token = content.accessToken;
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return (payload.exp - Date.now() / 1000) / 60;
  } catch {
    return -1;
  }
}

async function telegramEnviar(botToken, chatId, texto) {
  await fetch(`https://api.telegram.org/bot${botToken}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      chat_id: chatId,
      text: texto,
      parse_mode: "Markdown",
    }),
  });
}
