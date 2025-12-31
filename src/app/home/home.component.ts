import { Component, OnInit, OnDestroy } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { interval, Subscription } from 'rxjs';

@Component({
  selector: 'app-home',
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.css']
})
export class HomeComponent implements OnInit, OnDestroy {
  logs = '';
  private pollSub?: Subscription;
  private backend = 'http://localhost:5000';

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    // start the python backend (idempotent)
    this.http.post(`${this.backend}/start`, {}).subscribe({});

    // poll logs every 2s
    this.pollSub = interval(2000).subscribe(() => {
      this.http.get(`${this.backend}/logs`, { responseType: 'text' }).subscribe(text => {
        this.logs = text;
      }, () => {});
    });
  }

  ngOnDestroy(): void {
    this.pollSub?.unsubscribe();
    // stop the backend when leaving
    this.http.post(`${this.backend}/stop`, {}).subscribe({});
  }

}
