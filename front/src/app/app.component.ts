import { Component, OnInit } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpClientModule } from '@angular/common/http';

// Interfejsy dla API
interface GenerateRequest {
  rows: number;
  columns: number;
  filename?: string;
}

interface TransformRequest {
  input_filename: string;
  batch_size: number;
}

interface DownloadRequest {
  format: string;
  pivoted: boolean;
  filename?: string;
  batch_dir?: string;
  // nowość: opcjonalna kolumna pivot
  pivot_column?: string;
}

interface FileInfo {
  filename: string;
  size_mb: number;
  modified: string;
}

interface BatchInfo {
  directory: string;
  batch_count: number;
  total_rows: number;
  total_size_mb: number;
  modified: string;
}

interface SystemStatus {
  status: string;
  timestamp: string;
  statistics: {
    original_files_count: number;
    batch_directories_count: number;
    data_directory_size_mb: number;
    batch_directory_size_mb: number;
    total_size_mb: number;
  };
}

interface TaskSummary {
  task_id: string;
  task_type: string;
  status: string;
  start_time: string;
  end_time?: string;
  duration_seconds: number;
  input_file?: string;
  output_file?: string;
  total_rows: number;
  processed_rows: number;
  events_count: number;
}

interface TaskReport {
  task_id: string;
  report_markdown: string;
  task_summary: {
    task_type: string;
    status: string;
    duration_seconds: number;
    total_rows: number;
    processed_rows: number;
  };
}

interface OperationLog {
  timestamp: Date;
  type: 'success' | 'error' | 'info';
  message: string;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, CommonModule, FormsModule, HttpClientModule],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit {
  title = 'Kożu Ofiarny';
  
  // URL backend API
  private apiUrl = 'http://localhost:8000';
  
  // Stany ładowania
  isGenerating = false;
  isTransforming = false;
  isDownloading = false;
  
  // Żądania API
  generateRequest: GenerateRequest = {
    rows: 10000,
    columns: 100,
    filename: ''
  };
  
  transformRequest: TransformRequest = {
    input_filename: '',
    batch_size: 50000
  };
  
  downloadRequest: DownloadRequest = {
    format: 'csv',
    pivoted: false,
    filename: '',
    batch_dir: '',
    pivot_column: ''
  };
  
  // Dane systemu
  availableFiles: FileInfo[] = [];
  availableBatches: BatchInfo[] = [];
  systemStatus: SystemStatus | null = null;
  operationLogs: OperationLog[] = [];
  
  // dostępne kolumny w wybranym pliku (do pivotu)
  availableColumns: string[] = [];
  
  // Dane raportowania
  tasks: TaskSummary[] = [];
  selectedTaskReport: TaskReport | null = null;
  allTaskReports: string[] = [];
  overlapAnalysis: string = '';
  showTaskReports = false;
  
  constructor(private http: HttpClient) {}
  
  ngOnInit() {
    this.refreshStatus();
    this.loadFiles();
  }
  
  /**
   * Dodaje log operacji
   */
  addLog(type: 'success' | 'error' | 'info', message: string) {
    this.operationLogs.push({
      timestamp: new Date(),
      type,
      message
    });
    
    // Zachowaj maksymalnie 50 logów
    if (this.operationLogs.length > 50) {
      this.operationLogs = this.operationLogs.slice(-50);
    }
  }
  
  /**
   * Generuje dane testowe
   */
  async generateData() {
    if (this.isGenerating) return;
    
    this.isGenerating = true;
    this.addLog('info', 'Rozpoczęcie generowania danych...');
    
    try {
      const response = await this.http.post<any>(`${this.apiUrl}/generate`, this.generateRequest).toPromise();
      
      this.addLog('success', `Dane wygenerowane: ${response.filename} (${response.file_info.num_rows} wierszy)`);
      
      // Jeśli otrzymaliśmy raport, wyświetl go
      if (response.report_markdown) {
        this.selectedTaskReport = {
          task_id: response.task_id,
          report_markdown: response.report_markdown,
          task_summary: {
            task_type: 'generation',
            status: 'completed',
            duration_seconds: 0,
            total_rows: response.file_info.num_rows,
            processed_rows: response.file_info.num_rows
          }
        };
        this.showTaskReports = true;
        this.addLog('info', `Raport zadania: ${response.task_id}`);
      }
      
      // Odśwież listę plików i zadań
      await this.loadFiles();
      if (this.showTaskReports) {
        await this.loadTasks();
      }
      
    } catch (error: any) {
      console.error('Błąd generowania danych:', error);
      this.addLog('error', `Błąd generowania: ${error.error?.detail || error.message}`);
      
      // Jeśli błąd zawiera raport, wyświetl go
      if (error.error?.report_markdown) {
        this.selectedTaskReport = {
          task_id: error.error.task_id,
          report_markdown: error.error.report_markdown,
          task_summary: {
            task_type: 'generation',
            status: 'failed',
            duration_seconds: 0,
            total_rows: 0,
            processed_rows: 0
          }
        };
        this.showTaskReports = true;
      }
    } finally {
      this.isGenerating = false;
    }
  }
  
  /**
   * Wykonuje pivotowanie i batchowanie
   */
  async transformData() {
    if (this.isTransforming) return;
    
    this.isTransforming = true;
    this.addLog('info', 'Rozpoczęcie transformacji danych...');
    
    try {
      const response = await this.http.post<any>(`${this.apiUrl}/transform`, this.transformRequest).toPromise();
      
      this.addLog('success', `Transformacja zakończona: ${response.batch_count} batchów utworzonych`);
      
      // Jeśli otrzymaliśmy raport, wyświetl go
      if (response.report_markdown) {
        this.selectedTaskReport = {
          task_id: response.task_id,
          report_markdown: response.report_markdown,
          task_summary: {
            task_type: 'transformation',
            status: 'completed',
            duration_seconds: 0,
            total_rows: response.batch_info.total_rows || 0,
            processed_rows: response.batch_info.total_rows || 0
          }
        };
        this.showTaskReports = true;
        this.addLog('info', `Raport zadania: ${response.task_id}`);
      }
      
      // Odśwież listę plików i zadań
      await this.loadFiles();
      if (this.showTaskReports) {
        await this.loadTasks();
      }
      
    } catch (error: any) {
      console.error('Błąd transformacji:', error);
      this.addLog('error', `Błąd transformacji: ${error.error?.detail || error.message}`);
      
      // Jeśli błąd zawiera raport, wyświetl go
      if (error.error?.report_markdown) {
        this.selectedTaskReport = {
          task_id: error.error.task_id,
          report_markdown: error.error.report_markdown,
          task_summary: {
            task_type: 'transformation',
            status: 'failed',
            duration_seconds: 0,
            total_rows: 0,
            processed_rows: 0
          }
        };
        this.showTaskReports = true;
      }
    } finally {
      this.isTransforming = false;
    }
  }
  
  /**
   * Pobiera dane
   */
  async downloadData() {
    if (this.isDownloading) return;
    
    this.isDownloading = true;
    this.addLog('info', 'Rozpoczęcie pobierania danych...');
    
    try {
      // Przygotowanie parametrów URL
      const params = new URLSearchParams();
      params.append('format', this.downloadRequest.format);
      params.append('pivoted', this.downloadRequest.pivoted.toString());
      
      if (this.downloadRequest.filename) {
        params.append('filename', this.downloadRequest.filename);
      }
      
      if (this.downloadRequest.batch_dir) {
        params.append('batch_dir', this.downloadRequest.batch_dir);
      }

      if (this.downloadRequest.pivoted && this.downloadRequest.pivot_column) {
        params.append('pivot_column', this.downloadRequest.pivot_column);
      }
      
      // Pobranie pliku
      const url = `${this.apiUrl}/download?${params.toString()}`;
      window.open(url, '_blank');
      
      this.addLog('success', `Pobieranie rozpoczęte: ${this.downloadRequest.format.toUpperCase()}`);
      
    } catch (error: any) {
      console.error('Błąd pobierania:', error);
      this.addLog('error', `Błąd pobierania: ${error.error?.detail || error.message}`);
    } finally {
      this.isDownloading = false;
    }
  }
  
  /**
   * Ładuje listę dostępnych plików i batchów
   */
  async loadFiles() {
    try {
      const response = await this.http.get<any>(`${this.apiUrl}/files`).toPromise();
      
      this.availableFiles = response.original_files || [];
      this.availableBatches = response.batch_directories || [];
      
      // Ustaw domyślnie najnowszy plik do transformacji i pobierania
      if (this.availableFiles.length > 0) {
        if (!this.transformRequest.input_filename) {
          this.transformRequest.input_filename = this.availableFiles[0].filename;
        }
        if (!this.downloadRequest.filename) {
          this.downloadRequest.filename = this.availableFiles[0].filename;
        }
        await this.loadColumns(this.downloadRequest.filename);
      }
      
    } catch (error: any) {
      console.error('Błąd ładowania plików:', error);
      this.addLog('error', `Błąd ładowania listy plików: ${error.error?.detail || error.message}`);
    }
  }

  async loadColumns(filename: string) {
    if (!filename) {
      this.availableColumns = [];
      return;
    }
    try {
      const response = await this.http.get<any>(`${this.apiUrl}/file-schema`, { params: { filename } }).toPromise();
      const cols: string[] = (response?.columns || []).map((c: any) => c.name || c);
      this.availableColumns = cols;
    } catch (error: any) {
      console.warn('Nie udało się pobrać schematu pliku:', error);
      this.availableColumns = [];
    }
  }

  onDownloadFileChange(filename: string) {
    this.downloadRequest.filename = filename;
    this.loadColumns(filename);
  }

  /**
   * Odświeża status systemu
   */
  async refreshStatus() {
    try {
      const response = await this.http.get<SystemStatus>(`${this.apiUrl}/status`).toPromise();
      this.systemStatus = response || null;
      
    } catch (error: any) {
      console.error('Błąd pobierania statusu:', error);
      this.addLog('error', `Błąd pobierania statusu: ${error.error?.detail || error.message}`);
    }
  }

  async loadSystemStatus() {
    try {
      const response = await this.http.get<SystemStatus>(`${this.apiUrl}/status`).toPromise();
      this.systemStatus = response || null;
      
    } catch (error) {
      console.error('Błąd ładowania statusu systemu:', error);
      this.addLog('error', 'Nie udało się załadować statusu systemu');
    }
  }

  /**
   * Odświeża listę plików
   */
  async refreshFiles() {
    await this.loadFiles();
    this.addLog('info', 'Lista plików odświeżona');
  }

  /**
   * Czyści logi operacji
   */
  clearLogs() {
    this.operationLogs = [];
    this.addLog('info', 'Logi wyczyszczone');
  }

  /**
   * Formatuje datę
   */
  formatDate(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleDateString('pl-PL') + ' ' + date.toLocaleTimeString('pl-PL');
  }

  /**
   * Formatuje czas
   */
  formatTime(date: Date): string {
    return date.toLocaleTimeString('pl-PL');
  }

  /**
   * Przełącza widoczność raportów zadań
   */
  toggleTaskReports() {
    this.showTaskReports = !this.showTaskReports;
    if (this.showTaskReports) {
      this.loadTasks();
    }
  }

  /**
   * Ładuje listę zadań
   */
  async loadTasks() {
    try {
      const response = await this.http.get<any>(`${this.apiUrl}/tasks`).toPromise();
      this.tasks = response.tasks || [];
      this.addLog('info', `Załadowano ${this.tasks.length} zadań`);
    } catch (error: any) {
      console.error('Błąd ładowania zadań:', error);
      this.addLog('error', `Błąd ładowania zadań: ${error.error?.detail || error.message}`);
    }
  }

  /**
   * Ładuje szczegółowy raport zadania
   */
  async loadTaskReport(taskId: string) {
    try {
      const response = await this.http.get<TaskReport>(`${this.apiUrl}/tasks/${taskId}/report`).toPromise();
      this.selectedTaskReport = response || null;
      this.addLog('info', `Załadowano raport zadania ${taskId}`);
    } catch (error: any) {
      console.error('Błąd ładowania raportu:', error);
      this.addLog('error', `Błąd ładowania raportu: ${error.error?.detail || error.message}`);
    }
  }

  /**
   * Ładuje analizę nakładania zadań
   */
  async loadOverlapAnalysis() {
    try {
      const response = await this.http.get<any>(`${this.apiUrl}/tasks/overlap-analysis`).toPromise();
      this.overlapAnalysis = response.overlap_analysis_markdown || '';
      this.addLog('info', 'Załadowano analizę nakładania zadań');
    } catch (error: any) {
      console.error('Błąd ładowania analizy:', error);
      this.addLog('error', `Błąd ładowania analizy: ${error.error?.detail || error.message}`);
    }
  }

  /**
   * Metody pomocnicze do nowego layoutu
   */
  getTaskTypeFromReport(report: string): string {
    if (report.includes('Generation Report') || report.includes('GENERATION')) return 'generation';
    if (report.includes('Transformation Report') || report.includes('TRANSFORMATION')) return 'transformation';
    if (report.includes('Download Report') || report.includes('DOWNLOAD')) return 'download';
    return 'unknown';
  }

  getTaskIdFromReport(report: string): string {
    const match = report.match(/Task ID: ([a-f0-9-]+)/);
    return match ? match[1] : 'unknown';
  }

  getShortFilename(filename: string): string {
    if (!filename || filename === '-') return '-';
    if (filename.length > 20) {
      return '...' + filename.slice(-17);
    }
    return filename;
  }

  async loadAllTaskReports() {
    try {
      await this.loadTasks();
      
      if (this.tasks.length === 0) {
        this.addLog('info', 'Brak zadań do wyświetlenia');
        return;
      }

      this.allTaskReports = [];
      
      for (const task of this.tasks) {
        try {
          const response = await this.http.get<any>(`${this.apiUrl}/tasks/${task.task_id}/report`).toPromise();
          if (response?.report_markdown) {
            this.allTaskReports.push(response.report_markdown);
          }
        } catch (error) {
          console.warn(`Nie można załadować raportu dla zadania ${task.task_id}:`, error);
        }
      }

      this.addLog('success', `Załadowano ${this.allTaskReports.length} raportów zadań`);
      
      // Wyczyść pojedynczy raport
      this.selectedTaskReport = null;
      
    } catch (error) {
      console.error('Błąd ładowania wszystkich raportów:', error);
      this.addLog('error', 'Nie udało się załadować wszystkich raportów zadań');
    }
  }

  async clearCompletedTasks() {
    try {
      const response = await this.http.delete<any>(`${this.apiUrl}/tasks`).toPromise();
      this.addLog('success', `Wyczyszczono ${response.cleared_tasks_count} ukończonych zadań`);
      
      // Odśwież zadania
      await this.loadTasks();
      
      // Wyczyść raporty
      this.allTaskReports = [];
      this.selectedTaskReport = null;
      this.overlapAnalysis = '';
      
    } catch (error) {
      console.error('Błąd czyszczenia zadań:', error);
      this.addLog('error', 'Nie udało się wyczyścić ukończonych zadań');
    }
  }
}
