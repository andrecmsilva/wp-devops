import React, { useState, useEffect, useRef } from 'react';
import { Settings, Rocket, Terminal, CheckCircle, AlertCircle, ChevronRight, Play, Loader2 } from 'lucide-react';

const App = () => {
    const [step, setStep] = useState(1);
    const [loading, setLoading] = useState(false);
    const [logs, setLogs] = useState([]);
    const [formData, setFormData] = useState({
        adminUrl: '',
        username: '',
        password: '',
        rocketToken: '',
        rocketName: '',
        rocketLocation: 21,
        rocketLabel: '',
        visual: false
    });

    const logEndRef = useRef(null);

    useEffect(() => {
        logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [logs]);

    const handleChange = (e) => {
        const { name, value, type, checked } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value
        }));
    };

    const handleStartMigration = async () => {
        setLoading(true);
        setStep(3);
        setLogs(['[SYSTEM] Starting migration process...']);

        try {
            const response = await fetch('/migrate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n\n');

                lines.forEach(line => {
                    if (line.startsWith('data: ')) {
                        const data = line.replace('data: ', '');
                        if (data === '[DONE]') {
                            setLogs(prev => [...prev, '[SYSTEM] Migration task finished!']);
                            setLoading(false);
                        } else {
                            setLogs(prev => [...prev, data]);
                        }
                    }
                });
            }
        } catch (error) {
            setLogs(prev => [...prev, `[ERROR] Connection failed: ${error.message}`]);
            setLoading(false);
        }
    };

    return (
        <div className="container">
            <div className="glass main-card">
                <header>
                    <h1 className="title-gradient">Migration Assistant</h1>
                    <p className="subtitle">Move your WordPress site to Rocket.net effortlessly</p>
                </header>

                <div className="stepper">
                    <div className={`step-item ${step >= 1 ? 'active' : ''}`}>Source Settings</div>
                    <div className={`step-divider ${step >= 2 ? 'active' : ''}`}></div>
                    <div className={`step-item ${step >= 2 ? 'active' : ''}`}>Rocket.net Settings</div>
                    <div className={`step-divider ${step >= 3 ? 'active' : ''}`}></div>
                    <div className={`step-item ${step >= 3 ? 'active' : ''}`}>Execution</div>
                </div>

                <div className="form-content">
                    {step === 1 && (
                        <div className="step-pane animate-in">
                            <h2><Settings size={20} /> Source Site Details</h2>
                            <div className="input-group">
                                <label>WP Admin URL</label>
                                <input
                                    name="adminUrl"
                                    placeholder="https://example.com/wp-admin/"
                                    value={formData.adminUrl}
                                    onChange={handleChange}
                                />
                            </div>
                            <div className="input-row">
                                <div className="input-group">
                                    <label>Username</label>
                                    <input
                                        name="username"
                                        value={formData.username}
                                        onChange={handleChange}
                                    />
                                </div>
                                <div className="input-group">
                                    <label>Password</label>
                                    <input
                                        type="password"
                                        name="password"
                                        value={formData.password}
                                        onChange={handleChange}
                                    />
                                </div>
                            </div>
                            <button className="primary-btn" onClick={() => setStep(2)}>
                                Next Step <ChevronRight size={18} />
                            </button>
                        </div>
                    )}

                    {step === 2 && (
                        <div className="step-pane animate-in">
                            <h2><Rocket size={20} /> Destination Details</h2>
                            <div className="input-group">
                                <label>Rocket.net API Token</label>
                                <input
                                    type="password"
                                    name="rocketToken"
                                    value={formData.rocketToken}
                                    onChange={handleChange}
                                />
                            </div>
                            <div className="input-row">
                                <div className="input-group">
                                    <label>Site Slug</label>
                                    <input
                                        name="rocketName"
                                        placeholder="my-new-site"
                                        value={formData.rocketName}
                                        onChange={handleChange}
                                    />
                                </div>
                                <div className="input-group">
                                    <label>Location ID</label>
                                    <select name="rocketLocation" value={formData.rocketLocation} onChange={handleChange}>
                                        <option value={12}>US - Central</option>
                                        <option value={21}>US - East</option>
                                        <option value={25}>CA - Toronto</option>
                                        <option value={4}>GB - London</option>
                                        <option value={7}>DE - Frankfurt</option>
                                        <option value={16}>AU - Sydney</option>
                                        <option value={20}>SG - Singapore</option>
                                    </select>
                                </div>
                            </div>
                            <div className="input-group">
                                <label>Site Label</label>
                                <input
                                    name="rocketLabel"
                                    placeholder="Production Migration"
                                    value={formData.rocketLabel}
                                    onChange={handleChange}
                                />
                            </div>
                            <div className="actions">
                                <button className="secondary-btn" onClick={() => setStep(1)}>Back</button>
                                <button className="primary-btn" onClick={handleStartMigration}>
                                    Launch Migration <Play size={18} />
                                </button>
                            </div>
                        </div>
                    )}

                    {step === 3 && (
                        <div className="step-pane animate-in">
                            <div className="execution-header">
                                <h2><Terminal size={20} /> Execution Logs</h2>
                                {loading && <Loader2 className="animate-spin" size={20} />}
                            </div>
                            <div className="console scrollbar">
                                {logs.map((log, i) => (
                                    <div key={i} className={`log-line ${log.includes('[ERROR]') ? 'error' : ''}`}>
                                        {log}
                                    </div>
                                ))}
                                <div ref={logEndRef} />
                            </div>
                            {!loading && (
                                <button className="primary-btn" onClick={() => setStep(1)}>
                                    Start New Migration
                                </button>
                            )}
                        </div>
                    )}
                </div>
            </div>

            <style jsx>{`
        .container {
          width: 100%;
          max-width: 800px;
        }
        .main-card {
          padding: 3rem;
          display: flex;
          flex-direction: column;
          gap: 2rem;
        }
        header {
          text-align: center;
        }
        .subtitle {
          color: var(--text-muted);
          font-weight: 300;
        }
        .stepper {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0 1rem;
        }
        .step-item {
          font-size: 0.85rem;
          color: var(--text-muted);
          position: relative;
          transition: all 0.3s ease;
        }
        .step-item.active {
          color: var(--primary);
          font-weight: 600;
        }
        .step-divider {
          flex: 1;
          height: 1px;
          background: var(--border);
          margin: 0 1rem;
        }
        .step-divider.active {
          background: var(--primary);
        }
        .form-content {
          min-height: 400px;
        }
        .step-pane {
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
        }
        h2 {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          font-size: 1.25rem;
          margin-bottom: 0.5rem;
        }
        .input-group {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }
        .input-row {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 1.5rem;
        }
        label {
          font-size: 0.85rem;
          color: var(--text-muted);
          font-weight: 500;
        }
        input, select {
          background: rgba(15, 23, 42, 0.5);
          border: 1px solid var(--border);
          border-radius: 12px;
          padding: 0.8rem 1rem;
          color: white;
          outline: none;
          transition: all 0.2s;
        }
        input:focus {
          border-color: var(--primary);
          box-shadow: 0 0 0 2px var(--primary-glow);
        }
        .primary-btn {
          background: linear-gradient(135deg, var(--primary), var(--secondary));
          border: none;
          border-radius: 12px;
          padding: 1rem;
          color: white;
          font-weight: 600;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.5rem;
          transition: all 0.3s;
        }
        .primary-btn:hover {
          transform: translateY(-2px);
          box-shadow: 0 10px 20px -10px var(--primary);
        }
        .secondary-btn {
          background: transparent;
          border: 1px solid var(--border);
          border-radius: 12px;
          padding: 1rem;
          color: white;
          cursor: pointer;
          transition: all 0.2s;
        }
        .secondary-btn:hover {
          background: rgba(255, 255, 255, 0.05);
        }
        .actions {
          display: grid;
          grid-template-columns: auto 1fr;
          gap: 1rem;
        }
        .console {
          background: #000;
          border-radius: 12px;
          padding: 1rem;
          height: 350px;
          overflow-y: auto;
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.85rem;
          color: #d1d5db;
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
        }
        .execution-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        .log-line {
          white-space: pre-wrap;
          word-break: break-all;
        }
        .log-line.error {
          color: var(--error);
        }
        .animate-in {
          animation: slideUp 0.4s ease-out forwards;
        }
        @keyframes slideUp {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-spin {
          animation: spin 1s linear infinite;
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .scrollbar::-webkit-scrollbar {
          width: 8px;
        }
        .scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .scrollbar::-webkit-scrollbar-thumb {
          background: var(--border);
          border-radius: 10px;
        }
      `}</style>
        </div>
    );
};

export default App;
