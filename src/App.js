// import logo from './logo.svg';
// import './App.css';

// function App() {
//   return (
//     <div className="App">
//       <header className="App-header">
//         <img src={logo} className="App-logo" alt="logo" />
//         <p>
//           Edit <code>src/App.js</code> and save to reload.
//         </p>
//         <a
//           className="App-link"
//           href="https://reactjs.org"
//           target="_blank"
//           rel="noopener noreferrer"
//         >
//           Learn React
//         </a>
//       </header>
//     </div>
//   );
// }

// export default App;

// frontend/src/App.js

import React, { useState, useEffect } from 'react';
import './App.css'; // Anda bisa menambahkan styling di sini

function App() {
  // State untuk menyimpan pesan dari backend
  const [backendMessage, setBackendMessage] = useState('');

  // State untuk file yang dipilih dan deskripsi pekerjaan
  const [selectedFile, setSelectedFile] = useState(null);
  const [jobDescription, setJobDescription] = useState('');

  // State untuk menyimpan hasil analisis
  const [analysisResult, setAnalysisResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  // 1. Tes koneksi ke backend saat komponen pertama kali dimuat
  useEffect(() => {
    fetch('http://127.0.0.1:5000/api/test')
      .then(response => response.json())
      .then(data => {
        console.log(data); // Cek console browser
        setBackendMessage(data.message);
      })
      .catch(error => console.error("Error fetching test data:", error));
  }, []); // Array kosong berarti efek ini hanya berjalan sekali

  // 2. Fungsi untuk menangani submit form
  const handleSubmit = async (event) => {
    event.preventDefault(); // Mencegah form reload halaman
    if (!selectedFile) {
      alert("Silakan pilih file CV terlebih dahulu!");
      return;
    }

    setIsLoading(true);
    setAnalysisResult(null);

    const formData = new FormData();
    formData.append('cv', selectedFile);
    formData.append('jobDescription', jobDescription);

    try {
      const response = await fetch('http://127.0.0.1:5000/api/upload', {
        method: 'POST',
        body: formData,
      });

      const result = await response.json();

      if(response.ok) {
        setAnalysisResult(result);
      } else {
        alert(result.error || "Terjadi kesalahan pada server.");
      }

    } catch (error) {
      console.error("Error uploading file:", error);
      alert("Gagal terhubung ke server.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>🚀 Smart CV Analyzer & Optimizer</h1>
        <p style={{ fontSize: '0.8em', color: '#aaa' }}>
          Status Koneksi: <span style={{ color: 'lightgreen' }}>{backendMessage}</span>
        </p>

        <form onSubmit={handleSubmit} className="upload-form">
          <div className="form-group">
            <label htmlFor="job-desc">Deskripsi Pekerjaan Target</label>
            <textarea
              id="job-desc"
              placeholder="Tempel deskripsi pekerjaan di sini..."
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              rows="8"
            />
          </div>

          <div className="form-group">
            <label htmlFor="cv-file">Unggah CV Anda (PDF/DOCX)</label>
            <input
              id="cv-file"
              type="file"
              accept=".pdf,.docx"
              onChange={(e) => setSelectedFile(e.target.files[0])}
            />
          </div>

          <button type="submit" disabled={isLoading}>
            {isLoading ? 'Menganalisis...' : 'Analisis Sekarang'}
          </button>
        </form>

        {analysisResult && (
          <div className="result-card">
            <h3>Hasil Analisis</h3>
            <p><strong>Nama File:</strong> {selectedFile.name}</p>
            <p className="score"><strong>Skor Kecocokan:</strong> {analysisResult.score}%</p>
            <div className="recommendations">
              <strong>Rekomendasi:</strong>
              <p>{analysisResult.recommendations}</p>
            </div>
          </div>
        )}

      </header>
    </div>
  );
}

export default App;