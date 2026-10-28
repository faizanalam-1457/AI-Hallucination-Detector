import React, { useEffect, useState, useRef } from 'react';
import {
  FolderGit2,
  UploadCloud,
  FileText,
  Trash2,
  RefreshCw,
  Eye,
  AlertTriangle,
  CheckCircle2,
  File,
  X,
  Search,
} from 'lucide-react';
import { DocumentItem } from '../types';
import {
  deleteDocument,
  getDocumentPreview,
  getDocuments,
  reindexDocument,
  uploadDocument,
} from '../services/api';

export const DocumentLibrary: React.FC = () => {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Preview Modal
  const [previewDoc, setPreviewDoc] = useState<any | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadDocuments = async () => {
    try {
      setLoading(true);
      setError(null);
      const docs = await getDocuments();
      setDocuments(docs);
    } catch (err: any) {
      setError(err.message || 'Failed to load documents.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setError(null);
    setSuccessMsg(null);

    try {
      const doc = await uploadDocument(file);
      setSuccessMsg(`Successfully uploaded and indexed "${doc.filename}" (${doc.chunk_count} chunks).`);
      await loadDocuments();
    } catch (err: any) {
      setError(err.message || 'Failed to upload document.');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDelete = async (docId: string, filename: string) => {
    if (!confirm(`Are you sure you want to delete "${filename}" and its vector index chunks?`)) return;

    try {
      await deleteDocument(docId);
      setSuccessMsg(`Document "${filename}" deleted.`);
      await loadDocuments();
    } catch (err: any) {
      setError(err.message || 'Failed to delete document.');
    }
  };

  const handleReindex = async (docId: string) => {
    try {
      setSuccessMsg('Re-indexing document...');
      const res = await reindexDocument(docId);
      setSuccessMsg(`Re-indexed successfully. Generated ${res.chunk_count} chunks.`);
      await loadDocuments();
    } catch (err: any) {
      setError(err.message || 'Failed to re-index document.');
    }
  };

  const handleOpenPreview = async (docId: string) => {
    setPreviewLoading(true);
    setPreviewDoc(null);
    try {
      const preview = await getDocumentPreview(docId);
      setPreviewDoc(preview);
    } catch (err: any) {
      setError(err.message || 'Failed to load document preview.');
    } finally {
      setPreviewLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            Reference Document Library
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Ingest reference PDF and TXT corpora with PyMuPDF text extraction and page-level citation tracking.
          </p>
        </div>
        <div>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            accept=".pdf,.txt"
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium text-sm shadow-lg shadow-indigo-600/20 transition-all hover:scale-[1.02]"
          >
            <UploadCloud className="w-4 h-4" />
            <span>{uploading ? 'Processing File...' : 'Upload Document'}</span>
          </button>
        </div>
      </div>

      {/* Notifications */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{error}</span>
        </div>
      )}

      {successMsg && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-sm flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Drag & Drop Upload Zone */}
      <div
        onClick={() => fileInputRef.current?.click()}
        className="p-8 rounded-2xl border-2 border-dashed border-slate-800 hover:border-indigo-500/50 bg-slate-900/30 hover:bg-slate-900/60 transition-all cursor-pointer text-center space-y-3"
      >
        <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center mx-auto">
          <UploadCloud className="w-6 h-6" />
        </div>
        <div>
          <p className="text-sm font-semibold text-white">Click or drag file to upload</p>
          <p className="text-xs text-slate-400 mt-1">Supports PDF and TXT documents up to 25 MB</p>
        </div>
        <div className="flex items-center justify-center gap-4 text-[11px] text-slate-500 font-mono">
          <span>• PyMuPDF text parser</span>
          <span>• Sliding window chunking (150 words)</span>
          <span>• Page citations preserved</span>
        </div>
      </div>

      {/* Documents List */}
      <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-white">
            Indexed Documents ({documents.length})
          </h3>
          <span className="text-xs text-slate-400">Stored locally in ChromaDB & SQLite</span>
        </div>

        {loading ? (
          <div className="py-8 text-center text-sm text-slate-400">Loading document library...</div>
        ) : documents.length === 0 ? (
          <div className="py-8 text-center text-xs text-slate-400">
            No custom documents uploaded yet. Upload reference texts to ground verification.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 uppercase tracking-wider text-[11px]">
                  <th className="py-3 px-4">Filename</th>
                  <th className="py-3 px-4">Format</th>
                  <th className="py-3 px-4">Size</th>
                  <th className="py-3 px-4">Pages</th>
                  <th className="py-3 px-4">Chunks</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {documents.map((doc) => (
                  <tr key={doc.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 px-4 font-medium text-slate-200 flex items-center gap-2">
                      <FileText className="w-4 h-4 text-indigo-400 shrink-0" />
                      <span className="truncate max-w-xs">{doc.filename}</span>
                    </td>
                    <td className="py-3 px-4 uppercase font-mono text-[10px] text-slate-400">
                      {doc.file_type}
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-400">
                      {(doc.file_size_bytes / 1024).toFixed(1)} KB
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-300">{doc.page_count}</td>
                    <td className="py-3 px-4 font-mono text-indigo-400 font-semibold">{doc.chunk_count}</td>
                    <td className="py-3 px-4">
                      {doc.is_scanned_warning ? (
                        <span
                          title={doc.warning_message || 'Image-only PDF'}
                          className="px-2 py-0.5 rounded bg-amber-500/15 text-amber-400 border border-amber-500/30 font-medium text-[10px] flex items-center gap-1 w-fit"
                        >
                          <AlertTriangle className="w-3 h-3" />
                          Scanned / OCR Needed
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 font-medium text-[10px] flex items-center gap-1 w-fit">
                          <CheckCircle2 className="w-3 h-3" />
                          Indexed
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => handleOpenPreview(doc.id)}
                          title="Preview Text"
                          className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
                        >
                          <Eye className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleReindex(doc.id)}
                          title="Re-index Chunks"
                          className="p-1.5 rounded-lg text-slate-400 hover:text-indigo-400 hover:bg-slate-800 transition-colors"
                        >
                          <RefreshCw className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleDelete(doc.id, doc.filename)}
                          title="Delete Document"
                          className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-800 transition-colors"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Document Preview Modal */}
      {(previewDoc || previewLoading) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-3xl rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl overflow-hidden max-h-[85vh] flex flex-col">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-indigo-400" />
                <h3 className="text-sm font-semibold text-white">
                  {previewDoc?.filename || 'Loading Preview...'}
                </h3>
              </div>
              <button
                onClick={() => setPreviewDoc(null)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-4 text-xs">
              {previewLoading ? (
                <div className="py-12 text-center text-slate-400">Extracting document pages...</div>
              ) : previewDoc?.pages_preview?.length === 0 ? (
                <p className="text-slate-400 text-center py-6">No extracted text found on pages.</p>
              ) : (
                previewDoc?.pages_preview?.map((page: any, pI: number) => (
                  <div key={pI} className="p-4 rounded-xl bg-slate-950/70 border border-slate-800/80 space-y-2">
                    <div className="flex items-center justify-between text-slate-400 text-[11px] font-mono pb-1 border-b border-slate-800">
                      <span>Page {page.page_number}</span>
                      <span>{page.char_count} chars</span>
                    </div>
                    <pre className="whitespace-pre-wrap font-sans text-slate-300 leading-relaxed text-xs">
                      {page.text}
                    </pre>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
