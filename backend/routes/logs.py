from flask import Blueprint, render_template_string, jsonify, request
from datetime import datetime
from collections import deque
import json

logs_bp = Blueprint('logs', __name__)

# Store logs in memory (last 100 requests)
_chat_logs = deque(maxlen=100)

def add_chat_log(question: str, session_id: str, debug_trace: dict = None, answer: str = None, error: str = None):
    """Simpan log chat ke memory."""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id,
        "question": question,
        "answer": answer,
        "error": error,
        "debug": debug_trace
    }
    _chat_logs.append(log_entry)

def get_chat_logs(limit: int = 50, session_id: str = None):
    """Ambil chat logs."""
    logs = list(_chat_logs)
    
    # Filter by session_id if provided
    if session_id:
        logs = [log for log in logs if log.get('session_id') == session_id]
    
    # Return latest N logs
    return logs[-limit:]

@logs_bp.route("/logs")
def view_logs():
    """Halaman HTML untuk lihat logs."""
    limit = request.args.get('limit', 50, type=int)
    session_id = request.args.get('session', None)
    
    logs = get_chat_logs(limit=limit, session_id=session_id)
    
    html = """
<!DOCTYPE html>
<html>
<head>
    <title>Chatbot Debug Logs</title>
    <meta charset="UTF-8">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #0d1117;
            color: #c9d1d9;
            padding: 20px;
        }
        .header {
            background: linear-gradient(135deg, #1f6feb 0%, #388bfd 100%);
            padding: 20px 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }
        .header h1 {
            color: white;
            font-size: 28px;
            margin-bottom: 10px;
        }
        .header .subtitle {
            color: rgba(255,255,255,0.8);
            font-size: 14px;
        }
        .controls {
            background: #161b22;
            padding: 15px 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: flex;
            gap: 15px;
            align-items: center;
            flex-wrap: wrap;
        }
        .controls label {
            color: #8b949e;
            font-size: 13px;
        }
        .controls input, .controls select {
            background: #0d1117;
            border: 1px solid #30363d;
            color: #c9d1d9;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 13px;
        }
        .controls button {
            background: #238636;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 600;
        }
        .controls button:hover { background: #2ea043; }
        .controls button.secondary {
            background: #21262d;
            border: 1px solid #30363d;
        }
        .controls button.secondary:hover { background: #30363d; }
        .stats {
            background: #161b22;
            padding: 15px 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: flex;
            gap: 30px;
        }
        .stat-item {
            display: flex;
            flex-direction: column;
        }
        .stat-label {
            color: #8b949e;
            font-size: 12px;
            margin-bottom: 4px;
        }
        .stat-value {
            color: #58a6ff;
            font-size: 20px;
            font-weight: 700;
        }
        .log-entry {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            transition: all 0.2s;
        }
        .log-entry:hover {
            border-color: #58a6ff;
            box-shadow: 0 0 0 1px #58a6ff;
        }
        .log-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 12px;
            border-bottom: 1px solid #30363d;
        }
        .log-time {
            color: #8b949e;
            font-size: 12px;
            font-family: 'Courier New', monospace;
        }
        .session-badge {
            background: #1f6feb;
            color: white;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
        }
        .log-question {
            background: #0d1117;
            border-left: 3px solid #58a6ff;
            padding: 12px;
            margin-bottom: 12px;
            border-radius: 4px;
        }
        .log-question .label {
            color: #8b949e;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            margin-bottom: 6px;
        }
        .log-question .content {
            color: #c9d1d9;
            font-size: 14px;
        }
        .log-answer {
            background: #0d1117;
            border-left: 3px solid #3fb950;
            padding: 12px;
            margin-bottom: 12px;
            border-radius: 4px;
        }
        .log-answer .label {
            color: #8b949e;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            margin-bottom: 6px;
        }
        .log-answer .content {
            color: #c9d1d9;
            font-size: 14px;
            line-height: 1.6;
        }
        .log-error {
            background: #0d1117;
            border-left: 3px solid #f85149;
            padding: 12px;
            margin-bottom: 12px;
            border-radius: 4px;
        }
        .log-error .label {
            color: #f85149;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            margin-bottom: 6px;
        }
        .log-error .content {
            color: #f85149;
            font-size: 14px;
        }
        .debug-section {
            margin-top: 15px;
        }
        .debug-toggle {
            background: #21262d;
            border: 1px solid #30363d;
            color: #58a6ff;
            padding: 8px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 12px;
            font-weight: 600;
            width: 100%;
            text-align: left;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .debug-toggle:hover { background: #30363d; }
        .debug-toggle .icon { transition: transform 0.2s; }
        .debug-toggle.active .icon { transform: rotate(90deg); }
        .debug-content {
            display: none;
            background: #0d1117;
            border: 1px solid #30363d;
            border-radius: 6px;
            padding: 15px;
            margin-top: 10px;
            max-height: 500px;
            overflow-y: auto;
        }
        .debug-content.active { display: block; }
        .debug-step {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 6px;
            padding: 12px;
            margin-bottom: 10px;
        }
        .debug-step .step-header {
            color: #58a6ff;
            font-weight: 600;
            font-size: 13px;
            margin-bottom: 8px;
        }
        .debug-step pre {
            background: #0d1117;
            padding: 10px;
            border-radius: 4px;
            overflow-x: auto;
            font-size: 12px;
            line-height: 1.5;
            color: #c9d1d9;
            font-family: 'Courier New', monospace;
        }
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #8b949e;
        }
        .empty-state .icon {
            font-size: 48px;
            margin-bottom: 15px;
            opacity: 0.5;
        }
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: #0d1117; }
        ::-webkit-scrollbar-thumb { background: #30363d; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #484f58; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 Chatbot Debug Logs</h1>
        <div class="subtitle">Real-time AI conversation tracking & debugging</div>
    </div>
    
    <div class="controls">
        <label>Limit:</label>
        <input type="number" id="limit" value="{{ limit }}" min="1" max="100" style="width: 80px;">
        
        <label>Session:</label>
        <input type="text" id="session" placeholder="All sessions" value="{{ session_id or '' }}" style="width: 200px;">
        
        <button onclick="applyFilters()">Apply Filters</button>
        <button class="secondary" onclick="location.reload()">Refresh</button>
        <button class="secondary" onclick="clearLogs()">Clear All</button>
    </div>
    
    <div class="stats">
        <div class="stat-item">
            <div class="stat-label">Total Logs</div>
            <div class="stat-value">{{ logs|length }}</div>
        </div>
        <div class="stat-item">
            <div class="stat-label">Sessions</div>
            <div class="stat-value">{{ logs|map(attribute='session_id')|unique|list|length }}</div>
        </div>
        <div class="stat-item">
            <div class="stat-label">Errors</div>
            <div class="stat-value" style="color: #f85149;">{{ logs|selectattr('error')|list|length }}</div>
        </div>
    </div>
    
    <div class="logs-container">
        {% if logs %}
            {% for log in logs[::-1] %}
            <div class="log-entry">
                <div class="log-header">
                    <span class="log-time">{{ log.timestamp }}</span>
                    <span class="session-badge">{{ log.session_id }}</span>
                </div>
                
                <div class="log-question">
                    <div class="label">Question</div>
                    <div class="content">{{ log.question }}</div>
                </div>
                
                {% if log.answer %}
                <div class="log-answer">
                    <div class="label">Answer</div>
                    <div class="content">{{ log.answer }}</div>
                </div>
                {% endif %}
                
                {% if log.error %}
                <div class="log-error">
                    <div class="label">Error</div>
                    <div class="content">{{ log.error }}</div>
                </div>
                {% endif %}
                
                {% if log.debug %}
                <div class="debug-section">
                    <button class="debug-toggle" onclick="toggleDebug(this)">
                        <span>🔍 Debug Trace ({{ log.debug.steps|length }} steps)</span>
                        <span class="icon">▶</span>
                    </button>
                    <div class="debug-content">
                        {% for step in log.debug.steps %}
                        <div class="debug-step">
                            <div class="step-header">Step {{ step.step }}: {{ step.name }}</div>
                            <pre>{{ step|tojson(indent=2) }}</pre>
                        </div>
                        {% endfor %}
                    </div>
                </div>
                {% endif %}
            </div>
            {% endfor %}
        {% else %}
            <div class="empty-state">
                <div class="icon">📭</div>
                <h3>No logs yet</h3>
                <p>Start chatting to see logs appear here</p>
            </div>
        {% endif %}
    </div>
    
    <script>
        function toggleDebug(btn) {
            btn.classList.toggle('active');
            btn.nextElementSibling.classList.toggle('active');
        }
        
        function applyFilters() {
            const limit = document.getElementById('limit').value;
            const session = document.getElementById('session').value;
            let url = '/logs?limit=' + limit;
            if (session) url += '&session=' + encodeURIComponent(session);
            window.location.href = url;
        }
        
        function clearLogs() {
            if (confirm('Clear all logs?')) {
                fetch('/logs/clear', {method: 'POST'})
                    .then(() => location.reload())
                    .catch(err => alert('Failed to clear logs: ' + err));
            }
        }
        
        // Auto-refresh setiap 30 detik (optional)
        // setInterval(() => location.reload(), 30000);
    </script>
</body>
</html>
    """
    
    return render_template_string(html, logs=logs, limit=limit, session_id=session_id)

@logs_bp.route("/logs/api")
def api_logs():
    """API endpoint untuk ambil logs dalam JSON."""
    limit = request.args.get('limit', 50, type=int)
    session_id = request.args.get('session', None)
    
    logs = get_chat_logs(limit=limit, session_id=session_id)
    return jsonify(logs)

@logs_bp.route("/logs/clear", methods=["POST"])
def clear_logs():
    """Clear all logs."""
    _chat_logs.clear()
    return jsonify({"status": "ok", "message": "Logs cleared"})
