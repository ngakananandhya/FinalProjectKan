import { useState, useEffect, useRef } from "react";
import axios from "axios";
import "./App.css";

const API = "http://127.0.0.1:8000";

const WELCOME_MESSAGE = {
  id: 1,
  from: "bot",
  type: "welcome",
  text: `Selamat datang di **Culinary Bridge AI**

Sistem rekomendasi adaptasi resep masakan Indonesia berbasis data *Mustika Rasa* (1.779 resep).

Pilih fitur yang ingin kamu gunakan:`,
  options: [
    { label: "/cari", desc: "Cari resep dari database", cmd: "/cari" },
    { label: "/adaptasi", desc: "Adaptasi resep untuk wilayah tertentu", cmd: "/adaptasi" },
    { label: "/custom", desc: "Adaptasi resep buatanmu sendiri", cmd: "/custom" },
  ],
};

const FLOWS = {
  "/cari": [
    {
      key: "sub",
      text: "Cari berdasarkan:",
      options: [
        { label: "/nama", desc: "Cari berdasarkan nama resep", cmd: "/nama" },
        { label: "/wilayah", desc: "Cari berdasarkan wilayah", cmd: "/wilayah" },
      ],
    },
  ],
  "/nama": [
    { key: "query", text: "Ketik nama resep yang ingin dicari:\n*Contoh: rendang, sayur asam, pecel*" },
  ],
  "/wilayah": [
    { key: "region", text: "Ketik nama wilayah:\n*Contoh: Bali, Jakarta, Yogyakarta, Surabaya*" },
  ],
  "/adaptasi": [
    { key: "recipe_name", text: "Ketik nama resep yang ingin diadaptasi:\n*Contoh: rendang, ayam goreng, gado-gado*" },
    { key: "target_region", text: "Ketik target wilayah:\n*Contoh: Jakarta, Yogyakarta, Bali, jogja, sby*" },
  ],
  "/custom": [
    { key: "recipe_name", text: "Ketik nama masakan kamu:\n*Contoh: Ayam Bakar Madu*" },
    { key: "ingredients", text: "Ketik bahan-bahan beserta takaran, pisahkan dengan koma.\n\n*Contoh:*\n*ayam 1 ekor, kecap 3 sdm, gula merah 2 sdm, cabai rawit 5 buah, santan 200 ml*" },
    { key: "target_region", text: "Ketik target wilayah:\n*Contoh: Jakarta, Yogyakarta, Bali, jogja, sby*" },
  ],
};

function formatText(text) {
  return text
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    .replace(/\n/g, "<br/>");
}

function formatOutputLine(line, i) {
  const trimmed = line.trim();
  if (!trimmed) return <div key={i} className="out-spacer" />;

  // Heading: semua huruf kapital, minimal 3 karakter
  const isHeading = trimmed === trimmed.toUpperCase() && 
                    trimmed.length > 3 && 
                    !/^[-\d•]/.test(trimmed) &&
                    !/[=|:]/.test(trimmed.slice(-1));

  if (isHeading) return <div key={i} className="out-heading">{trimmed}</div>;

  // Sub-heading: diawali huruf kapital, diakhiri titik dua atau dash
  const isSubheading = /^[A-Z][\w\s]+[:\-]$/.test(trimmed) || 
                       /^[A-Z]\.\s/.test(trimmed);
  if (isSubheading) return <div key={i} className="out-subheading">{trimmed}</div>;

  // List item
  if (trimmed.startsWith('-')) {
    return (
      <div key={i} className="out-list-item">
        <span className="out-bullet">—</span>
        <span>{trimmed.slice(1).trim()}</span>
      </div>
    );
  }

  // Numbered step
  if (/^\d+\./.test(trimmed)) {
    const num = trimmed.match(/^(\d+)\./)[1];
    const content = trimmed.replace(/^\d+\.\s*/, '');
    return (
      <div key={i} className="out-numbered">
        <span className="out-num">{num}.</span>
        <span>{content}</span>
      </div>
    );
  }

  // Regular line
  // Regular line — cek apakah ada (disesuaikan)
  if (trimmed.includes("(disesuaikan)")) {
    const parts = trimmed.split("(disesuaikan)");
    return (
      <div key={i} className="out-line">
        {parts[0]}<strong>(disesuaikan)</strong>{parts[1]}
      </div>
    );
  }
  return <div key={i} className="out-line">{trimmed}</div>;
}

function OutputMessage({ text, onDownload }) {
  const lines = text.split("\n");
  return (
    <div className="output-message">
      <div className="output-body">
        {lines.map((line, i) => formatOutputLine(line, i))}
      </div>
      {onDownload && (
        <button className="download-btn" onClick={onDownload}>
          Download PDF
        </button>
      )}
    </div>
  );
}

function BotMessage({ msg, onOptionClick }) {
  if (msg.type === "output") {
    return (
      <div className="message bot">
        <div className="avatar"></div>
        <div className="bubble bot-bubble">
          <OutputMessage text={msg.text} onDownload={msg.onDownload} />
        </div>
      </div>
    );
  }

  return (
    <div className="message bot">
      <div className="avatar"></div>
      <div className="bubble bot-bubble">
        <p dangerouslySetInnerHTML={{ __html: formatText(msg.text) }} />
        {msg.options && (
          <div className="options">
            {msg.options.map((opt) => (
              <button
                key={opt.cmd}
                className="option-btn"
                onClick={() => onOptionClick(opt.cmd)}
              >
                <span className="opt-label">{opt.label}</span>
                <span className="opt-desc">{opt.desc}</span>
              </button>
            ))}
          </div>
        )}
        {msg.list && (
          <div className="list-options">
            {msg.list.map((item, i) => (
              <button
                key={i}
                className="list-item-btn"
                onClick={() => onOptionClick(`__pick__${item.title}`)}
              >
                <span className="list-num">{i + 1}</span>
                <span className="list-title">{item.title}</span>
                <span className="list-region">{item.region}</span>
              </button>
            ))}
          </div>
        )}
        {msg.suggestions && (
          <div className="list-options">
            {msg.suggestions.map((item, i) => (
              <button
                key={i}
                className="list-item-btn"
                onClick={() => onOptionClick(`__pick__${item.title}`)}
              >
                <span className="list-num">{i + 1}</span>
                <span className="list-title">{item.title}</span>
                <span className="list-region">{item.region}</span>
              </button>
            ))}
          </div>
        )}
        {msg.followup && (
          <div className="followup">
            {msg.followup.map((f) => (
              <button
                key={f.cmd}
                className="followup-btn"
                onClick={() => onOptionClick(f.cmd)}
              >
                {f.label}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

let msgId = 10;

export default function App() {
  const [messages, setMessages] = useState([WELCOME_MESSAGE]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingText, setLoadingText] = useState("Memproses...");
  const [flow, setFlow] = useState(null);
  const [flowStep, setFlowStep] = useState(0);
  const [flowData, setFlowData] = useState({});
  const [awaitingInvalid, setAwaitingInvalid] = useState(false);
  const bottomRef = useRef();
  const inputRef = useRef();
  const healthChecked = useRef(false);

  useEffect(() => {
    if (!loading) return;
    const steps = [
      "Memuat data resep...",
      "Menghitung profil rasa...",
      "Menganalisis preferensi wilayah...",
      "Menyusun rekomendasi adaptasi...",
    ];
    let i = 0;
    setLoadingText(steps[0]);
    const interval = setInterval(() => {
      i = (i + 1) % steps.length;
      setLoadingText(steps[i]);
    }, 2000);
    return () => clearInterval(interval);
  }, [loading]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const addMessage = (msg) => {
    setMessages((prev) => [...prev, { id: msgId++, ...msg }]);
  };

  const addUserMessage = (text) => {
    addMessage({ from: "user", text });
  };

  const addBotMessage = (props) => {
    addMessage({ from: "bot", ...props });
  };

  const resetFlow = () => {
    setFlow(null);
    setFlowStep(0);
    setFlowData({});
    setAwaitingInvalid(false);
  };

  const showMenu = () => {
    resetFlow();
    addBotMessage({
      type: "menu",
      text: "Pilih fitur:",
      options: WELCOME_MESSAGE.options,
    });
  };

  useEffect(() => {
    if (healthChecked.current) return;
    healthChecked.current = true;
    
    axios.get(`${API}/api/health`)
      .catch(() => {
        setMessages(prev => [{
          id: msgId++,
          from: "bot",
          type: "text",
          text: "Peringatan: server tidak dapat dijangkau.\n\nPastikan backend sudah berjalan sebelum menggunakan aplikasi.",
        }, ...prev]);
      });
  }, []);

const handleDownloadPDF = (text, recipeName) => {
    import("jspdf").then(({ jsPDF }) => {
      const doc = new jsPDF();
      
      const cleanText = text
        .replace(/→/g, '->')
        .replace(/—/g, '-')
        .replace(/←/g, '<-')
        .replace(/[^\x00-\x7F]/g, '')
        .replace(/\|/g, ' | ');

      const rawLines = cleanText.split('\n');
      let y = 15;
      doc.setFontSize(11);

      rawLines.forEach((rawLine) => {
        const line = rawLine.trim();
        if (!line) { y += 4; return; }

        // Tentukan apakah bold
        const isHeading = line === line.toUpperCase() && 
                          line.length > 3 && 
                          !/^[-\d]/.test(line);
        
        const isNotif = line.includes("Ditemukan") || 
                        line.includes("Menampilkan") ||
                        line.includes("tidak ditemukan") ||
                        line.includes("sudah sesuai");
        
        const hasDisesuaikan = line.includes("(disesuaikan)");

        if (y > 280) { doc.addPage(); y = 15; }

        if (isHeading || isNotif) {
          doc.setFont("helvetica", "bold");
          const wrapped = doc.splitTextToSize(line, 180);
          wrapped.forEach((l) => {
            if (y > 280) { doc.addPage(); y = 15; }
            doc.text(l, 15, y);
            y += 6;
          });
          doc.setFont("helvetica", "normal");
        } else if (hasDisesuaikan) {
          // Print bagian biasa dulu, lalu "(disesuaikan)" bold
          const parts = line.split("(disesuaikan)");
          const normalPart = parts[0];
          const boldPart = "(disesuaikan)";
          
          doc.setFont("helvetica", "normal");
          const normalWidth = doc.getTextWidth(normalPart);
          doc.text(normalPart, 15, y);
          doc.setFont("helvetica", "bold");
          doc.text(boldPart, 15 + normalWidth, y);
          doc.setFont("helvetica", "normal");
          y += 6;
        } else {
          doc.setFont("helvetica", "normal");
          const wrapped = doc.splitTextToSize(line, 180);
          wrapped.forEach((l) => {
            if (y > 280) { doc.addPage(); y = 15; }
            doc.text(l, 15, y);
            y += 6;
          });
        }
      });

      doc.save(`culinary-bridge-${recipeName || "resep"}.pdf`);
    });
  };

const executeFlow = async (currentFlow, data) => {
    setLoading(true);
    try {
      if (currentFlow === "/nama" || currentFlow === "/wilayah__pick") {
        // Cari detail lengkap resep
        const res = await axios.post(`${API}/api/cari/detail`, { query: data.query });
        if (!res.data.found) {
          addBotMessage({
            type: "text",
            text: `Resep "${data.query}" tidak ditemukan.\n\nCoba nama lain atau cek ejaan kamu.`,
            followup: [
              { label: "Cari lagi", cmd: "/nama" },
              { label: "Menu", cmd: "/menu" },
            ],
          });
        } else {
          addBotMessage({
            type: "output",
            text: res.data.output,
          });
          addBotMessage({
            type: "text",
            text: "Apa selanjutnya?",
            followup: [
              { label: `Adaptasi resep ini`, cmd: `__adaptasi__${res.data.title}` },
              { label: "Cari lagi", cmd: "/nama" },
              { label: "Menu", cmd: "/menu" },
            ],
          });
        }
} else if (currentFlow === "/wilayah") {
        const res = await axios.post(`${API}/api/cari/wilayah`, { region: data.region });
        if (!res.data.found) {
          addBotMessage({
            type: "text",
            text: `Tidak ada resep dari wilayah "${data.region}".`,
            followup: [
              { label: "Cari wilayah lain", cmd: "/wilayah" },
              { label: "Menu", cmd: "/menu" },
            ],
          });
        } else {
          const allResults = res.data.results;
          const shown = allResults.slice(0, 10);
          const hasMore = allResults.length > 10;
          addBotMessage({
            type: "text",
            text: `${allResults.length} resep dari ${res.data.region}. Menampilkan 10 pertama:`,
            list: shown,
            followup: hasMore ? [
              { label: `Lihat ${allResults.length - 10} resep lainnya`, cmd: `__more__${res.data.region}__10` },
            ] : [],
          });
          // Simpan semua hasil ke window untuk pagination
          window.__wilayahResults = allResults;
          window.__wilayahRegion = res.data.region;
        }
      } else if (currentFlow === "/adaptasi") {
        const res = await axios.post(`${API}/api/adaptasi`, {
          recipe_name: data.recipe_name,
          target_region: data.target_region,
        });
        const outputText = res.data.output;
        addBotMessage({
          type: "output",
          text: outputText,
          onDownload: () => handleDownloadPDF(outputText, data.recipe_name),
        });
        addBotMessage({
          type: "text",
          text: "Selesai. Apa selanjutnya?",
          followup: [
            { label: "Adaptasi lagi", cmd: "/adaptasi" },
            { label: "Cari resep", cmd: "/cari" },
            { label: "Menu", cmd: "/menu" },
          ],
        });
      } else if (currentFlow === "/custom") {
        const res = await axios.post(`${API}/api/custom`, {
          recipe_name: data.recipe_name,
          ingredients: data.ingredients,
          target_region: data.target_region,
        });
        const outputText = res.data.output;
        addBotMessage({
          type: "output",
          text: outputText,
          onDownload: () => handleDownloadPDF(outputText, data.recipe_name),
        });
        addBotMessage({
          type: "text",
          text: "Selesai. Apa selanjutnya?",
          followup: [
            { label: "Custom lagi", cmd: "/custom" },
            { label: "Cari resep", cmd: "/cari" },
            { label: "Menu", cmd: "/menu" },
          ],
        });
      }
    } catch (err) {
      const isNetworkError = !err.response;
      addBotMessage({
        type: "text",
        text: isNetworkError
          ? "Tidak dapat terhubung ke server.\n\nPastikan backend sudah berjalan, lalu coba lagi."
          : `Terjadi kesalahan: ${err.response?.data?.detail || "Unknown error"}.\n\nCoba lagi atau kembali ke menu.`,
        followup: [
          { label: "Coba lagi", cmd: "/lanjut" },
          { label: "Menu", cmd: "/menu" },
        ],
      });
    }
    setLoading(false);
    resetFlow();
  };

  const handleOptionClick = (cmd) => {
        if (cmd.startsWith("__more__")) {
      const parts = cmd.split("__");
      const region = parts[2];
      const offset = parseInt(parts[3]);
      const allResults = window.__wilayahResults || [];
      const nextBatch = allResults.slice(offset, offset + 10);
      const hasMore = allResults.length > offset + 10;
      
      addUserMessage(`Lihat lebih banyak`);
      addBotMessage({
        type: "text",
        text: `Resep ${offset + 1}–${offset + nextBatch.length} dari ${allResults.length}:`,
        list: nextBatch,
        followup: hasMore ? [
          { label: `Lihat ${allResults.length - offset - 10} resep lainnya`, cmd: `__more__${region}__${offset + 10}` },
        ] : [],
      });
      return;
    }
    
    if (cmd === "/menu") {
      addUserMessage("/menu");
      showMenu();
      return;
    }

    if (cmd === "/lanjut") {
      setAwaitingInvalid(false);
      addUserMessage("/lanjut");
      if (flow) {
        const steps = FLOWS[flow];
        addBotMessage({ type: "text", text: steps[flowStep].text });
      } else {
        showMenu();
      }
      return;
    }

    if (cmd === "/selesai") {
      addUserMessage("/selesai");
      addBotMessage({ type: "text", text: "Sampai jumpa! Ketik /menu untuk memulai lagi." });
      resetFlow();
      return;
    }

    if (cmd.startsWith("__adaptasi__")) {
      const recipeName = cmd.replace("__adaptasi__", "");
      addUserMessage(`/adaptasi ${recipeName}`);
      setFlow("/adaptasi");
      setFlowStep(1);
      setFlowData({ recipe_name: recipeName });
      addBotMessage({ type: "text", text: FLOWS["/adaptasi"][1].text });
      return;
    }

    if (cmd.startsWith("__pick__")) {
      const title = cmd.replace("__pick__", "");
      addUserMessage(title);
      if (flow === "/wilayah") {
        executeFlow("/wilayah__pick", { query: title });
      } else {
        executeFlow("/nama", { query: title });
      }
      return;
    }

    addUserMessage(cmd);

    if (FLOWS[cmd]) {
      setFlow(cmd);
      setFlowStep(0);
      addBotMessage({ type: "text", text: FLOWS[cmd][0].text, options: FLOWS[cmd][0].options });
      if (!FLOWS[cmd][0].options) setFlowStep(0);
      return;
    }

    if (cmd === "/cari") {
      setFlow("/cari");
      setFlowStep(0);
      addBotMessage({
        type: "text",
        text: FLOWS["/cari"][0].text,
        options: FLOWS["/cari"][0].options,
      });
    }
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");

    addUserMessage(text);

    // Handle global commands
    if (text === "/menu") { showMenu(); return; }
    if (text === "/selesai") {
      addBotMessage({ type: "text", text: "Sampai jumpa! Ketik /menu untuk memulai lagi." });
      resetFlow();
      return;
    }
    if (text === "/lanjut") {
      setAwaitingInvalid(false);
      if (flow) {
        addBotMessage({ type: "text", text: FLOWS[flow][flowStep].text });
      } else {
        showMenu();
      }
      return;
    }

    // Awaiting invalid resolution
    if (awaitingInvalid) {
      addBotMessage({
        type: "text",
        text: ` Input tidak dikenali: **"${text}"**\n\nKetik **/lanjut** untuk melanjutkan atau **/selesai** untuk berhenti.`,
        followup: [
          { label: "/lanjut", cmd: "/lanjut" },
          { label: "/selesai", cmd: "/selesai" },
        ],
      });
      return;
    }

    // In a flow
    if (flow && FLOWS[flow]) {
      const steps = FLOWS[flow];
      const currentStep = steps[flowStep];

      if (!currentStep) return;

      // If step has options (sub-menu), validate
      if (currentStep.options) {
        const validCmds = currentStep.options.map((o) => o.cmd);
        if (!validCmds.includes(text)) {
          setAwaitingInvalid(true);
          addBotMessage({
            type: "text",
            text: ` Input tidak dikenali: **"${text}"**\n\nContoh input yang valid:\n${validCmds.map((c) => `• ${c}`).join("\n")}\n\nLanjutkan atau sudahi?`,
            followup: [
              { label: "/lanjut", cmd: "/lanjut" },
              { label: "/selesai", cmd: "/selesai" },
            ],
          });
          return;
        }
        handleOptionClick(text);
        return;
      }

      // Collect data
      const newData = { ...flowData, [currentStep.key]: text };
      setFlowData(newData);

      const nextStep = flowStep + 1;
      if (nextStep < steps.length && !steps[nextStep].options) {
        setFlowStep(nextStep);
        addBotMessage({ type: "text", text: steps[nextStep].text });
      } else if (nextStep < steps.length && steps[nextStep].options) {
        setFlowStep(nextStep);
        addBotMessage({
          type: "text",
          text: steps[nextStep].text,
          options: steps[nextStep].options,
        });
      } else {
        // All steps done — execute
        setLoading(true);
        await executeFlow(flow, newData);
      }
      return;
    }

    // No active flow — check if valid command
    if (text.startsWith("/")) {
      const cmd = text.split(" ")[0];
      if (FLOWS[cmd]) {
        handleOptionClick(cmd);
        return;
      }
    }

    // Invalid input
    setAwaitingInvalid(true);
    addBotMessage({
      type: "text",
      text: ` Input tidak dikenali: **"${text}"**\n\nContoh input yang valid:\n• Ketik **/cari** untuk mencari resep\n• Ketik **/adaptasi** untuk adaptasi resep\n• Ketik **/custom** untuk resep buatanmu\n• Ketik **/menu** untuk melihat semua pilihan\n\nLanjutkan atau sudahi?`,
      followup: [
        { label: "/lanjut", cmd: "/lanjut" },
        { label: "/selesai", cmd: "/selesai" },
      ],
    });
  };

  return (
    <div className="app">
      <header className="header">
        <div className="header-inner">
          <h1 className="title">Culinary Bridge AI</h1>
          <p className="subtitle">Adaptasi Resep Lintas Wilayah • Mustika Rasa</p>
        </div>
      </header>

      <main className="chat-area">
        <div className="chat-inner">
          {messages.map((msg) =>
            msg.from === "user" ? (
              <div key={msg.id} className="message user">
                <div className="bubble user-bubble">{msg.text}</div>
              </div>
            ) : (
              <BotMessage key={msg.id} msg={msg} onOptionClick={handleOptionClick} />
            )
          )}
          {loading && (
            <div className="message bot">
              <div className="bubble bot-bubble loading-bubble">
                <div className="loading-dots">
                  <span />
                  <span />
                  <span />
                </div>
                <div className="loading-text">{loadingText}</div>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </main>

      <footer className="input-area">
        <div className="input-inner">
          <input
            ref={inputRef}
            className="input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="Ketik pesan atau command (/cari, /adaptasi, /custom)..."
            disabled={loading}
          />
          <button className="send-btn" onClick={handleSend} disabled={loading}>
            Kirim
          </button>
        </div>
      </footer>
    </div>
  );
}