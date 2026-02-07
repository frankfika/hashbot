/**
 * HashBot Chat Interface
 * Sends messages via A2A JSON-RPC and renders responses with markdown.
 */

const chatMessages = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');

let sessionId = crypto.randomUUID();

// Configure marked for safe rendering
marked.setOptions({
  breaks: true,
  gfm: true,
});

// Enter key sends message
chatInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

function scrollToBottom() {
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addUserBubble(text) {
  const div = document.createElement('div');
  div.className = 'chat chat-end';
  div.innerHTML = `<div class="chat-bubble">${escapeHtml(text)}</div>`;
  chatMessages.appendChild(div);
  scrollToBottom();
}

function addAgentBubble(html) {
  const div = document.createElement('div');
  div.className = 'chat chat-start';
  div.innerHTML = `<div class="chat-bubble chat-bubble-primary">${html}</div>`;
  chatMessages.appendChild(div);
  scrollToBottom();
}

function addPaymentBubble(paymentData) {
  const accepts = paymentData.accepts || [];
  let details = '';
  if (accepts.length > 0) {
    const req = accepts[0];
    details = `
      <div><strong>Network:</strong> ${req.network || 'HashKey Chain'}</div>
      <div><strong>Amount:</strong> ${req.maxAmountRequired || 'N/A'}</div>
      <div><strong>Currency:</strong> ${req.asset || 'HKDC'}</div>
    `;
  }

  const div = document.createElement('div');
  div.className = 'chat chat-start';
  div.innerHTML = `
    <div class="chat-bubble chat-bubble-warning">
      <div class="font-bold mb-1">💰 Payment Required</div>
      <div class="payment-info">
        <div class="text-sm">x402 Payment Protocol v${paymentData.x402Version || '0.1'}</div>
        ${details}
      </div>
      <div class="text-xs mt-2 opacity-70">Send payment via x402 to continue</div>
    </div>
  `;
  chatMessages.appendChild(div);
  scrollToBottom();
}

function addTypingIndicator() {
  const div = document.createElement('div');
  div.className = 'chat chat-start';
  div.id = 'typing-indicator';
  div.innerHTML = `
    <div class="chat-bubble chat-bubble-primary">
      <span class="typing-indicator">
        <span>●</span><span>●</span><span>●</span>
      </span>
    </div>
  `;
  chatMessages.appendChild(div);
  scrollToBottom();
}

function removeTypingIndicator() {
  const el = document.getElementById('typing-indicator');
  if (el) el.remove();
}

function addErrorBubble(message) {
  const div = document.createElement('div');
  div.className = 'chat chat-start';
  div.innerHTML = `<div class="chat-bubble chat-bubble-error">${escapeHtml(message)}</div>`;
  chatMessages.appendChild(div);
  scrollToBottom();
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

async function sendMessage() {
  const text = chatInput.value.trim();
  if (!text) return;

  // Disable input while processing
  chatInput.value = '';
  chatInput.disabled = true;
  sendBtn.disabled = true;

  addUserBubble(text);
  addTypingIndicator();

  try {
    // Check if this is an OpenClaw agent (set by template)
    const isOpenClaw = typeof IS_OPENCLAW !== 'undefined' && IS_OPENCLAW;

    if (isOpenClaw) {
      // Route to OpenClaw agent API
      const resp = await fetch(`/api/agents/${AGENT_ID}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, session_key: sessionId }),
      });
      const data = await resp.json();
      removeTypingIndicator();

      if (!resp.ok) {
        addErrorBubble(data.detail || 'Error communicating with agent');
        return;
      }
      addAgentBubble(marked.parse(data.response || 'No response'));
      return;
    }

    // Built-in A2A agent flow
    const taskId = crypto.randomUUID();

    const resp = await fetch('/a2a', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        jsonrpc: '2.0',
        id: taskId,
        method: 'tasks/send',
        params: {
          id: taskId,
          sessionId: sessionId,
          message: {
            role: 'user',
            parts: [{ type: 'text', text: text }],
          },
          metadata: {
            skill_id: AGENT_ID,
          },
        },
      }),
    });

    const data = await resp.json();
    removeTypingIndicator();

    if (data.error) {
      addErrorBubble(`Error: ${data.error.message}`);
      return;
    }

    const result = data.result;
    if (!result) {
      addErrorBubble('No response from agent');
      return;
    }

    // Check for payment required (input-required state with x402 data)
    const status = result.status || {};
    if (status.state === 'input-required') {
      const statusMsg = status.message;
      if (statusMsg && statusMsg.parts) {
        for (const part of statusMsg.parts) {
          if (part.type === 'text') {
            addAgentBubble(marked.parse(part.text));
          }
          if (part.type === 'data' && part.data && part.data.x402Version) {
            addPaymentBubble(part.data);
          }
        }
      }
      return;
    }

    // Process history for agent responses
    const history = result.history || [];
    for (const msg of history) {
      if (msg.role !== 'agent') continue;
      for (const part of msg.parts || []) {
        if (part.type === 'text') {
          addAgentBubble(marked.parse(part.text));
        } else if (part.type === 'data') {
          // Render data as formatted JSON
          const json = JSON.stringify(part.data, null, 2);
          addAgentBubble(`
            <details class="collapse collapse-arrow">
              <summary class="collapse-title text-sm font-medium p-0 min-h-0">📊 View Data</summary>
              <div class="collapse-content p-0 pt-2">
                <pre><code>${escapeHtml(json)}</code></pre>
              </div>
            </details>
          `);
        }
      }
    }

    // Also check status message for completed tasks
    if (status.state === 'completed' && status.message) {
      for (const part of status.message.parts || []) {
        if (part.type === 'text') {
          addAgentBubble(marked.parse(part.text));
        }
      }
    }

    // If no agent messages were found, show a fallback
    const agentMessages = history.filter(m => m.role === 'agent');
    if (agentMessages.length === 0 && !status.message) {
      addAgentBubble('<em>Agent processed the request but returned no text.</em>');
    }

  } catch (err) {
    removeTypingIndicator();
    addErrorBubble(`Network error: ${err.message}`);
  } finally {
    chatInput.disabled = false;
    sendBtn.disabled = false;
    chatInput.focus();
  }
}
