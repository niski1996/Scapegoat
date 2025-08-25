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
    <!-- Header aplikacji -->
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
      <div class="container">
        <a class="navbar-brand" href="#">
          <i class="fas fa-database me-2"></i>
          {{ title }}
        </a>
        <div class="navbar-nav ms-auto">
          <span class="navbar-text">
            <i class="fas fa-circle text-success me-1"></i>
            System aktywny
          </span>
        </div>
      </div>
    </nav>

    <!-- Główna zawartość -->
    <div class="container-fluid mt-4">
      <div class="row">
        
        <!-- Panel sterowania -->
        <div class="col-lg-8">
          
          <!-- Sekcja generowania danych -->
          <div class="card mb-4">
            <div class="card-header bg-primary text-white">
              <h5 class="mb-0">
                <i class="fas fa-plus-circle me-2"></i>
                Generowanie danych
              </h5>
            </div>
            <div class="card-body">
              <form (ngSubmit)="generateData()" #generateForm="ngForm">
                <div class="row">
                  <div class="col-md-4 mb-3">
                    <label for="rows" class="form-label">Liczba wierszy</label>
                    <input 
                      type="number" 
                      class="form-control" 
                      id="rows"
                      [(ngModel)]="generateRequest.rows"
                      name="rows"
                      min="1"
                      max="1000000"
                      required>
                  </div>
                  <div class="col-md-4 mb-3">
                    <label for="columns" class="form-label">Liczba kolumn</label>
                    <input 
                      type="number" 
                      class="form-control" 
                      id="columns"
                      [(ngModel)]="generateRequest.columns"
                      name="columns"
                      min="1"
                      max="1000"
                      required>
                  </div>
                  <div class="col-md-4 mb-3">
                    <label for="filename" class="form-label">Nazwa pliku (opcjonalna)</label>
                    <input 
                      type="text" 
                      class="form-control" 
                      id="filename"
                      [(ngModel)]="generateRequest.filename"
                      name="filename"
                      placeholder="np. dane_testowe">
                  </div>
                </div>
                <button 
                  type="submit" 
                  class="btn btn-primary"
                  [disabled]="isGenerating || generateForm.invalid">
                  <span *ngIf="isGenerating" class="spinner-border spinner-border-sm me-2"></span>
                  <i *ngIf="!isGenerating" class="fas fa-play me-2"></i>
                  {{ isGenerating ? 'Generowanie...' : 'Generuj dane' }}
                </button>
              </form>
            </div>
          </div>

          <!-- Sekcja transformacji -->
          <div class="card mb-4">
            <div class="card-header bg-success text-white">
              <h5 class="mb-0">
                <i class="fas fa-cogs me-2"></i>
                Transformacja i pivotowanie
              </h5>
            </div>
            <div class="card-body">
              <form (ngSubmit)="transformData()" #transformForm="ngForm">
                <div class="row">
                  <div class="col-md-6 mb-3">
                    <label for="inputFile" class="form-label">Plik źródłowy</label>
                    <select 
                      class="form-select" 
                      id="inputFile"
                      [(ngModel)]="transformRequest.input_filename"
                      name="inputFile"
                      required>
                      <option value="">Wybierz plik...</option>
                      <option *ngFor="let file of availableFiles" [value]="file.filename">
                        {{ file.filename }} ({{ file.size_mb.toFixed(2) }} MB)
                      </option>
                    </select>
                  </div>
                  <div class="col-md-6 mb-3">
                    <label for="batchSize" class="form-label">Rozmiar batcha</label>
                    <input 
                      type="number" 
                      class="form-control" 
                      id="batchSize"
                      [(ngModel)]="transformRequest.batch_size"
                      name="batchSize"
                      min="1000"
                      max="100000"
                      required>
                  </div>
                </div>
                <button 
                  type="submit" 
                  class="btn btn-success"
                  [disabled]="isTransforming || transformForm.invalid">
                  <span *ngIf="isTransforming" class="spinner-border spinner-border-sm me-2"></span>
                  <i *ngIf="!isTransforming" class="fas fa-sync me-2"></i>
                  {{ isTransforming ? 'Transformowanie...' : 'Transformuj dane' }}
                </button>
              </form>
            </div>
          </div>

          <!-- Sekcja pobierania -->
          <div class="card mb-4">
            <div class="card-header bg-warning text-dark">
              <h5 class="mb-0">
                <i class="fas fa-download me-2"></i>
                Pobieranie danych
              </h5>
            </div>
            <div class="card-body">
              <form (ngSubmit)="downloadData()" #downloadForm="ngForm">
                <div class="row">
                  <div class="col-md-3 mb-3">
                    <label for="format" class="form-label">Format</label>
                    <select 
                      class="form-select" 
                      id="format"
                      [(ngModel)]="downloadRequest.format"
                      name="format"
                      required>
                      <option value="csv">CSV</option>
                      <option value="parquet">Parquet</option>
                      <option value="zip">ZIP</option>
                    </select>
                  </div>
                  <div class="col-md-3 mb-3">
                    <div class="form-check form-switch mt-4">
                      <input 
                        class="form-check-input" 
                        type="checkbox" 
                        id="pivoted"
                        [(ngModel)]="downloadRequest.pivoted"
                        name="pivoted">
                      <label class="form-check-label" for="pivoted">
                        Dane pivotowane
                      </label>
                    </div>
                  </div>
                  <div class="col-md-3 mb-3" *ngIf="!downloadRequest.pivoted">
                    <label for="downloadFile" class="form-label">Plik oryginalny</label>
                    <select 
                      class="form-select" 
                      id="downloadFile"
                      [(ngModel)]="downloadRequest.filename"
                      name="downloadFile">
                      <option value="">Najnowszy plik</option>
                      <option *ngFor="let file of availableFiles" [value]="file.filename">
                        {{ file.filename }}
                      </option>
                    </select>
                  </div>
                  <div class="col-md-3 mb-3" *ngIf="downloadRequest.pivoted">
                    <label for="batchDir" class="form-label">Katalog batchów</label>
                    <select 
                      class="form-select" 
                      id="batchDir"
                      [(ngModel)]="downloadRequest.batch_dir"
                      name="batchDir">
                      <option value="">Najnowszy katalog</option>
                      <option *ngFor="let batch of availableBatches" [value]="batch.directory">
                        {{ batch.directory }} ({{ batch.batch_count }} batchy)
                      </option>
                    </select>
                  </div>
                </div>
                <button 
                  type="submit" 
                  class="btn btn-warning text-dark"
                  [disabled]="isDownloading || downloadForm.invalid">
                  <span *ngIf="isDownloading" class="spinner-border spinner-border-sm me-2"></span>
                  <i *ngIf="!isDownloading" class="fas fa-download me-2"></i>
                  {{ isDownloading ? 'Pobieranie...' : 'Pobierz dane' }}
                </button>
              </form>
            </div>
          </div>

          <!-- Test prostego tekstu -->
          <div class="alert alert-info">
            <h4>Test komponentu Angular</h4>
            <p>Jeśli widzisz ten tekst, Angular działa poprawnie!</p>
            <p>Tytuł aplikacji: <strong>{{ title }}</strong></p>
            <p>Liczba dostępnych plików: {{ availableFiles.length }}</p>
          </div>

          <!-- Sekcja raportowania zadań -->
          <div class="card mb-4">
            <div class="card-header bg-dark text-white">
              <h5 class="mb-0">
                <i class="fas fa-chart-line me-2"></i>
                Raportowanie zadań
                <button class="btn btn-sm btn-outline-light float-end" (click)="toggleTaskReports()">
                  <i class="fas" [class.fa-eye]="!showTaskReports" [class.fa-eye-slash]="showTaskReports"></i>
                  {{ showTaskReports ? 'Ukryj' : 'Pokaż' }}
                </button>
              </h5>
            </div>
            <div class="card-body" *ngIf="showTaskReports">
              
              <!-- Przyciski akcji -->
              <div class="row mb-3">
                <div class="col-md-6 mb-2">
                  <button class="btn btn-primary w-100" (click)="loadTasks()">
                    <i class="fas fa-sync me-2"></i>
                    Odśwież zadania
                  </button>
                </div>
                <div class="col-md-6 mb-2">
                  <button class="btn btn-info w-100" (click)="loadOverlapAnalysis()">
                    <i class="fas fa-chart-bar me-2"></i>
                    Analiza nakładania
                  </button>
                </div>
              </div>

              <!-- Lista zadań -->
              <div class="mb-3" *ngIf="tasks.length > 0">
                <h6>Zadania ({{ tasks.length }})</h6>
                <div class="table-responsive" style="max-height: 300px; overflow-y: auto;">
                  <table class="table table-sm table-striped">
                    <thead class="table-dark">
                      <tr>
                        <th>Typ</th>
                        <th>Status</th>
                        <th>Czas [s]</th>
                        <th>Wiersze</th>
                        <th>Akcje</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr *ngFor="let task of tasks">
                        <td>
                          <span class="badge" 
                                [class.bg-primary]="task.task_type === 'generation'"
                                [class.bg-success]="task.task_type === 'transformation'"
                                [class.bg-warning]="task.task_type === 'download'">
                            {{ task.task_type }}
                          </span>
                        </td>
                        <td>
                          <span class="badge" 
                                [class.bg-success]="task.status === 'completed'"
                                [class.bg-danger]="task.status === 'failed'"
                                [class.bg-info]="task.status === 'in_progress'"
                                [class.bg-secondary]="task.status === 'started'">
                            {{ task.status }}
                          </span>
                        </td>
                        <td>{{ task.duration_seconds.toFixed(1) }}</td>
                        <td>{{ task.processed_rows.toLocaleString() }}</td>
                        <td>
                          <button class="btn btn-sm btn-outline-primary" 
                                  (click)="loadTaskReport(task.task_id)">
                            <i class="fas fa-file-alt"></i>
                          </button>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <!-- Raport wybranego zadania -->
              <div *ngIf="selectedTaskReport" class="mb-3">
                <h6>Raport zadania: {{ selectedTaskReport.task_id }}</h6>
                <div class="card">
                  <div class="card-body">
                    <pre class="text-sm" style="white-space: pre-wrap; font-size: 0.8rem; max-height: 400px; overflow-y: auto;">{{ selectedTaskReport.report_markdown }}</pre>
                  </div>
                </div>
              </div>

              <!-- Analiza nakładania -->
              <div *ngIf="overlapAnalysis" class="mb-3">
                <h6>Analiza nakładania zadań</h6>
                <div class="card">
                  <div class="card-body">
                    <pre class="text-sm" style="white-space: pre-wrap; font-size: 0.8rem; max-height: 400px; overflow-y: auto;">{{ overlapAnalysis }}</pre>
                  </div>
                </div>
              </div>

            </div>
          </div>

        </div>

        <!-- Panel informacyjny -->
        <div class="col-lg-4">
          
          <!-- Status systemu -->
          <div class="card mb-4" *ngIf="systemStatus">
            <div class="card-header bg-info text-white">
              <h6 class="mb-0">
                <i class="fas fa-info-circle me-2"></i>
                Status systemu
              </h6>
            </div>
            <div class="card-body">
              <div class="row text-center">
                <div class="col-6 mb-3">
                  <div class="h4 text-primary">{{ systemStatus.statistics.original_files_count }}</div>
                  <small class="text-muted">Pliki oryginalne</small>
                </div>
                <div class="col-6 mb-3">
                  <div class="h4 text-success">{{ systemStatus.statistics.batch_directories_count }}</div>
                  <small class="text-muted">Katalogi batchów</small>
                </div>
                <div class="col-12">
                  <div class="h5 text-warning">{{ systemStatus.statistics.total_size_mb.toFixed(2) }} MB</div>
                  <small class="text-muted">Całkowity rozmiar</small>
                </div>
              </div>
            </div>
          </div>

          <!-- Dostępne pliki -->
          <div class="card mb-4">
            <div class="card-header bg-secondary text-white">
              <h6 class="mb-0">
                <i class="fas fa-file me-2"></i>
                Dostępne pliki ({{ availableFiles.length }})
              </h6>
            </div>
            <div class="card-body" style="max-height: 300px; overflow-y: auto;">
              <div *ngIf="availableFiles.length === 0" class="text-muted text-center py-3">
                Brak dostępnych plików
              </div>
              <div *ngFor="let file of availableFiles" class="border-bottom pb-2 mb-2">
                <div class="fw-bold">{{ file.filename }}</div>
                <small class="text-muted">
                  {{ file.size_mb.toFixed(2) }} MB • 
                  {{ formatDate(file.modified) }}
                </small>
              </div>
            </div>
            <div class="card-footer">
              <button class="btn btn-sm btn-outline-secondary" (click)="refreshFiles()">
                <i class="fas fa-sync-alt me-1"></i>
                Odśwież
              </button>
            </div>
          </div>

          <!-- Katalogi batchów -->
          <div class="card mb-4">
            <div class="card-header bg-dark text-white">
              <h6 class="mb-0">
                <i class="fas fa-folder me-2"></i>
                Katalogi batchów ({{ availableBatches.length }})
              </h6>
            </div>
            <div class="card-body" style="max-height: 300px; overflow-y: auto;">
              <div *ngIf="availableBatches.length === 0" class="text-muted text-center py-3">
                Brak katalogów batchów
              </div>
              <div *ngFor="let batch of availableBatches" class="border-bottom pb-2 mb-2">
                <div class="fw-bold">{{ batch.directory }}</div>
                <small class="text-muted">
                  {{ batch.batch_count }} batchy • 
                  {{ batch.total_rows.toLocaleString() }} wierszy • 
                  {{ batch.total_size_mb.toFixed(2) }} MB
                </small>
              </div>
            </div>
          </div>

        </div>
      </div>

      <!-- Logi operacji -->
      <div class="row mt-4">
        <div class="col-12">
          <div class="card">
            <div class="card-header bg-light">
              <h6 class="mb-0">
                <i class="fas fa-list me-2"></i>
                Logi operacji
                <button class="btn btn-sm btn-outline-secondary float-end" (click)="clearLogs()">
                  <i class="fas fa-trash me-1"></i>
                  Wyczyść
                </button>
              </h6>
            </div>
            <div class="card-body" style="max-height: 200px; overflow-y: auto;">
              <div *ngIf="operationLogs.length === 0" class="text-muted text-center py-3">
                Brak logów operacji
              </div>
              <div *ngFor="let log of operationLogs" class="mb-2">
                <span class="badge me-2" 
                      [class.bg-success]="log.type === 'success'"
                      [class.bg-danger]="log.type === 'error'"
                      [class.bg-info]="log.type === 'info'">
                  {{ log.type.toUpperCase() }}
                </span>
                <small class="text-muted me-2">{{ formatTime(log.timestamp) }}</small>
                {{ log.message }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
  styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit {
  title = 'Kożucha Ofiarny';
  
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
    batch_dir: ''
  };
  
  // Dane systemu
  availableFiles: FileInfo[] = [];
  availableBatches: BatchInfo[] = [];
  systemStatus: SystemStatus | null = null;
  operationLogs: OperationLog[] = [];
  
  // Dane raportowania
  tasks: TaskSummary[] = [];
  selectedTaskReport: TaskReport | null = null;
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
      
      // Ustaw domyślnie najnowszy plik do transformacji
      if (this.availableFiles.length > 0 && !this.transformRequest.input_filename) {
        this.transformRequest.input_filename = this.availableFiles[0].filename;
      }
      
    } catch (error: any) {
      console.error('Błąd ładowania plików:', error);
      this.addLog('error', `Błąd ładowania listy plików: ${error.error?.detail || error.message}`);
    }
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
}
