import React, { useState, useRef, useEffect } from 'react';
import {
  FileText,
  Upload,
  MessageSquare,
  Send,
  X,
  AlertCircle,
  CheckCircle,
  Loader,
  Users,
  Trash2,
  FolderOpen,
  Edit2,
  Save,
} from 'lucide-react';

export default function ContractAnalyzerApp() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [contract, setContract] = useState(null);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [activeTab, setActiveTab] = useState('chat');
  const [clients, setClients] = useState([]);
  const [library, setLibrary] = useState([]);
  const [editingClient, setEditingClient] = useState(null);
  const [newClient, setNewClient] = useState({
    name: '',
    company: '',
    email: '',
    phone: '',
    address: '',
  });

  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    loadClients();
    loadLibrary();
  }, []);

  const loadClients = async () => {
    try {
      const result = await window.storage.list('client:', false);
      if (result && result.keys) {
        const clientPromises = result.keys.map(async (key) => {
          const data = await window.storage.get(key, false);
          return data ? JSON.parse(data.value) : null;
        });
        const loadedClients = await Promise.all(clientPromises);
        setClients(loadedClients.filter((c) => c !== null));
      }
    } catch (error) {
      console.log('No clients found');
      setClients([]);
    }
  };

  const loadLibrary = async () => {
    try {
      const result = await window.storage.list('doc:', false);
      if (result && result.keys) {
        const docPromises = result.keys.map(async (key) => {
          const data = await window.storage.get(key, false);
          return data ? JSON.parse(data.value) : null;
        });
        const loadedDocs = await Promise.all(docPromises);
        setLibrary(loadedDocs.filter((d) => d !== null));
      }
    } catch (error) {
      console.log('No documents found');
      setLibrary([]);
    }
  };

  const saveClient = async () => {
    if (!newClient.name || !newClient.email) {
      alert('Please fill in at least name and email');
      return;
    }

    const clientId = editingClient?.id || `client:${Date.now()}`;
    const clientData = {
      id: clientId,
      ...newClient,
      createdAt: editingClient?.createdAt || new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    try {
      await window.storage.set(clientId, JSON.stringify(clientData), false);
      await loadClients();
      setNewClient({ name: '', company: '', email: '', phone: '', address: '' });
      setEditingClient(null);
    } catch (error) {
      console.error('Error saving client:', error);
      alert('Error saving client');
    }
  };

  const deleteClient = async (clientId) => {
    if (!confirm('Are you sure you want to delete this client?')) return;

    try {
      await window.storage.delete(clientId, false);
      await loadClients();
    } catch (error) {
      console.error('Error deleting client:', error);
    }
  };

  const editClient = (client) => {
    setEditingClient(client);
    setNewClient({
      name: client.name,
      company: client.company,
      email: client.email,
      phone: client.phone,
      address: client.address,
    });
  };

  const saveToLibrary = async (file, content) => {
    const docId = `doc:${Date.now()}`;
    const docData = {
      id: docId,
      name: file.name,
      content: content,
      size: content.length,
      uploadedAt: new Date().toISOString(),
    };

    try {
      await window.storage.set(docId, JSON.stringify(docData), false);
      await loadLibrary();
    } catch (error) {
      console.error('Error saving document:', error);
    }
  };

  const deleteDocument = async (docId) => {
    if (!confirm('Are you sure you want to delete this document?')) return;

    try {
      await window.storage.delete(docId, false);
      await loadLibrary();
      if (contract?.id === docId) {
        setContract(null);
        setMessages([]);
      }
    } catch (error) {
      console.error('Error deleting document:', error);
    }
  };

  const loadDocumentFromLibrary = async (doc) => {
    setContract(doc);
    setActiveTab('chat');

    const analysisPrompt =
      'I have loaded the contract from library. Please provide analysis.';

    setMessages([
      {
        role: 'assistant',
        content: `Contract "${doc.name}" loaded from library. Ready for analysis.`,
      },
    ]);

    const aiResponse = await sendToAI(analysisPrompt, doc.content);
    setMessages((prev) => [...prev, { role: 'assistant', content: aiResponse }]);
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(scrollToBottom, [messages]);

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.match(/\.(txt|pdf|doc|docx)$/i)) {
      alert('Please upload a valid contract file');
      return;
    }

    setAnalyzing(true);

    try {
      const reader = new FileReader();
      reader.onload = async (event) => {
        const text = event.target.result;
        const contractData = {
          id: `doc:${Date.now()}`,
          name: file.name,
          content: text,
          size: text.length,
          uploadedAt: new Date().toISOString(),
        };

        setContract(contractData);
        await saveToLibrary(file, text);

        const aiResponse = await sendToAI(`Analyze contract ${file.name}`, text);

        setMessages([
          {
            role: 'assistant',
            content: `Contract "${file.name}" loaded and saved to library.`,
          },
          {
            role: 'assistant',
            content: aiResponse,
          },
        ]);

        setActiveTab('chat');
      };

      reader.readAsText(file);
    } catch (error) {
      console.error('Error processing file:', error);
      setMessages([
        {
          role: 'assistant',
          content: 'Error processing contract.',
        },
      ]);
    } finally {
      setAnalyzing(false);
    }
  };

  /**
   * NUEVO cerebro real: llama al backend Python en 127.0.0.1:4050/llm/ask-basic
   * con { question, context } y devuelve la respuesta del LLM.
   */
    const sendToAI = async (userMessage, contractContext = "") => {
    const payload = {
      question: userMessage,
      contractText: contractContext || "",
      extraContext: ""
    };

    try {
      const response = await fetch("http://127.0.0.1:4050/llm/ask-basic", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
      });

      const rawText = await response.text();
      let data;

      try {
        data = JSON.parse(rawText);
      } catch (jsonErr) {
        console.error("Invalid JSON from analysis server:", rawText);
        return `The analysis server returned invalid JSON:\\n\\n${rawText}`;
      }

      if (!response.ok || !data.ok) {
        const detail =
          (data && data.detail) ||
          rawText ||
          `${response.status} ${response.statusText || ""}`.trim();

        if (data && data.error === "lm_http_error") {
          return (
            "The analysis server reached LM Studio but it returned an error.\\n\\n" +
            (detail || "LM Studio HTTP error.")
          );
        }

        return (
          "The analysis server reported an error.\\n\\n" +
          `Code: ${ (data && data.error) || response.status }\\n` +
          (detail ? `Details: ${detail}` : "")
        );
      }

      let answer = (data.answer || "").trim();

      // Quitar bloque <think>...</think> si viene incluido
      const thinkClose = "</think>";
      const idx = answer.indexOf(thinkClose);
      if (idx !== -1) {
        const visible = answer.slice(idx + thinkClose.length).trim();
        if (visible) {
          answer = visible;
        }
      }

      if (!answer) {
        return "The analysis server returned an empty answer.";
      }

      return answer;
    } catch (err) {
      console.error("Error calling analysis server:", err);
      const msg = err && err.message ? err.message : String(err);
      return (
        "Could not reach the analysis server at http://127.0.0.1:4050/llm/ask-basic.\\n\\n" +
        msg
      );
    }
  };

      const response = await fetch('http://127.0.0.1:4050/llm/ask-basic', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json; charset=utf-8',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const text = await response.text().catch(() => '');
        console.error('Backend HTTP error:', response.status, text);
        return `The analysis server reported an error (HTTP ${response.status}).`;
      }

      let data;
      try {
        data = await response.json();
      } catch (e) {
        console.error('Error parsing backend JSON:', e);
        return 'The analysis server returned invalid JSON.';
      }

      console.log('Backend JSON:', data);

      if (!data || typeof data !== 'object') {
        return 'The analysis server returned an invalid response.';
      }

      if (data.ok === false) {
        // Mostramos el mensaje de error que viene del backend si existe
        return (
          data.error ||
          data.detail ||
          'The analysis server reported an internal error.'
        );
      }

      const answer =
        typeof data.answer === 'string' && data.answer.trim().length > 0
          ? data.answer
          : JSON.stringify(data, null, 2);

      return answer;
    } catch (err) {
      console.error('Error calling backend:', err);
      return 'Could not reach the analysis server at http://127.0.0.1:4050/llm/ask-basic. Is the Python backend running?';
    }
  };

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput('');
    setLoading(true);

    setMessages((prev) => [...prev, { role: 'user', content: userMessage }]);

    try {
      const aiResponse = await sendToAI(userMessage, contract?.content);
      setMessages((prev) => [...prev, { role: 'assistant', content: aiResponse }]);
    } catch (error) {
      console.error('Error:', error);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Error processing query.',
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const clearContract = () => {
    setContract(null);
    setMessages([]);
  };

  return (
    <div className="flex h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <div className="w-80 bg-white border-r border-slate-200 flex flex-col">
        <div className="p-6 border-b border-slate-200">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-blue-600 rounded-lg">
              <FileText className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-800">ContractAI Pro</h1>
              <p className="text-xs text-slate-500">Legal Analysis System</p>
            </div>
          </div>

          <div className="flex gap-2">
            <button
              onClick={() => setActiveTab('chat')}
              className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === 'chat'
                  ? 'bg-blue-100 text-blue-700'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              <MessageSquare className="w-4 h-4 inline mr-1" />
              Chat
            </button>
            <button
              onClick={() => setActiveTab('clients')}
              className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === 'clients'
                  ? 'bg-blue-100 text-blue-700'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              <Users className="w-4 h-4 inline mr-1" />
              Clients
            </button>
            <button
              onClick={() => setActiveTab('library')}
              className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === 'library'
                  ? 'bg-blue-100 text-blue-700'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              <FolderOpen className="w-4 h-4 inline mr-1" />
              Library
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === 'chat' && (
            <>
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-slate-700 mb-3">
                  Upload Contract
                </h3>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".txt,.pdf,.doc,.docx"
                  onChange={handleFileUpload}
                  className="hidden"
                />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={analyzing}
                  className="w-full p-4 border-2 border-dashed border-slate-300 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-all flex flex-col items-center gap-2 disabled:opacity-50"
                >
                  {analyzing ? (
                    <Loader className="w-8 h-8 text-blue-600 animate-spin" />
                  ) : (
                    <Upload className="w-8 h-8 text-slate-400" />
                  )}
                  <span className="text-sm text-slate-600 font-medium">
                    {analyzing ? 'Analyzing...' : 'Upload Contract'}
                  </span>
                  <span className="text-xs text-slate-400">TXT, PDF, DOC, DOCX</span>
                </button>
              </div>

              {contract && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-green-800 truncate">
                          {contract.name}
                        </p>
                        <p className="text-xs text-green-600">Active</p>
                      </div>
                    </div>
                    <button
                      onClick={clearContract}
                      className="text-green-600 hover:text-green-800"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )}

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h3 className="text-sm font-semibold text-blue-800 mb-2 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4" />
                  AI Capabilities
                </h3>
                <ul className="text-xs text-blue-700 space-y-1">
                  <li>✓ Risk analysis</li>
                  <li>✓ Clause review</li>
                  <li>✓ Negotiation strategy</li>
                  <li>✓ Legal explanations</li>
                </ul>
              </div>
            </>
          )}

          {activeTab === 'clients' && (
            <div className="space-y-4">
              <div className="bg-white border border-slate-200 rounded-lg p-4">
                <h3 className="text-sm font-semibold text-slate-800 mb-3">
                  {editingClient ? 'Edit Client' : 'Add Client'}
                </h3>
                <div className="space-y-3">
                  <input
                    type="text"
                    placeholder="Name *"
                    value={newClient.name}
                    onChange={(e) =>
                      setNewClient({ ...newClient, name: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <input
                    type="text"
                    placeholder="Company"
                    value={newClient.company}
                    onChange={(e) =>
                      setNewClient({ ...newClient, company: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <input
                    type="email"
                    placeholder="Email *"
                    value={newClient.email}
                    onChange={(e) =>
                      setNewClient({ ...newClient, email: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <input
                    type="tel"
                    placeholder="Phone"
                    value={newClient.phone}
                    onChange={(e) =>
                      setNewClient({ ...newClient, phone: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <input
                    type="text"
                    placeholder="Address"
                    value={newClient.address}
                    onChange={(e) =>
                      setNewClient({ ...newClient, address: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={saveClient}
                      className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 flex items-center justify-center gap-2"
                    >
                      <Save className="w-4 h-4" />
                      {editingClient ? 'Update' : 'Save'}
                    </button>
                    {editingClient && (
                      <button
                        onClick={() => {
                          setEditingClient(null);
                          setNewClient({
                            name: '',
                            company: '',
                            email: '',
                            phone: '',
                            address: '',
                          });
                        }}
                        className="px-4 py-2 bg-slate-200 text-slate-700 rounded-lg text-sm font-medium hover:bg-slate-300"
                      >
                        Cancel
                      </button>
                    )}
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <h3 className="text-sm font-semibold text-slate-700">
                  Clients ({clients.length})
                </h3>
                {clients.map((client) => (
                  <div
                    key={client.id}
                    className="bg-white border border-slate-200 rounded-lg p-3"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <p className="font-semibold text-slate-800 text-sm">
                          {client.name}
                        </p>
                        {client.company && (
                          <p className="text-xs text-slate-600">
                            {client.company}
                          </p>
                        )}
                        <p className="text-xs text-slate-500 mt-1">
                          {client.email}
                        </p>
                        {client.phone && (
                          <p className="text-xs text-slate-500">
                            {client.phone}
                          </p>
                        )}
                      </div>
                      <div className="flex gap-1">
                        <button
                          onClick={() => editClient(client)}
                          className="p-1 text-blue-600 hover:bg-blue-50 rounded"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => deleteClient(client.id)}
                          className="p-1 text-red-600 hover:bg-red-50 rounded"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
                {clients.length === 0 && (
                  <p className="text-sm text-slate-500 text-center py-4">
                    No clients yet
                  </p>
                )}
              </div>
            </div>
          )}

          {activeTab === 'library' && (
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-slate-700 mb-3">
                Documents ({library.length})
              </h3>
              {library.map((doc) => (
                <div
                  key={doc.id}
                  className="bg-white border border-slate-200 rounded-lg p-3 hover:border-blue-300 transition-all"
                >
                  <div className="flex items-start justify-between gap-2">
                    <button
                      onClick={() => loadDocumentFromLibrary(doc)}
                      className="flex-1 text-left"
                    >
                      <div className="flex items-center gap-2">
                        <FileText className="w-4 h-4 text-blue-600 flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <p className="font-semibold text-slate-800 text-sm truncate">
                            {doc.name}
                          </p>
                          <p className="text-xs text-slate-500">
                            {new Date(doc.uploadedAt).toLocaleDateString()} •{' '}
                            {Math.round(doc.size / 1024)} KB
                          </p>
                        </div>
                      </div>
                    </button>
                    <button
                      onClick={() => deleteDocument(doc.id)}
                      className="p-1 text-red-600 hover:bg-red-50 rounded flex-shrink-0"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
              {library.length === 0 && (
                <div className="text-center py-8">
                  <FolderOpen className="w-12 h-12 text-slate-300 mx-auto mb-2" />
                  <p className="text-sm text-slate-500">No documents</p>
                  <p className="text-xs text-slate-400 mt-1">
                    Upload to get started
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="flex-1 flex flex-col">
        <div className="bg-white border-b border-slate-200 p-6">
          <h2 className="text-2xl font-bold text-slate-800">
            Legal AI Consultant
          </h2>
          <p className="text-sm text-slate-500 mt-1">Expert contract analysis</p>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {messages.length === 0 ? (
            <div className="h-full flex items-center justify-center">
              <div className="text-center max-w-2xl">
                <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-6">
                  <MessageSquare className="w-10 h-10 text-white" />
                </div>
                <h3 className="text-2xl font-bold text-slate-800 mb-3">
                  Welcome to ContractAI Pro
                </h3>
                <p className="text-slate-600 mb-6">
                  Your legal advisor for contracts
                </p>
                <div className="grid grid-cols-2 gap-4 text-left">
                  <div className="bg-white p-4 rounded-lg border border-slate-200">
                    <div className="text-2xl mb-2">🔍</div>
                    <h4 className="font-semibold text-slate-800 mb-1">
                      Analyze Contracts
                    </h4>
                    <p className="text-sm text-slate-600">
                      Review terms and conditions
                    </p>
                  </div>
                  <div className="bg-white p-4 rounded-lg border border-slate-200">
                    <div className="text-2xl mb-2">⚠️</div>
                    <h4 className="font-semibold text-slate-800 mb-1">
                      Identify Risks
                    </h4>
                    <p className="text-sm text-slate-600">
                      Find problematic clauses
                    </p>
                  </div>
                  <div className="bg-white p-4 rounded-lg border border-slate-200">
                    <div className="text-2xl mb-2">👥</div>
                    <h4 className="font-semibold text-slate-800 mb-1">
                      Manage Clients
                    </h4>
                    <p className="text-sm text-slate-600">
                      Track client information
                    </p>
                  </div>
                  <div className="bg-white p-4 rounded-lg border border-slate-200">
                    <div className="text-2xl mb-2">📁</div>
                    <h4 className="font-semibold text-slate-800 mb-1">
                      Document Library
                    </h4>
                    <p className="text-sm text-slate-600">
                      Store and access contracts
                    </p>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-6 max-w-4xl mx-auto">
              {messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex gap-4 ${
                    msg.role === 'user' ? 'justify-end' : ''
                  }`}
                >
                  {msg.role === 'assistant' && (
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center flex-shrink-0">
                      <FileText className="w-5 h-5 text-white" />
                    </div>
                  )}
                  <div
                    className={`flex-1 ${
                      msg.role === 'user' ? 'max-w-2xl' : ''
                    }`}
                  >
                    <div
                      className={`rounded-2xl p-6 ${
                        msg.role === 'user'
                          ? 'bg-blue-600 text-white ml-auto'
                          : 'bg-white border border-slate-200'
                      }`}
                    >
                      <div className="whitespace-pre-wrap">
                        {msg.content.split('\n').map((line, i) => (
                          <p
                            key={i}
                            className={`${
                              msg.role === 'user'
                                ? 'text-white'
                                : 'text-slate-800'
                            } ${i > 0 ? 'mt-2' : ''}`}
                          >
                            {line}
                          </p>
                        ))}
                      </div>
                    </div>
                  </div>
                  {msg.role === 'user' && (
                    <div className="w-10 h-10 rounded-full bg-slate-700 flex items-center justify-center flex-shrink-0">
                      <span className="text-white font-semibold text-xs">
                        YOU
                      </span>
                    </div>
                  )}
                </div>
              ))}
              {loading && (
                <div className="flex gap-4">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                    <FileText className="w-5 h-5 text-white" />
                  </div>
                  <div className="bg-white border border-slate-200 rounded-2xl p-6">
                    <div className="flex items-center gap-2">
                      <Loader className="w-4 h-4 animate-spin text-blue-600" />
                      <span className="text-slate-600">Analyzing...</span>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        <div className="border-t border-slate-200 bg-white p-6">
          <div className="max-w-4xl mx-auto">
            <div className="flex gap-3">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                placeholder="Ask about the contract..."
                className="flex-1 px-6 py-4 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={loading}
              />
              <button
                onClick={handleSend}
                disabled={loading || !input.trim()}
                className="px-8 py-4 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-xl hover:from-blue-700 hover:to-purple-700 transition-all disabled:opacity-50 flex items-center gap-2 font-semibold"
              >
                {loading ? (
                  <Loader className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
                Send
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

